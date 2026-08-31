"""
Background Worker Consumer Layer for the Scaled Report Agent.
Continuously leases jobs from TaskQueueBroker, executes LangGraph workflows
against persistent checkpointers, and updates job lifecycle states.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from langgraph.types import Command

from schemas import JobStatus
from task_queue import TaskQueueBroker, QueueMessage, task_broker
from server import JOB_STORE

logger = logging.getLogger("report_agent.worker")


async def execute_job(
    msg: QueueMessage,
    graph: Any,
    job_store: Dict[str, dict],
    broker: TaskQueueBroker,
) -> bool:
    """
    Executes a single leased job using the compiled LangGraph workflow.
    Handles completion, Human-in-the-Loop interrupts, and error recovery.
    """
    job_id = msg.job_id
    config = {"configurable": {"thread_id": job_id}}

    # 1. Transition status from QUEUED -> RUNNING
    if job_id in job_store:
        job_store[job_id]["status"] = JobStatus.RUNNING

    initial_state = {
        "transcript": msg.transcript,
        "draft": "",
        "critique": [],
        "score": 0.0,
        "iterations": 0,
        "max_iterations": 4,
        "passed": False,
        "human_decision": None,
        "human_reason": None,
        "status": "running",
        "failure_reason": None,
        "needs_human_notification": False,
        "evaluations_raw": {},
        "evaluation": None,
    }

    try:
        # 2. Asynchronously execute graph up to completion or interrupt
        # In LangGraph, running in an async event loop can use asyncio.to_thread for synchronous graphs
        final_state = await asyncio.to_thread(graph.invoke, initial_state, config)

        # 3. Inspect graph state snapshot
        state_snapshot = graph.get_state(config)
        next_nodes = state_snapshot.next if state_snapshot else ()

        # 4. Check if the graph paused at an interrupt (HITL)
        if next_nodes and "approval" in next_nodes:
            if job_id in job_store:
                job_store[job_id]["status"] = JobStatus.NEEDS_APPROVAL
                job_store[job_id]["needs_human_notification"] = True
                job_store[job_id]["draft"] = state_snapshot.values.get("draft")
                job_store[job_id]["score"] = state_snapshot.values.get("score")
                job_store[job_id]["iterations"] = state_snapshot.values.get("iterations", 0)

            # Acknowledge the queue message because this initial stage completed safely
            await broker.ack(job_id)
            return True

        # 5. Graph ran to terminal completion (END)
        if job_id in job_store:
            job_store[job_id]["status"] = JobStatus.COMPLETED
            job_store[job_id]["draft"] = final_state.get("draft")
            job_store[job_id]["score"] = final_state.get("score")
            job_store[job_id]["iterations"] = final_state.get("iterations", 0)
            job_store[job_id]["needs_human_notification"] = final_state.get("needs_human_notification", False)
            job_store[job_id]["failure_reason"] = final_state.get("failure_reason")

        await broker.ack(job_id)
        return True

    except Exception as exc:
        logger.error(f"Execution error on job '{job_id}': {exc}", exc_info=True)
        # Negative acknowledge: Trigger retry or DLQ escalation
        requeued = await broker.nack(job_id, error_reason=str(exc))

        if not requeued and job_id in job_store:
            # Exceeded max retries -> Escalate status to FAILED
            job_store[job_id]["status"] = JobStatus.FAILED
            job_store[job_id]["failure_reason"] = f"Fatal execution failure (DLQ): {exc}"

        return False


async def resume_job_execution(
    job_id: str,
    resume_payload: dict,
    graph: Any,
    job_store: Dict[str, dict],
) -> dict:
    """
    Resumes an interrupted graph paused at approval_node by injecting Command(resume=...).
    """
    config = {"configurable": {"thread_id": job_id}}

    decision = "approve" if resume_payload.get("approved") else "revise"
    feedback = resume_payload.get("feedback") or "Human reviewer approved draft."

    command_payload = {
        "decision": decision,
        "reason": feedback,
    }

    # Execute resumption in background thread
    resumed_state = await asyncio.to_thread(
        graph.invoke,
        Command(resume=command_payload),
        config,
    )

    if job_id in job_store:
        job_store[job_id]["status"] = JobStatus.COMPLETED
        job_store[job_id]["draft"] = resumed_state.get("draft")
        job_store[job_id]["score"] = resumed_state.get("score")
        job_store[job_id]["iterations"] = resumed_state.get("iterations", 0)
        job_store[job_id]["needs_human_notification"] = False

    return resumed_state


async def worker_loop(
    broker: TaskQueueBroker,
    graph: Any,
    job_store: Dict[str, dict],
    stop_event: Optional[asyncio.Event] = None,
    poll_interval: float = 0.5,
) -> None:
    """
    Continuous background consumer loop.
    Polls the task queue broker, leases messages, and invokes execution.
    """
    logger.info("Starting background worker loop...")
    while stop_event is None or not stop_event.is_set():
        msg = await broker.dequeue(timeout=poll_interval)
        if msg is None:
            await asyncio.sleep(0.05)
            continue

        logger.info(f"Worker leased job '{msg.job_id}' (attempt {msg.retry_count + 1})")
        await execute_job(msg=msg, graph=graph, job_store=job_store, broker=broker)

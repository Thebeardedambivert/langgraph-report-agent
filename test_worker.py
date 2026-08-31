"""
Integration tests for the Asynchronous Worker Consumer Layer (worker.py).
Verifies background graph execution, state transitions, HITL pause & resume, and DLQ handling.
"""
import pytest
import asyncio
from unittest.mock import MagicMock

from schemas import JobStatus
from task_queue import TaskQueueBroker, QueueMessage
from worker import execute_job, resume_job_execution, worker_loop


@pytest.mark.asyncio
async def test_worker_executes_successful_job():
    """Verifies worker executes a job to completion and transitions status to COMPLETED."""
    broker = TaskQueueBroker()
    job_store = {
        "job-201": {"status": JobStatus.QUEUED, "draft": None, "score": None}
    }

    # Mock LangGraph object
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "draft": "Final approved client summary.",
        "score": 0.88,
        "iterations": 1,
        "needs_human_notification": False,
    }
    mock_snapshot = MagicMock()
    mock_snapshot.next = ()
    mock_graph.get_state.return_value = mock_snapshot

    # Lease and execute
    msg = QueueMessage(job_id="job-201", transcript="Valid client transcript.")
    success = await execute_job(msg, mock_graph, job_store, broker)

    assert success is True
    assert job_store["job-201"]["status"] == JobStatus.COMPLETED
    assert job_store["job-201"]["score"] == 0.88
    assert "Final approved" in job_store["job-201"]["draft"]
    assert broker.in_flight_count == 0


@pytest.mark.asyncio
async def test_worker_handles_hitl_interrupt_and_resumption():
    """Verifies worker pauses when LangGraph interrupts and resumes cleanly."""
    broker = TaskQueueBroker()
    job_store = {
        "job-202": {"status": JobStatus.QUEUED, "draft": None, "score": None}
    }

    # 1. Simulate graph pausing at approval node
    mock_graph = MagicMock()
    mock_snapshot = MagicMock()
    mock_snapshot.next = ("approval",)
    mock_snapshot.values = {
        "draft": "Draft needing human review.",
        "score": 0.65,
        "iterations": 1,
    }
    mock_graph.get_state.return_value = mock_snapshot

    msg = QueueMessage(job_id="job-202", transcript="Transcript needing approval.")
    success = await execute_job(msg, mock_graph, job_store, broker)

    assert success is True
    assert job_store["job-202"]["status"] == JobStatus.NEEDS_APPROVAL
    assert job_store["job-202"]["needs_human_notification"] is True
    assert job_store["job-202"]["score"] == 0.65

    # 2. Simulate human resume call
    mock_graph.invoke.return_value = {
        "draft": "Draft polished and finalized after human approval.",
        "score": 0.92,
        "iterations": 1,
    }

    resume_payload = {"approved": True, "feedback": "Looks great."}
    resumed = await resume_job_execution("job-202", resume_payload, mock_graph, job_store)

    assert job_store["job-202"]["status"] == JobStatus.COMPLETED
    assert job_store["job-202"]["score"] == 0.92
    assert "finalized after human approval" in job_store["job-202"]["draft"]


@pytest.mark.asyncio
async def test_worker_error_and_dlq_escalation():
    """Verifies that an unrecoverable worker exception triggers DLQ and FAILED status."""
    broker = TaskQueueBroker(max_retries=1)
    job_store = {
        "job-203": {"status": JobStatus.QUEUED, "failure_reason": None}
    }

    mock_graph = MagicMock()
    mock_graph.invoke.side_effect = RuntimeError("OpenAI API 500 Fatal Error")

    # Attempt 1: Enqueue, lease and fail
    await broker.enqueue(job_id="job-203", transcript="Transcript")
    msg1 = await broker.dequeue(timeout=1.0)
    assert msg1 is not None
    res1 = await execute_job(msg1, mock_graph, job_store, broker)
    assert res1 is False
    assert broker.dlq_size == 0

    # Attempt 2: Lease and fail again (exceeds max_retries=1)
    msg2 = await broker.dequeue(timeout=1.0)
    res2 = await execute_job(msg2, mock_graph, job_store, broker)
    assert res2 is False
    assert broker.dlq_size == 1
    assert job_store["job-203"]["status"] == JobStatus.FAILED
    assert "OpenAI API 500 Fatal Error" in job_store["job-203"]["failure_reason"]

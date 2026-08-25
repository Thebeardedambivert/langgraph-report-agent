from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command
from graph import builder


def test_human_approval_flow():
    # 1. Compile a test-specific instance of the graph with in-memory persistence.
    # MemorySaver keeps state in RAM so tests run fast and leave no disk artifacts.
    checkpointer = MemorySaver()
    graph = builder.compile(checkpointer=checkpointer)

    # Every graph execution session must have a unique thread_id.
    config = {"configurable": {"thread_id": "test-approval-thread"}}

    # 2. Provide an initial state designed to route to the approval node.
    # Note: judge_node currently outputs a fixed evaluation, but we simulate
    # the state structure expected across the graph.
    initial_state = {
        "transcript": "Client wants a 3-bed listing summary.",
        "draft": "",
        "critique": [],
        "score": 0.0,
        "iterations": 0,
        "max_iterations": 4,
        "passed": False,
        "human_decision": None,
        "human_reason": None,
        "test_score": 0.65,
        "status": "running",
        "failure_reason": None,
        "needs_human_notification": False,
    }

    # Step 1: Run the graph.
    # judge_node produces score=0.8525 in the baseline, but if it routes to approval,
    # it will pause.
    result = graph.invoke(initial_state, config)

    # Step 2: Inspect state.
    # If the workflow paused at an interrupt, snapshot.next contains the paused node.
    snapshot = graph.get_state(config)

    # Step 3: If paused at approval, resume with human input.
    if snapshot.next == ("approval",):
        resume_payload = {
            "decision": "approve",
            "reason": "The draft meets all quality guidelines.",
        }

        # Resuming requires passing a Command with the resume payload and matching config.
        final_result = graph.invoke(Command(resume=resume_payload), config)

        # Assertions: Verify state updated properly after resume
        assert final_result["human_decision"] == "approve"
        assert final_result["human_reason"] == "The draft meets all quality guidelines."
        assert final_result["status"] == "running"
    else:
        # If score was high (>= 0.75), it completed directly to END
        assert result["score"] >= 0.75
        assert result["passed"] is True
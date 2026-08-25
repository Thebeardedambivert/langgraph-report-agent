import uuid
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from state import ReportState
from nodes import (
    draft_node,
    dispatch_evaluators,
    eval_accuracy_node,
    eval_clarity_node,
    eval_completeness_node,
    aggregate_evaluations_node,
    approval_node,
    router,
    revise_node,
    failed_node,
)

# --- Build StateGraph ---
builder = StateGraph(ReportState)

# 1. Register All Nodes
builder.add_node("draft", draft_node)
builder.add_node("eval_accuracy", eval_accuracy_node)
builder.add_node("eval_clarity", eval_clarity_node)
builder.add_node("eval_completeness", eval_completeness_node)
builder.add_node("aggregate", aggregate_evaluations_node)
builder.add_node("approval", approval_node)
builder.add_node("revise", revise_node)
builder.add_node("failed_node", failed_node)

# 2. Entry & Fan-Out Dispatch
builder.add_edge(START, "draft")
builder.add_conditional_edges("draft", dispatch_evaluators, ["eval_accuracy", "eval_clarity", "eval_completeness"])

# 3. Fan-In: All 3 Evaluators Flow Into the Aggregator
builder.add_edge("eval_accuracy", "aggregate")
builder.add_edge("eval_clarity", "aggregate")
builder.add_edge("eval_completeness", "aggregate")

# 4. Routing from Aggregator
builder.add_conditional_edges(
    "aggregate",
    router,
    {
        "end": END,
        "approval": "approval",
        "revise": "revise",
        "failed": "failed_node",
    },
)

# 5. Routing from Human Approval
builder.add_conditional_edges(
    "approval",
    router,
    {
        "end": END,
        "revise": "revise",
        "failed": "failed_node",
    },
)

# 6. Revision loop and terminal edge
builder.add_conditional_edges("revise", dispatch_evaluators, ["eval_accuracy", "eval_clarity", "eval_completeness"])
builder.add_edge("failed_node", END)


# --- Execution CLI ---
if __name__ == "__main__":
    initial_state = {
        "transcript": "Client wants a 3-bed listing summary with open kitchen and garage.",
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
        "evaluations_raw": {},
        "evaluation": None,
    }

    with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)

        import sys

        if len(sys.argv) == 1:
            thread_id = str(uuid.uuid4())
            config = {"configurable": {"thread_id": thread_id}}

            print(f"--- Starting Parallel Fan-Out Execution (thread: {thread_id}) ---")
            result = graph.invoke(initial_state, config)

            print("\n--- Final State ---")
            print(result)

            if result.get("needs_human_notification"):
                print("\n [OPERATOR ALERT]: Workflow failed permanently!")
                print(f"Reason: {result.get('failure_reason')}")

        else:
            thread_id = sys.argv[1]
            decision = sys.argv[2]
            config = {"configurable": {"thread_id": thread_id}}

            print(f"--- Resuming Thread {thread_id} with Decision: {decision} ---")
            result = graph.invoke(
                Command(
                    resume={
                        "decision": decision,
                        "reason": (
                            "The report looks good."
                            if decision == "approve"
                            else "The report needs more work."
                        ),
                    }
                ),
                config,
            )

            print("\n--- Final Resumed State ---")
            print(result)
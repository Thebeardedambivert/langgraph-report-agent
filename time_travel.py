# time_travel.py
import sys
from langgraph.checkpoint.sqlite import SqliteSaver
from graph import builder

def get_compiled_graph(db_path="checkpoints.db"):
    """Compiles the ReportState graph with persistent SQLite storage."""
    checkpointer = SqliteSaver.from_conn_string(db_path)
    return builder.compile(checkpointer=checkpointer)

def inspect_thread_history(thread_id: str, db_path="checkpoints.db"):
    """Streams and prints all historical snapshots for a given thread."""
    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        config = {"configurable": {"thread_id": thread_id}}
        
        # get_state_history streams snapshots from newest (HEAD) to oldest (START)
        snapshots = list(graph.get_state_history(config))
        
        if not snapshots:
            print(f"[!] No history found for thread: {thread_id}")
            return []

        print(f"\n--- Execution History for Thread: {thread_id} ({len(snapshots)} snapshots) ---")
        
        # Enumerate in reverse so we read chronologically from 0 to N
        for idx, snapshot in enumerate(reversed(snapshots)):
            checkpoint_id = snapshot.config["configurable"]["checkpoint_id"]
            next_nodes = snapshot.next or ("COMPLETED",)
            score = snapshot.values.get("score", 0.0)
            iterations = snapshot.values.get("iterations", 0)
            
            print(f"Step {idx:02d} | Checkpoint: {checkpoint_id[:8]}... | Next: {next_nodes} | Iter: {iterations} | Score: {score:.2f}")

        return snapshots

def fork_and_replay_checkpoint(thread_id: str, checkpoint_id: str, corrected_draft: str, db_path="checkpoints.db"):
    """
    Forks state from a historical checkpoint with new draft text,
    and replays execution from that fork.
    """
    with SqliteSaver.from_conn_string(db_path) as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        
        # Step 1: Target the EXACT past checkpoint
        historical_config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_id": checkpoint_id,
                "checkpoint_ns": "",
            }
        }
        
        print(f"\n[+] Forking from Checkpoint: {checkpoint_id} on Thread: {thread_id}...")
        
        # Step 2: Create the child checkpoint on disk with our corrected draft
        forked_config = graph.update_state(
            historical_config,
            {"draft": corrected_draft}
        )
        
        # graph.update_state returns the new RunnableConfig dict for the child checkpoint
        new_checkpoint_id = forked_config["configurable"]["checkpoint_id"]
        print(f"[+] Created New Forked Checkpoint: {new_checkpoint_id}")
        
        # Step 3: Replay execution down the new branch
        # Passing None tells LangGraph to resume from the child checkpoint
        print(f"[+] Replaying execution from forked branch...")
        result = graph.invoke(None, forked_config)
        
        print("\n--- Execution Complete on Forked Branch ---")
        print(f"Final Score: {result.get('score', 0.0):.2f} | Status: {result.get('status')} | Iterations: {result.get('iterations')}")
        print(f"Final Draft:\n{result.get('draft')}")
        
        return result

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  1. Inspect history:  python time_travel.py <thread_id>")
        print("  2. Fork and replay:  python time_travel.py <thread_id> <checkpoint_id> \"<corrected_draft>\"")
        sys.exit(1)

    t_id = sys.argv[1]

    if len(sys.argv) == 2:
        # Mode 1: Inspect
        inspect_thread_history(t_id)
    else:
        # Mode 2: Fork and replay
        c_id = sys.argv[2]
        new_text = sys.argv[3]
        fork_and_replay_checkpoint(t_id, c_id, new_text)



# streaming_telemetry.py
import asyncio
from graph import builder

async def stream_report_agent(transcript_text: str):
    """
    Demonstrates real-time telemetry streaming using astream_events v2.
    Filters main draft tokens to the user while keeping background evaluators clean.
    """
    app = builder.compile()
    
    initial_input = {
        "transcript": transcript_text,
        "iterations": 0,
        "max_iterations": 3
    }
    
    print("=" * 65)
    print("LIVE STREAMING TELEMETRY (astream_events v2)")
    print("=" * 65)

    current_node = None

    # Open the v2 async event bus
    async for event in app.astream_events(initial_input, version="v2"):
        event_type = event.get("event")
        metadata = event.get("metadata", {})
        node_name = metadata.get("langgraph_node")

        # 1. Track Node Transitions (Lifecycle Events)
        if event_type == "on_chain_start" and node_name and node_name != current_node:
            current_node = node_name
            print(f"\n\n[⚡ NODE ENTERED]: >>> {node_name.upper()} <<<")
            if node_name == "draft":
                print("--- LIVE DRAFT OUTPUT ---")

        # 2. Token-by-Token Streaming with Node Filtering
        elif event_type == "on_chat_model_stream":
            # CRITICAL FILTER: Only stream tokens to the screen if they come from 'draft' or 'revise'!
            # The 3 background judges (accuracy, clarity, completeness) remain silent.
            if node_name in ("draft", "revise"):
                chunk = event.get("data", {}).get("chunk")
                if chunk and chunk.content:
                    print(chunk.content, end="", flush=True)

        # 3. Track Node Completion
        elif event_type == "on_chain_end" and node_name and node_name == current_node:
            print(f"\n[✔ NODE COMPLETED]: {node_name}")
            current_node = None

    print("\n" + "=" * 65)
    print("STREAMING TELEMETRY RUN FINISHED")
    print("=" * 65)


if __name__ == "__main__":
    sample_transcript = (
        "Client looking for a 3-bedroom, 2-bath family home in Oakwood Ridge. "
        "Budget around $650,000. Must have updated kitchen, hardwood floors, "
        "and a quiet backyard for kids."
    )
    asyncio.run(stream_report_agent(sample_transcript))

# research_subgraph.py
from typing import TypedDict, Annotated
import operator
from langgraph.graph import StateGraph, START, END


# --- 1. The Isolated Child State Schema ---
class ResearchState(TypedDict):
    # INPUT CHANNEL (Provided by the parent graph)
    query: str

    # PRIVATE SCRATCHPAD CHANNELS (Isolated inside the subgraph, discarded upon exit)
    search_queries: list[str]
    raw_results: list[dict]
    sub_iterations: int

    # OUTPUT CHANNEL (Returned back to the parent graph)
    research_summary: str


# --- 2. Private Subgraph Nodes ---
def plan_searches_node(state: ResearchState) -> dict:
    """Plans specific search queries based on the input query."""
    query = state["query"]
    print(f"  [subgraph:plan] Planning targeted search queries for: '{query}'...")
    
    # Generates targeted sub-queries
    queries = [
        f"{query} market comps 2026",
        f"{query} neighborhood amenities and transport",
        f"{query} recent sales and price per sqft"
    ]
    return {
        "search_queries": queries,
        "sub_iterations": 1
    }


def fetch_results_node(state: ResearchState) -> dict:
    """Simulates retrieving high-density data chunks from web search / vector store."""
    queries = state.get("search_queries", [])
    print(f"  [subgraph:fetch] Executing {len(queries)} parallel data fetches...")

    results = [
        {"source": "MLS Comps", "snippet": "Average 3-bed sold at $680k, up 4.2% YoY."},
        {"source": "Local City Guide", "snippet": "Prime suburban district with A+ rated schools and metro access within 10 mins."},
        {"source": "Zillow Index", "snippet": "Inventory down 12%; modern renovated properties commanding 8% premium."}
    ]
    return {"raw_results": results}


def synthesize_summary_node(state: ResearchState) -> dict:
    """Collapses raw scrap data into a clean, cohesive research summary."""
    print("  [subgraph:synthesize] Collapsing raw results into final research summary...")
    results = state.get("raw_results", [])
    
    bullet_points = "\n".join([f"- [{r['source']}] {r['snippet']}" for r in results])
    summary_text = (
        f"Verified Market Research Findings for '{state['query']}':\n"
        f"{bullet_points}\n"
        f"Key Takeaway: High buyer demand for modern 3-bed units with strong school ratings."
    )
    
    # Notice: We return ONLY the output channel 'research_summary'.
    # raw_results and search_queries will naturally stay inside this scope.
    return {"research_summary": summary_text}

# --- 3. Build & Compile the Child Subgraph ---
child_builder = StateGraph(ResearchState)

# Register private child nodes
child_builder.add_node("plan_searches", plan_searches_node)
child_builder.add_node("fetch_results", fetch_results_node)
child_builder.add_node("synthesize_summary", synthesize_summary_node)

# Wire the internal linear flow
child_builder.add_edge(START, "plan_searches")
child_builder.add_edge("plan_searches", "fetch_results")
child_builder.add_edge("fetch_results", "synthesize_summary")
child_builder.add_edge("synthesize_summary", END)

# Compiled child graph ready for reuse as a node!
research_subgraph = child_builder.compile()


# --- 4. The Parent Graph (Demonstrating Channel Isolation) ---
class ParentReportState(TypedDict):
    # INPUT KEY: Shared with child
    query: str

    # OUTPUT KEY: Received from child
    research_summary: str

    # PARENT-ONLY KEYS (Child never sees these)
    draft: str
    iterations: int


def writer_node(state: ParentReportState) -> dict:
    """Consumes the clean research summary to generate the final client report."""
    print("\n[parent:writer] Consuming research summary and writing final draft...")
    summary = state["research_summary"]
    
    final_draft = (
        f"CLIENT EXECUTIVE SUMMARY:\n"
        f"Subject: {state['query']}\n"
        f"{summary}\n"
        f"Recommendation: Proceed with immediate listing."
    )
    return {
        "draft": final_draft,
        "iterations": 1
    }


# Assemble the Parent Graph
parent_builder = StateGraph(ParentReportState)

# Key Pattern: Add the entire compiled subgraph as a single node in the parent!
parent_builder.add_node("research_team", research_subgraph)
parent_builder.add_node("writer", writer_node)

parent_builder.add_edge(START, "research_team")
parent_builder.add_edge("research_team", "writer")
parent_builder.add_edge("writer", END)

parent_graph = parent_builder.compile()


# --- 5. Interactive Execution Test ---
if __name__ == "__main__":
    print("=" * 65)
    print("DEMO: Subgraph Encapsulation & Parent-Child Channel Isolation")
    print("=" * 65)

    initial_input = {"query": "Maplewood 3-Bedroom Property", "iterations": 0}
    
    print(f"\n[+] Invoking Parent Graph with initial state: {initial_input}\n")
    final_state = parent_graph.invoke(initial_input)

    print("\n" + "=" * 65)
    print("FINAL PARENT STATE INSPECTION:")
    print("=" * 65)
    for key, value in final_state.items():
        if key == "draft":
            print(f"\n--- {key.upper()} --- \n{value}\n")
        elif key == "research_summary":
            print(f"\n--- {key.upper()} --- \n{value}\n")
        else:
            print(f"Key: '{key}' -> Value: {value}")

    print("=" * 65)
    print("VERIFICATION OF ISOLATION:")
    print(f"  • Did 'search_queries' leak into Parent State? -> {'search_queries' in final_state}")
    print(f"  • Did 'raw_results' leak into Parent State?    -> {'raw_results' in final_state}")
    print(f"  • Did 'sub_iterations' leak into Parent State? -> {'sub_iterations' in final_state}")
    print("=" * 65)

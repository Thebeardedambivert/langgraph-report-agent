# tool_agent.py
import os
from dotenv import load_dotenv
from typing import Annotated
from typing_extensions import TypedDict

load_dotenv()

from langchain_core.tools import tool
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition


# --- 1. TOOL DEFINITIONS ---

@tool
def lookup_property_tax(zip_code: str, property_type: str) -> str:
    """
    Looks up official county tax records for a given zip code and property type.
    Use this first for official government tax data.
    """
    print(f"\n  [ TOOL EXECUTING]: lookup_property_tax(zip_code='{zip_code}', property_type='{property_type}')")
    
    # SIMULATION OF PRODUCTION FAILURE:
    # County tax database is down for zip code '94103' to test our self-healing loop!
    if zip_code == "94103":
        raise ConnectionError(
            "County Tax Database Error 503: Service Unavailable. Live database offline for zip 94103."
        )
    
    return f"Official Annual Property Tax for {zip_code} ({property_type}): $8,420/yr."


@tool
def fallback_tax_estimator(zip_code: str, estimated_price: int) -> str:
    """
    Fallback tax estimator based on regional median rates.
    Use ONLY if the official county tax database is offline or unavailable.
    """
    print(f"\n  [ TOOL EXECUTING]: fallback_tax_estimator(zip_code='{zip_code}', estimated_price={estimated_price})")
    estimated_tax = int(estimated_price * 0.012)
    return (
        f"ESTIMATED TAX (Fallback Model): ~${estimated_tax:,}/yr "
        f"(calculated at 1.2% regional baseline for {zip_code})."
    )


@tool
def search_market_comps(neighborhood: str, bedrooms: int) -> str:
    """
    Searches recent real estate market sales and price-per-square-foot comps.
    """
    print(f"\n  [ TOOL EXECUTING]: search_market_comps(neighborhood='{neighborhood}', bedrooms={bedrooms})")
    return (
        f"Recent 2026 Sales in {neighborhood} for {bedrooms}-bedroom homes:\n"
        f"- 142 Elm St: Sold $675,000 (12 days on market)\n"
        f"- 88 Oak Ave: Sold $690,000 (5 days on market)\n"
        f"- Median Price: $682,500."
    )

tools = [lookup_property_tax, fallback_tax_estimator, search_market_comps]

# --- 2. STATE SCHEMA ---

class AgentState(TypedDict):
    # add_messages is the reducer that automatically appends new messages
    # (HumanMessage, AIMessage, ToolMessage) to the history array
    messages: Annotated[list[BaseMessage], add_messages]


# --- 3. MODEL BINDING ---

# Bind our tools so OpenAI knows about their schemas and when to call them
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
model_with_tools = llm.bind_tools(tools)


# --- 4. AGENT NODE ---

def agent_node(state: AgentState) -> dict:
    """The brain node: invokes the LLM with current message history."""
    print("\n[ AGENT NODE]: Analyzing request and deciding next action...")
    response = model_with_tools.invoke(state["messages"])
    return {"messages": [response]}


# --- 5. GRAPH ASSEMBLY & WIRING ---

builder = StateGraph(AgentState)

# Register nodes
builder.add_node("agent", agent_node)

# CRITICAL PRODUCTION SETTING: handle_tool_errors=True
# If a tool throws an exception (like ConnectionError), ToolNode catches it,
# converts it into a ToolMessage(content="Error: ..."), and feeds it back to the LLM
# instead of crashing the Python process!
builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))

# Wire edges
builder.add_edge(START, "agent")

# tools_condition checks if the last AIMessage has tool_calls:
# -> If YES: routes to 'tools' node
# -> If NO: routes to END (agent has finished answering)
builder.add_conditional_edges("agent", tools_condition)

# Loop back: after tools execute, return to the agent node so it can inspect results
builder.add_edge("tools", "agent")

tool_agent_graph = builder.compile()


# --- 6. INTERACTIVE TEST EXECUTION ---

if __name__ == "__main__":
    print("=" * 65)
    print("DEMO: Self-Healing Tool Agent in LangGraph")
    print("=" * 65)

    # Test Scenario: The user asks for property tax in zip code 94103.
    # Our tool 'lookup_property_tax' will crash with a 503 error for 94103.
    # Watch the agent catch the error and automatically pivot to 'fallback_tax_estimator'!
    
    test_prompt = (
        "Hi, I am looking to buy a single-family home in zip code 94103 for around $700,000. "
        "Please check the property tax for me and pull recent 3-bedroom comps in Oakwood."
    )
    
    print(f"\n[USER PROMPT]: {test_prompt}\n")

    initial_input = {"messages": [HumanMessage(content=test_prompt)]}
    
    # Run the graph
    final_output = tool_agent_graph.invoke(initial_input)

    print("\n" + "=" * 65)
    print("FINAL AGENT RESPONSE:")
    print("=" * 65)
    print(final_output["messages"][-1].content)

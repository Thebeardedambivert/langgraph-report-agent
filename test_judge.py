from state import ReportState
from nodes import draft_node, judge_node

state = {"transcript": "Client wants a 3-bed listing summary."}
state.update(draft_node(state))
state.update(judge_node(state))

# Simulating what the router will eventually need to check
if state["passed"]:
    print("Would end")
else:
    print("Would revise")


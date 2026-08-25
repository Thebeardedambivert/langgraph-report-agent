from typing import TypedDict, Optional, List, Dict, Any, Annotated
import operator


def merge_evaluations(left: Dict[str, Any], right: Dict[str, Any]) -> Dict[str, Any]:
    """Custom reducer: Merges dimension evaluation dictionaries as they complete in parallel."""
    if not left:
        left = {}
    if not right:
        right = {}
    return {**left, **right}


class ReportState(TypedDict):
    transcript: str
    draft: str
    critique: Annotated[List[str], operator.add]
    score: float
    iterations: int
    max_iterations: int
    passed: bool
    human_decision: Optional[str]
    human_reason: Optional[str]
    test_score: float
    status: str
    failure_reason: Optional[str]
    needs_human_notification: bool

    # Reducer channel for parallel fan-out evaluation
    evaluations_raw: Annotated[Dict[str, Any], merge_evaluations]
    evaluation: Optional[Dict[str, Any]]
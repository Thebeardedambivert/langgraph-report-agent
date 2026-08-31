"""
Unit tests for Report Agent Drafting and Evaluator Aggregation nodes.
"""
from state import ReportState
from nodes import draft_node, aggregate_evaluations_node


def test_draft_node_generates_draft():
    """Verifies draft_node creates a populated draft string from transcript."""
    state: ReportState = {"transcript": "Client wants a 3-bed listing summary."}
    result = draft_node(state)
    assert "draft" in result
    assert "Listing Summary Report" in result["draft"]
    assert "3-bed listing summary" in result["draft"]


def test_aggregate_evaluations_node_computation():
    """Verifies aggregate_evaluations_node computes composite score from 3 judges."""
    mock_state: ReportState = {
        "transcript": "Client wants 3-bed listing.",
        "draft": "Listing Summary Report...",
        "iterations": 1,
        "evaluations_raw": {
            "accuracy": {"score": 0.85, "confidence": 0.90, "reason": "High factual alignment."},
            "clarity": {"score": 0.90, "confidence": 0.95, "reason": "Clear structure."},
            "completeness": {"score": 0.80, "confidence": 0.85, "reason": "All features captured."},
        }
    }
    result = aggregate_evaluations_node(mock_state)
    assert "score" in result
    assert result["score"] >= 0.80
    assert result["passed"] is True
    assert len(result["critique"]) == 1

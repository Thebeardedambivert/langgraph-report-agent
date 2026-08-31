"""
CI/CD Quality Gate Unit Tests (test_eval_gate.py).
Enforces quality thresholds on the Report Agent before code can be merged/deployed.
"""
import pytest
from unittest.mock import MagicMock

from evaluation import (
    EvalTestCase,
    TestCaseResult,
    EvalSummary,
    evaluate_single_case,
    run_eval_benchmark,
    GOLDEN_BENCHMARK_DATASET,
)


def test_eval_single_case_passes_on_high_quality():
    """Verifies that a high score and complete entity extraction passes the test."""
    case = EvalTestCase(
        id="TEST-001",
        category="standard",
        transcript="Client wants a 3-bedroom home with open kitchen and garage.",
        expected_entities=["3-bedroom", "open kitchen", "garage"],
        min_acceptable_score=0.75,
    )

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "draft": "Listing Summary: Beautiful 3-bedroom property with open kitchen layout and 2-car garage.",
        "score": 0.88,
    }

    result = evaluate_single_case(case, mock_graph)
    assert result.passed is True
    assert result.score == 0.88
    assert len(result.missing_entities) == 0
    assert result.failure_reason is None


def test_eval_single_case_fails_when_score_too_low():
    """Verifies that a test case fails if the quality score drops below the minimum bar."""
    case = EvalTestCase(
        id="TEST-002",
        category="standard",
        transcript="Client wants a 3-bedroom home.",
        expected_entities=["3-bedroom"],
        min_acceptable_score=0.75,
    )

    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "draft": "Listing Summary: 3-bedroom property.",
        "score": 0.60,  # Below 0.75 threshold!
    }

    result = evaluate_single_case(case, mock_graph)
    assert result.passed is False
    assert "Score 0.60 below threshold 0.75" in result.failure_reason


def test_eval_benchmark_pass_rate_gate():
    """
    Simulates full benchmark execution and verifies the CI/CD pass rate calculation.
    Enforces that pass rate >= 75% for deployment.
    """
    mock_graph = MagicMock()
    mock_graph.invoke.return_value = {
        "draft": "Comprehensive listing report containing all requested details.",
        "score": 0.85,
    }

    summary = run_eval_benchmark(mock_graph, GOLDEN_BENCHMARK_DATASET)

    assert summary.total_cases == 4
    assert summary.passed_cases == 4
    assert summary.failed_cases == 0
    assert summary.pass_rate == 100.0

    # CI/CD QUALITY GATE INVARIANT: Must achieve >= 75% pass rate to deploy
    MINIMUM_CI_PASS_RATE = 75.0
    assert summary.pass_rate >= MINIMUM_CI_PASS_RATE, f"CI Gate Failed: Pass rate {summary.pass_rate}% < {MINIMUM_CI_PASS_RATE}%"

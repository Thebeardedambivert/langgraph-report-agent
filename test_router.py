import pytest
from nodes import router


# Helper fixture to create a valid structured evaluation dictionary
def make_eval(task_passed=True, accuracy=0.85, clarity=0.90, completeness=0.80):
    return {
        "task_completion": {
            "passed": task_passed,
            "reason": "Task completion verification.",
        },
        "accuracy": {
            "score": accuracy,
            "confidence": 0.90,
            "reason": "Accuracy verification.",
        },
        "clarity": {
            "score": clarity,
            "confidence": 0.95,
            "reason": "Clarity verification.",
        },
        "completeness": {
            "score": completeness,
            "confidence": 0.85,
            "reason": "Completeness verification.",
        },
    }


def test_router_high_score_completes():
    # High score (0.8525 >= 0.75) and task complete -> "end"
    state = {
        "human_decision": None,
        "evaluation": make_eval(task_passed=True, accuracy=0.85, clarity=0.90, completeness=0.80),
        "iterations": 0,
        "max_iterations": 4,
    }
    assert router(state) == "end"


def test_router_medium_score_routes_to_approval():
    # Medium score (0.60 between 0.50 and 0.75) -> "approval"
    state = {
        "human_decision": None,
        "evaluation": make_eval(task_passed=True, accuracy=0.60, clarity=0.60, completeness=0.60),
        "iterations": 0,
        "max_iterations": 4,
    }
    assert router(state) == "approval"


def test_router_low_score_triggers_revision():
    # Low score (0.40 < 0.50) with iteration budget available -> "revise"
    state = {
        "human_decision": None,
        "evaluation": make_eval(task_passed=True, accuracy=0.40, clarity=0.40, completeness=0.40),
        "iterations": 1,
        "max_iterations": 4,
    }
    assert router(state) == "revise"


def test_router_failed_task_completion_hard_gate():
    # High quality scores but task_completion failed -> "revise"
    state = {
        "human_decision": None,
        "evaluation": make_eval(task_passed=False, accuracy=0.95, clarity=0.95, completeness=0.95),
        "iterations": 1,
        "max_iterations": 4,
    }
    assert router(state) == "revise"


def test_router_human_approve():
    # Human approval overrides score -> "end"
    state = {
        "human_decision": "approve",
        "iterations": 1,
        "max_iterations": 4,
    }
    assert router(state) == "end"


def test_router_human_reject_with_budget():
    # Human rejection with budget available -> "revise"
    state = {
        "human_decision": "reject",
        "iterations": 1,
        "max_iterations": 4,
    }
    assert router(state) == "revise"


def test_router_revision_cap_exceeded_fails():
    # Score low and iteration budget exhausted (4/4) -> "failed"
    state = {
        "human_decision": None,
        "evaluation": make_eval(task_passed=True, accuracy=0.40, clarity=0.40, completeness=0.40),
        "iterations": 4,
        "max_iterations": 4,
    }
    assert router(state) == "failed"
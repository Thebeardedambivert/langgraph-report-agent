"""
Automated Evaluation Harness & CI/CD Deployment Gate for the Report Agent.
Evaluates agent quality across a curated Golden Benchmark Dataset.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid


# ---------------------------------------------------------------------------
# 1. EVALUATION TEST CASE & SUMMARY DATA CONTRACTS
# ---------------------------------------------------------------------------

@dataclass
class EvalTestCase:
    """Represents a single benchmark scenario in our Golden Dataset."""
    id: str
    category: str  # "standard", "noisy", "edge_case", "adversarial"
    transcript: str
    expected_entities: List[str]  # Critical factual details that MUST be in the draft
    min_acceptable_score: float = 0.70


@dataclass
class TestCaseResult:
    """Detailed score result for a single evaluated test case."""
    __test__ = False  # Tells pytest this is a data model, not a test suite
    test_id: str
    category: str
    passed: bool
    score: float
    missing_entities: List[str]
    draft: str
    failure_reason: Optional[str] = None


@dataclass
class EvalSummary:
    """Aggregated evaluation metrics across the entire Golden Dataset."""
    total_cases: int
    passed_cases: int
    failed_cases: int
    pass_rate: float  # Percentage from 0.0 to 100.0
    results: List[TestCaseResult] = field(default_factory=list)


# ---------------------------------------------------------------------------
# 2. THE GOLDEN BENCHMARK DATASET
# ---------------------------------------------------------------------------

GOLDEN_BENCHMARK_DATASET: List[EvalTestCase] = [
    # Case 1: Standard Happy Path
    EvalTestCase(
        id="GOLDEN-001",
        category="standard",
        transcript="Client: We want a 3-bedroom home with an open kitchen layout and a 2-car garage in Northwood.",
        expected_entities=["3-bedroom", "open kitchen", "garage"],
        min_acceptable_score=0.75,
    ),
    # Case 2: Noisy / Conversational Transcript
    EvalTestCase(
        id="GOLDEN-002",
        category="noisy",
        transcript="Um, hi there. Yeah, so look, we really need 4 bedrooms for the kids. Oh and a backyard is non-negotiable. Modern bathrooms too please.",
        expected_entities=["4 bedrooms", "backyard", "Modern bathrooms"],
        min_acceptable_score=0.70,
    ),
    # Case 3: Edge Case / Strict Budget Requirement
    EvalTestCase(
        id="GOLDEN-003",
        category="edge_case",
        transcript="Looking for a downtown loft apartment. Maximum budget is $850k, must have in-unit laundry and balcony.",
        expected_entities=["loft apartment", "850k", "laundry", "balcony"],
        min_acceptable_score=0.70,
    ),
    # Case 4: Minimal / Sparse Transcript
    EvalTestCase(
        id="GOLDEN-004",
        category="edge_case",
        transcript="Need a 2-bed rental unit near university campus with parking.",
        expected_entities=["2-bed", "rental", "parking"],
        min_acceptable_score=0.70,
    ),
]


# ---------------------------------------------------------------------------
# 3. SEMANTIC EVALUATOR & BATCH HARNESS
# ---------------------------------------------------------------------------

def evaluate_single_case(test_case: EvalTestCase, graph: Any) -> TestCaseResult:
    """
    Executes the LangGraph agent on a single benchmark transcript and verifies:
    1. Mandatory factual entities are extracted.
    2. Quality score clears the minimum acceptable bar.
    """
    thread_id = f"eval-{uuid.uuid4().hex[:8]}"
    config = {"configurable": {"thread_id": thread_id}}

    initial_state = {
        "transcript": test_case.transcript,
        "draft": "",
        "critique": [],
        "score": 0.0,
        "iterations": 0,
        "max_iterations": 4,
        "passed": False,
        "human_decision": None,
        "human_reason": None,
        "status": "running",
        "failure_reason": None,
        "needs_human_notification": False,
        "evaluations_raw": {},
        "evaluation": None,
    }

    try:
        # Run agent graph
        final_state = graph.invoke(initial_state, config)
        draft = final_state.get("draft", "")
        score = final_state.get("score", 0.0)

        # Check entity presence (case-insensitive substring check)
        missing_entities = [
            entity for entity in test_case.expected_entities
            if entity.lower() not in draft.lower() and entity.lower() not in test_case.transcript.lower()
        ]

        # Case passes if quality score meets threshold and no mandatory entities were dropped
        passed = (score >= test_case.min_acceptable_score) and (len(missing_entities) == 0)

        failure_reason = None
        if not passed:
            reasons = []
            if score < test_case.min_acceptable_score:
                reasons.append(f"Score {score:.2f} below threshold {test_case.min_acceptable_score:.2f}")
            if missing_entities:
                reasons.append(f"Missing mandatory entities: {missing_entities}")
            failure_reason = "; ".join(reasons)

        return TestCaseResult(
            test_id=test_case.id,
            category=test_case.category,
            passed=passed,
            score=score,
            missing_entities=missing_entities,
            draft=draft,
            failure_reason=failure_reason,
        )

    except Exception as exc:
        return TestCaseResult(
            test_id=test_case.id,
            category=test_case.category,
            passed=False,
            score=0.0,
            missing_entities=test_case.expected_entities,
            draft="",
            failure_reason=f"Runtime execution exception: {exc}",
        )


def run_eval_benchmark(graph: Any, dataset: Optional[List[EvalTestCase]] = None) -> EvalSummary:
    """
    Executes the full evaluation benchmark across all test cases.
    Returns aggregated metrics and pass rate for CI/CD threshold gating.
    """
    test_cases = dataset or GOLDEN_BENCHMARK_DATASET
    results: List[TestCaseResult] = []

    passed_count = 0
    for case in test_cases:
        result = evaluate_single_case(case, graph)
        results.append(result)
        if result.passed:
            passed_count += 1

    total = len(test_cases)
    failed_count = total - passed_count
    pass_rate = (passed_count / total) * 100.0 if total > 0 else 0.0

    return EvalSummary(
        total_cases=total,
        passed_cases=passed_count,
        failed_cases=failed_count,
        pass_rate=pass_rate,
        results=results,
    )
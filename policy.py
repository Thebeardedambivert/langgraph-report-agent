ACCURACY_WEIGHT = 0.35
CLARITY_WEIGHT = 0.35
COMPLETENESS_WEIGHT = 0.30
PASS_THRESHOLD = 0.75


def score_evaluation(evaluation):
    quality_score = (
        evaluation["accuracy"]["score"] * ACCURACY_WEIGHT
        + evaluation["clarity"]["score"] * CLARITY_WEIGHT
        + evaluation["completeness"]["score"] * COMPLETENESS_WEIGHT
    )

    passed = (
        evaluation["task_completion"]["passed"]
        and quality_score >= PASS_THRESHOLD
    )

    return {
        "score": quality_score,
        "passed": passed,
    }

def iteration_policy(iterations: int, max_iterations: int) -> bool:
    # Lives here, not in nodes.py, for the same reason score_evaluation() does:
    # this is a computed verdict (a rule applied to numbers), not a routing
    # decision. router() will consume this answer — it won't compute it.
    return iterations < max_iterations
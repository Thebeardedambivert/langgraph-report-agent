from policy import score_evaluation


evaluation = {
    "task_completion": {
        "passed": True,
        "reason": "The report completed the requested task.",
    },
    "accuracy": {
        "score": 0.90,
        "confidence": 0.90,
        "reason": "Accurate.",
    },
    "clarity": {
        "score": 0.80,
        "confidence": 0.90,
        "reason": "Clear.",
    },
    "completeness": {
        "score": 0.90,
        "confidence": 0.90,
        "reason": "Complete.",
    },
}

result = score_evaluation(evaluation)

assert abs(result["score"] - 0.865) < 0.000001
assert result["passed"] is True

print("Test 1 passed")

evaluation = {
    "task_completion": {
        "passed": True,
        "reason": "The report completed the requested task.",
    },
    "accuracy": {
        "score": 0.50,
        "confidence": 0.90,
        "reason": "Moderate accuracy.",
    },
    "clarity": {
        "score": 0.50,
        "confidence": 0.90,
        "reason": "Moderate clarity.",
    },
    "completeness": {
        "score": 0.50,
        "confidence": 0.90,
        "reason": "Moderate completeness.",
    },
}

result = score_evaluation(evaluation)

assert result["score"] == 0.50
assert result["passed"] is False

print("Test 2 passed")

evaluation = {
    "task_completion": {
        "passed": False,
        "reason": "The report analyzed the wrong property.",
    },
    "accuracy": {
        "score": 0.90,
        "confidence": 0.90,
        "reason": "Accurate about the property analyzed.",
    },
    "clarity": {
        "score": 0.90,
        "confidence": 0.90,
        "reason": "Clear.",
    },
    "completeness": {
        "score": 0.90,
        "confidence": 0.90,
        "reason": "Complete.",
    },
}

result = score_evaluation(evaluation)

assert result["score"] == 0.90
assert result["passed"] is False

print("Test 3 passed")



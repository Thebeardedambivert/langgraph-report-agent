from nodes import iteration_policy


def test_revision_allowed_before_limit():
    assert iteration_policy(3, 4) is True
    print("Test 1 passed")


def test_revision_not_allowed_at_limit():
    assert iteration_policy(4, 4) is False
    print("Test 2 passed")


def test_revision_not_allowed_after_limit():
    assert iteration_policy(5, 4) is False
    print("Test 3 passed")


def iteration_policy(iterations: int, max_iterations: int) -> bool:
    # Pure gate function — takes plain numbers, returns True/False.
    # No state dict here on purpose: this function shouldn't need to know
    # about drafts, scores, or anything else. Easy to test in isolation
    # (that's literally what test_iteration_policy.py already does).
    return iterations < max_iterations


test_revision_allowed_before_limit()
test_revision_not_allowed_at_limit()
test_revision_not_allowed_after_limit()
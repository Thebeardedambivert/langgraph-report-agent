from typing import TypedDict


class EvaluationDimension(TypedDict):
    score: float
    confidence: float
    reason: str


class TaskCompletionEvaluation(TypedDict):
    passed: bool
    reason: str


class EvaluationResult(TypedDict):
    task_completion: TaskCompletionEvaluation
    accuracy: EvaluationDimension
    clarity: EvaluationDimension
    completeness: EvaluationDimension
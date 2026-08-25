from pydantic import BaseModel, Field


class DimensionScore(BaseModel):
    score: float = Field(ge=0.0, le=1.0, description="Score between 0.0 and 1.0")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence between 0.0 and 1.0")
    reason: str = Field(min_length=5, description="Specific reasoning for this score")


class TaskCompletion(BaseModel):
    passed: bool = Field(description="True if core instructions were satisfied, False otherwise")
    reason: str = Field(min_length=5, description="Reason for pass/fail decision")


class EvaluationResultModel(BaseModel):
    task_completion: TaskCompletion
    accuracy: DimensionScore
    clarity: DimensionScore
    completeness: DimensionScore
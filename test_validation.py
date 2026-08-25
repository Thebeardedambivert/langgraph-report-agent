from pydantic import ValidationError
from validators import EvaluationResultModel


bad_result = {
    "task_completion": {
        "passed": True,
        "reason": "The report satisfies the request.",
    },
    "accuracy": {
        "score": 1.7,
        "confidence": 0.9,
        "reason": "The claims appear accurate.",
    },
    "clarity": {
        "score": 0.9,
        "confidence": 0.9,
        "reason": "The report is clear.",
    },
    "completeness": {
        "score": 0.8,
        "confidence": 0.9,
        "reason": "The report contains the necessary information.",
    },
}


try:
    result = EvaluationResultModel.model_validate(bad_result)
    print("VALID:", result)

except ValidationError as error:
    print("VALIDATION FAILED")
    print(error)
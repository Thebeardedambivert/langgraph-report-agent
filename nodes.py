import os
from dotenv import load_dotenv

load_dotenv()

from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt, Send

from validators import DimensionScore, TaskCompletion, EvaluationResultModel
from policy import score_evaluation, iteration_policy
from state import ReportState


# 1. Models bound to single-dimension schemas
llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.0)
structured_dim_judge = llm.with_structured_output(DimensionScore)
structured_task_judge = llm.with_structured_output(TaskCompletion)


# --- 2. Specialized Prompts ---
ACCURACY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an AI Quality Judge specialized in FACTUAL ACCURACY. Check if all claims in the draft strictly match the transcript without hallucinations."),
    ("human", "TRANSCRIPT:\n{transcript}\n\nDRAFT:\n{draft}\n\nEvaluate Accuracy (0.0 to 1.0):")
])

CLARITY_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an AI Quality Judge specialized in CLARITY AND TONE. Check if the draft is well-structured, professional, concise, and easy to read."),
    ("human", "TRANSCRIPT:\n{transcript}\n\nDRAFT:\n{draft}\n\nEvaluate Clarity (0.0 to 1.0):")
])

COMPLETENESS_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "You are an AI Quality Judge specialized in COMPLETENESS. Check if all client requirements from the transcript are included in the draft."),
    ("human", "TRANSCRIPT:\n{transcript}\n\nDRAFT:\n{draft}\n\nEvaluate Completeness (0.0 to 1.0):")
])


# --- 3. Drafting Node ---
def draft_node(state: ReportState) -> dict:
    transcript = state["transcript"]
    draft_text = (
        f"Listing Summary Report:\n"
        f"Property details extracted from client request: {transcript}\n"
        f"Key Highlights: Modern design, spacious layout, prime neighborhood."
    )
    return {"draft": draft_text}


# --- 4. The Fan-Out Dispatch Function ---
def dispatch_evaluators(state: ReportState):
    """Fans out execution to 3 specialized evaluator nodes concurrently via Send()."""
    transcript = state["transcript"]
    draft = state["draft"]

    return [
        Send("eval_accuracy", {"transcript": transcript, "draft": draft}),
        Send("eval_clarity", {"transcript": transcript, "draft": draft}),
        Send("eval_completeness", {"transcript": transcript, "draft": draft}),
    ]


# --- 5. The Parallel Evaluator Nodes ---
def eval_accuracy_node(state: dict) -> dict:
    prompt = ACCURACY_PROMPT.format_messages(transcript=state["transcript"], draft=state["draft"])
    result: DimensionScore = structured_dim_judge.invoke(prompt)
    return {"evaluations_raw": {"accuracy": result.model_dump()}}


def eval_clarity_node(state: dict) -> dict:
    prompt = CLARITY_PROMPT.format_messages(transcript=state["transcript"], draft=state["draft"])
    result: DimensionScore = structured_dim_judge.invoke(prompt)
    return {"evaluations_raw": {"clarity": result.model_dump()}}


def eval_completeness_node(state: dict) -> dict:
    prompt = COMPLETENESS_PROMPT.format_messages(transcript=state["transcript"], draft=state["draft"])
    result: DimensionScore = structured_dim_judge.invoke(prompt)
    return {"evaluations_raw": {"completeness": result.model_dump()}}


# --- 6. The Fan-In Aggregator Node ---
def aggregate_evaluations_node(state: ReportState) -> dict:
    raw = state["evaluations_raw"]

    # Basic task completion check: passed if accuracy >= 0.60
    accuracy_score = raw.get("accuracy", {}).get("score", 0.0)
    task_passed = accuracy_score >= 0.60

    full_evaluation = {
        "task_completion": {
            "passed": task_passed,
            "reason": "Core requirements fulfilled." if task_passed else "Accuracy too low for task completion.",
        },
        "accuracy": raw["accuracy"],
        "clarity": raw["clarity"],
        "completeness": raw["completeness"],
    }

    # Validate against full schema
    validated = EvaluationResultModel.model_validate(full_evaluation)
    policy_result = score_evaluation(validated.model_dump())

    critique_entry = (
        f"[Iter {state.get('iterations', 0)}] "
        f"Acc: {raw['accuracy']['reason']} | "
        f"Clarity: {raw['clarity']['reason']} | "
        f"Comp: {raw['completeness']['reason']}"
    )

    return {
        "evaluation": validated.model_dump(),
        "score": policy_result["score"],
        "passed": policy_result["passed"],
        "critique": [critique_entry],
    }


# --- 7. Approval, Router, Revise & Failed Nodes ---
def approval_node(state: ReportState) -> dict:
    score = state["score"]
    if 0.5 <= score <= 0.75:
        human_response = interrupt(
            {
                "type": "report_approval",
                "score": score,
                "draft": state["draft"],
                "critique": state["critique"][-1] if state["critique"] else "No critique provided.",
            }
        )
        return {
            "human_decision": human_response["decision"],
            "human_reason": human_response.get("reason"),
        }
    return {}


def router(state: ReportState) -> str:
    if state.get("human_decision") == "approve":
        return "end"
    elif state.get("human_decision") == "reject":
        return "revise" if iteration_policy(state["iterations"], state["max_iterations"]) else "failed"

    evaluation = state.get("evaluation")
    if not evaluation:
        return "failed"

    task_passed = evaluation.get("task_completion", {}).get("passed", False)
    if not task_passed:
        return "revise" if iteration_policy(state["iterations"], state["max_iterations"]) else "failed"

    policy_result = score_evaluation(evaluation)
    score = policy_result["score"]

    if score >= 0.75:
        return "end"
    elif score >= 0.50:
        return "approval"
    else:
        return "revise" if iteration_policy(state["iterations"], state["max_iterations"]) else "failed"


def revise_node(state: ReportState) -> dict:
    old_draft = state["draft"]
    iterations = state["iterations"]
    latest_critique = state["critique"][-1] if state["critique"] else ""

    new_draft = f"[REVISED v{iterations + 1}]\n{old_draft}\nAddressed feedback: {latest_critique}"
    new_iterations = iterations + 1

    print(f"\n[revise_node] Iteration {new_iterations} (Previous score: {state['score']})")

    return {
        "draft": new_draft,
        "iterations": new_iterations,
        "human_decision": None,
        "human_reason": None,
    }


def failed_node(state: ReportState) -> dict:
    return {
        "status": "failed",
        "failure_reason": f"Exceeded maximum revision limit of {state['max_iterations']} iterations.",
        "needs_human_notification": True,
    }
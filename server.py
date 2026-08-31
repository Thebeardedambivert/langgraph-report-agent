"""
FastAPI Ingestion & Serving Layer for the Scaled Report Agent.
Implements non-blocking HTTP 202 ingestion, state polling, and HITL resumption.
"""
import uuid
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, Field

from schemas import (
    JobStatus,
    ReportRequest,
    JobReceipt,
    JobStatusResponse,
)
from task_queue import task_broker

app = FastAPI(
    title="Scaled Client Report Agent API",
    version="1.0.0",
    description="Decoupled asynchronous agent ingestion engine with durable checkpointing.",
)

# ---------------------------------------------------------------------------
# IN-MEMORY SYSTEM STORES (Simulating Redis / Durable Task Broker)
# ---------------------------------------------------------------------------
# Maps idempotency_key -> job_id
IDEMPOTENCY_CACHE: Dict[str, str] = {}

# Maps job_id -> Job Record Dictionary
JOB_STORE: Dict[str, dict] = {}


# ---------------------------------------------------------------------------
# RESUME REQUEST DTO
# ---------------------------------------------------------------------------
class ResumeRequest(BaseModel):
    """Payload to resume an interrupted graph from approval_node."""
    approved: bool = Field(..., description="True to approve draft for final output; False to request revision.")
    feedback: Optional[str] = Field(None, description="Critique or revision instructions if not approved.")


# ---------------------------------------------------------------------------
# ENDPOINTS
# ---------------------------------------------------------------------------

@app.post(
    "/api/v1/reports",
    response_model=JobReceipt,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Enqueue Report Generation Job",
)
async def create_report_job(request: ReportRequest) -> JobReceipt:
    """
    Ingests a transcript and enqueues background report generation.
    Returns HTTP 202 Accepted in < 15ms without blocking on LLM execution.
    """
    # 1. Idempotency Gate Check
    if request.idempotency_key:
        if request.idempotency_key in IDEMPOTENCY_CACHE:
            existing_job_id = IDEMPOTENCY_CACHE[request.idempotency_key]
            existing_job = JOB_STORE[existing_job_id]
            return JobReceipt(
                job_id=existing_job_id,
                status=existing_job["status"],
                poll_url=f"/api/v1/reports/{existing_job_id}",
                message="Duplicate request detected. Returning existing job receipt.",
            )

    # 2. Generate Deterministic Unique Job ID (Thread ID)
    job_id = f"job-{uuid.uuid4().hex[:8]}"

    # 3. Register Job Record
    job_record = {
        "job_id": job_id,
        "status": JobStatus.QUEUED,
        "transcript": request.transcript,
        "score": None,
        "iterations": 0,
        "draft": None,
        "failure_reason": None,
        "needs_human_notification": False,
    }
    JOB_STORE[job_id] = job_record

    # 4. Cache Idempotency Key (if provided)
    if request.idempotency_key:
        IDEMPOTENCY_CACHE[request.idempotency_key] = job_id

    # 5. Push to Durable Task Queue Broker
    await task_broker.enqueue(job_id=job_id, transcript=request.transcript)

    # 6. Return HTTP 202 Receipt Immediately
    return JobReceipt(
        job_id=job_id,
        status=JobStatus.QUEUED,
        poll_url=f"/api/v1/reports/{job_id}",
        message="Job accepted and enqueued for processing.",
    )


@app.get(
    "/api/v1/reports/{job_id}",
    response_model=JobStatusResponse,
    summary="Poll Job Status & State Snapshot",
)
async def get_report_status(job_id: str) -> JobStatusResponse:
    """
    Polls the current status, score, iterations, and draft snapshot for a given job_id.
    """
    if job_id not in JOB_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report job '{job_id}' not found.",
        )

    job = JOB_STORE[job_id]
    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        score=job.get("score"),
        iterations=job.get("iterations"),
        draft=job.get("draft"),
        failure_reason=job.get("failure_reason"),
        needs_human_notification=job.get("needs_human_notification", False),
    )


@app.post(
    "/api/v1/reports/{job_id}/resume",
    response_model=JobStatusResponse,
    summary="Resume Interrupted Graph with Human Approval/Feedback",
)
async def resume_report_job(job_id: str, request: ResumeRequest) -> JobStatusResponse:
    """
    Injects human decision into a paused graph waiting at approval_node.
    Transitions status back to RUNNING and signals worker loop to resume execution.
    """
    if job_id not in JOB_STORE:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report job '{job_id}' not found.",
        )

    job = JOB_STORE[job_id]

    # Validate that the job is currently paused waiting for human intervention
    if job["status"] != JobStatus.NEEDS_APPROVAL:
        current_status_val = job["status"].value if hasattr(job["status"], "value") else job["status"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Job '{job_id}' is in status '{current_status_val}', cannot resume unless '{JobStatus.NEEDS_APPROVAL.value}'.",
        )

    # Transition state to RUNNING
    job["status"] = JobStatus.RUNNING
    job["needs_human_notification"] = False
    job["resume_payload"] = {
        "approved": request.approved,
        "feedback": request.feedback,
    }

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        score=job.get("score"),
        iterations=job.get("iterations"),
        draft=job.get("draft"),
        needs_human_notification=False,
    )

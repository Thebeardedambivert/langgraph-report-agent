"""
Data transfer objects (DTOs) for the Scaled Report Agent API.
Defines strict Pydantic contracts for ingestion, job receipts, and polling.
"""
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class JobStatus(str, Enum):
    """Lifecycle states of an asynchronous report generation job."""
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NEEDS_APPROVAL = "NEEDS_APPROVAL"


class ReportRequest(BaseModel):
    """Payload submitted by the client to generate a report."""
    transcript: str = Field(
        ..., 
        min_length=20, 
        description="Raw conversation transcript to analyze."
    )
    idempotency_key: Optional[str] = Field(
        None, 
        description="Unique client-generated key to prevent duplicate job creation on network retry."
    )


class JobReceipt(BaseModel):
    """Immediate HTTP 202 Accepted response returned to client in < 15ms."""
    job_id: str = Field(..., description="Unique thread ID for tracking the background job.")
    status: JobStatus = Field(default=JobStatus.QUEUED)
    poll_url: str = Field(..., description="HTTP endpoint where the client can poll for status.")
    message: str = Field(default="Job accepted and enqueued for processing.")


class JobStatusResponse(BaseModel):
    """Payload returned when polling GET /api/v1/reports/{job_id}."""
    job_id: str
    status: JobStatus
    score: Optional[float] = None
    iterations: Optional[int] = None
    draft: Optional[str] = None
    failure_reason: Optional[str] = None
    needs_human_notification: bool = False

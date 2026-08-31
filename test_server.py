"""
Unit tests for FastAPI Scaled Serving Layer (server.py).
Verifies 202 Ingestion, Idempotency Caching, Validation, Polling, and HITL Resumption.
"""
import pytest
from fastapi.testclient import TestClient
from server import app, IDEMPOTENCY_CACHE, JOB_STORE
from schemas import JobStatus

client = TestClient(app)


@pytest.fixture(autouse=True)
def clean_stores():
    """Wipes stores before each test to guarantee test isolation."""
    IDEMPOTENCY_CACHE.clear()
    JOB_STORE.clear()
    yield
    IDEMPOTENCY_CACHE.clear()
    JOB_STORE.clear()


def test_enqueue_report_success():
    """Tests normal HTTP 202 ingestion of a valid transcript."""
    payload = {
        "transcript": "Client: We need a scalable FastAPI queue architecture with checkpointer for our agents.",
        "idempotency_key": "req-abc-123",
    }
    response = client.post("/api/v1/reports", json=payload)
    assert response.status_code == 202
    
    data = response.json()
    assert "job_id" in data
    assert data["status"] == "QUEUED"
    assert data["poll_url"] == f"/api/v1/reports/{data['job_id']}"
    assert "Job accepted" in data["message"]


def test_idempotency_duplicate_submission():
    """
    Tests that a network retry with the exact same idempotency_key
    returns the existing JobReceipt without creating a new job.
    """
    payload = {
        "transcript": "Client: We need a scalable FastAPI queue architecture with checkpointer for our agents.",
        "idempotency_key": "idemp-unique-999",
    }
    # 1. First submission
    res1 = client.post("/api/v1/reports", json=payload)
    assert res1.status_code == 202
    job_id_1 = res1.json()["job_id"]

    # 2. Duplicate submission (retry)
    res2 = client.post("/api/v1/reports", json=payload)
    assert res2.status_code == 202
    job_id_2 = res2.json()["job_id"]

    # INVARIANT: Must return the same job_id and indicate duplicate detection
    assert job_id_1 == job_id_2
    assert "Duplicate request detected" in res2.json()["message"]
    assert len(JOB_STORE) == 1


def test_short_transcript_schema_validation():
    """Tests that transcripts < 20 chars fail fast with 422 Unprocessable Entity."""
    payload = {
        "transcript": "Too short",
        "idempotency_key": "key-1",
    }
    response = client.post("/api/v1/reports", json=payload)
    assert response.status_code == 422


def test_poll_job_status_success_and_404():
    """Tests polling an active job status and 404 on missing jobs."""
    # 1. 404 on unknown job
    res_404 = client.get("/api/v1/reports/job-nonexistent")
    assert res_404.status_code == 404

    # 2. 200 on created job
    create_res = client.post(
        "/api/v1/reports", 
        json={"transcript": "Valid transcript with sufficient length for analysis."}
    )
    job_id = create_res.json()["job_id"]

    poll_res = client.get(f"/api/v1/reports/{job_id}")
    assert poll_res.status_code == 200
    poll_data = poll_res.json()
    assert poll_data["job_id"] == job_id
    assert poll_data["status"] == "QUEUED"
    assert poll_data["draft"] is None


def test_resume_job_validation_and_transition():
    """Tests human-in-the-loop resume endpoint guards and state transition."""
    # Create job
    create_res = client.post(
        "/api/v1/reports", 
        json={"transcript": "Valid transcript with sufficient length for analysis."}
    )
    job_id = create_res.json()["job_id"]

    # 1. Attempt resume while status is QUEUED -> should fail with 400 Bad Request
    bad_resume = client.post(
        f"/api/v1/reports/{job_id}/resume",
        json={"approved": True, "feedback": "LGTM"},
    )
    assert bad_resume.status_code == 400
    assert "cannot resume unless 'NEEDS_APPROVAL'" in bad_resume.json()["detail"]

    # 2. Simulate worker setting status to NEEDS_APPROVAL
    JOB_STORE[job_id]["status"] = JobStatus.NEEDS_APPROVAL
    JOB_STORE[job_id]["needs_human_notification"] = True
    JOB_STORE[job_id]["draft"] = "Preliminary draft requiring human signoff."

    # 3. Resume with human approval
    valid_resume = client.post(
        f"/api/v1/reports/{job_id}/resume",
        json={"approved": True, "feedback": "Approved with no changes."},
    )
    assert valid_resume.status_code == 200
    resume_data = valid_resume.json()
    assert resume_data["status"] == "RUNNING"
    assert resume_data["needs_human_notification"] is False
    assert JOB_STORE[job_id]["resume_payload"] == {
        "approved": True,
        "feedback": "Approved with no changes.",
    }

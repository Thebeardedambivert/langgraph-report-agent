"""
Unit tests for TaskQueueBroker (task_queue.py).
Verifies FIFO dispatch, worker leasing, ACK/NACK semantics, and Dead-Letter Queue escalation.
"""
import pytest
import asyncio
from task_queue import TaskQueueBroker, QueueMessage


@pytest.mark.asyncio
async def test_enqueue_and_dequeue_lease():
    """Verifies that enqueued jobs can be leased by a worker and tracked in-flight."""
    broker = TaskQueueBroker()
    assert broker.queue_size == 0
    assert broker.in_flight_count == 0

    # 1. Enqueue Job
    await broker.enqueue(job_id="job-101", transcript="Valid transcript for test.")
    assert broker.queue_size == 1
    assert broker.in_flight_count == 0

    # 2. Dequeue (Lease)
    msg = await broker.dequeue(timeout=1.0)
    assert msg is not None
    assert msg.job_id == "job-101"
    assert msg.retry_count == 0
    assert broker.queue_size == 0
    assert broker.in_flight_count == 1


@pytest.mark.asyncio
async def test_ack_removes_in_flight():
    """Verifies that acknowledging a completed job clears the in-flight lease."""
    broker = TaskQueueBroker()
    await broker.enqueue(job_id="job-102", transcript="Transcript")
    msg = await broker.dequeue(timeout=1.0)
    assert msg is not None

    # ACK
    success = await broker.ack(job_id="job-102")
    assert success is True
    assert broker.in_flight_count == 0
    assert broker.queue_size == 0


@pytest.mark.asyncio
async def test_nack_requeues_with_incremented_retry():
    """Verifies that failing a job re-enqueues it with incremented retry count."""
    broker = TaskQueueBroker(max_retries=2)
    await broker.enqueue(job_id="job-103", transcript="Transcript")
    
    # First attempt lease
    msg1 = await broker.dequeue(timeout=1.0)
    assert msg1.job_id == "job-103"
    assert msg1.retry_count == 0

    # NACK (Simulating LLM rate limit or network glitch)
    requeued = await broker.nack(job_id="job-103", error_reason="RateLimitError 429")
    assert requeued is True
    assert broker.in_flight_count == 0
    assert broker.queue_size == 1

    # Second attempt lease (Worker 2 picks it up)
    msg2 = await broker.dequeue(timeout=1.0)
    assert msg2.job_id == "job-103"
    assert msg2.retry_count == 1
    assert msg2.payload["last_error"] == "RateLimitError 429"


@pytest.mark.asyncio
async def test_nack_escalation_to_dlq():
    """Verifies that exceeding max_retries routes the message to Dead-Letter Queue."""
    broker = TaskQueueBroker(max_retries=1)
    await broker.enqueue(job_id="job-104", transcript="Bad Transcript")

    # Attempt 1
    msg = await broker.dequeue(timeout=1.0)
    assert await broker.nack("job-104", error_reason="Transient Error") is True
    assert broker.dlq_size == 0

    # Attempt 2 (Exceeds max_retries=1)
    msg = await broker.dequeue(timeout=1.0)
    requeued = await broker.nack("job-104", error_reason="Fatal Poison Pill Exception")
    assert requeued is False  # Not requeued
    assert broker.queue_size == 0
    assert broker.in_flight_count == 0
    assert broker.dlq_size == 1
    assert "job-104" in broker._dead_letter_queue
    assert broker._dead_letter_queue["job-104"].retry_count == 2


@pytest.mark.asyncio
async def test_dequeue_timeout_on_empty_queue():
    """Verifies that dequeuing from an empty queue cleanly returns None on timeout."""
    broker = TaskQueueBroker()
    msg = await broker.dequeue(timeout=0.1)
    assert msg is None

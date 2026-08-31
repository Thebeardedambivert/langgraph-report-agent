"""
Task Queue & Broker Layer for the Scaled Report Agent.
Implements decoupled FIFO job dispatch, leasing semantics, and dead-letter queues (DLQ).
"""
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class QueueMessage:
    """Represents an atomic task unit leased by a background worker."""
    job_id: str
    transcript: str
    retry_count: int = 0
    max_retries: int = 3
    enqueued_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    payload: Dict[str, Any] = field(default_factory=dict)


class TaskQueueBroker:
    """
    Durable Task Queue Interface.
    Encapsulates queue ingestion, atomic worker leasing, and failure recovery.
    """
    def __init__(self, max_retries: int = 3):
        self._queue: asyncio.Queue[QueueMessage] = asyncio.Queue()
        self._in_flight: Dict[str, QueueMessage] = {}
        self._dead_letter_queue: Dict[str, QueueMessage] = {}
        self.max_retries = max_retries

    async def enqueue(self, job_id: str, transcript: str, payload: Optional[Dict[str, Any]] = None) -> QueueMessage:
        """
        Pushes a new job message to the FIFO queue.
        Invariant: Fast O(1) non-blocking enqueue.
        """
        msg = QueueMessage(
            job_id=job_id,
            transcript=transcript,
            max_retries=self.max_retries,
            payload=payload or {},
        )
        await self._queue.put(msg)
        return msg

    async def dequeue(self, timeout: Optional[float] = None) -> Optional[QueueMessage]:
        """
        Pops and leases the next available job message for a worker.
        Marks the job as 'in_flight'.
        """
        try:
            if timeout is not None:
                msg = await asyncio.wait_for(self._queue.get(), timeout=timeout)
            else:
                msg = await self._queue.get()
            
            # Atomic lease: Record job in in-flight tracking
            self._in_flight[msg.job_id] = msg
            return msg
        except asyncio.TimeoutError:
            return None

    async def ack(self, job_id: str) -> bool:
        """
        Acknowledges successful completion of a job.
        Removes the message from in-flight tracking and marks queue task as done.
        """
        if job_id in self._in_flight:
            del self._in_flight[job_id]
            self._queue.task_done()
            return True
        return False

    async def nack(self, job_id: str, error_reason: str) -> bool:
        """
        Negative acknowledgement (job failure).
        Increments retry count. If retries exceeded, escalates to Dead-Letter Queue (DLQ).
        Otherwise, re-enqueues for another worker attempt.
        """
        if job_id not in self._in_flight:
            return False

        msg = self._in_flight.pop(job_id)
        self._queue.task_done()
        msg.retry_count += 1
        msg.payload["last_error"] = error_reason

        if msg.retry_count > msg.max_retries:
            # Escalation to Dead-Letter Queue (DLQ) for forensic debugging
            self._dead_letter_queue[job_id] = msg
            return False
        else:
            # Re-enqueue for retry
            await self._queue.put(msg)
            return True

    @property
    def queue_size(self) -> int:
        """Current number of pending jobs waiting to be leased."""
        return self._queue.qsize()

    @property
    def in_flight_count(self) -> int:
        """Current number of jobs actively being executed by workers."""
        return len(self._in_flight)

    @property
    def dlq_size(self) -> int:
        """Number of unrecoverable failed jobs in Dead-Letter Queue."""
        return len(self._dead_letter_queue)


# Global Singleton Broker Instance
task_broker = TaskQueueBroker()

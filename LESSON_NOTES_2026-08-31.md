# 📚 Lesson Study Notes — August 31, 2026

> **Date:** August 31, 2026  
> **Topics Covered:** 
> 1. **DSA Pattern 3:** Fixed-Size Sliding Window Algorithm ($O(N)$ Time, $O(1)$ Space)
> 2. **Module A3 (Serving & Asynchronous Architecture):** FastAPI 202 Ingestion, Task Queue Broker, Background Worker Consumer Loop
> 3. **Module A4 (Automated Quality Gates):** Golden Benchmark Dataset, Semantic Extraction Evals, CI/CD Deployment Regression Gates
> **Workspace:** `report_agent/` & `Lessons/`  
> **Master Notes References:** `LANGGRAPH_ENGINEERING_MASTER_NOTES.md` & `DSA_ALGORITHMIC_PATTERNS_MASTER_NOTES.md`

---

## 1. Pillar 1: DSA Pattern 3 — Fixed-Size Sliding Window

### The Problem:
Given an array `nums` and a window size `k`, find the maximum sum of any contiguous subarray of length `k`.

### The Mechanism & Mental Model: "The Bus Window"
Instead of re-adding all $k$ numbers from scratch in $O(k)$ for each slide (which takes $O(N \times k)$ overall), we use the **constant-time $O(1)$ sliding formula**:

```text
new_sum = old_sum - outgoing_element + incoming_element
```

* **Outgoing Element (Left Edge):** `nums[i - k]`
* **Incoming Element (Right Edge):** `nums[i]`

### Key Invariants & Traps:
* **Off-by-One Index Trap:** The outgoing element is always at index `i - k`.
* **Complexity:** $O(N)$ Single-Pass Time, $O(1)$ Space.
* **Code Reference:** `sliding_window_demo.py`

---

## 2. Pillar 2: Module A3 — Production Serving & Asynchronous Architecture

### The Core Problem:
Running a full self-reflective LangGraph agent takes **30–45+ seconds of LLM execution**. Holding open synchronous HTTP connections blocks server thread pools, triggers proxy timeouts (Cloudflare 30s limit), and causes duplicate runs on client retry.

### The Decoupled Architecture Blueprint:
```
[Client] ──(POST /api/v1/reports)──► [FastAPI server.py] ──(Enqueue)──► [TaskQueueBroker]
                                           │ (< 15ms)                          │
                                    202 Accepted {job_id}               [Worker Pool]
                                           │                                   │
[Client] ◄──(GET /api/v1/reports/{job_id} Polling)─────────────────────────────┘
```

### Components Built:
1. **Data Transfer Objects (`schemas.py`):**
   * `JobStatus` Enum (`QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, `NEEDS_APPROVAL`)
   * `ReportRequest`: Validates transcript length $\ge 20$ chars, handles `idempotency_key`.
   * `JobReceipt`: Immediate HTTP 202 response (`job_id`, `status="QUEUED"`, `poll_url`).
   * `JobStatusResponse`: Polling payload containing quality scores and draft snapshot.
2. **FastAPI Serving Layer (`server.py`):**
   * `POST /api/v1/reports`: Checks idempotency cache to prevent duplicate LLM double-spend, assigns `job_id`, pushes to queue, returns in $<15\text{ms}$.
   * `GET /api/v1/reports/{job_id}`: Returns state snapshot.
   * `POST /api/v1/reports/{job_id}/resume`: Validates `NEEDS_APPROVAL` state, attaches human decision, transitions status to `RUNNING`.
3. **Task Queue Broker (`task_queue.py`):**
   * Implements FIFO queuing, atomic worker leasing (`_in_flight`), `ack()`, `nack()` with retry counter, and Dead-Letter Queue (`_dead_letter_queue`) quarantine for poison pills.
4. **Background Worker Consumer (`worker.py`):**
   * Asynchronously leases tasks, executes LangGraph workflows with `asyncio.to_thread` to prevent event loop blocking, detects `interrupt()` pauses, and commits checkpoints to SQLite.

---

## 3. Pillar 2: Module A4 — Automated Evaluation Harness as CI/CD Gates

### The Core Problem:
LLMs are probabilistic. Exact string matching (`assert output == expected`) fails constantly. But without automated evals, prompt edits or model updates introduce **silent quality degradation** (dropped entities or hallucinations).

### Components Built:
1. **Golden Benchmark Dataset (`evaluation.py`):**
   * 4 curated benchmark transcripts covering Standard Happy Path, Noisy Conversations, Strict Budget Edge-Cases, and Sparse Inputs.
   * Defines mandatory `expected_entities` that must be present in output.
2. **Semantic Evaluator (`evaluate_single_case`):**
   * Verifies agent quality score meets `min_acceptable_score` ($\ge 0.70$) AND all mandatory entities were extracted.
3. **CI/CD Quality Threshold Gate (`test_eval_gate.py`):**
   * Runs the agent over the full benchmark dataset.
   * Enforces a strict deployment gate: **Pass Rate $\ge 75.0\%$**. If regressions occur, the CI pipeline fails and blocks production deployment.

---

## 4. Test Suite Summary

* **Total Tests:** 29 / 29 Passing (100% Green)
  * `test_approval.py`: Human approval state transitions
  * `test_eval_gate.py`: CI/CD regression threshold tests
  * `test_iteration_policy.py`: Max iteration loop caps
  * `test_judge.py`: Multi-judge fan-out & aggregation
  * `test_router.py`: Deterministic routing thresholds
  * `test_server.py`: FastAPI HTTP 202, idempotency, polling, and resume
  * `test_task_queue.py`: Broker leasing, ACK, NACK, and DLQ
  * `test_worker.py`: Async LangGraph execution & HITL pauses

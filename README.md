# Self-Reflective Client Report Agent (LangGraph)

An enterprise-grade, stateful cyclical agent built with **LangGraph**, **Pydantic**, and **SQLite Checkpointing**. Features deterministic map-reduce multi-judge evaluations, boundary validation, human-in-the-loop (HITL) approval gates, and time-travel state replay.

---

## 🌟 Key Architecture Highlights

1. **Deterministic Channel Schema:** [`ReportState`](state.py) configured with custom reducers (`merge_evaluations`, `operator.add`).
2. **Map-Reduce Dynamic Fan-Out:** [`dispatch_evaluators`](nodes.py) using the `Send()` API to invoke 3 parallel single-dimension judges (`eval_accuracy`, `eval_clarity`, `eval_completeness`) with barrier synchronization in `aggregate_evaluations_node`.
3. **Strict Validation & Policy Separation:** Pydantic models in [`validators.py`](validators.py) boundary-check LLM outputs before pure-Python policy evaluation in [`policy.py`](policy.py).
4. **Human-in-the-Loop & Persistence:** [`approval_node`](nodes.py) using `interrupt()`, persisted via `SqliteSaver`, resumable via `Command(resume=...)`.
5. **Time-Travel & DAG Branching:** Historical replay and non-destructive checkpoint forking via [`time_travel.py`](time_travel.py).

---

## 📁 Repository Structure

```text
report_agent/
├── state.py                  # TypedDict schema & channel reducers
├── validators.py             # Pydantic boundary validation models
├── policy.py                 # Pure Python policy scoring & iteration limits
├── nodes.py                  # Graph nodes & evaluator judges (OpenAI / Gemini)
├── graph.py                  # StateGraph assembly & compilation
├── time_travel.py            # Checkpoint history inspection & fork/replay CLI
├── test_router.py            # Deterministic router test suite
├── test_policy.py            # Pure Python policy unit tests
├── test_iteration_policy.py  # Iteration budget & ceiling tests
├── test_approval.py          # HITL interrupt & resume tests
├── test_validation.py        # Pydantic schema validation tests
└── LANGGRAPH_ENGINEERING_MASTER_NOTES.md # Full architecture & design guide
```

---

## 🚀 Quickstart

### 1. Setup Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install langgraph langchain-openai pydantic python-dotenv pytest
```

### 2. Configure Environment Variables
Create a `.env` file:
```env
OPENAI_API_KEY=your_openai_api_key
```

### 3. Run Test Suite
```powershell
pytest -v
```

### 4. Inspect Thread History & Time-Travel
```powershell
# Inspect state history for a thread
python time_travel.py <thread_id>

# Fork from a historical checkpoint and replay with corrected draft
python time_travel.py <thread_id> <checkpoint_id> "<corrected_draft>"
```

---

## 📚 Study Notes
For a deep dive into the three architectural anchors, failure modes, and Pregel execution mechanics, see [LANGGRAPH_ENGINEERING_MASTER_NOTES.md](LANGGRAPH_ENGINEERING_MASTER_NOTES.md).

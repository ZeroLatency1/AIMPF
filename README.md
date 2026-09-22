# AIMPF — AI Impact and Maintainability Prediction Framework

A local research-oriented framework for predicting the consequences of AI-system changes, estimating behavioral risk, and spending validation effort where it reduces the most uncertainty.

## Core loop

`Change → fingerprint → weighted dependency propagation → behavior-conditioned prediction → uncertainty → adaptive minimum validation set → observed outcome → residual → calibration → improved future prediction`

## Stack

- **Frontend:** Next.js, React, TypeScript, Tailwind CSS, Cytoscape.js, Plotly.js
- **Backend:** Python 3.12+, FastAPI, Pydantic, SQLAlchemy 2.x, Alembic
- **Database:** PostgreSQL + pgvector
- **Analysis:** NetworkX, NumPy, Pandas
- **Evaluation:** versioned datasets, behavioral metrics, deterministic RAG evaluation, prompt/version tracking, regression history, experiment comparison
- **Observability:** OpenTelemetry + structured logging
- **Testing:** pytest, pytest-asyncio/httpx-compatible API stack, Playwright

## Local run

### Easiest cross-platform start

From `project/`, run one command:

```bash
python run.py
```

On Windows, `py run.py` is equivalent. The launcher starts PostgreSQL + pgvector, creates a virtual environment, installs dependencies, applies migrations, seeds demo data, and starts FastAPI + Next.js. It uses only Python/Node/Docker commands so the same entry point works on Windows, macOS, and Linux.

See [`RUN.md`](RUN.md) for optional modes and troubleshooting.

Open `http://127.0.0.1:3000`.

Demo account: `demo@aimpf.local` / `aimpf-demo-password`.

## Main workspaces

- `/projects` — project creation and navigation
- `/projects/:id` — AIMI dashboard, dependency graph, recommendations, report
- `/projects/:id/manage` — component/dependency management and criticality
- `/changes` — counterfactual impact analysis and adaptive test selection
- `/validation` — observed result, residual, calibration and history
- `/evaluations` — behavioral evaluation + deterministic RAG scoring
- `/experiments` — adaptive-vs-full validation comparison
- `/login` — local authentication

## Testing

Backend:

```bash
cd backend
pytest -q
python -m compileall app tests
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
npx playwright test
```

The browser suite mocks backend responses so the UI flows are deterministic; backend behavior is separately verified by Python tests and live local integration runs.


### Database migrations
From the repository root:

```bash
source .venv/bin/activate
cd backend
alembic upgrade head
python seed.py
python auth_seed.py
```

The current migration chain ends at `003_experiment_results`. Version 1.1.0 adds metric and research logic without requiring a schema migration, so existing PostgreSQL validation/calibration/experiment data remains compatible.

### Signature workflow verification
1. Run a change from **Changes**.
2. Open **Validation**; the latest impact is selected automatically.
3. Record an observed score for a selected behavioral test.
4. Confirm the residual and calibration update appear in history.
5. Re-run the same change and compare the calibrated behavioral prediction.
6. Run **Experiments → Run the adaptive baseline comparison** to persist a research result.
7. Generate the PDF report from the project dashboard.

### CRUD and local research workflow
The API exposes create/read/update/delete operations for projects, AI components, dependencies, evaluation datasets, evaluation records, prompts, and experiments. The research flow is deterministic and does not require an external LLM.

### Research artifacts
`research/protocol.md` defines the repeatable evaluation protocol and explicitly separates engineering evidence from statistical claims.

### End-to-end signature verification
With PostgreSQL and the API running:

```bash
./scripts/verify_signature.sh
```

The script verifies health, change analysis, adaptive test selection, observation/residual calculation, calibration, future-prediction movement, and persisted adaptive-vs-full experiment comparison.

### Database lifecycle
Alembic is the schema authority. The API does not mutate schema on startup; run `alembic upgrade head` before starting the backend. The seed script is intentionally idempotent and only inserts missing demo records.

### Metric sophistication
See `docs/METRICS.md`. PVS is driven by historical prediction residuals, KFS by knowledge/evidence categories, and BSS by behavioral quality + consistency + repeatability. Hallucination is normalized as lower-is-better before aggregation.

### Research baseline comparison
`/api/projects/{id}/research/comparison` and **Experiments → Run comparison** compare AIMPF against uncertainty-only, cheapest-first, full-suite, and an exact finite-test-set minimum-cost oracle. The offline reproduction script is `scripts/research_benchmark.py`. The latest UI runtime snapshot is preserved in `research/results/live_runtime_comparison.md` and `.csv`; it reflects the current persisted analysis state and is intentionally separate from the five-scenario fixture benchmark.

To remove duplicate persisted experiment registrations while keeping the newest result for each exact experiment name/hypothesis pair:

```bash
./scripts/cleanup_duplicate_experiments.sh 1
```


### Version 1.1.0 verification
`./scripts/verify_signature.sh` now checks the signature loop, recomputed higher-is-better maintainability metrics, and the complete research baseline-comparison strategy set.

# AIMPF implementation status

## Engineering status
**Feature-complete for the intended semester scope.** The repository contains the local FastAPI/PostgreSQL application, research workflow, frontend workspaces, migrations, tests, CI, reporting, and reproducible research scripts.

## Implemented
- Next.js + React + TypeScript frontend with project-aware research workspaces
- FastAPI + PostgreSQL + pgvector persistence with Alembic migrations
- Local JWT authentication with PBKDF2 password hashing
- Project/component/dependency/dataset/evaluation/prompt/experiment CRUD APIs
- Weighted AI dependency graph using NetworkX betweenness and path propagation
- Change fingerprint normalization and behavior-conditioned sensitivity
- Impact, confidence, risk, maintenance effort and AIMI metrics
- Adaptive minimum validation-set selection using uncertainty, coverage, information gain and cost
- Explicit validation observation → residual/error → calibration → future prediction adjustment
- Calibration and validation history persisted in PostgreSQL
- Deterministic offline RAG evaluator with precision/recall/F1/lexical relevance/grounding
- Versioned evaluation datasets and prompt versions
- Maintainability/criticality ranking and actionable recommendations
- Adaptive-vs-full validation experiment comparison with persisted structured results
- Project dashboard with AIMI trend, metric cards, dependency graph, recommendations and PDF export
- OpenTelemetry FastAPI instrumentation and structured logging
- Backend unit tests and Playwright browser E2E coverage for core workspaces
- GitHub Actions CI for backend compile/tests and frontend typecheck/build/E2E
- `scripts/verify_signature.sh` for the complete prediction/validation/calibration loop
- `scripts/research_benchmark.py` with deterministic benchmark results under `research/results/`
- Research protocol documenting measurements and claim boundaries

## Metric and research strengthening
- PVS now uses historical validation residuals rather than evaluation weakness.
- KFS now uses weighted grounding/retrieval/domain/accuracy evidence.
- BSS now combines behavioral quality, consistency, and repeat-evaluation stability.
- Hallucination is normalized in the correct lower-is-better direction.
- Baseline comparison now includes full-suite, uncertainty-only, cheapest-first, and exact finite-set oracle strategies.
- Documentation added under `docs/` and research artifacts under `research/results/`.

## Research evidence
The shipped offline benchmark evaluates five fixed change scenarios and produced a mean modeled validation-cost reduction of **63.5%** and mean modeled uncertainty reduction of **51.7%** across those scenarios.

The latest end-to-end UI runtime snapshot is recorded separately in `research/results/live_runtime_comparison.md`: AIMPF adaptive cost **3.70** vs full-suite **10.20** (63.7% reduction), with **53.6%** modeled uncertainty reduction; the uncertainty-only baseline is **4.70**, cheapest-first is **5.70**, and the exact finite-set oracle is **3.70** (0.0% cost gap).

These are algorithmic engineering measurements, not statistical-significance claims. Repeated controlled trials would be required for statistical inference.

## Verification
Verified in the build environment:
- Python syntax compilation
- AIMPF analysis unit tests
- benchmark execution and result generation
- shell-script syntax
- frontend JSON/package configuration parsing
- ZIP integrity for the final artifact

The build environment cannot complete the real PostgreSQL-backed test suite because `psycopg`/`pgvector` are not installed locally and external package installation is network-blocked. It also cannot complete the Next.js production build because frontend package installation is network-blocked. The repository includes the required lock-step commands for running those checks in the user's local environment/CI.

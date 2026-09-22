# AIMPF Live Runtime Research Snapshot

This artifact records the latest end-to-end comparison executed through the running AIMPF UI for the current `Customer Support AI` project state. It is intentionally separate from the reproducible five-scenario offline benchmark in `baseline_comparison.md`.

## Runtime result

| Strategy | Cost | Cost reduction vs full suite | Modeled uncertainty reduction |
|---|---:|---:|---:|
| AIMPF adaptive | 3.70 | 63.7% | 53.6% |
| Uncertainty-only baseline | 4.70 | 53.9% | 58.7% |
| Cheapest-first baseline | 5.70 | 44.1% | 59.8% |
| Full-suite baseline | 10.20 | 0.0% | 64.6% |
| Exact minimum-cost oracle | 3.70 | 63.7% | 53.6% |

**AIMPF oracle cost gap: 0.0%.**

Adaptive tests selected by the live run:

- `retrieval_recall`
- `hallucination_evaluation`
- `accuracy_evaluation`

The live comparison is a deterministic engineering measurement for the current persisted impact prediction and validation-test catalog. It is not a statistical significance test and does not establish global optimality outside the finite test catalog.

## Why this is separate from the offline benchmark

`research_benchmark.py` evaluates five fixed change scenarios with deterministic in-memory fixtures. The live UI comparison evaluates the latest persisted project analysis after the application's stateful validation/calibration workflow has been exercised. Because the latest persisted predictions can differ from the fixed fixture scenarios, the two artifacts are expected to have different baseline values.

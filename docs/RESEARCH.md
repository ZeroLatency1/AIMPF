# AIMPF Research Evaluation

## Research question

Can AIMPF reduce validation effort by selecting a minimum set of behavioral tests using modeled uncertainty, behavior coverage, expected information gain, and test cost?

## Baselines

The evaluator compares AIMPF against:

1. **Full-suite baseline** — execute every test in the catalog.
2. **Uncertainty-only baseline** — greedily choose the test with the largest modeled uncertainty reduction, ignoring test cost.
3. **Cheapest-first baseline** — greedily choose the cheapest useful test, ignoring information gain.
4. **Exact minimum-cost oracle** — enumerate all subsets of the ten-test catalog and find the cheapest subset that reaches or beats AIMPF's modeled final uncertainty.

## Measurements

- Validation cost
- Cost reduction vs full suite
- Modeled uncertainty reduction
- Selection efficiency
- Cost gap to the exact oracle

## Claim boundary

The evaluator is deterministic and reproducible. It supports engineering comparison of the selection heuristic. It does not establish statistical significance, production reliability, or global optimality outside the finite test catalog.

## Reproduction

```bash
source .venv/bin/activate
python3 scripts/research_benchmark.py
```

Results are written to `research/results/baseline_comparison.csv` and `research/results/baseline_comparison.md`.

The latest end-to-end UI comparison is recorded separately in `research/results/live_runtime_comparison.csv` and `research/results/live_runtime_comparison.md`. The live snapshot is for the current persisted project state; it is not expected to numerically match the fixed five-scenario offline fixture benchmark.

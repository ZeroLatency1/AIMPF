# Changelog

## 1.1.0 — Metric and Research Strengthening

- Corrected AIMI to average seven higher-is-better metrics directly.
- Replaced the shared evaluation proxy with distinct PVS, KFS, and BSS evidence paths.
- Added correct lower-is-better handling for hallucination evaluations.
- Added deterministic baseline comparison against uncertainty-only, cheapest-first, full-suite, and exact finite-set oracle strategies.
- Added reproducible research results under `research/results/`.
- Expanded PDF reporting with research-comparison and methodology sections.
- Added architecture and metric-methodology documentation.
- Added unit tests for metric distinctness, direction normalization, and baseline comparison.
- Bumped algorithm version to 1.1.0.
- Added a live runtime research snapshot and safe duplicate-experiment cleanup helper.
- Included the verified Cytoscape TypeScript compatibility fix and Plotly module declaration used by the production frontend build.

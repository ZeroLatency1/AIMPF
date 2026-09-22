# AIMPF Metric Methodology

AIMPF reports seven maintainability dimensions on a 0–100 scale plus their direct mean, AIMI. Every maintainability score is **higher-is-better**.

## Structural metrics

- **CCS — Coupling Complexity Score:** inverse structural coupling burden from dependency count per component.
- **ECS — Edge Complexity Score:** inverse graph density; sparser dependency graphs score higher.
- **CDS — Coupling Density Score:** inverse average dependency weight.
- **MPS — Maintenance Pressure Score:** inverse dependency-count pressure proxy.

## Evidence metrics

- **PVS — Prediction Stability Score:** historical prediction reliability derived from validation absolute error, residual dispersion, and amount of validation evidence. With no validation history, AIMPF uses an explicit cold-start prior rather than claiming measured prediction accuracy.
- **KFS — Knowledge Fitness Score:** weighted grounding, retrieval-quality, domain-relevance, and accuracy evidence.
- **BSS — Behavior Stability Score:** behavioral quality, explicit consistency evidence, and repeat-evaluation stability. Hallucination is treated as lower-is-better and is inverted before aggregation.

## AIMI

`AIMI = mean(CCS, PVS, KFS, ECS, CDS, BSS, MPS)`

AIMI is a project-level comparative maintainability index. It is not a production reliability guarantee or a statistical estimate of system failure probability.

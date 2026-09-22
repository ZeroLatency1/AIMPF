# AIMPF Research & Demonstration Protocol

## Research question
Can AIMPF reduce validation effort by selecting a minimum set of behavioral tests using predicted uncertainty, behavior coverage, expected information gain, and test cost, while retaining an auditable prediction→observation→residual→calibration loop?

## Controlled workflow
1. Seed the same project, components, weighted dependencies, evaluation evidence, and validation-test catalog.
2. Run a deterministic change analysis for a fixed change description and severity.
3. Record AIMPF's adaptive test set, modeled uncertainty before/after selection, and adaptive/full validation cost.
4. Execute one or more selected tests and record observed behavioral scores against the exact impact result.
5. Compute residual `observed - predicted`, absolute error, percentage error, and update calibration with learning rate 0.25.
6. Repeat the identical change analysis and compare the calibrated prediction with the pre-calibration prediction.
7. Compare AIMPF with uncertainty-only, cheapest-first, full-suite, and exact finite-test-set oracle baselines; persist the comparison as an Experiment record.
8. Export the project PDF report as the audit artifact.

## Primary measurements
- Overall impact and risk
- Behavior-level predicted value and confidence
- Initial/final modeled uncertainty
- Expected uncertainty reduction
- Adaptive validation cost
- Full-suite validation cost
- Cost reduction
- Selection efficiency = modeled uncertainty reduction / validation cost
- Baseline cost gap to the exact finite-set oracle
- Residual and absolute prediction error
- Calibrated future prediction

## Interpretation rules
The adaptive selector is an engineering heuristic. The exact oracle is optimal only within the finite test catalog and deterministic uncertainty simulation used by the experiment. The deterministic RAG evaluator is intentionally local and reproducible and does not claim semantic LLM-judge quality. A single run demonstrates functional behavior; statistical significance requires repeated controlled trials and is not claimed by the application.

## Reproducibility
Use `scripts/verify_signature.sh` against a running local API. The script runs the complete signature workflow and fails when calibration does not change a future prediction or the adaptive suite does not reduce modeled validation cost.

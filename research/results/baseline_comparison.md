# AIMPF Baseline Comparison

Deterministic controlled comparison across five fixed change scenarios. No external model or cloud service is used.

- Scenarios: 5
- Mean AIMPF cost reduction vs full-suite baseline: 63.5%
- Mean AIMPF modeled uncertainty reduction: 51.7%
- Mean AIMPF cost gap to exact minimum-cost oracle: 0.0%

| Scenario | Risk | Impact | Strategy | Cost | Cost reduction | Uncertainty reduction |
|---|---|---:|---|---:|---:|---:|
| knowledge_update_repo | MEDIUM | 0.561 | AIMPF adaptive | 3.70 | 63.7% | 53.7% |
| knowledge_update_repo | MEDIUM | 0.561 | Uncertainty-only baseline | 5.70 | 44.1% | 65.2% |
| knowledge_update_repo | MEDIUM | 0.561 | Cheapest-first baseline | 5.70 | 44.1% | 65.2% |
| knowledge_update_repo | MEDIUM | 0.561 | Full-suite baseline | 10.20 | 0.0% | 65.2% |
| knowledge_update_repo | MEDIUM | 0.561 | Exact minimum-cost oracle | 3.70 | 63.7% | 53.7% |
| knowledge_update_rag | HIGH | 0.703 | AIMPF adaptive | 3.70 | 63.7% | 53.7% |
| knowledge_update_rag | HIGH | 0.703 | Uncertainty-only baseline | 5.70 | 44.1% | 65.1% |
| knowledge_update_rag | HIGH | 0.703 | Cheapest-first baseline | 5.70 | 44.1% | 65.1% |
| knowledge_update_rag | HIGH | 0.703 | Full-suite baseline | 10.20 | 0.0% | 65.1% |
| knowledge_update_rag | HIGH | 0.703 | Exact minimum-cost oracle | 3.70 | 63.7% | 53.7% |
| prompt_change | MEDIUM | 0.521 | AIMPF adaptive | 4.30 | 57.8% | 53.8% |
| prompt_change | MEDIUM | 0.521 | Uncertainty-only baseline | 4.30 | 57.8% | 53.8% |
| prompt_change | MEDIUM | 0.521 | Cheapest-first baseline | 4.30 | 57.8% | 53.8% |
| prompt_change | MEDIUM | 0.521 | Full-suite baseline | 10.20 | 0.0% | 53.8% |
| prompt_change | MEDIUM | 0.521 | Exact minimum-cost oracle | 4.30 | 57.8% | 53.8% |
| model_change | MEDIUM | 0.622 | AIMPF adaptive | 4.10 | 59.8% | 48.8% |
| model_change | MEDIUM | 0.622 | Uncertainty-only baseline | 5.00 | 51.0% | 54.5% |
| model_change | MEDIUM | 0.622 | Cheapest-first baseline | 5.00 | 51.0% | 54.5% |
| model_change | MEDIUM | 0.622 | Full-suite baseline | 10.20 | 0.0% | 54.5% |
| model_change | MEDIUM | 0.622 | Exact minimum-cost oracle | 4.10 | 59.8% | 48.8% |
| configuration_change | MEDIUM | 0.503 | AIMPF adaptive | 2.80 | 72.5% | 48.4% |
| configuration_change | MEDIUM | 0.503 | Uncertainty-only baseline | 3.80 | 62.7% | 55.1% |
| configuration_change | MEDIUM | 0.503 | Cheapest-first baseline | 3.80 | 62.7% | 55.1% |
| configuration_change | MEDIUM | 0.503 | Full-suite baseline | 10.20 | 0.0% | 55.1% |
| configuration_change | MEDIUM | 0.503 | Exact minimum-cost oracle | 2.80 | 72.5% | 48.4% |

Interpretation:
- Full-suite executes every catalog test.
- Uncertainty-only ignores test cost; cheapest-first ignores information gain.
- The exact oracle enumerates all subsets of the ten-test catalog and finds the minimum-cost subset matching or beating AIMPF's modeled final uncertainty.
- These are deterministic engineering measurements, not statistical significance claims.

from pathlib import Path
from types import SimpleNamespace as S
import csv
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app.services.analysis import compare_validation_strategies, fingerprint, analyze

OUT = ROOT / 'research' / 'results'
TESTS = [
    S(id=1, test_name='retrieval_precision', behavior_dimensions_covered=['retrieval_quality'], estimated_cost=1.0, expected_information_gain=.45),
    S(id=2, test_name='retrieval_recall', behavior_dimensions_covered=['retrieval_quality', 'grounding'], estimated_cost=1.2, expected_information_gain=.55),
    S(id=3, test_name='grounding_evaluation', behavior_dimensions_covered=['grounding'], estimated_cost=1.0, expected_information_gain=.60),
    S(id=4, test_name='hallucination_evaluation', behavior_dimensions_covered=['hallucination'], estimated_cost=1.1, expected_information_gain=.50),
    S(id=5, test_name='prompt_regression', behavior_dimensions_covered=['format_compliance', 'consistency'], estimated_cost=.8, expected_information_gain=.50),
    S(id=6, test_name='accuracy_evaluation', behavior_dimensions_covered=['accuracy', 'domain_relevance'], estimated_cost=1.4, expected_information_gain=.55),
    S(id=7, test_name='safety_evaluation', behavior_dimensions_covered=['safety'], estimated_cost=1.0, expected_information_gain=.60),
    S(id=8, test_name='privacy_evaluation', behavior_dimensions_covered=['privacy'], estimated_cost=1.0, expected_information_gain=.70),
    S(id=9, test_name='consistency_evaluation', behavior_dimensions_covered=['consistency'], estimated_cost=.9, expected_information_gain=.45),
    S(id=10, test_name='latency_evaluation', behavior_dimensions_covered=['latency'], estimated_cost=.8, expected_information_gain=.40),
]
COMPONENTS = [
    S(id=1, type='KNOWLEDGE_REPOSITORY', criticality_override=None),
    S(id=2, type='RAG_PIPELINE', criticality_override=None),
    S(id=3, type='LLM', criticality_override=None),
    S(id=4, type='RAG_PIPELINE', criticality_override=None),
    S(id=5, type='PROMPT', criticality_override=None),
]
DEPS = [
    S(source_component_id=1, target_component_id=2, weight=.88, dependency_type='depends_on'),
    S(source_component_id=2, target_component_id=3, weight=.80, dependency_type='invokes'),
    S(source_component_id=5, target_component_id=3, weight=.85, dependency_type='uses'),
]
SCENARIOS = [
    ('knowledge_update_repo', 1, 'KNOWLEDGE_UPDATE', .8, 'refresh product documentation'),
    ('knowledge_update_rag', 2, 'KNOWLEDGE_UPDATE', .8, 'refresh retrieval sources and pricing'),
    ('prompt_change', 5, 'PROMPT_CHANGE', .6, 'tighten answer format and refusal rules'),
    ('model_change', 3, 'MODEL_CHANGE', .7, 'replace inference model with a lower-latency version'),
    ('configuration_change', 3, 'CONFIGURATION_CHANGE', .55, 'adjust runtime decoding and timeout configuration'),
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    strategy_rows = []
    for scenario, cid, change_type, severity, description in SCENARIOS:
        result = analyze(cid, change_type, fingerprint(change_type, severity, description), COMPONENTS, DEPS, [])
        comp = compare_validation_strategies(result['predictions'], result['prediction_confidence'], TESTS)
        rows.append({
            'scenario': scenario,
            'risk': result['risk'],
            'overall_impact': round(result['overall'], 6),
            'aimpf_cost': next(r['cost'] for r in comp['strategies'] if r['strategy'] == 'AIMPF adaptive'),
            'aimpf_cost_reduction': next(r['cost_reduction'] for r in comp['strategies'] if r['strategy'] == 'AIMPF adaptive'),
            'aimpf_uncertainty_reduction': next(r['uncertainty_reduction'] for r in comp['strategies'] if r['strategy'] == 'AIMPF adaptive'),
            'oracle_cost_gap': comp['aimpf_oracle_cost_gap'],
        })
        for strategy in comp['strategies']:
            strategy_rows.append({'scenario': scenario, **strategy})

    with (OUT / 'baseline_comparison.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=strategy_rows[0].keys())
        writer.writeheader()
        writer.writerows(strategy_rows)

    mean_adaptive = sum(r['aimpf_cost_reduction'] for r in rows) / len(rows)
    mean_unc = sum(r['aimpf_uncertainty_reduction'] for r in rows) / len(rows)
    mean_gap = sum(r['oracle_cost_gap'] for r in rows) / len(rows)
    text = [
        '# AIMPF Baseline Comparison', '',
        'Deterministic controlled comparison across five fixed change scenarios. No external model or cloud service is used.', '',
        f'- Scenarios: {len(rows)}',
        f'- Mean AIMPF cost reduction vs full-suite baseline: {mean_adaptive * 100:.1f}%',
        f'- Mean AIMPF modeled uncertainty reduction: {mean_unc * 100:.1f}%',
        f'- Mean AIMPF cost gap to exact minimum-cost oracle: {mean_gap * 100:.1f}%', '',
        '| Scenario | Risk | Impact | Strategy | Cost | Cost reduction | Uncertainty reduction |',
        '|---|---|---:|---|---:|---:|---:|',
    ]
    scenario_lookup = {r['scenario']: r for r in rows}
    for row in strategy_rows:
        sr = scenario_lookup[row['scenario']]
        text.append(
            f"| {row['scenario']} | {sr['risk']} | {sr['overall_impact']:.3f} | {row['strategy']} | "
            f"{row['cost']:.2f} | {row['cost_reduction'] * 100:.1f}% | {row['uncertainty_reduction'] * 100:.1f}% |"
        )
    text += [
        '',
        'Interpretation:',
        '- Full-suite executes every catalog test.',
        '- Uncertainty-only ignores test cost; cheapest-first ignores information gain.',
        "- The exact oracle enumerates all subsets of the ten-test catalog and finds the minimum-cost subset matching or beating AIMPF's modeled final uncertainty.",
        '- These are deterministic engineering measurements, not statistical significance claims.',
    ]
    (OUT / 'baseline_comparison.md').write_text('\n'.join(text) + '\n')
    print('Wrote', OUT / 'baseline_comparison.csv')
    print('Wrote', OUT / 'baseline_comparison.md')
    print(f'mean_aimpf_cost_reduction={mean_adaptive:.6f}')
    print(f'mean_aimpf_uncertainty_reduction={mean_unc:.6f}')
    print(f'mean_oracle_cost_gap={mean_gap:.6f}')


if __name__ == '__main__':
    main()

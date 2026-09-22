from types import SimpleNamespace as S

from app.services.analysis import analyze, fingerprint, validation_plan


def test_fingerprint_knowledge():
    fp = fingerprint('KNOWLEDGE_UPDATE', .8, 'pricing and documentation refresh')
    assert fp['freshness_delta'] > .8


def test_validation_selects_useful_tests():
    tests = [
        S(id=1, test_name='grounding', behavior_dimensions_covered=['grounding'], estimated_cost=1, expected_information_gain=.6),
        S(id=2, test_name='latency', behavior_dimensions_covered=['latency'], estimated_cost=1, expected_information_gain=.2),
    ]
    result = validation_plan({'grounding': .8}, {'grounding': .5}, tests)
    assert result['selected'][0]['name'] == 'grounding'


def test_validation_prefers_new_coverage_and_avoids_redundancy():
    tests = [
        S(id=2, test_name='retrieval_recall', behavior_dimensions_covered=['retrieval_quality', 'grounding'], estimated_cost=1.2, expected_information_gain=.55),
        S(id=1, test_name='retrieval_precision', behavior_dimensions_covered=['retrieval_quality'], estimated_cost=1.0, expected_information_gain=.45),
        S(id=3, test_name='grounding_evaluation', behavior_dimensions_covered=['grounding'], estimated_cost=1.0, expected_information_gain=.6),
        S(id=4, test_name='hallucination_evaluation', behavior_dimensions_covered=['hallucination'], estimated_cost=1.1, expected_information_gain=.5),
        S(id=5, test_name='latency_evaluation', behavior_dimensions_covered=['latency'], estimated_cost=.8, expected_information_gain=.4),
        S(id=6, test_name='accuracy_evaluation', behavior_dimensions_covered=['accuracy', 'domain_relevance'], estimated_cost=1.4, expected_information_gain=.55),
    ]
    result = validation_plan(
        {'grounding': .82, 'retrieval_quality': .78, 'accuracy': .55, 'hallucination': .46, 'latency': .10},
        {'grounding': .50, 'retrieval_quality': .50, 'accuracy': .50, 'hallucination': .50, 'latency': .90},
        tests,
    )
    names = [item['name'] for item in result['selected']]
    assert names == ['retrieval_recall', 'hallucination_evaluation', 'accuracy_evaluation']
    assert result['expected_uncertainty_reduction'] > 0


def test_depth_decay_and_dependency_weight():
    comps = [
        S(id=1, type='KNOWLEDGE_REPOSITORY', criticality_override=None),
        S(id=2, type='RAG_PIPELINE', criticality_override=None),
        S(id=3, type='LLM', criticality_override=None),
    ]
    deps = [
        S(source_component_id=1, target_component_id=2, weight=.9, dependency_type='feeds'),
        S(source_component_id=2, target_component_id=3, weight=.9, dependency_type='depends_on'),
    ]
    result = analyze(1, 'KNOWLEDGE_UPDATE', fingerprint('KNOWLEDGE_UPDATE', 1, 'x'), comps, deps, [])
    assert result['overall'] > 0


def test_calibration_re_scoring_moves_future_impact():
    from app.services.analysis import score_impact
    base = score_impact(.6, {'grounding': .8, 'accuracy': .6}, {'grounding': .5, 'accuracy': .5})
    calibrated = score_impact(.6, {'grounding': .7, 'accuracy': .6}, {'grounding': .55, 'accuracy': .5})
    assert calibrated['overall'] < base['overall']
    assert calibrated['confidence'] > base['confidence']


def test_maintainability_metrics_use_distinct_evidence_signals():
    from app.services.analysis import maintainability_metrics

    evaluations = [
        S(evaluation_category='Grounding', score=.91),
        S(evaluation_category='Retrieval Quality', score=.89),
        S(evaluation_category='Accuracy', score=.87),
        S(evaluation_category='Hallucination', score=.18),
        S(evaluation_category='Consistency', score=.84),
    ]
    validations = [S(absolute_error=.04), S(absolute_error=.06), S(absolute_error=.10)]
    deps = [S(weight=.8), S(weight=.9)]
    comps = [S() for _ in range(4)]
    values = maintainability_metrics(comps, deps, evaluations, validations)
    assert 0 <= values['AIMI'] <= 100
    assert values['PVS'] < 100
    assert values['KFS'] != values['PVS']
    assert values['BSS'] != values['PVS']
    assert all(0 <= values[name] <= 100 for name in ['CCS', 'PVS', 'KFS', 'ECS', 'CDS', 'BSS', 'MPS', 'AIMI'])


def test_hallucination_is_inverted_for_maintainability_quality():
    from app.services.analysis import normalized_evaluation_score

    assert normalized_evaluation_score('hallucination', .20) == .80
    assert normalized_evaluation_score('grounding', .80) == .80


def test_baseline_comparison_includes_exact_oracle():
    from app.services.analysis import compare_validation_strategies

    tests = [
        S(id=1, test_name='grounding', behavior_dimensions_covered=['grounding'], estimated_cost=2, expected_information_gain=.6),
        S(id=2, test_name='accuracy', behavior_dimensions_covered=['accuracy'], estimated_cost=1, expected_information_gain=.6),
        S(id=3, test_name='joint', behavior_dimensions_covered=['grounding', 'accuracy'], estimated_cost=2.2, expected_information_gain=.6),
    ]
    result = compare_validation_strategies(
        {'grounding': .8, 'accuracy': .8},
        {'grounding': .5, 'accuracy': .5},
        tests,
    )
    names = {r['strategy'] for r in result['strategies']}
    assert 'AIMPF adaptive' in names
    assert 'Full-suite baseline' in names
    assert 'Exact minimum-cost oracle' in names

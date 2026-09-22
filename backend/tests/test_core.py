from types import SimpleNamespace as S

from app.api.routes import _hash_password, _verify_password, _normalize_change_type
from app.services.analysis import aimi, fingerprint, validation_plan, analyze


def test_password_hash_round_trip():
    encoded = _hash_password('correct horse battery staple')
    assert encoded.startswith('pbkdf2_sha256$')
    assert _verify_password('correct horse battery staple', encoded)
    assert not _verify_password('wrong password', encoded)


def test_normalization_is_stable():
    assert _normalize_change_type(' knowledge-update ') == 'KNOWLEDGE_UPDATE'
    assert _normalize_change_type('Prompt Change') == 'PROMPT_CHANGE'


def test_adaptive_plan_minimizes_redundant_tests():
    tests = [
        S(id=2, test_name='retrieval_recall', behavior_dimensions_covered=['retrieval_quality', 'grounding'], estimated_cost=1.2, expected_information_gain=.55),
        S(id=1, test_name='retrieval_precision', behavior_dimensions_covered=['retrieval_quality'], estimated_cost=1.0, expected_information_gain=.45),
        S(id=3, test_name='safety', behavior_dimensions_covered=['safety'], estimated_cost=1.0, expected_information_gain=.6),
    ]
    result = validation_plan({'grounding': .82, 'retrieval_quality': .78, 'safety': .2}, {'grounding': .5, 'retrieval_quality': .5, 'safety': .85}, tests)
    assert [x['name'] for x in result['selected']] == ['retrieval_recall']
    assert result['expected_uncertainty_reduction'] > 0


def test_analysis_produces_only_behaviorally_relevant_predictions():
    comps = [S(id=1, type='RAG_PIPELINE', criticality_override=None), S(id=2, type='LLM', criticality_override=None)]
    deps = [S(source_component_id=1, target_component_id=2, weight=.9, dependency_type='invokes')]
    result = analyze(1, 'knowledge-update', fingerprint('knowledge-update', .8, 'refresh knowledge'), comps, deps, [])
    assert set(result['predictions']) == {'grounding', 'retrieval_quality', 'accuracy', 'hallucination'}
    assert result['overall'] > 0
    assert 0 <= result['confidence'] <= 1


def test_aimi_is_bounded():
    assert 0 <= aimi({'CCS': 0, 'PVS': 0, 'KFS': 100, 'ECS': 100, 'CDS': 0, 'BSS': 0, 'MPS': 0}) <= 100


def test_validation_plan_exposes_reasons_and_excludes_redundant_tests():
    tests = [
        S(id=1, test_name='primary', behavior_dimensions_covered=['grounding', 'retrieval_quality'], estimated_cost=1.0, expected_information_gain=.55),
        S(id=2, test_name='duplicate_grounding', behavior_dimensions_covered=['grounding'], estimated_cost=1.0, expected_information_gain=.1),
    ]
    result = validation_plan(
        {'grounding': .8, 'retrieval_quality': .7},
        {'grounding': .5, 'retrieval_quality': .5},
        tests,
    )
    assert result['selected'][0]['name'] == 'primary'
    assert 'new coverage' in result['selected'][0]['reason']
    assert result['unselected'][0]['name'] == 'duplicate_grounding'

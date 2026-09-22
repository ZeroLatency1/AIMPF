from collections import defaultdict
from itertools import combinations
import math
from statistics import mean, pstdev

import networkx as nx

BEHAVIORS = [
    'accuracy', 'grounding', 'hallucination', 'safety', 'privacy', 'consistency',
    'latency', 'retrieval_quality', 'format_compliance', 'domain_relevance'
]
PRIORS = {
    'LLM': .95, 'SYSTEM_PROMPT': .90, 'AI_AGENT': .95, 'RAG_PIPELINE': .90,
    'PROMPT': .85, 'VECTOR_DATABASE': .80, 'KNOWLEDGE_REPOSITORY': .75,
    'EMBEDDING_MODEL': .80, 'API': .75, 'CONFIGURATION': .70, 'EVALUATION_DATASET': .65,
}
SENS = {
    'KNOWLEDGE_UPDATE': {'grounding': .91, 'retrieval_quality': .88, 'accuracy': .72, 'hallucination': .60},
    'PROMPT_CHANGE': {'hallucination': .77, 'format_compliance': .80, 'accuracy': .55, 'safety': .62},
    'MODEL_CHANGE': {'accuracy': .72, 'latency': .74, 'hallucination': .58, 'consistency': .61},
    'CONFIGURATION_CHANGE': {'latency': .58, 'retrieval_quality': .55, 'format_compliance': .42},
}


def _normalize_change_type(change_type: str) -> str:
    return str(change_type).strip().upper().replace(' ', '_').replace('-', '_')


def fingerprint(change_type: str, severity: float, description: str):
    change_type = _normalize_change_type(change_type)
    d = description.lower()
    out = {
        'severity': max(0, min(1, severity)), 'semantic_delta': 0, 'freshness_delta': 0,
        'volume_delta': 0, 'schema_delta': 0, 'instruction_delta': 0, 'format_delta': 0,
        'safety_delta': 0, 'quality_delta': 0, 'latency_delta': 0,
    }
    if change_type == 'KNOWLEDGE_UPDATE':
        out.update(freshness_delta=.9, volume_delta=min(1, len(d) / 180), semantic_delta=.65)
    elif change_type == 'PROMPT_CHANGE':
        out.update(instruction_delta=.8, format_delta=.55, safety_delta=.45, semantic_delta=.65)
    elif change_type == 'MODEL_CHANGE':
        out.update(quality_delta=.7, latency_delta=.65, semantic_delta=.55)
    elif change_type == 'CONFIGURATION_CHANGE':
        out.update(latency_delta=.45, semantic_delta=.4)
    return out


def build_graph(components, deps):
    g = nx.DiGraph()
    for component in components:
        criticality = (
            component.criticality_override
            if component.criticality_override is not None
            else PRIORS.get(component.type, .5)
        )
        g.add_node(component.id, type=component.type, criticality=criticality)
    for dependency in deps:
        g.add_edge(
            dependency.source_component_id,
            dependency.target_component_id,
            weight=dependency.weight,
            dependency_type=getattr(dependency, 'dependency_type', 'unknown'),
        )
    return g


def score_impact(structural, predictions, confidences):
    """Convert structural/behavioral predictions into the composite impact score."""
    behavioral = sum(predictions.values()) / max(1, len(predictions))
    evaluation = min(1, behavioral * .9)
    maintenance = min(1, 0.35 * structural + 0.35 * behavioral + 0.3 * evaluation)
    overall = min(1, .28 * structural + .32 * behavioral + .18 * evaluation + .22 * maintenance)
    risk = 'HIGH' if overall >= .66 else 'MEDIUM' if overall >= .36 else 'LOW'
    confidence = sum(confidences.values()) / max(1, len(confidences))
    return {
        'behavioral': behavioral,
        'evaluation': evaluation,
        'maintenance': maintenance,
        'overall': overall,
        'confidence': confidence,
        'risk': risk,
    }


def analyze(source_id, change_type, fp, components, deps, evals):
    change_type = _normalize_change_type(change_type)
    graph = build_graph(components, deps)
    criticality = nx.betweenness_centrality(graph, normalized=True) if graph else {}
    predictions = defaultdict(float)
    paths = {}
    direct = (
        nx.single_source_dijkstra_path_length(
            graph, source_id, weight=lambda u, v, edge: max(.01, 1 - edge['weight'])
        )
        if source_id in graph else {}
    )
    source_criticality = graph.nodes[source_id]['criticality'] if source_id in graph else .5
    sensitivity = SENS.get(change_type, {})

    for node, distance in direct.items():
        path_value = graph.nodes[node]['criticality'] * (
            0.55 * source_criticality + 0.45 * criticality.get(node, 0)
        ) * math.exp(-0.35 * distance)
        if node == source_id:
            path_value = min(1, path_value + fp['severity'] * .45)
        else:
            path_value = min(1, path_value * fp['severity'])
        paths[node] = path_value
        for behavior, sensitivity_value in sensitivity.items():
            predictions[behavior] = max(predictions[behavior], path_value * sensitivity_value)

    active_predictions = {behavior: float(value) for behavior, value in predictions.items() if value > 0}
    evidence_map = {
        'accuracy': {'accuracy'}, 'grounding': {'grounding'}, 'hallucination': {'hallucination'},
        'safety': {'safety'}, 'privacy': {'privacy'}, 'consistency': {'consistency'},
        'latency': set(), 'retrieval_quality': {'retrieval quality', 'retrieval_quality'},
        'format_compliance': {'format compliance', 'format_compliance'},
        'domain_relevance': {'domain specific', 'domain relevance', 'domain_relevance'},
    }

    def relevant_evidence(behavior):
        targets = evidence_map.get(behavior, {behavior})
        return sum(1 for evaluation in evals if str(evaluation.evaluation_category).strip().lower() in targets)

    confidences = {
        behavior: min(
            .90,
            .35 + .07 * min(relevant_evidence(behavior), 5) + .18 * min(value, 1)
        )
        for behavior, value in active_predictions.items()
    }
    structural = max(paths.values(), default=0)
    scored = score_impact(structural, active_predictions, confidences)
    return {
        'structural': structural,
        'behavioral': scored['behavioral'],
        'evaluation': scored['evaluation'],
        'maintenance': scored['maintenance'],
        'overall': scored['overall'],
        'confidence': scored['confidence'],
        'risk': scored['risk'],
        'predictions': active_predictions,
        'prediction_confidence': confidences,
        'paths': paths,
    }


def validation_plan(predictions, confidences, tests, target=.20):
    """Select a small validation set using uncertainty, coverage, information gain, and cost."""
    state = {behavior: 1 - confidences.get(behavior, .5) for behavior in predictions}
    remaining = list(tests)
    selected = []
    covered = set()

    while True:
        urgent = {
            behavior for behavior, uncertainty in state.items()
            if uncertainty > target and predictions.get(behavior, 0) >= .25
        }
        if not urgent:
            break

        best = None
        for test in remaining:
            covers = set(test.behavior_dimensions_covered)
            useful = covers & urgent
            new_coverage = useful - covered
            if not useful:
                continue

            gain = max(0.0, min(1.0, float(test.expected_information_gain)))
            raw_reduction = sum(state.get(behavior, 0.0) * gain for behavior in useful)
            coverage_bonus = 1.0 + 0.35 * len(new_coverage) if new_coverage else 0.15
            effective_reduction = raw_reduction * coverage_bonus
            if effective_reduction < 0.025:
                continue
            if not new_coverage and raw_reduction < 0.20:
                continue

            ratio = effective_reduction / max(0.25, float(test.estimated_cost))
            candidate = (ratio, test, useful, new_coverage, effective_reduction)
            if best is None or (ratio, -test.estimated_cost, test.id) > (
                best[0], -best[1].estimated_cost, best[1].id
            ):
                best = candidate

        if best is None:
            break

        _, test, useful, new_coverage, _ = best
        gain = max(0.0, min(1.0, float(test.expected_information_gain)))
        for behavior in useful:
            state[behavior] *= 1 - gain
        selected.append({
            'id': test.id,
            'name': test.test_name,
            'reason': (
                f"Selected for {', '.join(sorted(useful))}; "
                f"new coverage: {', '.join(sorted(new_coverage)) or 'none'}; "
                'highest modeled uncertainty reduction per unit cost at this step.'
            ),
        })
        covered.update(useful)
        remaining = [item for item in remaining if item.id != test.id]

    before = sum(1 - confidences.get(behavior, .5) for behavior in predictions) / max(1, len(predictions))
    after = sum(state.values()) / max(1, len(state))
    return {
        'selected': selected,
        'unselected': [
            {
                'id': test.id,
                'name': test.test_name,
                'reason': 'Not required after higher-value coverage or below uncertainty target.',
            }
            for test in remaining
        ],
        'initial_uncertainty': before,
        'final_uncertainty': after,
        'expected_uncertainty_reduction': 0 if before == 0 else (before - after) / before,
    }


def aimi(metrics):
    """Composite 0-100 maintainability index; every component is higher-is-better."""
    names = ['CCS', 'PVS', 'KFS', 'ECS', 'CDS', 'BSS', 'MPS']
    values = [max(0, min(100, float(metrics.get(name, 0)))) for name in names]
    return sum(values) / len(values)


LOWER_IS_BETTER_EVALUATIONS = {'hallucination'}


def normalized_evaluation_score(category: str, score: float) -> float:
    """Return a 0-1 quality score with one consistent higher-is-better direction."""
    key = str(category).strip().lower()
    value = max(0.0, min(1.0, float(score)))
    if key in LOWER_IS_BETTER_EVALUATIONS:
        return 1.0 - value
    return value


def maintainability_metrics(components, deps, evals, validations):
    """Compute distinct maintainability signals from structural, evaluation, and validation evidence."""
    n_components = max(1, len(components))
    n_deps = len(deps)
    density = n_deps / max(1, n_components * (n_components - 1))
    avg_weight = sum(float(d.weight) for d in deps) / max(1, n_deps)

    grouped = defaultdict(list)
    for evaluation in evals:
        grouped[str(evaluation.evaluation_category).strip().lower()].append(
            normalized_evaluation_score(evaluation.evaluation_category, evaluation.score)
        )
    latest_quality = {k: values[-1] for k, values in grouped.items() if values}
    all_quality = [value for values in grouped.values() for value in values]
    overall_quality = mean(all_quality) if all_quality else 0.70

    # Coupling / graph signals: higher is better.
    ccs = 100 * max(0.0, min(1.0, 1.0 - (n_deps / n_components) * 0.12))
    ecs = 100 * max(0.0, min(1.0, 1.0 - density))
    cds = 100 * max(0.0, min(1.0, 1.0 - avg_weight * 0.25))
    mps = 100 * max(0.0, min(1.0, 1.0 - n_deps * 0.015))

    # Knowledge fitness: specifically use retrieval/grounding/domain evidence, not unrelated scores.
    knowledge_terms = ('grounding', 'retrieval quality', 'retrieval_quality', 'domain specific',
                       'domain relevance', 'domain_relevance', 'accuracy')
    knowledge_weights = {
        'grounding': 0.30, 'retrieval quality': 0.25, 'retrieval_quality': 0.25,
        'domain specific': 0.20, 'domain relevance': 0.20, 'domain_relevance': 0.20,
        'accuracy': 0.25,
    }
    selected = []
    weighted_total = 0.0
    weight_total = 0.0
    for key in knowledge_terms:
        if key in latest_quality:
            weight = knowledge_weights[key]
            weighted_total += latest_quality[key] * weight
            weight_total += weight
    kfs_quality = weighted_total / weight_total if weight_total else overall_quality
    kfs = 100 * kfs_quality

    # Prediction stability: historical prediction residuals, with a transparent cold-start prior.
    errors = [abs(float(v.absolute_error)) for v in validations]
    if errors:
        mean_abs_error = mean(errors)
        error_quality = 1.0 - min(1.0, mean_abs_error / 0.25)
        error_stability = 1.0 - min(1.0, (pstdev(errors) if len(errors) > 1 else 0.0) / 0.15)
        history_confidence = min(1.0, len(errors) / 5.0)
        pvs_quality = 0.65 * error_quality + 0.20 * error_stability + 0.15 * history_confidence
    else:
        pvs_quality = 0.55 + 0.20 * kfs_quality
    pvs = 100 * max(0.0, min(1.0, pvs_quality))

    # Behavioral stability: quality + explicit consistency signal + repeatability evidence.
    consistency_quality = latest_quality.get('consistency', overall_quality)
    repeat_stabilities = []
    repeated_categories = 0
    for key, values in grouped.items():
        if len(values) >= 2:
            repeated_categories += 1
            spread = pstdev(values)
            repeat_stabilities.append(1.0 - min(1.0, spread / 0.20))
    repeat_stability = mean(repeat_stabilities) if repeat_stabilities else 0.75
    repeat_coverage = repeated_categories / max(1, len(grouped))
    repeatability_signal = 0.75 + 0.25 * repeat_coverage * repeat_stability
    bss_quality = 0.50 * overall_quality + 0.30 * consistency_quality + 0.20 * repeatability_signal
    bss = 100 * max(0.0, min(1.0, bss_quality))

    values = {
        'CCS': max(0.0, min(100.0, ccs)),
        'PVS': max(0.0, min(100.0, pvs)),
        'KFS': max(0.0, min(100.0, kfs)),
        'ECS': max(0.0, min(100.0, ecs)),
        'CDS': max(0.0, min(100.0, cds)),
        'BSS': max(0.0, min(100.0, bss)),
        'MPS': max(0.0, min(100.0, mps)),
    }
    values['AIMI'] = aimi(values)
    return values


def _simulate_tests(predictions, confidences, tests, selected):
    state = {behavior: 1.0 - confidences.get(behavior, 0.5) for behavior in predictions}
    for test in selected:
        gain = max(0.0, min(1.0, float(test.expected_information_gain)))
        for behavior in set(test.behavior_dimensions_covered) & set(state):
            state[behavior] *= 1.0 - gain
    before = mean(state.values()) if state else 0.0
    return state, before


def _strategy_until_stop(predictions, confidences, tests, mode: str, target=.20):
    remaining = list(tests)
    selected = []
    state = {behavior: 1.0 - confidences.get(behavior, 0.5) for behavior in predictions}
    while True:
        urgent = {b for b, u in state.items() if u > target and predictions.get(b, 0) >= .25}
        if not urgent:
            break
        candidates = []
        for test in remaining:
            useful = set(test.behavior_dimensions_covered) & urgent
            if not useful:
                continue
            gain = max(0.0, min(1.0, float(test.expected_information_gain)))
            raw = sum(state.get(b, 0.0) * gain for b in useful)
            if raw <= 0:
                continue
            if mode == 'uncertainty_only':
                key = (raw, len(useful), -float(test.estimated_cost), -int(test.id))
            else:
                key = (-float(test.estimated_cost), raw, len(useful), -int(test.id))
            candidates.append((key, test, useful, gain))
        if not candidates:
            break
        _, test, useful, gain = max(candidates, key=lambda item: item[0])
        for behavior in useful:
            state[behavior] *= 1.0 - gain
        selected.append(test)
        remaining = [t for t in remaining if t.id != test.id]
    before = mean(1.0 - confidences.get(b, 0.5) for b in predictions) if predictions else 0.0
    after = mean(state.values()) if state else 0.0
    reduction = 0.0 if before == 0 else (before - after) / before
    return selected, before, after, reduction


def compare_validation_strategies(predictions, confidences, tests, target=.20):
    """Compare AIMPF to simple deterministic baselines and an exact subset oracle."""
    tests = list(tests)
    adaptive = validation_plan(predictions, confidences, tests, target=target)
    adaptive_names = {item['name'] for item in adaptive['selected']}
    adaptive_tests = [t for t in tests if t.test_name in adaptive_names]
    before = adaptive['initial_uncertainty']

    def pack(name, selected, after, reduction):
        cost = sum(float(t.estimated_cost) for t in selected)
        full_cost = sum(float(t.estimated_cost) for t in tests)
        return {
            'strategy': name,
            'selected_tests': [t.test_name for t in selected],
            'selected_count': len(selected),
            'cost': round(cost, 6),
            'full_suite_cost': round(full_cost, 6),
            'cost_reduction': round((full_cost - cost) / full_cost, 6) if full_cost else 0.0,
            'uncertainty_before': round(before, 6),
            'uncertainty_after': round(after, 6),
            'uncertainty_reduction': round(reduction, 6),
            'selection_efficiency': round(reduction / cost, 6) if cost else 0.0,
        }

    adaptive_after_state, _ = _simulate_tests(predictions, confidences, tests, adaptive_tests)
    adaptive_after = mean(adaptive_after_state.values()) if adaptive_after_state else 0.0
    results = [pack('AIMPF adaptive', adaptive_tests, adaptive_after, adaptive['expected_uncertainty_reduction'])]

    unc_selected, _, unc_after, unc_red = _strategy_until_stop(predictions, confidences, tests, 'uncertainty_only', target)
    results.append(pack('Uncertainty-only baseline', unc_selected, unc_after, unc_red))
    cheap_selected, _, cheap_after, cheap_red = _strategy_until_stop(predictions, confidences, tests, 'cost_only', target)
    results.append(pack('Cheapest-first baseline', cheap_selected, cheap_after, cheap_red))

    full_state, _ = _simulate_tests(predictions, confidences, tests, tests)
    full_after = mean(full_state.values()) if full_state else 0.0
    full_reduction = 0.0 if before == 0 else (before - full_after) / before
    results.append(pack('Full-suite baseline', tests, full_after, full_reduction))

    target_after = adaptive_after
    oracle = None
    for r in range(len(tests) + 1):
        for combo in combinations(tests, r):
            state, _ = _simulate_tests(predictions, confidences, tests, combo)
            after = mean(state.values()) if state else 0.0
            if after > target_after + 1e-12:
                continue
            cost = sum(float(t.estimated_cost) for t in combo)
            candidate = (cost, len(combo), tuple(t.id for t in combo), combo, after)
            if oracle is None or candidate[:3] < oracle[:3]:
                oracle = candidate
    if oracle is not None:
        _, _, _, combo, after = oracle
        reduction = 0.0 if before == 0 else (before - after) / before
        results.append(pack('Exact minimum-cost oracle', list(combo), after, reduction))

    adaptive_cost = next(r['cost'] for r in results if r['strategy'] == 'AIMPF adaptive')
    oracle_cost = next((r['cost'] for r in results if r['strategy'] == 'Exact minimum-cost oracle'), adaptive_cost)
    gap = 0.0 if oracle_cost == 0 else (adaptive_cost - oracle_cost) / oracle_cost
    return {
        'target_uncertainty': target,
        'strategies': results,
        'aimpf_oracle_cost_gap': round(gap, 6),
        'interpretation': 'Deterministic controlled comparison. It measures this heuristic against fixed baselines; it is not a statistical significance test.',
    }

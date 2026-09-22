#!/usr/bin/env bash
set -euo pipefail

API="${AIMPF_API_URL:-http://127.0.0.1:8000}"
PROJECT_ID="${AIMPF_PROJECT_ID:-1}"

command -v curl >/dev/null || { echo 'curl is required'; exit 1; }
command -v python3 >/dev/null || { echo 'python3 is required'; exit 1; }

json_get() {
  python3 - "$1" <<'PY'
import json, sys
obj=json.loads(sys.argv[1])
print(obj)
PY
}

health="$(curl -fsS "$API/api/health")"
echo "Health: $health"

metrics="$(curl -fsS -X POST "$API/api/projects/$PROJECT_ID/metrics/recompute")"
python3 - "$metrics" <<'PY'
import json, sys
obj=json.loads(sys.argv[1])
print('Maintainability:', ', '.join(f"{k}={v:.2f}" for k,v in obj.items()))
if not (0 <= obj['AIMI'] <= 100):
    raise SystemExit('AIMI outside 0-100')
PY

components="$(curl -fsS "$API/api/projects/$PROJECT_ID/components")"
component_id="$(python3 - "$components" <<'PY'
import json, sys
rows=json.loads(sys.argv[1])
if not rows:
    raise SystemExit('No components found')
print(rows[0]['id'])
PY
)"

echo "Analyzing knowledge update on component #$component_id"
change="$(curl -fsS -X POST "$API/api/projects/$PROJECT_ID/changes/analyze" \
  -H 'Content-Type: application/json' \
  -d "{\"component_id\":$component_id,\"change_type\":\"KNOWLEDGE_UPDATE\",\"description\":\"Updated product documentation and pricing information.\",\"severity\":0.8}")"
python3 - "$change" <<'PY'
import json, sys
obj=json.loads(sys.argv[1])
print('Impact:', round(obj['overall_impact'], 3), obj['risk'])
print('Predictions:', ', '.join(f"{k}={v:.3f}" for k, v in obj['predictions'].items()))
print('Adaptive tests:', ', '.join(obj['validation']['selected']))
print('Uncertainty reduction:', round(obj['validation']['expected_uncertainty_reduction'] * 100, 1), '%')
if not obj['validation']['selected']:
    raise SystemExit('Adaptive selector returned no tests')
PY

impact_id="$(python3 - "$change" <<'PY'
import json, sys
print(json.loads(sys.argv[1])['id'])
PY
)"
tests="$(curl -fsS "$API/api/validation/tests")"
test_id="$(python3 - "$tests" <<'PY'
import json, sys
for t in json.loads(sys.argv[1]):
    if t['test_name'] == 'retrieval_recall':
        print(t['id']); break
else:
    raise SystemExit('retrieval_recall test missing')
PY
)"

obs="$(curl -fsS -X POST "$API/api/projects/$PROJECT_ID/validation/observe" \
  -H 'Content-Type: application/json' \
  -d "{\"test_id\":$test_id,\"observed_value\":0.70,\"behavior\":\"grounding\",\"impact_result_id\":$impact_id}")"
python3 - "$obs" <<'PY'
import json, sys
obj=json.loads(sys.argv[1])
print('Residual:', round(obj['prediction_error'], 4))
print('Calibrated value:', round(obj['calibration']['updated_value'], 4))
PY

rerun="$(curl -fsS -X POST "$API/api/projects/$PROJECT_ID/changes/analyze" \
  -H 'Content-Type: application/json' \
  -d "{\"component_id\":$component_id,\"change_type\":\"KNOWLEDGE_UPDATE\",\"description\":\"Updated product documentation and pricing information.\",\"severity\":0.8}")"
python3 - "$rerun" "$change" <<'PY'
import json, sys
before=json.loads(sys.argv[2])['predictions']['grounding']
after=json.loads(sys.argv[1])['predictions']['grounding']
print(f'Grounding prediction: {before:.6f} -> {after:.6f}')
if abs(after-before) < 1e-9:
    raise SystemExit('Calibration did not alter future prediction')
PY

experiment="$(curl -fsS -X POST "$API/api/projects/$PROJECT_ID/experiments/run")"
python3 - "$experiment" <<'PY'
import json, sys
obj=json.loads(sys.argv[1])
print('Experiment:', obj['experiment_id'])
print('Adaptive cost:', round(obj['adaptive_cost'], 3))
print('Full cost:', round(obj['full_suite_cost'], 3))
print('Cost reduction:', round(obj['cost_reduction'] * 100, 1), '%')
print('Selection efficiency:', round(obj['selection_efficiency'], 4))
if obj['adaptive_cost'] >= obj['full_suite_cost']:
    raise SystemExit('Adaptive suite did not reduce validation cost')
PY

research="$(curl -fsS "$API/api/projects/$PROJECT_ID/research/comparison")"
python3 - "$research" <<'PY'
import json, sys
obj=json.loads(sys.argv[1])
strategies={row['strategy'] for row in obj['strategies']}
required={'AIMPF adaptive','Uncertainty-only baseline','Cheapest-first baseline','Full-suite baseline','Exact minimum-cost oracle'}
print('Research strategies:', ', '.join(sorted(strategies)))
if not required.issubset(strategies):
    raise SystemExit('Research baseline comparison incomplete')
PY

echo 'AIMPF SIGNATURE VERIFICATION PASS'

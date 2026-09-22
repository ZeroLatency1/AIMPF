#!/usr/bin/env bash
set -euo pipefail

API_BASE="${API_BASE:-http://127.0.0.1:8000/api}"
PROJECT_ID="${1:-1}"

python3 - "$API_BASE" "$PROJECT_ID" <<'PY'
import json
import subprocess
import sys
from collections import defaultdict

api, project_id = sys.argv[1:]
url = f"{api}/projects/{project_id}/experiments"
raw = subprocess.check_output(["curl", "-fsS", url], text=True)
rows = json.loads(raw)

# Keep the newest experiment for each exact name+hypothesis pair.
groups = defaultdict(list)
for row in rows:
    groups[(row.get("name"), row.get("hypothesis"))].append(row)

deleted = []
for key, items in groups.items():
    if len(items) <= 1:
        continue
    items.sort(key=lambda r: (r.get("created_at") or "", int(r.get("id", 0))), reverse=True)
    keep = items[0]
    for row in items[1:]:
        eid = int(row["id"])
        subprocess.check_call(["curl", "-fsS", "-X", "DELETE", f"{url}/{eid}"])
        deleted.append(eid)
    print(f"kept experiment #{keep['id']} for {key[0]!r}")

print("deleted:", deleted if deleted else "none")
PY

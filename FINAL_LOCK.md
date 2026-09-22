# AIMPF Final Presentation Lock

Release: AIMPF 1.1.0
Artifact: Final presentation package — runtime-fixed


This directory is the locked presentation copy of AIMPF.

Verified before lock:
- Python source compilation: PASS
- Deterministic research benchmark: PASS
- Shell-script syntax: PASS
- ZIP integrity: PASS
- No local secret/key files included
- No TODO/FIXME markers in shipped source
- Frontend production build: PASS in the previously verified local environment; runtime fix applied afterward for browser-only Plotly/Cytoscape imports
- AIMPF signature verification: PASS in the verified local environment
- Adaptive Counterfactual Validation stateful flow: PASS in the verified local environment
- PDF report generation: PASS in the verified local environment

Research claim boundary:
- Offline benchmark: five fixed scenarios; mean AIMPF modeled validation-cost reduction 63.5%, mean modeled uncertainty reduction 51.7%, mean cost gap to exact finite-set oracle 0.0%.
- Live runtime snapshot: AIMPF adaptive cost 3.70 vs full-suite 10.20, 63.7% modeled cost reduction; exact finite-set oracle cost 3.70.
- These are deterministic engineering measurements, not statistical-significance claims.

Do not modify this copy for the presentation/submission. Make future development changes in a separate working copy.

Runtime compatibility fix applied after the original lock: Plotly and Cytoscape are now lazy-loaded on the client to prevent `self is not defined` during `next start` server rendering.

This runtime-fixed package should replace the earlier presentation ZIP. Re-run `npm install && npm run build && npm run start` in the target environment before presentation.

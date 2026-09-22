.PHONY: backend-test backend-check frontend-install frontend-check frontend-e2e
backend-test:
	cd backend && pytest -q
backend-check:
	cd backend && python -m compileall app tests && pytest -q
frontend-install:
	cd frontend && npm install
frontend-check:
	cd frontend && npm run typecheck && npm run build
frontend-e2e:
	cd frontend && npx playwright test

---
name: run-tests
description: Run all project tests and checks
disable-model-invocation: true
---

Run the full test and check suite for this project:

1. Backend linting: `cd backend && ruff check .`
2. Backend formatting check: `cd backend && ruff format --check .`
3. Backend tests: `cd backend && pytest`
4. Frontend lint: `cd frontend && npm run lint`
5. Frontend type check: `cd frontend && npx tsc --noEmit`

Report results for each step. If any step fails, report the specific errors.

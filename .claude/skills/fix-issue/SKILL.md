---
name: fix-issue
description: Fix a GitHub issue end-to-end
disable-model-invocation: true
---

Analyze and fix the GitHub issue: $ARGUMENTS.

1. Use the GitHub MCP tools to read the issue details
2. Understand the problem described in the issue
3. Search the codebase for relevant files
4. Implement the necessary changes to fix the issue
5. Run backend tests: `cd backend && pytest`
6. Run frontend lint and type check: `cd frontend && npm run lint && npx tsc --noEmit`
7. Ensure all checks pass — fix any failures
8. Create a descriptive commit message
9. Push the changes

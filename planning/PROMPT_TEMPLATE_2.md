# Worker Prompt Template: Code Review Remediation

Execute the assigned task in strict compliance with the plan specification.

## Context & Conventions
- Codebase: `source-bundler` (Python 3.10+)
- Frameworks: Typer, Playwright, Pydantic, BeautifulSoup4, Markdownify, Pytest
- Plan: `planning/EXECUTION_PLAN_2.md`
- State: `planning/STATE_2.md`

## Task Instructions
1. Inspect files in scope for your task ID using anchors provided in `planning/EXECUTION_PLAN_2.md`.
2. Do not modify files outside your assigned `files in scope`.
3. Adhere to conventional commit standards upon completion (e.g. `refactor(extract): deduplicate title extraction and clean AST DOM traversal`).
4. Execute the targeted acceptance test command before marking task complete in `STATE_2.md`.

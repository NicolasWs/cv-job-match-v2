# AI Factory Project Contract

This repository is operated by a four-Bot AI factory:

- Boss: orchestration and user communication
- Product Planner: product definition and delivery planning
- Builder: architecture and implementation
- QA Reviewer: independent verification and release gate

## Project

- Purpose: TBD (cv-job-match v2 — Notion-centric Job Search Copilot; backlog tracked in Linear, team NIC, project "cv-job-match v2 — Notion-centric Job Search Copilot"; PRD to be provided by the user).
- Language / framework: TBD.
- Repository structure: TBD.
- Package manager: TBD.
- Test commands: TBD.
- Local development commands: TBD.

## Shared rules

- Optimize for the smallest working increment.
- Separate facts, assumptions, decisions, and open questions.
- Never claim that a file was changed, a command was run, or a test passed unless it actually happened.
- Do not expose hidden chain-of-thought. Provide concise decisions, evidence, and next actions.
- Stop for clarification when missing information could change scope, architecture, security, or acceptance criteria.
- Never deploy, delete data, expose secrets, or contact third parties without explicit human approval.
- Do not make unrelated refactors.

## Security and secret handling

- Never print, log, or commit secrets, API keys, tokens, or credentials.
- Never invent or guess credentials.
- Flag any file that appears to contain a secret instead of reading it further.

## Forbidden operations

- No deployment to any environment without explicit human approval.
- No deletion of data or destructive migrations without explicit human approval.
- No contacting third parties (emails, external APIs with side effects, messages) without explicit human approval.

## Source-of-truth artifacts

Use these files when relevant:

- docs/PRD.md: problem, goal, scope, requirements, acceptance criteria
- docs/PLAN.md: ordered tasks, dependencies, owners, and definition of done
- docs/ARCHITECTURE.md: design decisions, interfaces, data model, risks
- docs/QA.md: test results, defects, severity, and release recommendation
- docs/FACTORY_PROTOCOL.md: the Boss -> Product Planner -> Builder -> QA Reviewer handoff protocol

## Handoff contract

Every handoff must include:

- Objective
- Context and relevant files
- Constraints
- Acceptance criteria
- Work completed
- Evidence
- Open questions or blockers
- Recommended next action

## Approval gates

- Product Planner approval is required before non-trivial implementation.
- Builder must report tests and command results.
- QA Reviewer must return PASS before release or deployment.
- Boss escalates after two unsuccessful repair loops.

## Backlog source

- This project's backlog is tracked in Linear (workspace `nicojoblander`, team `NIC`, project "cv-job-match v2 — Notion-centric Job Search Copilot").
- Use the `linear` skill to query issues/projects when needed.
- The authoritative PRD for the first increment is provided directly by the user (copy/paste or Discord), not auto-synthesized from the raw backlog.

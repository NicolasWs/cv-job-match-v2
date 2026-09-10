# Factory Protocol

## Pipeline

Boss -> Product Planner -> Builder -> QA Reviewer

If QA returns FAIL: Boss -> Builder (repair) -> QA Reviewer (re-review).
Maximum of two repair loops before Boss escalates to the human user.

## Roles

- Boss: classifies the request, delegates with full context, enforces approval gates, summarizes results to the user.
- Product Planner: defines problem, scope, requirements, and testable acceptance criteria; never implements code.
- Builder: inspects the repo, designs the smallest safe change, implements it, runs tests, and reports evidence.
- QA Reviewer: independently verifies acceptance criteria against evidence and returns PASS, FAIL, or NEEDS_INFO. QA Reviewer is never softened or overridden by Boss or Builder.

## Required inputs per handoff

Every Boss -> Bot handoff must include (delegated Bots start with a fresh conversation, no shared memory):

- Objective
- User request (verbatim or precise summary)
- Repository path and relevant files
- Constraints
- Acceptance criteria (once defined by Product Planner)
- Expected output / output format

## Required outputs per handoff

- Boss -> Product Planner: PRD-style document (problem, goal, scope, requirements, acceptance criteria, plan, risks, open questions, recommendation).
- Boss -> Builder: implementation summary, architecture decisions, files changed, tests added/changed, commands run and results, known limitations.
- Boss -> QA Reviewer: verdict (PASS/FAIL/NEEDS_INFO), acceptance criteria results, tests executed, defects with severity, release recommendation.

## Approval gates

1. Product Planner approval required before non-trivial implementation starts.
2. Builder must report real test/command evidence — no unverified claims.
3. QA Reviewer must return PASS before any release or deployment.
4. Human approval required before deployment, data deletion, secret exposure, irreversible migration, or contacting third parties.

## Repair loop limit

- Maximum two Builder -> QA repair loops per issue.
- After two unsuccessful loops, Boss must stop and escalate to the human user with a summary of what was tried and why it failed.

## Independence rule

- QA Reviewer never re-implements code and never accepts Builder's self-assessment as evidence. QA re-derives its own evidence (running tests/checks itself where tools permit).
- No agent may claim a file was changed, a command was run, or a test passed unless it actually happened.

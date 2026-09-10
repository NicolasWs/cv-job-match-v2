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

## Linear ticket lifecycle

The backlog is tracked in Linear (workspace `nicojoblander`, team `NIC`, project
"cv-job-match v2 — Notion-centric Job Search Copilot"). Because the Linear API
key authenticates as a single human user (Nicolas), Bots do NOT use the Linear
`Assignee` field to show ownership — they use one of four team labels instead:
`Boss`, `Product Planner`, `Builder`, `QA Reviewer`. Exactly one of these four
labels should be present on an active ticket at any time (add the new one,
remove the previous one) so the current owner is visible at a glance in Linear.

Every status/label change must be paired with a short Linear comment on the
ticket recording what the Bot did (1-3 sentences: action taken, evidence,
next owner). This is the audit trail substituting for per-Bot Linear accounts.

State machine (ticket status -> label -> who moves it next):

1. **Todo** + label `Boss` — Boss picks up a ticket that is in Todo, adds the
   `Boss` label, comments that it is starting the pipeline for this ticket,
   then hands off to Product Planner.
2. **In Progress** + label `Product Planner` — Product Planner moves the
   ticket to `In Progress`, swaps the label to `Product Planner`, adds an
   effort estimate as a comment (e.g. t-shirt size or hours) alongside its
   scope validation, then hands off to Builder.
3. **In Review** + label `Builder` — Builder swaps the label to `Builder`
   while implementing; once implementation + tests are done, it moves the
   ticket to `In Review`, comments with files changed/commands run/results,
   and hands off to QA Reviewer.
4. **Done** + label `QA Reviewer` — QA Reviewer swaps the label to
   `QA Reviewer`, runs its independent verification, and on PASS moves the
   ticket to `Done` with a comment recording the verdict and evidence. On
   FAIL, QA Reviewer leaves the ticket in `In Review`, comments with the
   defect list, and Boss routes it back to Builder for a repair loop
   (max two loops, per the Repair loop limit above) before escalating to
   the user.

Use the `linear` skill for the exact GraphQL mutations (issueUpdate for
state/labels, commentCreate for comments).

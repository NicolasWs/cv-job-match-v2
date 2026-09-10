# NIC-45 (P1-T4) — Product Planner Scope Validation

**Ticket:** NIC-45 — "P1-T4 — Notion as sole tracker of record for newly selected jobs"
**Traces to:** FR-D5, US-11 (docs/PRD.md)
**Depends on:** P1-T1 / NIC-42 (Notion Kanban DB) — **Done**
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-10
**Role boundary respected:** no code/content implementation performed; this is scope definition only.

---

## 1. Objective

Validate the scope of NIC-45 against the approved PRD (FR-D5, US-11, OQ-4) and the actual state of both repos, then produce a Builder-ready delivery plan that makes the Google Sheet tracker deprecated-for-new-entries and Notion the sole tracker of record for newly selected jobs going forward — without migrating data and without any destructive change to the live v1 production pipeline.

## 2. Context and relevant files

**Two repositories are in play — this is the central scoping fact for this ticket:**

| Repo | Role | Files touched by this ticket |
|---|---|---|
| `/home/nicow/cv-job-match-v2` (this repo) | v2 rebuild, docs/PRD source of truth | `docs/PLAN.md` (record shipped status) |
| `/home/nicow/cv-job-match` (v1, **sibling repo, active production pipeline**) | Currently running weekly n8n scrape + 5 Claude skills; NOT part of this repo | `tracker/job-tracker-model.md`, `.claude/skills/run-my-week/SKILL.md` |

Confirmed by direct read (read-only, as instructed):

- `tracker/job-tracker-model.md` in the v1 repo is a **design/reference document** (column spec, formulas, sample rows) for the tracker — it is *not* the live spreadsheet itself. The live Google Sheet is a separate Drive resource: "Job Application Tracker — Nicolas", ID `1byMx-OFX0HM6rjCdKP4bKYdvEPuLvEOVWlx8C0iiUPE` (documented in v1's `context/tracker.md`).
- The **only live code path that writes new rows** to that Sheet is step 5 ("Log and close the loop") of `.claude/skills/run-my-week/SKILL.md`: *"append a row to the real Job Application Tracker — Nicolas Google Sheet via the Drive connector … using the tracker's real columns (`tracker/job-tracker-model.md`)."* `find-opportunities` explicitly does **not** write to this sheet (it keeps a separate local screening list); `app/server.py`'s `/api/log` endpoint only formats a row for manual copy-paste, it doesn't write either.
- Consequence: **marking `tracker/job-tracker-model.md` as deprecated is a documentation change only — it does not, by itself, stop new Sheet entries.** To satisfy AC3 ("Google Sheet is not updated for new entries"), the `run-my-week` skill instructions themselves must be changed to stop directing the agent to log there. This is an edit to a live, active-production skill file (v1 repo), not a docs-only edit in v2 — flagged explicitly per the task's own IMPORTANT REPO NOTE and AGENTS.md forbidden-operations rule (no destructive change to production without explicit approval).
- v2's own Notion side is only partially built: NIC-42 (Done) created the Kanban **database schema** — Status/Company/Role/Priority properties — but **no card/page yet exists and no skill or automation to create one exists in this repo.** P1-T2 (NIC-43, per-job page template) and P1-T3 (NIC-44, conversational Kanban status updates) are both still **Backlog**, not dependencies declared on this ticket.

Relevant files read: `AGENTS.md`, `docs/FACTORY_PROTOCOL.md`, `docs/PRD.md` (§5, §6.1, §6.2, FR-D5, US-11, OQ-4), `docs/PLAN.md`, `docs/ARCHITECTURE.md` (NIC-42 evidence), and in the v1 repo (read-only): `tracker/job-tracker-model.md`, `context/tracker.md`, `CLAUDE.md`, `README.md`, `.claude/skills/run-my-week/SKILL.md`, `.claude/skills/find-opportunities/SKILL.md`, `app/server.py`.

## 3. Constraints

- **Do not migrate or backfill any historical data** into Notion (FR-D5, OQ-4 explicitly resolved "No").
- **No deletion of the Google Sheet or its historical rows** — it is retained read-only, indefinitely, for historical reference.
- **v1 repo is an active production pipeline** (weekly n8n scrape + skills used by Nicolas today). Any edit there must be additive/non-destructive: a deprecation notice and an instruction-text change to one skill step, not a rewrite, deletion, or restructuring of the repo. No destructive migration without explicit human approval (AGENTS.md).
- No new infrastructure, no auto-apply/auto-send anywhere (unchanged hard rule).
- Product Planner (this Bot) must not implement any of the above — scoping only.

## 4. Acceptance criteria (validated, restated as testable)

| # | Criterion | Source | Testable check |
|---|---|---|---|
| AC1 | `tracker/job-tracker-model.md` carries a visible deprecation notice (as-of date, "read-only, historical reference only", pointer to the Notion DB) and its content is otherwise unchanged/undeleted. | FR-D5 | Diff shows only an added header block; no rows/sections removed. |
| AC2 | No script, mutation, or migration copies existing Sheet rows into Notion. | FR-D5, OQ-4 | Repo diff contains no data-migration code/calls; Builder's evidence log shows zero Notion `pages.create` calls seeded from Sheet data. |
| AC3 | `run-my-week/SKILL.md` step 5 no longer instructs the agent to write new rows to the Google Sheet; it instructs tracking newly selected jobs in the Notion DB (`database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`) instead — manual card creation is acceptable until NIC-43/NIC-44 ship (see §6 risk). | US-11 | Reading the updated skill file shows no remaining "append a row… Google Sheet" instruction; a Notion-tracking instruction replaces it. |
| AC4 | Sheet stays reachable/functional for historical read (no access revoked, no rows touched). | FR-D5 | Manual spot-check: sheet still opens, prior rows intact. |

## 5. Work completed (Product Planner phase)

- Confirmed NIC-42 dependency is genuinely Done (schema, IDs verified against `docs/ARCHITECTURE.md`).
- Located and read (read-only) the actual file referenced by the ticket in the v1 sibling repo; confirmed it is a design doc, not the live Sheet.
- Traced the single production code path that writes to the Sheet (`run-my-week` step 5) — this was not obvious from the ticket text alone and materially changes what "deprecate the Sheet" requires.
- Cross-checked full Linear backlog (NIC-5…NIC-53) to confirm NIC-45 has no undeclared dependency on NIC-43/NIC-44 — none of the other P1 tickets are marked as blocking it, and the AC as written is satisfiable without them (manual Notion card entry is sufficient in the interim).
- No code, skill files, or Linear ticket content were altered as part of this analysis beyond the Linear status/label/comment updates described below (which are this ticket's own required workflow step, not implementation).

## 6. Evidence

- `docs/PRD.md` lines 84, 92, 140, 228, 271 (FR-D5, OQ-4, US-11, non-goal on backfill).
- `docs/PLAN.md` lines 7, 15–35 (NIC-42 Done, schema-only, no cards).
- `docs/ARCHITECTURE.md` lines 41–105 (NIC-42 created IDs: `database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `data_source_id 47340a66-9e15-4ea1-8edf-45bba44c2334`).
- v1 repo (read-only): `tracker/job-tracker-model.md` (full content read, confirmed design-doc format, no deprecation notice present yet); `context/tracker.md` line 3–5 (live Sheet ID); `.claude/skills/run-my-week/SKILL.md` lines 76–84 ("Log and close the loop" — the only Sheet-write path); `.claude/skills/find-opportunities/SKILL.md` line 13–17 (explicitly *not* the tracker); `app/server.py` lines 325–333 (`/api/log` is copy-paste formatting only, not a write).
- Linear: full NIC team issue list queried directly (`issues` GraphQL query) — confirmed NIC-43/NIC-44 are Backlog with no dependency edge onto NIC-45.

## 7. Open questions / blockers

- **OQ-A (not blocking):** "Ship date" for the AC3 cutover isn't a fixed calendar date anywhere in the docs — recommend it be defined as the date this ticket (NIC-45) is merged/shipped, recorded in `docs/PLAN.md`, since that's the natural, auditable trigger.
- **OQ-B (flag, not blocking):** Until NIC-43 (page template) and NIC-44 (conversational status updates) ship, "tracking in Notion" for newly selected jobs means Nicolas manually creating a card in the existing Kanban DB via the Notion UI — functionally fine (DB is Done, UI-usable today) but worth surfacing to Nicolas so expectations are set: no automated card creation yet.
- **No blockers to starting Builder work.**

## 8. Recommended next action

Hand off to **Builder** with this explicit, narrow scope (do not expand beyond it):

1. In `/home/nicow/cv-job-match` (v1, sibling repo — confirm this exact path before editing): add a short deprecation header to `tracker/job-tracker-model.md` (as-of date = ship date, "read-only / historical reference only", one-line pointer to the new Notion Job Search Kanban DB). Additive only — do not remove/restructure existing content.
2. In the same v1 repo: edit `.claude/skills/run-my-week/SKILL.md` step 5 ("Log and close the loop") to remove the Google Sheet write instruction and replace it with an instruction to track the job in the Notion Kanban DB (`database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`), noting manual card creation is expected until NIC-43/NIC-44 ship.
3. In this repo (`cv-job-match-v2`): update `docs/PLAN.md` recording NIC-45 shipped, the ship-date decision (OQ-A), and a note on the interim manual-entry gap (OQ-B).
4. No Notion API writes, no Sheet data deletion, no migration script — this ticket is instruction/documentation text only, in two repos.
5. Builder reports files changed (both repos, explicit paths) + diffs as evidence per the handoff contract, then hands to QA Reviewer, who should independently verify: (a) Sheet still intact/readable, (b) no data-migration code exists, (c) `run-my-week` no longer references the Sheet write.

**Effort estimate:** **XS/S (~1.5–2 hours)** — two small, additive text edits across two repos plus one docs update; no new infrastructure, no automation build, no code.

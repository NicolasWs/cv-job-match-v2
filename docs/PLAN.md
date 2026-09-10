# PLAN — cv-job-match v2

Ordered tasks, dependencies, owners, and definition of done. Backlog source of truth is Linear (team NIC). This file tracks what has actually shipped per increment, in build order.

## Rollout phases (per PRD Section 12)

1. **Phase 1** — Notion Kanban database (schema only, no cards/automation). **<- NIC-42, DONE (schema only)**; per-job page template (Track A helper) — **NIC-43, DONE (this increment)**
2. Phase 2 — Native file attachments (tailored CV, cover letter) on job pages.
3. Phase 3 — `company-research` skill + brief attachment.
4. Phase 4 — Interview cheat sheet for every interview-stage job; decommission CV Coach cron.
5. Phase 5 — n8n Notion-polling automation (FR-G), built last (highest risk).

---

## NIC-42 — P1-T1 — Notion Kanban database with 9-status property

**Status:** DONE (schema only — no seed cards, per explicit scope decision)
**Owner:** Builder
**Date:** 2026-09-10

### Definition of done
- [x] New Notion database created as a child of the existing "Job Search" page (`page_id 3ab05073-c5b0-8061-bc12-e92aa903bebc`), not a new top-level page.
- [x] `Status` property is Notion's native `status` type (not `select`), with exactly the 9 confirmed option values, correctly grouped for board-view support.
- [x] `Company` (rich_text), `Role` (rich_text), `Priority` (select: High/Med/Low) properties present.
- [x] All four filterable properties (Status, Priority, Company, Role) verified queryable via `POST /v1/data_sources/{id}/query`.
- [ ] **NOT done, out of scope for this ticket:** any Kanban *board view* configuration (API cannot create/configure views — manual Notion UI step, see Known limitations in ARCHITECTURE.md).
- [ ] **NOT done, deliberately deferred:** seed job cards. No job/card pages were created — this ticket ships schema only, per explicit no-fabrication decision (oneshot run, no interactive user available to seed real pipeline data).

### Evidence
See docs/ARCHITECTURE.md "NIC-42 — Notion Kanban Database" section for full API evidence (created IDs, schema verification JSON, filter query results).

### Dependencies / follow-ups (not this ticket)
- Manual: user adds a Board view in Notion (View → Add View → Board, group by Status).
- Future ticket: seed real job cards once the user has actual pipeline data to enter (no fabricated data was created here).
- Future ticket (Phase 2+): file attachments, company-research skill, cheat sheet automation, n8n polling — per PRD Sections 6.1 and 12.

---

## NIC-45 — P1-T4 — Notion as sole tracker of record for newly selected jobs

**Status:** PARTIALLY SHIPPED / IN PROGRESS (v2-side policy decision recorded; v1-repo implementation deferred pending human approval)
**Owner:** Builder
**Date:** 2026-09-10

### Scope split (why this ticket is not fully shippable in this increment)

Satisfying this ticket's three acceptance criteria in full requires edits in **two repositories**:

- `/home/nicow/cv-job-match-v2` (this repo, docs only) — **in scope, done this increment.**
- `/home/nicow/cv-job-match` (v1, sibling repo, **active production pipeline**) — **out of scope this increment**, escalated to the human for approval before touching a live production skill (AGENTS.md forbidden-operations rule: no destructive/behavioral change to production systems without explicit human approval). Boss ran in unattended/oneshot mode with no user available to confirm, so the v1 edit was deliberately **not authorized** this round.

### Ship-date decision (resolves Product Planner's OQ-A)

**Ship date for the "Notion is sole tracker of record for newly selected jobs" policy: 2026-09-10** (date of this ticket's Builder work). From this date forward, the *policy* is that newly selected jobs are tracked in Notion, not the Google Sheet — recorded here as the v2-side decision of record. Actual enforcement of that policy (i.e., the production skill no longer writing to the Sheet) is **not yet in effect**, see below.

### Definition of done

- [x] **AC-policy (v2-side):** Ship-date decision for the Notion-sole-tracker policy documented here, in this repo, as the source of truth for the going-forward policy (FR-D5, US-11).
- [ ] **AC1, NOT done this increment, deferred:** `tracker/job-tracker-model.md` in the **v1 repo** carries a deprecation header (as-of date, read-only/historical-reference-only, pointer to the Notion DB). Requires editing a file in the v1 production repo — deferred to a new, separate Linear ticket requiring explicit human approval before any v1 production file is touched.
- [ ] **AC3, NOT done this increment / only partially met, deferred:** `.claude/skills/run-my-week/SKILL.md` step 5 in the **v1 repo** still instructs the agent to append new rows to the live Google Sheet — this is the only production code path that writes new tracker entries, and it is **untouched**. Editing it is deferred to the same new, separate, human-approved ticket. **AC3 as originally written ("Google Sheet is not updated for new entries") is not yet satisfied in production; only the v2-side policy statement is in place.**
- [x] **AC2 (no migration):** No data migration or backfill was performed or scripted — confirmed out of scope, nothing done, nothing to undo. Zero Notion API calls were made as part of this increment.
- [x] **AC4 (Sheet stays reachable):** No Sheet access was touched, no rows modified — untouched by definition since no v1-repo or Notion work occurred in this increment.

### Interim manual-entry gap (Product Planner's OQ-B, unresolved, not blocking)

Until NIC-43 (per-job page template) and NIC-44 (conversational Kanban status updates) ship, "tracking in Notion" for any newly selected job means **manual card creation via the Notion UI** — there is no skill or automation in this repo yet that creates a job card. The Kanban database itself (NIC-42, Done) is fully usable today for this manual workflow: `database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, under the existing "Job Search" Notion page. This gap is independent of the v1/v2 split above and will remain until NIC-43/NIC-44 ship, regardless of when the v1 Sheet-write instruction is removed.

### Evidence

- Product Planner scope validation: `docs/handoffs/NIC-45-product-planner-scope-validation.md` (full investigation, AC table, v1 `run-my-week/SKILL.md` step 5 traced as the sole Sheet-write path).
- This entry itself (`docs/PLAN.md`) is the only file changed by Builder in this increment. No other file in this repo, and no file in the v1 repo, was modified.

### Dependencies / follow-ups (not this ticket)

- **New Linear ticket required (human-approval-gated):** add deprecation header to v1's `tracker/job-tracker-model.md`, and edit v1's `.claude/skills/run-my-week/SKILL.md` step 5 to stop writing to the Google Sheet and instead instruct (manual, until NIC-43/NIC-44) tracking in the Notion Kanban DB (`database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`). Must not proceed without explicit human sign-off, since it changes an active production pipeline skill.
- NIC-43 (per-job Notion page template) and NIC-44 (conversational Kanban status updates) remain Backlog; once shipped they remove the manual-card-creation gap noted above.

---

## NIC-43 — P1-T2 — Per-job Notion page template

**Status:** DONE (Track A — API-driven block helper, implemented and verified with one archived test card; Track B — Notion-native UI template — documented as a non-blocking manual recommendation, NOT configured by Builder)
**Owner:** Builder
**Date:** 2026-09-11

### Definition of done

- [x] Reusable 14-block `children` helper implemented at `scripts/notion_job_page_blocks.py` (`build_job_page_children()`), producing the 5-section structure (Job Details → Company Research Brief → Tailored CV → Cover Letter → Interview Cheat Sheet) specified in `docs/handoffs/NIC-43-product-planner-scope-validation.md` §7.
- [x] Verified end-to-end with exactly **one** test card: `POST /v1/pages` (`parent.database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, test `properties`, full `children` array) in a single request → `200 OK`, page id `3d705073-c5b0-814a-9ea3-e76663da7b28`.
- [x] `GET /v1/blocks/{page_id}/children` confirmed exactly 14 blocks in the specified order, correct heading/callout text (AC1, AC2 satisfied).
- [x] `properties` + `children` sent in the same `POST /v1/pages` call — no follow-up call needed (AC3 satisfied for API-driven creation).
- [x] Test card archived immediately after evidence capture: `PATCH /v1/pages/{page_id}` `{"archived": true}` → confirmed `200 OK`, `"archived": true`. No fabricated data left live in the production Notion database.
- [x] Block schema, `pages.create` call shape, and Track A/Track B distinction documented in `docs/ARCHITECTURE.md` ("NIC-43 — Per-job Notion page template" section).
- [ ] **NOT done, deliberately deferred (non-blocking per scope doc §5/§9/OQ-2):** Track B — a matching Notion-native database template configured by hand in the Notion UI, for the current manual "+ New" card-creation workflow. Documented as a recommendation in `docs/ARCHITECTURE.md`, not implemented — requires human UI interaction, same category of gap as NIC-42's Kanban board-view limitation.
- [ ] **NOT done, explicitly out of scope (per scope doc §5):** no card-creation skill/trigger built (that's NIC-44); no real section content populated (Phase 2/3/4 work); no NIC-42 schema changes; no n8n automation touched.

### Evidence

See `docs/ARCHITECTURE.md` "NIC-43 — Per-job Notion page template" section for full API evidence: block schema table, exact `pages.create` request shape, test-card creation response (id/url), `blocks/children` GET confirming the 14-block structure, and the archive-confirmation response.

### Dependencies / follow-ups (not this ticket)

- Manual, optional: Nicolas (or a future ticket) configures the Track B Notion-native database template in the Notion UI, mirroring the same 5 sections — flagged, not blocking.
- NIC-44 (conversational Kanban status updates) or a later automation ticket should call `scripts/notion_job_page_blocks.py`'s `build_job_page_children()` as part of any programmatic card-creation flow, so every API-created card gets the structure automatically.
- Phase 2/3/4 work (file attachments, company-research skill, interview cheat sheet automation) will locate and replace/append near each section's placeholder `callout` block once real content exists — see ARCHITECTURE.md note on `file` blocks not being creatable empty.

---

## Backlog (not yet started)

Tracked in Linear (team NIC, project "cv-job-match v2 — Notion-centric Job Search Copilot"). Query Linear directly for the current open ticket list beyond NIC-42/NIC-43; this file only records what Builder has actually shipped, to avoid drift between Linear and this doc.

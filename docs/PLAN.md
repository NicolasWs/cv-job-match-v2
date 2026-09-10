# PLAN — cv-job-match v2

Ordered tasks, dependencies, owners, and definition of done. Backlog source of truth is Linear (team NIC). This file tracks what has actually shipped per increment, in build order.

## Rollout phases (per PRD Section 12)

1. **Phase 1** — Notion Kanban database (schema only, no cards/automation). **<- this increment (NIC-42), DONE (schema only)**
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

## Backlog (not yet started)

Tracked in Linear (team NIC, project "cv-job-match v2 — Notion-centric Job Search Copilot"). Query Linear directly for the current open ticket list beyond NIC-42; this file only records what Builder has actually shipped, to avoid drift between Linear and this doc.

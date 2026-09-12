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

## NIC-46 — P2-T1 — Native Notion file attachment for tailored CV

**Status:** DONE (attachment mechanism implemented and verified live with one archived test card; synthetic PDFs used for verification per explicit ticket authorization — see known limitations)
**Owner:** Builder
**Date:** 2026-09-11

### Definition of done

- [x] Reusable file-attachment mechanism implemented at `scripts/notion_cv_attachment.py`: 3-step `file_uploads` flow (`create_file_upload`/`put_file_bytes`/`upload_pdf`), Tailored CV section locator (`find_tailored_cv_section`, heading-agnostic so it's reusable for FR-E2), and final-version-only replace logic (`attach_final_cv`) that inserts the new `file` block then archives whatever `callout`/`file`/`paragraph` blocks previously occupied the section.
- [x] Option A (block-level `file` object, per Product Planner scope doc §6) implemented — no NIC-42 schema change, reuses NIC-43's page-content structure.
- [x] AC1 verified live: real `file_uploads` 3-step flow executed, `file` block appears under "📄 Tailored CV" heading, fetched the resulting presigned S3 URL directly and confirmed byte-for-byte match (`Content-Type: application/pdf`, `Content-Length: 498`) against the uploaded synthetic PDF.
- [x] AC2 verified live: attached once (1 file block), simulated a "revised CV" re-attach with a different (506-byte) synthetic PDF on the same test card, re-fetched the block list — still exactly 1 file block (old one archived, not appended), confirmed by refetching and byte-comparing the new file's content.
- [x] AC3 verified: `content_type: "application/pdf"` sent on both `file_uploads` create calls; both resulting blocks/file objects reflect `.pdf` filenames and `application/pdf` content type.
- [x] AC4 verified: only the dedicated test card (`page_id 3d805073-c5b0-8174-9372-c114f6c398b4`, hardcoded, never name-matched) was touched; baseline vs. post-work `POST /v1/data_sources/{id}/query` comparison confirmed all 5 real cards' `page_id`/`Name`/`last_edited_time` unchanged.
- [x] AC5: explicitly documented (here and in ARCHITECTURE.md) that both test PDFs were small synthetic/dummy files (498 and 506 bytes) generated purely for mechanism verification — not a real `cv-match` output, no real end-to-end run performed or claimed.
- [x] AC6: test card built via `build_job_page_children()` (Name: "TEST NIC-46 verification", Company/Role: TEST, Status: selected), evidence captured, then `PATCH /v1/pages/{page_id}` `{"archived": true}` → `200 OK`, confirmed via a follow-up `GET` showing `archived: true`. Test card no longer appears in live database queries.
- [ ] **NOT done, explicitly out of scope (per scope doc §5):** no change to `cv-match`'s analysis/refinement logic; no PDF-export step built inside `cv-match` (confirmed real gap, flagged as follow-up OQ-A); FR-E2 (cover letter attachment) not implemented or verified (mechanism is reusable by design but untested against that heading); FR-E3 (file naming convention) not formally confirmed, only approximated for the test filename; no NIC-42 schema changes; no card-creation skill/automation; no n8n automation touched.

### Evidence

See `docs/ARCHITECTURE.md` "NIC-46 — Tailored CV Notion file attachment" section for full API evidence: design decision rationale, exact call shapes (including a correction to the generic 3-step flow — step 2 is `POST {upload_url}` multipart, not a raw `PUT`, confirmed live), and the complete request/response evidence trail for AC1–AC6 (test card create, structure check, attach-v1, byte-fetch verification, attach-v2/no-accumulation check, real-cards-untouched diff, and the final archive + re-verification).

### Dependencies / follow-ups (not this ticket)

- **Recommended new ticket (OQ-A):** PDF-export step for `cv-match` (and `write-outreach`) — the actual prerequisite for a true end-to-end Phase 2 flow (real tailored CV → real PDF → Notion). This ticket's mechanism is ready and waiting for that input.
- **CLOSED by NIC-62 (2026-09-11/12):** the PDF-export step above now exists (`scripts/render_markdown_to_pdf.py`). NIC-62's real end-to-end run rendered the real NEXTON `cv-v2.md` and attached the resulting PDF via this ticket's own unmodified `attach_final_cv()` — see NIC-62's `docs/PLAN.md` entry and `docs/ARCHITECTURE.md` section for full evidence.
- **Recommended fast-follow (OQ-B):** FR-E2 cover letter attachment — same mechanism (`attach_final_cv()` in `scripts/notion_cv_attachment.py`) is reusable via its `heading_text` parameter; not implemented or verified against the "✉️ Cover Letter" heading in this ticket.
- File-size/workspace-plan limits were not empirically probed (`GET /v1/users/me` not called) — flagged as a theoretical risk for future large real CV files, not ruled out with evidence here.

---

## NIC-47 — P2-T2 — Native Notion file attachment for cover letter

**Status:** DONE (attachment mechanism reused unmodified via a thin wrapper, verified live with one archived test card; synthetic PDF used for verification per explicit ticket authorization — see known limitations)
**Owner:** Builder
**Date:** 2026-09-11

### Definition of done

- [x] NIC-46's `attach_final_cv()` mechanism reused **unmodified** (zero lines changed in `scripts/notion_cv_attachment.py`) via a new thin wrapper module `scripts/notion_cover_letter_attachment.py`, exposing `COVER_LETTER_HEADING` constant and `attach_final_cover_letter(page_id, pdf_path, filename)` convenience function that calls `attach_final_cv(..., heading_text=COVER_LETTER_HEADING)`.
- [x] AC1/AC2 verified: `write-outreach/SKILL.md` (v1 repo) confirmed byte-for-byte unchanged (`sha256sum` identical before/after, `git status`/`git log` show no touch) — non-regression confirmation, no new drafting-quality testing performed.
- [x] AC3 verified live: real `file_uploads` 3-step flow executed, `file` block appears under "✉️ Cover Letter" heading via `attach_final_cover_letter()`, resulting block carries a resolvable presigned S3 URL (not a Drive link), old NIC-43 placeholder callout archived.
- [x] AC4 verified live: fetched the resulting file's presigned URL directly, confirmed byte-for-byte match (`Content-Type: application/pdf`, `Content-Length: 633`) against the uploaded synthetic PDF.
- [x] AC5 verified: `content_type: "application/pdf"` sent on both `file_uploads` create calls; both resulting blocks/file objects reflect `.pdf` filenames and `application/pdf` content type.
- [x] AC6 verified live: attached once (1 file block), simulated a "revised letter" re-attach with a different (641-byte) synthetic PDF on the same test card, re-fetched the block list — still exactly 1 file block under Cover Letter (old one archived, not appended), confirmed by byte-comparing the new file's content against v2 (match) and v1 (no match).
- [x] AC7 verified: only the dedicated test card (`page_id 3d805073-c5b0-811a-9640-e652e54717fe`, hardcoded, never name-matched) was touched; baseline vs. post-work `POST /v1/data_sources/{id}/query` comparison confirmed all 5 real cards' `page_id`/`Name`/`last_edited_time`/`archived` unchanged; NIC-46's own archived test card independently re-fetched and confirmed still archived/untouched.
- [x] AC8: explicitly documented (here and in ARCHITECTURE.md) that both test PDFs were small synthetic/dummy files (633 and 641 bytes) generated purely for mechanism verification — not real `write-outreach` output, no real end-to-end run performed or claimed.
- [x] AC9: test card built via `build_job_page_children()` (Name: "TEST NIC-47 verification", Company/Role: TEST, Status: selected), evidence captured, then `PATCH /v1/pages/{page_id}` `{"archived": true}` → `200 OK`, confirmed via a follow-up `GET` showing `archived: true`. Test card no longer appears in live database queries.
- [ ] **NOT done, explicitly out of scope (per scope doc §5):** no change to `write-outreach`'s drafting/refinement logic; no PDF-export step built inside `write-outreach` (confirmed real gap, mirrors NIC-46's `cv-match` finding, flagged again as follow-up OQ-A); no change to `scripts/notion_cv_attachment.py`; FR-E3 (file naming convention) not formally confirmed, only approximated for the test filename; no card-creation skill/automation; no n8n automation touched; no NIC-42 schema changes.

### Evidence

See `docs/ARCHITECTURE.md` "NIC-47 — Cover Letter Notion file attachment" section for full API evidence: design decision rationale (thin wrapper chosen over direct call to keep NIC-46's file at zero changed lines), exact call shape used, and the complete request/response evidence trail for AC1–AC9 (non-regression check, test card create, structure check, attach-v1, byte-fetch verification, attach-v2/no-accumulation check, real-cards-and-NIC-46-test-card-untouched diff, and the final archive + re-verification).

### Dependencies / follow-ups (not this ticket)

- **Recommended new ticket (OQ-A, reinforced twice now):** PDF-export step for `cv-match` and `write-outreach` — the actual prerequisite for a true end-to-end Phase 2 flow (real cover letter → real PDF → Notion). Both this ticket's and NIC-46's mechanisms are ready and waiting for that input.
- **CLOSED by NIC-62 (2026-09-11/12):** the PDF-export step above now exists (`scripts/render_markdown_to_pdf.py`, including a cover-letter section extractor for write-outreach's combined output). NIC-62's real end-to-end run isolated and rendered the real NEXTON `outreach-v2.md`'s cover-letter section and attached the resulting PDF via this ticket's own unmodified `attach_final_cover_letter()` — see NIC-62's `docs/PLAN.md` entry and `docs/ARCHITECTURE.md` section for full evidence.
- File-size/workspace-plan limits still not empirically probed (`GET /v1/users/me` not called) — same theoretical-risk flag as NIC-46, not ruled out with evidence here either.
- FR-E3 (file naming convention) remains "proposed, not yet confirmed" — not required to pass this ticket's AC, same status as NIC-46 left it.

---

## NIC-48 — P2-T3 — Consistent file naming convention for job page attachments

**Status:** DONE (shared filename-builder helper implemented and unit-tested; verified live end-to-end with one archived test card; zero lines changed in either existing attachment script)
**Owner:** Builder
**Date:** 2026-09-11

### Definition of done

- [x] New, shared, pure-Python filename-builder helper implemented at `scripts/notion_attachment_naming.py`: `build_attachment_filename(company, role, kind, ext="pdf") -> str`, implementing the `{Company} - {Role} - {Kind}.{ext}` convention (FR-E3, US-7) with the exact 8-step sanitization rule from `docs/handoffs/NIC-48-product-planner-scope-validation.md` §5.
- [x] `kind` is a closed, validated set (`{"CV", "Cover Letter"}`) — raises `ValueError` on any other value, no case-insensitive guessing or silent normalization.
- [x] AC1 verified: `build_attachment_filename("Acme", "Backend Engineer", "CV")` → `"Acme - Backend Engineer - CV.pdf"` exactly; same pattern for `"Cover Letter"`; invalid `kind` (`"cv"`, `"Resume"`) raises `ValueError`.
- [x] AC2 verified via isolated unit tests (`/tmp/test_nic48_naming.py`, no network, 21/21 assertions PASS, exit code 0): `/`/`\` never in output; control characters removed; irregular whitespace collapses with no leading/trailing space; accented characters (`"Société Générale"`) pass through unchanged; all-control-char/empty/whitespace-only input falls back to `"Unknown Company"`/`"Unknown Role"` without raising; 300-char input truncates to the 80-char cap without corrupting the `.pdf` extension.
- [x] AC3 verified: `sha256sum` of `scripts/notion_cv_attachment.py` and `scripts/notion_cover_letter_attachment.py` identical before/after this ticket's work; `git diff` for both files empty. Zero lines changed in either shipped attachment script.
- [x] AC4 verified: `scripts/notion_attachment_naming.py`'s only import is `re` (Python standard library) — no new third-party dependency.
- [x] AC5 verified live: test card `page_id 3d805073-c5b0-8199-b502-f20fae30c2ce` created via `build_job_page_children()`; `build_attachment_filename(company="TEST Company/Ops", role="TEST Role: Lead", kind="CV")` → `"TEST Company Ops - TEST Role Lead - CV.pdf"`, confirmed locally, then passed unmodified into the existing `attach_final_cv()` — `GET /v1/blocks/{page_id}/children` confirmed the resulting `file` block's `name` field exactly equals that string. Repeated for `kind="Cover Letter"` via the existing `attach_final_cover_letter()` on the same test card — exact match confirmed again. Proves the unsafe characters (`/`, `:`) were genuinely sanitized in a real Notion object, not just locally.
- [x] AC6 verified: test card archived (`PATCH /v1/pages/{page_id}` `{"archived": true}` → `200 OK`, confirmed via follow-up `GET`). Before/after diff of `POST /v1/data_sources/{id}/query {}` confirms all 5 real production cards' `page_id`/`Name`/`last_edited_time`/`archived` values are identical, no new cards appear. NIC-46's and NIC-47's own archived test cards independently re-fetched and confirmed still archived/untouched.
- [x] AC7 (documentation): `docs/ARCHITECTURE.md` "NIC-48 — Attachment filename convention" section added (sanitization rule, call shape, full AC1–AC6 evidence); this `docs/PLAN.md` entry added.
- [ ] **NOT done, explicitly out of scope (per scope doc §6):** no changes to the Notion Kanban schema, page template, or n8n automation; no retroactive renaming of any already-attached file (none exist on real production cards); no integration into `cv-match`/`write-outreach` themselves (still no PDF-export step in the v1 repo, per NIC-46/NIC-47's own flagged gap); no formal reconfirmation ceremony with Nicolas on the exact naming string (FR-E3 remains "proposed, not yet confirmed" — flagged as OQ-C, non-blocking).

### Evidence

See `docs/ARCHITECTURE.md` "NIC-48 — Attachment filename convention" section for full evidence: exact sanitization rule (8 steps), call shape, and the complete AC1–AC6 evidence trail (isolated unit test run output, `sha256sum`/`git diff` proof of zero attachment-script changes, live Notion API test-card create/attach-CV/attach-Cover-Letter/verify/archive cycle, and the before/after real-cards-and-NIC-46/47-test-cards-untouched diff).

### Dependencies / follow-ups (not this ticket)

- **OQ-C (non-blocking):** the exact naming string (`{Company} - {Role} - {Kind}.pdf`) has not been formally reconfirmed by Nicolas — NIC-40 only settled the file *format* question (PDF), not this naming string. Recommend surfacing at next convenient touchpoint; isolated to one easily-changed function (`build_attachment_filename`) if the answer comes back different.
- **OQ-D (non-blocking):** `kind` could be extended to a third value (e.g. an interview cheat sheet PDF, Phase 4) once that attachment type actually ships — not needed today, kept as a closed 2-value set.
- Future `cv-match`/`write-outreach` → Notion integration (once a PDF-export step exists in the v1 repo) should call `build_attachment_filename()` to compute its `filename` argument, per this ticket's documented expectation — not enforced at the API boundary (accepted limitation, see ARCHITECTURE.md).


---

## NIC-56 — LinkedIn Saved Jobs → Notion `selected`-card importer (semi-automated, Option c/d)

**Status:** DONE (semi-automated importer implemented and verified live with 9 archived test cards; Option (a) full LinkedIn automation explicitly NOT implemented, per hard constraint)
**Owner:** Builder
**Date:** 2026-09-11

### Definition of done

- [x] New script `scripts/notion_import_saved_jobs.py` implemented: parses a manually-provided, pipe-delimited (`Company | Role`) local text file/stdin (never fetches `linkedin.com`), deduplicates against existing non-archived Notion cards (and within the same batch), defaults to creating at most 5 non-duplicate cards unless `--all` is passed, and creates each card via the exact NIC-43 `POST /v1/pages` shape (`parent.database_id` + `properties` + `children=build_job_page_children()` in one call).
- [x] AC1 verified live: 7-entry synthetic input + 1 malformed line, no `--all` → exactly 5 cards created in input order, remaining 2 reported as `skipped_limit`; re-run with `--all` → exactly 2 new cards created, the original 5 correctly reported as duplicates (not re-created).
- [x] AC2 verified live: spot-checked created card has `Status="selected"` (exact), non-empty `Company`/`Role`.
- [x] AC3 verified live: `GET /v1/blocks/{page_id}/children` on the spot-checked card returns the exact same 14-block sequence (5 headings, types/order) documented in the NIC-43 ARCHITECTURE.md section.
- [x] AC4 verified live: seeded a test card with `Company="Acme"`/`Role="PM"`; importing `"  acme   |   pm"` (case/whitespace variant) skipped it as a duplicate, named it in the report with the matched `page_id`, and created no second card.
- [x] AC5/AC8 verified via static grep: zero `linkedin.com` references in executable code (2 matches, both in comments describing the constraint), exactly one hardcoded network base URL (`https://api.notion.com/v1`), imports limited to Python stdlib + the existing `notion_job_page_blocks` module.
- [x] AC6 verified live: one deliberately malformed line (no `|` separator) reported by exact line number and reason in both test runs; no card was ever created for it, no data fabricated.
- [x] AC7 verified live: all 9 test cards created during verification were archived (`PATCH` `{"archived": true}`, each independently re-confirmed via follow-up `GET`); before/after `POST /v1/data_sources/{id}/query {}` diff shows the 5 real production cards' `page_id`/`Name`/`last_edited_time` byte-for-byte unchanged (`diff` of the two captured outputs returns nothing).
- [x] Documentation: `docs/PRD.md` Section 6.1.a addendum, `docs/ARCHITECTURE.md` "NIC-56" section (design decision, input contract, call shapes, full AC1–AC8 evidence trail), this `docs/PLAN.md` entry.
- [ ] **NOT done, explicitly out of scope (per scope doc §5/§7, hard constraint):** Option (a) (browser automation / credentialed LinkedIn access) — not approved, not implemented, not attempted in any form. Option (b) (LinkedIn API) — confirmed unavailable, not a live option. No NIC-42 schema changes. No n8n automation touched. No job-URL capture (only `Company`/`Role` per the chosen input contract — see Known limitations in ARCHITECTURE.md).

### Evidence

See `docs/ARCHITECTURE.md` "NIC-56 — LinkedIn Saved Jobs → Notion `selected`-card importer (semi-automated)" section for full evidence: design decision rationale, the exact pipe-delimited input contract (Builder's resolution of scope doc OQ-3), module API surface, and the complete AC1–AC8 evidence trail (baseline query, two-run limit/dedup interaction test, dedup-normalization test, created-card structure spot-check, static LinkedIn-access grep, malformed-line reporting, and the before/after real-cards-untouched diff).

### Dependencies / follow-ups (not this ticket)

- **Option (a) (full LinkedIn automation)** remains a distinct, larger, explicitly-unapproved follow-up — requires a new Linear ticket with Nicolas's own explicit, informed written sign-off on the ToS/account-risk tradeoff (scope doc §4/§12) before any Builder work begins on it.
- **Optional future enhancement (not required by this ticket's AC):** extend the input contract with an optional `| URL` third field and auto-populate the existing "Job Details" placeholder section with it, closing the small manual gap where Nicolas currently pastes the job posting link in by hand after card creation.
- **Input format stability:** the `Company | Role` pipe-delimited contract is a Builder-chosen implementation detail (scope doc explicitly left this open, OQ-3) — if real usage reveals it's too fragile against Nicolas's actual copy/paste habits, revisit the parser design; not a blocking concern for this ticket's AC.

---

## NIC-62 — Real PDF generation for tailored CV / cover letter

**Status:** DONE (reportlab-based markdown→PDF renderer implemented and verified with one real, non-synthetic end-to-end run: real NEXTON `cv-match`/`write-outreach` output rendered to real PDFs, attached to one archived test card, verified via GET + direct S3 fetch; zero lines changed in the three protected attachment/naming scripts)
**Owner:** Builder
**Date:** 2026-09-11/12

### Definition of done

- [x] New script `scripts/render_markdown_to_pdf.py` implemented (reportlab platypus, direct): stdlib-`re` markdown block parser (`#`/`##`/`###` headings, `**bold**`/`*italic*`/`[link](url)` inline spans, `- ` bullet lists as real bulleted `Paragraph` flowables, `---` dividers, full-bold-line "emphasis line" detection), a cover-letter section extractor (`extract_cover_letter_section()`) that isolates only `write-outreach`'s `## 1. Lettre de motivation`/`## 1. Cover Letter` section (stopping at `## 2.` or `---`), and a CLI (`--kind cv|cover-letter -o <out.pdf>`).
- [x] Cover-letter extractor fails loudly (`CoverLetterBoundaryError`, exit 3) rather than guessing when it cannot confidently locate both boundaries — independently re-verified this session against a hand-made file with no matching heading (correctly raised, no output file written) and against two other real, older `write-outreach` files (UpSlide, Euronext) that use an unnumbered heading format the extractor doesn't recognize (correctly raised, not silently mis-extracted — see Known limitations in ARCHITECTURE.md).
- [x] AC1/AC2 (layout quality) verified via `vision_analyze` on real, rendered NEXTON CV (3 pages) and cover-letter (1 page) page images: distinct header/subtitle, 2-level heading hierarchy, genuine bulleted lists, paragraph/salutation/closing spacing, zero visible literal markdown syntax (`#`, `##`, `**`, `- `) on any page.
- [x] AC3 (no cover-letter section leakage) verified via text-extraction grep of the rendered cover-letter PDF: zero occurrences of `Objet :`, `Message LinkedIn`, or the source section headings.
- [x] AC4 (PDF format) verified via `pdfinfo`: both real rendered PDFs are valid, non-encrypted PDF 1.4, page counts 3 and 1.
- [x] AC5/AC6 (unmodified attach functions + NIC-48 naming) verified by direct inspection of the real end-to-end run script (`/tmp/nic62_e2e.py`): literal unmodified imports/calls to `attach_final_cv()`/`attach_final_cover_letter()` and `build_attachment_filename(REAL_COMPANY, REAL_ROLE, kind)` — no hand-typed filenames, no wrapper/monkeypatch.
- [x] AC7 (real end-to-end run) verified: real `/home/nicow/cv-job-match/applications/2026-09-01_NEXTON_Product-Owner-IA-Generative/cv-v2.md` + `outreach-v2.md` → real PDFs (37610 / 17407 bytes) → real attach to test card `page_id 3d805073-c5b0-8100-816c-f3d9669dc376` → `GET /v1/blocks/{page_id}/children` confirms 2 `file` blocks → direct presigned-S3-URL fetch confirms `HTTP 200`, `application/pdf`, byte-exact content-length for both files → archived. Render step independently reproduced this session (byte-identical output); live Notion cycle not repeated a second time to avoid an unnecessary duplicate test card, per explicit task instruction.
- [x] AC8 (no production card touched) verified: before/after `POST /v1/data_sources/{id}/query {}` diff shows all 5 real cards' `page_id`/`Name`/`last_edited_time`/`archived` identical, confirmed programmatically.
- [x] AC9 (documentation): `docs/ARCHITECTURE.md` "NIC-62" section added (design decision, parser/extractor approach, layout mapping, full AC1–AC10 evidence trail); NIC-46/NIC-47 "Known limitations" sections updated with closure notes pointing here; this `docs/PLAN.md` entry added, and NIC-46/NIC-47's "Dependencies / follow-ups" sections updated to note OQ-A is now closed.
- [x] AC10 (zero changes to protected scripts / v1 repo) verified this session: `sha256sum` of `scripts/notion_cv_attachment.py`, `scripts/notion_cover_letter_attachment.py`, `scripts/notion_attachment_naming.py` match the hashes already recorded in NIC-48's own AC3 evidence, byte-for-byte; `git diff` empty for all three; `git status --porcelain=v1` in `/home/nicow/cv-job-match` shows only pre-existing, unrelated dirty state predating this ticket by two weeks (last commit `a490e5b`, Aug 27) — no entry attributable to NIC-62's read-only markdown consumption.
- [x] `python3 -m py_compile scripts/render_markdown_to_pdf.py` → exit code 0 (this session, re-run).
- [ ] **NOT done, explicitly out of scope (per scope doc §4.2):** no changes to `cv-match`/`write-outreach`'s analysis/scoring/drafting logic or `SKILL.md` files; no changes to `scripts/notion_cv_attachment.py`/`scripts/notion_cover_letter_attachment.py`/`scripts/notion_attachment_naming.py`; no new backend/service; no third-party cloud PDF-rendering API; no pandoc/wkhtmltopdf/weasyprint install; no production Notion card touched beyond the one archived test card; no n8n/card-creation/Kanban schema change; no handling of the older, unnumbered `write-outreach` heading format found in the UpSlide/Euronext robustness spot-check (flagged as a known limitation, not silently patched over).

### Evidence

See `docs/ARCHITECTURE.md` "NIC-62 — Real PDF generation for tailored CV / cover letter" section for full evidence: design decision rationale (reportlab direct vs. `soffice`/docx vs. rejected external-dependency options), the exact markdown→PDF layout mapping and cover-letter extractor logic, the Python-environment (`.venv/`) setup finding not anticipated by the scope doc, the complete real end-to-end evidence trail (real NEXTON files, byte counts, presigned-URL fetch confirmation, real-cards-untouched diff), this session's independent `vision_analyze`/text-extraction/`pdfinfo`/`sha256sum`/`git diff` re-verification of every AC, and the AC1–AC10 evidence summary table.

### Dependencies / follow-ups (not this ticket)

- **Follow-up recommended (not blocking):** extend `extract_cover_letter_section()`'s recognized heading patterns to also match the older, unnumbered `write-outreach` format (`## Cover Letter` / `## Recruiter / Hiring Manager Email`) observed in two real, pre-existing application folders (UpSlide, Euronext) during this ticket's own robustness spot-check — today those files correctly fail loudly rather than being rendered, which is safe but means they can't be PDF-exported without a follow-up change.
- File-size/workspace-plan limits still not empirically probed (`GET /v1/users/me` not called) — same theoretical-risk flag carried since NIC-46/47/48.
- **OQ-E/OQ-F/OQ-G (from the scope doc, all explicitly non-blocking):** no intermediate `.docx` debugging aid was built (OQ-E, not needed); no `write-outreach`/`cv-match` "offer to export to PDF" step was added inside the v1 skills (OQ-F, requires separate human approval to edit v1 skill files, out of scope here); the new script lives flat under `scripts/` matching repo convention (OQ-G resolved as recommended).

---

## NIC-52 — `company-research` skill: significant recent news

**Status:** DONE (recent-news component implemented as a fresh `SKILL.md` file — NIC-49's sibling had not landed first; verified live against one real company with genuine recent news and one quiet/small company)
**Owner:** Builder
**Date:** 2026-09-12

### Definition of done

- [x] New file `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md` created (v1 repo) — confirmed the file did not already exist before writing (scope doc §9 coordination protocol); created fresh with the full "Recent Company News" section plus a status table and placeholder headings for the three sibling sections (NIC-49/50/51) so those Builders have a consistent file to extend into.
- [x] FR-52.1 (search mechanism): native web-search/fetch only, recommended query pattern from scope doc §6 written into the skill verbatim.
- [x] FR-52.2 (significance filter, AC5): the five-category table (Funding/financial, Expansion, Leadership change, Restructuring, Product launch/partnership) with include/exclude examples written explicitly into the skill file, plus an "always excluded" list — not a vague judgment-call instruction.
- [x] FR-52.3 (recency cutoff, AC2): "today minus 6 calendar months at generation time" computation rule written as an explicit step; no-discoverable-date items discarded, not guessed.
- [x] FR-52.4 (per-item schema): exactly 4 fields (Headline, Date, Source, Why it matters) in order, as a literal template block.
- [x] FR-52.5/AC3 (max 3, cap enforcement): written as an explicit step; verified live against Mistral AI (4 in-window qualifying items found, capped to the 3 most significant).
- [x] FR-52.6/AC4 (exact "no significant news found" string): written verbatim with `{Company}` substitution; verified live against PALO IT (0 qualifying items across 4 real search queries → exact string is the correct output).
- [x] FR-52.7/AC8 (never pad): written as its own explicit step; not exercised against a live 1-or-2-item real-world case in this pass (see Known limitations in ARCHITECTURE.md).
- [x] FR-52.8/AC7 (retrieval stamp): `_Retrieved: {date}_` line specified as distinct from each item's own Date field.
- [x] AC6 verified via static grep: exactly 1 match for `linkedin\.com|Apify|news API|paid actor` in the shipped file, inside the constraint-prohibition sentence itself — no actual usage.
- [x] Documentation: `docs/ARCHITECTURE.md` "NIC-52" section added (design decision, coordination outcome, full AC1–AC8 evidence trail with real search queries/results); this `docs/PLAN.md` entry added.
- [ ] **NOT done, explicitly out of scope (per scope doc §5):** company/website summary, video, or open-position-count sections (NIC-49/50/51's scope); assembling the full brief onto a Notion job page (NIC-53's scope); any Notion API call; correcting the stale 12-month reference in this file's NIC-43 section (flagged as non-blocking housekeeping, scope doc OQ-3).

### Evidence

See `docs/ARCHITECTURE.md` "NIC-52 — `company-research` skill: significant recent news" section for full evidence: the coordination outcome (file created fresh, no NIC-49 collision), the five-category filter and output-contract text as shipped, and the complete AC1–AC8 evidence trail — including the real web-search queries and real results run in this session against Mistral AI (funding/acquisition/partnership news, cap-at-3 demonstrated live) and PALO IT (zero qualifying items, exact fallback string confirmed correct).

### Dependencies / follow-ups (not this ticket)

- **NIC-49/50/51** extend the same `SKILL.md` file with their own sections (company/website summary, recent video, open-position counts) — this ticket left placeholder headings and a status table for them.
- **NIC-53** assembles all four `company-research` components into one brief and attaches it to the Notion job page — depends on NIC-49/50/51 landing too.
- **Minor evidence gap (non-blocking):** AC8's "1–2 items, never padded to 3" path was verified via the written procedure text only, not a live 1-or-2-item real-world run (the two verification targets landed on the 0-item and 4-in-window-capped-to-3 edge cases instead). Recommend QA Reviewer spot-check this against a convenient middle-case company if practical.

---

## NIC-49 — `company-research` skill: company / website summary

**Status:** DONE (script + thin SKILL.md wrapper implemented and unit-tested; verified live end-to-end against one real company, Mistral AI)
**Owner:** Builder
**Date:** 2026-09-12

### Definition of done

- [x] New, standalone, pure-Python module implemented at `scripts/company_research.py`: `build_company_summary(company_name, source_text, source_url, retrieved_date, job_url=None, company_website_url=None, not_found_reason=None) -> dict`, implementing the exact input/output contract from `docs/handoffs/NIC-49-product-planner-scope-validation.md` §5 — no redesign.
- [x] Script performs zero network calls (Decision D3) — only imports `re`, `typing.Optional`, `urllib.parse.urlparse` (all stdlib).
- [x] `status` is a closed enum (`{"ok", "not_found", "insufficient_content"}`) — `_build_failure()` raises `ValueError` on any other value.
- [x] Thin `SKILL.md` wrapper created at `.claude/skills/company-research/SKILL.md` (this v2 repo, per scope doc §4's explicit repo-location decision) instructing the invoking agent on the search→fetch→call→present procedure, including the explicit AC7 no-retry/no-bypass instruction.
- [x] AC1 verified live: real company (Mistral AI), real `web_search` + `browser_navigate` fetch of `https://mistral.ai/about`, real script output `status: "ok"` with exactly 5 sentences and `source_url` matching the input exactly — full evidence (search result, fetch snapshot, script output) in `docs/ARCHITECTURE.md` "NIC-49" section.
- [x] AC2 verified via isolated unit tests (`/tmp/test_nic49_company_research.py`, no network, 27/27 assertions PASS, exit code 0): 3-sentence, 5-sentence, and 8-sentence (truncated-to-5, verified as a strict prefix) fixtures all land within [3,5]; sentence-splitting rule documented (`(?<=[.!?])\s+` after whitespace collapse).
- [x] AC3 verified: `summary` non-empty string and `source_url` a syntactically valid absolute `http(s)` URL on every `status: "ok"` case (via `urllib.parse.urlparse`); a malformed `source_url` alongside real `source_text` raises `ValueError`.
- [x] AC4 verified both failure paths: `"not_found"` (simulated via `source_text=None` + required `not_found_reason`, raises `ValueError` if the reason is omitted) and `"insufficient_content"` (an under-80-char stub, and separately a longer-but-<3-sentence text) both return the exact fixed-shape failure object (`summary: null`, `source_url: null`, non-empty `reason`) — never a fabricated/padded summary.
- [x] AC5 verified: `scripts/company_research.py`'s only imports are `re`, `typing.Optional`, `urllib.parse.urlparse` — zero new third-party/paid dependency.
- [x] AC6 verified: zero credential/cookie/session-handling code anywhere in the script or the SKILL.md wrapper (grep for `cookie|session|login|credential|password|token` returns only constraint-describing prose, no actual handling logic).
- [x] AC7 verified: `.claude/skills/company-research/SKILL.md` step 3 explicitly states never to retry a blocked fetch with a spoofed identity or `robots.txt`-bypassing technique, and to treat any such failure as `"not_found"`.
- [x] AC8 verified: zero `notion` string matches anywhere in `scripts/company_research.py`'s imports or logic (static grep).
- [x] AC9 verified via the same unit test run: `set(result.keys())` matches the documented field set exactly for the success shape and for both failure shapes.
- [x] Documentation: `docs/ARCHITECTURE.md` "NIC-49" section added (design decision, call shape, sentence-splitting method, non-fabrication shape, full AC1–AC9 evidence including the real Mistral AI verification); this `docs/PLAN.md` entry added.
- [ ] **NOT done, explicitly out of scope (per scope doc §8):** recent YouTube video (NIC-50), open-position counts (NIC-51), significant recent news (NIC-52, already shipped separately in the v1 repo), any Notion API call or `scripts/notion_job_page_blocks.py` change (NIC-53), any n8n involvement, a self-contained standalone-runnable (no-agent) version of the script (flagged as a real, unresolved gap in the scope doc §6, not solved here).

### Evidence

See `docs/ARCHITECTURE.md` "NIC-49 — `company-research` skill: company / website summary" section for full evidence: design decision (including the flagged cross-repo split with NIC-52's v1-repo skill file), exact call shape, sentence-splitting method, non-fabrication failure shape, and the complete AC1–AC9 evidence trail (real Mistral AI search/fetch/script-output evidence for AC1, isolated 27/27-assertion unit test run for AC2/AC3/AC4/AC9, static import/grep checks for AC5/AC6/AC8, SKILL.md text confirmation for AC7).

### Dependencies / follow-ups (not this ticket)

- **Cross-repo split (flagged, not resolved here):** this ticket's `SKILL.md` lives in the v2 repo per its own scope doc's explicit repo-location decision; NIC-52's sibling "Recent Company News" section already shipped in the v1 repo. NIC-53's eventual four-part-brief assembly step will need this reconciled — recommend Product Planner/Boss decide which repo is authoritative before NIC-53 starts.
- **`web_extract` is not usable in this Hermes environment** (search-only DuckDuckGo backend) — the real AC1 verification used `browser_navigate` instead; documented as a known tooling limitation, not a company-side block, in `docs/ARCHITECTURE.md`.
- **Standalone-execution gap (scope doc §6, OQ-3):** this script cannot run outside an agent session (no built-in fetch capability, by design) — relevant only when Phase 5's n8n automation is eventually scoped; not this ticket's concern.
- NIC-50 (recent video), NIC-51 (open-position counts) are expected to follow this same script+thin-SKILL.md pattern and the same output-shape contract (`company_name`, `summary`-equivalent field, `source_url`, `retrieved_date`, `status`, optional `reason`) for NIC-53 to consume consistently.



Tracked in Linear (team NIC, project "cv-job-match v2 — Notion-centric Job Search Copilot"). Query Linear directly for the current open ticket list beyond NIC-42/NIC-43; this file only records what Builder has actually shipped, to avoid drift between Linear and this doc.

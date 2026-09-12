# NIC-48 (P2-T3) — Product Planner Scope Validation

**Ticket:** NIC-48 — "P2-T3 — Consistent file naming convention for job page attachments"
**Traces to:** FR-E3, US-7 (docs/PRD.md)
**Depends on:** P2-T1 / NIC-46 (Tailored CV attachment) — Done; P2-T2 / NIC-47 (Cover letter attachment) — Done
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-11
**Role boundary respected:** no code/implementation performed; this is scope definition only. No Notion API calls of any kind were made — this ticket's investigation was pure static code/doc reading, since the naming question does not require touching the live workspace to validate.

---

## 1. Problem

`attach_final_cv(page_id, pdf_path, filename, heading_text=...)` (`scripts/notion_cv_attachment.py`, shipped NIC-46) and its thin wrapper `attach_final_cover_letter(page_id, pdf_path, filename)` (`scripts/notion_cover_letter_attachment.py`, shipped NIC-47) both take **an explicit `filename` string supplied by the caller**. Neither script computes, validates, or enforces any naming convention internally — the caller invents the string. Confirmed by direct code read: `_file_block()` and `create_file_upload()` in `notion_cv_attachment.py` just pass whatever `filename` they're given straight into the Notion API body; there is no naming logic anywhere in either shipped file.

The real-world status quo (per ARCHITECTURE.md's own NIC-46/NIC-47 evidence sections) is that each ticket's Builder **manually typed** a filename string for its own verification test file:
- NIC-46: `"TEST Company - TEST Role - CV.pdf"`
- NIC-47: `"TEST Company - TEST Role - Cover Letter.pdf"`

Both happen to approximate the PRD's proposed convention (`{Company} - {Role} - CV.pdf` / `{Company} - {Role} - Cover Letter.pdf`, FR-E3), but this is coincidence, not enforcement — nothing in the code would stop a future caller (e.g. a not-yet-built `cv-match`/`write-outreach` → Notion integration script) from passing an arbitrary string, a typo'd separator, or a completely different format. There is also **no sanitization anywhere**: if a real company or role name contains a filesystem-unsafe character (e.g. `Acme/Corp`, `R&D: Data Team`), passing it directly into `filename` would either produce a broken/confusing attachment name or, in pathological cases, be misinterpreted by the OS/Notion. No real production job card has been attached yet (confirmed: both NIC-46 and NIC-47 only ever touched their own dedicated test cards — the 5 real cards' Tailored CV / Cover Letter sections are still the original NIC-43 placeholder callouts), so there is **no backward-compatibility or rename risk** for existing production data. This is a pure "formalize before it's used for real" ticket.

## 2. Objective

Determine whether this ticket can be satisfied by adding a **small, shared, pure-Python filename-builder helper** — imported by both existing scripts' *callers* (not by rewriting the scripts' own upload/replace mechanism) — that centralizes the naming convention and a concrete sanitization rule, so every future caller produces a consistent, filesystem-safe filename instead of inventing one ad hoc.

## 3. Context and relevant files read

- `AGENTS.md`, `docs/FACTORY_PROTOCOL.md` — handoff contract, Linear lifecycle, approval gates.
- `docs/PRD.md` — FR-E3 (line 155, "proposed, not yet confirmed"), US-7 (line 267, "consistent naming convention" as an explicit AC), OQ-13 (line 240/292, file format — separate question, resolved by NIC-40).
- `docs/PLAN.md` — NIC-46, NIC-47 entries (both explicitly leave FR-E3 "not formally confirmed, only approximated for the test filename").
- `docs/ARCHITECTURE.md` — NIC-46 and NIC-47 sections read in full, specifically the "Known limitations" bullets on file naming and the exact test filenames used (quoted above).
- `scripts/notion_cv_attachment.py`, `scripts/notion_cover_letter_attachment.py` — read in full. Confirmed: `filename` is a required, caller-supplied parameter in both; zero naming/sanitization logic exists in either file today.
- `docs/handoffs/NIC-46-product-planner-scope-validation.md` — confirms FR-E3 was explicitly deferred as out of scope for NIC-46 ("Recommend Builder adopt it as a reasonable default filename... but this ticket's AC does not require a specific naming scheme to pass").
- **NIC-40 in Linear** (checked directly via GraphQL, not assumed): status **Done**, closing comment (2026-09-10, in French) confirms **only the file *format* decision** ("format PDF retenu... S'applique à FR-C3, FR-E1, FR-E2, FR-E3"). It does **not** mention or confirm the naming-convention *string* itself — it resolves OQ-13 (PDF vs. Markdown vs. DOCX), a different, narrower question than FR-E3's naming format. **No other Linear ticket or comment was found that reconfirms the exact `{Company} - {Role} - {Kind}.ext` string.** Conclusion: FR-E3 remains genuinely unconfirmed by Nicolas as of this ticket — the task context's suspicion was correct, and this ticket's own AC wording ("PRD's proposed-but-unconfirmed recommendation... confirm before treating as final") is accurate, not stale. Per this ticket's own AC framing, I am proceeding with the PRD's proposed convention as the **working default to formalize**, flagged explicitly as an assumption pending a lightweight Nicolas confirm (see §9 Open Questions) — consistent with how NIC-46/47's Product Planner handled the same open point.

## 4. Investigation finding: (a) small shared helper is sufficient — no changes needed to the shipped attachment mechanisms

**Decision: Option (a).** A new, small, dependency-free helper module satisfies this ticket without touching `notion_cv_attachment.py` or `notion_cover_letter_attachment.py` at all.

Reasoning:
- Both shipped functions already separate "compute the filename" from "attach the file" — the `filename` parameter is the seam. Nothing about the naming convention requires new Notion API calls, new block logic, or a new upload/replace mechanism (that mechanism is already correct and QA-passed).
- Following the precedent NIC-47 itself set (choosing a thin wrapper specifically to keep NIC-46's already-shipped, QA-passed file at **zero changed lines**), the same principle applies here even more strongly: this ticket is pure string formatting/sanitization, with no reason to touch working, tested upload logic and reintroduce regression risk.
- Therefore: **do not modify** `scripts/notion_cv_attachment.py` or `scripts/notion_cover_letter_attachment.py`. **Add** a new module, e.g. `scripts/notion_attachment_naming.py`, exposing `build_attachment_filename(company: str, role: str, kind: str, ext: str = "pdf") -> str`. Any *caller* of `attach_final_cv()` / `attach_final_cover_letter()` (today: verification/test scripts; in the future: a not-yet-built `cv-match`/`write-outreach` → Notion integration) is expected to compute its `filename` argument via this helper instead of hand-typing a string.
- `kind` should be a closed, validated set of literal values matching the two currently-defined attachment types: `"CV"` and `"Cover Letter"` (exact display strings used in the final filename, distinct from the heading-text constants `TAILORED_CV_HEADING`/`COVER_LETTER_HEADING`, which are Notion block headings, not filenames — these must not be conflated). Passing any other `kind` value should raise loudly (`ValueError`), consistent with this codebase's established "fail loudly rather than guess" style (`find_tailored_cv_section`'s behavior when a heading isn't found).
- `ext` defaults to `"pdf"`, matching NIC-40's confirmed target-format decision — not re-litigated here.

## 5. Sanitization rule (concrete, since the PRD does not specify one)

Real company/role names will contain characters that are unsafe or ambiguous in filenames, and the source data (job postings, freeform user input) is not guaranteed clean. Rule, to be implemented exactly as specified so it is unit-testable:

For each of `company` and `role`, independently, in this exact order:
1. **Trim** leading/trailing whitespace.
2. **Strip control characters**: remove any character in the C0 control range (`U+0000`–`U+001F`) or `U+007F` (DEL) — these can corrupt filenames/terminals and have no legitimate use in a company/role name.
3. **Replace filesystem-unsafe characters** with a single space. Use the **Windows-reserved set** as the basis (the strictest common denominator, so filenames stay portable across macOS/Linux/Windows even though Notion itself is not a filesystem): `< > : " / \ | ? *`. This also covers the specific risk flagged in the task context (slashes, colons).
4. **Collapse whitespace**: any run of one or more whitespace characters (including the spaces introduced by step 3, plus tabs/newlines) becomes a single ASCII space.
5. **Trim again** (step 4 can reintroduce leading/trailing spaces, e.g. if the unsafe character was at the start/end).
6. **Do not otherwise touch non-ASCII characters.** Accented/non-Latin characters (é, à, ü, etc.) are common in real company/role names in Nicolas's target market (Paris) and must be preserved — sanitization is scoped to unsafe/control characters only, not an ASCII-only transliteration.
7. **Length cap:** truncate each of `company` and `role` to 80 characters after the above steps (not the final assembled filename) — generous for any real company/role name, prevents pathological input from producing an unwieldy or OS-limit-breaking filename, and keeps the truncation boundary predictable/testable per field rather than an awkward mid-assembly cut.
8. **Empty-after-sanitization fallback:** if a field is empty or whitespace-only after steps 1–7 (e.g. input was only control characters), substitute a fixed placeholder — `"Unknown Company"` / `"Unknown Role"` respectively — rather than producing a malformed filename like `" -  - CV.pdf"`. This must never raise; a placeholder is always safer than a crash in an attachment pipeline.

Final assembly: `f"{sanitized_company} - {sanitized_role} - {kind}.{ext}"`. No additional sanitization is applied to `kind` or `ext` since both are internally-controlled literal values, not external input.

**Explicitly not a collision risk:** two different companies sanitizing to the same string (e.g. `"Acme/Corp"` and `"Acme Corp"` both becoming `"Acme Corp"`) is a non-issue for this system — each file lives inside a single job's own Notion page, never in a shared flat directory, so filename uniqueness across jobs is not required.

## 6. Scope

**In scope for NIC-48:**
1. New module `scripts/notion_attachment_naming.py`: `build_attachment_filename(company, role, kind, ext="pdf") -> str`, implementing the convention and sanitization rule above, pure standard library, no network calls, no dependency on `notion_cv_attachment.py`/`notion_cover_letter_attachment.py` (naming has no reason to import attachment logic).
2. One verification pass proving the helper's output is genuinely what ends up as the Notion `file` block's visible name — i.e. an end-to-end call where a filename computed by `build_attachment_filename()` (using at least one input containing an unsafe character, to prove sanitization actually fires) is passed as the `filename` argument into the **existing, unmodified** `attach_final_cv()` / `attach_final_cover_letter()`, using one freshly-created, clearly-named `TEST NIC-48 verification` card, archived immediately after evidence capture.
3. Documentation: new "NIC-48" section in `docs/ARCHITECTURE.md` (call shape, exact sanitization rule, verification evidence) and a new NIC-48 entry in `docs/PLAN.md` — both Builder responsibilities per established pattern (NIC-42/43/46/47 precedent), not this document.

**Explicitly out of scope (this ticket does not rebuild the attachment mechanisms):**
- No changes to `scripts/notion_cv_attachment.py` or `scripts/notion_cover_letter_attachment.py` — both remain at their currently shipped, QA-passed state, zero lines changed.
- No changes to the Notion Kanban schema (NIC-42), page template (NIC-43), or any n8n automation.
- No retroactive renaming of any already-attached file — none exist on real production cards today (confirmed: both NIC-46 and NIC-47 verification only ever touched their own dedicated, now-archived test cards).
- No integration into `cv-match`/`write-outreach` themselves (v1 repo) — those skills still have no PDF-export step (confirmed fact, unchanged since NIC-46/47); wiring the naming helper into a real end-to-end pipeline is a future ticket once that PDF-export gap is closed (tracked as OQ-A in both NIC-46 and NIC-47's scope docs).
- No formal reconfirmation ceremony with Nicolas beyond what this doc + its Linear comment surface — per this ticket's own AC wording, the PRD's proposed convention is treated as the working default to formalize, consistent with how FR-E3 has been handled in every prior related ticket.

## 7. Acceptance criteria (restated as testable checks)

| # | Criterion | Source | Testable check |
|---|---|---|---|
| AC1 | A shared filename-builder helper exists and implements the convention `{Company} - {Role} - {Kind}.{ext}` for `kind` in `{"CV", "Cover Letter"}`. | Ticket, FR-E3, US-7 | `build_attachment_filename("Acme", "Backend Engineer", "CV")` returns exactly `"Acme - Backend Engineer - CV.pdf"`; same pattern for `"Cover Letter"`; an invalid `kind` value raises `ValueError` rather than silently producing a wrong string. |
| AC2 | The sanitization rule in §5 is implemented exactly and is testable in isolation (no network/Notion access required). | Task context ("decide and document a sanitization rule") | Direct calls to `build_attachment_filename()` with crafted inputs confirm: (a) a `/` or `\` in company/role never appears in the output; (b) control characters are removed; (c) irregular/multiple whitespace collapses to single spaces with no leading/trailing space; (d) accented/non-ASCII characters (e.g. `"Société Générale"`) pass through unchanged; (e) an all-control-character or empty-string input falls back to `"Unknown Company"`/`"Unknown Role"` without raising; (f) a 300-character input is truncated to the 80-character cap without raising or corrupting the extension. |
| AC3 | Zero changes to the already-shipped, QA-passed attachment mechanisms. | Design decision §4, mirrors NIC-47 precedent | `git diff` / `sha256sum` before and after this ticket's work shows `scripts/notion_cv_attachment.py` and `scripts/notion_cover_letter_attachment.py` byte-identical to their pre-NIC-48 state. |
| AC4 | No new third-party dependencies. | Consistency with existing scripts' dependency-light style | `scripts/notion_attachment_naming.py` imports only from the Python standard library (in practice: no imports beyond `re`/`string`, if even that). |
| AC5 | End-to-end proof that the helper's output becomes the real, visible Notion attachment name — not just a unit-tested string in isolation. | Ticket AC ("files appear as downloadable attachments... with a consistent naming convention", US-7) | Using one freshly-created `TEST NIC-48 verification` card (own hardcoded `page_id`), call `build_attachment_filename()` with at least one input containing an unsafe character (e.g. `company="TEST Company/Ops"`, `role="TEST Role: Lead"`), pass the result into `attach_final_cv()` unmodified, then `GET /v1/blocks/{page_id}/children` and confirm the resulting `file` block's `name` field exactly equals the sanitized, helper-computed string (e.g. `"TEST Company Ops - TEST Role Lead - CV.pdf"`) — proving the unsafe characters were actually stripped in a real Notion object, not just in a local test. |
| AC6 | Test artifact discipline (mirrors NIC-46/47 exactly). | Task safety constraint | Test card `Name` contains `"TEST NIC-48 verification"`; created via `build_job_page_children()`; evidence includes the creation response, the `GET` confirming the sanitized filename landed correctly, and the `PATCH {"archived": true}` cleanup + confirming follow-up `GET`; a before/after `POST /v1/data_sources/{id}/query {}` diff proves the 5 real production cards and NIC-46's/NIC-47's own archived test cards are byte-identical/untouched. |
| AC7 | Documentation updated. | Repo convention (NIC-42/43/46/47 precedent) | `docs/ARCHITECTURE.md` gets a new "NIC-48" section (design decision, exact sanitization rule, call shape, verification evidence); `docs/PLAN.md` gets a new NIC-48 entry with a Definition-of-Done checklist mirroring the existing entries' format. |

## 8. Effort estimate

**XS — approximately 45–75 minutes.** This is pure string-formatting/sanitization logic with no new Notion API call shapes (the 3-step upload flow, block replace/archive logic, and section-locator are all already shipped and untouched). Breakdown: helper module + sanitization implementation (~20 min — logic is fully specified in §5, no discovery needed), one verification test-card create/attach-with-unsafe-characters/inspect/archive cycle reusing the exact NIC-46/47 pattern (~20–25 min), `docs/ARCHITECTURE.md` + `docs/PLAN.md` write-up (~15–20 min). Smaller than NIC-46 (S, 2–3h) and NIC-47 (reuse via thin wrapper) because there is no HTTP/upload logic to write at all — only a pure function plus one thin proof that it plugs into the existing mechanism correctly.

## 9. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| FR-E3's naming *string* itself (`{Company} - {Role} - {Kind}.ext`) is still genuinely unconfirmed by Nicolas — confirmed by direct Linear check, NIC-40 only resolved file *format* (PDF), not this string. | Low-Medium — if Nicolas later wants a different format, filenames already attached under this convention would need renaming. | Isolate the convention to exactly one function (`build_attachment_filename`) so a future change is a one-line edit, not a scattered find-and-replace across callers. No real production files exist yet to migrate (confirmed §1), so the cost of being wrong today is near-zero. Recommend Boss surface the exact proposed string to Nicolas for a lightweight thumbs-up/down at the next convenient touchpoint (see Open Questions). |
| The sanitization rule (§5) is a Product Planner judgment call, not literally specified anywhere in the PRD. | Low | Documented explicitly and exhaustively here, with every step testable in isolation (AC2), so it's auditable and easy to challenge/adjust later — not a hidden implementation detail. |
| Non-ASCII company/role names (accented French names are common in Nicolas's actual target market) could be mishandled by an overly aggressive sanitizer. | Medium if mishandled (would silently mangle correct, common real-world input) | §5 step 6 explicitly preserves non-ASCII characters; AC2(d) requires a test case with an accented name (e.g. "Société Générale") to prove this. |
| A future caller could still bypass the helper and hand-type a filename directly into `attach_final_cv()`/`attach_final_cover_letter()`, since neither function's signature *requires* filenames to come from the helper (no enforcement at the API boundary). | Medium — this ticket formalizes a convention but cannot technically force its use, since the task explicitly rules out modifying the already-shipped attachment mechanisms. | Document the expectation clearly in the helper's own docstring and in ARCHITECTURE.md ("all callers of attach_final_cv/attach_final_cover_letter should compute filenames via build_attachment_filename()") so it's the obvious/path-of-least-resistance choice for whoever builds the future cv-match/write-outreach integration. Flagged as an accepted, documented limitation rather than silently ignored — enforcing it fully would require changing the shipped scripts' signatures, which is explicitly out of scope per §4's reasoning and this ticket's own framing (formalize/apply, don't rebuild). |
| `kind` as a free-form string could invite typos (`"cv"` vs `"CV"`) if Builder doesn't validate strictly. | Low | AC1 explicitly requires `ValueError` on an unrecognized `kind`, not case-insensitive guessing — consistent with the codebase's existing "fail loudly" pattern. |

## 10. Open questions

- **OQ-C (not blocking, recommend surfacing to Nicolas at next touchpoint):** Should the exact naming string (`{Company} - {Role} - CV.pdf` / `{Company} - {Role} - Cover Letter.pdf`) be explicitly reconfirmed, given NIC-40 only settled the file *format* question, not this one? Per this ticket's own AC wording, proceeding with the PRD's proposed convention as the working default to formalize now, isolated to one easily-changed function if the answer comes back different later.
- **OQ-D (not blocking):** Should the helper's `kind` parameter be extended later to cover a possible future third attachment type (e.g. an exported interview cheat sheet PDF, Phase 4)? Out of scope for NIC-48 (ticket is CV + cover letter only) — recommend keeping `kind` a closed 2-value set for now and extending only when/if a real third attachment type ships.
- **No blockers to starting Builder work.** No credential dependency (this ticket's core logic needs zero network access); NIC-46/NIC-47's shipped, QA-passed mechanisms are confirmed reusable as-is by direct code read; no contradiction found across PRD/ARCHITECTURE/PLAN/Linear.

## 11. Go/no-go recommendation

**GO.** This is the smallest possible change that satisfies the ticket: one new, dependency-free, pure-function module plus one thin end-to-end proof, with zero regression risk to already-shipped/QA-passed code (mirrors the exact risk posture NIC-47 chose for the same reason). No approval-gate conflict — nothing here is a deployment, destructive operation, secret exposure, or third-party contact per AGENTS.md's forbidden-operations list. Builder should proceed directly.

---

## HANDOFF TO BUILDER

**Objective:** Implement a small, shared, pure-Python filename-builder helper (`build_attachment_filename(company, role, kind, ext="pdf") -> str`) that formalizes the naming convention `{Company} - {Role} - {Kind}.{ext}` with the sanitization rule in §5 of this doc, and prove via one disposable test card that its output is what actually lands as the Notion attachment's visible name when passed into the existing, unmodified `attach_final_cv()` / `attach_final_cover_letter()`.

**Context and relevant files:**
- Repo: `/home/nicow/cv-job-match-v2`.
- `scripts/notion_cv_attachment.py` — `attach_final_cv(page_id, pdf_path, filename, heading_text=...)`. **Do not modify.** Its `filename` parameter is the integration seam for this ticket.
- `scripts/notion_cover_letter_attachment.py` — `attach_final_cover_letter(page_id, pdf_path, filename)`. **Do not modify.**
- `scripts/notion_job_page_blocks.py` — `build_job_page_children()`, for constructing the test card's initial 14-block structure (same pattern as NIC-46/47).
- Kanban DB: `database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `data_source_id 47340a66-9e15-4ea1-8edf-45bba44c2334`, under Notion page `3ab05073-c5b0-8061-bc12-e92aa903bebc` ("Job Search").
- `docs/ARCHITECTURE.md` NIC-46/NIC-47 sections for call-shape precedent and documentation format to follow.
- This document (`docs/handoffs/NIC-48-product-planner-scope-validation.md`) for full rationale, exact sanitization rule (§5), and testable AC (§7).

**Constraints:**
- Do not modify `scripts/notion_cv_attachment.py` or `scripts/notion_cover_letter_attachment.py` — zero lines changed in either (verify with `sha256sum`/`git diff` before and after, report both).
- New module must be pure standard library — no new third-party dependency.
- `kind` must be a validated, closed set (`"CV"`, `"Cover Letter"`) — raise `ValueError` on anything else, do not silently guess or lowercase-normalize.
- Sanitization must preserve non-ASCII characters (accented names) and only strip/replace control characters and the Windows-reserved unsafe set (`< > : " / \ | ? *`), per §5 exactly.
- **Never touch the live production Notion database's 5 real job cards or NIC-46's/NIC-47's own archived test cards.** Create and use your own dedicated test card only, referenced by its own hardcoded `page_id`, exactly like NIC-46/NIC-47's precedent: create via `build_job_page_children()`, `Name` containing `"TEST NIC-48 verification"`, attach a small synthetic PDF using a filename computed by `build_attachment_filename()` with at least one deliberately-unsafe character in the company/role input (e.g. `company="TEST Company/Ops"`, `role="TEST Role: Lead"`), confirm via `GET /v1/blocks/{page_id}/children` that the resulting `file` block's `name` exactly matches the sanitized output, THEN immediately `PATCH /v1/pages/{page_id}` `{"archived": true}` and confirm the response. Do not leave the test card live after evidence capture. Diff a before/after `POST /v1/data_sources/{id}/query {}` against the 5 known real cards to prove none were touched.
- No deployment, no destructive/irreversible operation beyond archiving your own test artifact, no secret exposure, no third-party contact.

**Acceptance criteria:** AC1–AC7 in §7 above (convention correctness, sanitization correctness in isolation, zero changes to shipped attachment scripts, no new dependencies, real end-to-end proof via one archived test card, test-artifact discipline, documentation).

**Files/scripts likely to touch:**
- New file: `scripts/notion_attachment_naming.py` (the helper, per §4–§5).
- `docs/ARCHITECTURE.md` — new "NIC-48" section (sanitization rule, call shape, verification evidence, explicitly noting zero lines changed in the two existing attachment scripts).
- `docs/PLAN.md` — new NIC-48 entry (Definition-of-Done checklist, evidence pointer, out-of-scope confirmations), mirroring NIC-42/43/46/47's format.

**Test-and-cleanup discipline (exact sequence):**
1. Create one test card via `POST /v1/pages` with `build_job_page_children()`'s 14-block array, `Name: "TEST NIC-48 verification"`, `Company`/`Role`: `"TEST"`, `Status: "selected"`. Record the returned `page_id`.
2. Call `build_attachment_filename(company="TEST Company/Ops", role="TEST Role: Lead", kind="CV")` — confirm locally it returns the expected sanitized string before using it.
3. Call `attach_final_cv(page_id, <synthetic_pdf_path>, filename=<result_from_step_2>)` — unmodified, exactly as NIC-46 verified it.
4. `GET /v1/blocks/{page_id}/children` — confirm the `file` block's `name` exactly equals the string from step 2.
5. Repeat steps 2–4 for `attach_final_cover_letter()` with `kind="Cover Letter"` on the same or a second hardcoded test card.
6. `PATCH /v1/pages/{page_id}` `{"archived": true}` for every test card created — confirm via follow-up `GET`.
7. Diff a before/after `POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query {}` against the 5 known real card `page_id`/`Name`/`last_edited_time` values (and NIC-46's/NIC-47's archived test cards) to prove none were touched.

**Recommended next action:** Builder implements the helper, runs the exact sequence above, documents evidence (including the `sha256sum`/`git diff` proof that the two existing attachment scripts are byte-identical to their pre-NIC-48 state), and hands off to QA Reviewer.

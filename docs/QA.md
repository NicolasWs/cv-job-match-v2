# QA — cv-job-match v2

Test results, defects, severity, and release recommendation. Populated per ticket as QA Reviewer independently verifies Builder's work.

---

## NIC-56 — LinkedIn Saved Jobs → Notion `selected`-card importer (semi-automated)

**Verdict: PASS**
**Reviewer:** QA Reviewer (Bot)
**Date:** 2026-09-11

### Scope reviewed

- New script `scripts/notion_import_saved_jobs.py` against `docs/handoffs/NIC-56-product-planner-scope-validation.md` §8 AC1–AC8.
- Docs: `docs/PRD.md` §6.1.a addendum, `docs/ARCHITECTURE.md` "NIC-56" section, `docs/PLAN.md` NIC-56 entry — all present and confirmed via direct read (not just Builder's claim).
- All evidence below is QA's own independently re-derived evidence (fresh test cards, fresh runs, fresh diffs) — Builder's self-report was used only to know what to re-check, never accepted as sufficient on its own, per FACTORY_PROTOCOL.md's independence rule.

### Acceptance criteria results

| # | Criterion | Result | QA's own evidence |
|---|---|---|---|
| AC1 | 5-cap default, `--all` override | PASS | Fresh 7-entry + 1-malformed input (`/tmp/qa_nic56_ac1.txt`). Run 1 (no `--all`): exactly 5 cards created (Co1–Co5, page_ids `3d805073-c5b0-815a-...` through `...-8160-...`), 2 reported `skipped_limit` (Co6, Co7), 1 malformed reported. Run 2 (`--all`, same file): exactly 2 new cards created (Co6, Co7), the original 5 correctly reported as `skipped_duplicates` (not recreated) — confirms dedup-before-limit ordering and correct `--all` override behavior. |
| AC2 | `Status=selected`, non-empty `Company`/`Role` | PASS | Live `GET /v1/pages/{page_id}` on QA's own created card `3d805073-c5b0-815a-820a-fd33b76438c8`: `status: "selected"` (exact), `company: "QA-TEST Co1"`, `role: "Role1"` — both non-empty. |
| AC3 | 14-block NIC-43 template attached | PASS | `GET /v1/blocks/3d805073-c5b0-815a-820a-fd33b76438c8/children` on the same card: `block_count: 14`, block-type sequence `heading_2, paragraph, divider, heading_2, callout, divider, heading_2, callout, divider, heading_2, callout, divider, heading_2, callout`, `has_more: false` — exact match to `build_job_page_children()`'s documented structure. |
| AC4 | Dedup by normalized Company+Role, skipped & reported by name | PASS | QA seeded its own test card (`Company="QA-TEST Acme"`, `Role="PM"`, page_id `3d805073-c5b0-8187-912c-d8e3c4a2cd6c`) via a direct `POST /v1/pages` call mirroring the script's own shape, then ran the script (`--all`) against an input containing `"  qa-test acme   |   pm  "` (case + whitespace variant) plus one genuinely new entry. Result: 1 card created (the new entry), the Acme/PM variant correctly skipped and reported with `matched_page_id` pointing at the seeded card — no second Acme/PM card created. |
| AC5 / AC8 | Zero `linkedin.com` network calls | PASS | QA's own `grep -in linkedin scripts/notion_import_saved_jobs.py`: 6 matches, all inside comments/docstring describing the constraint — zero in executable code. QA's own `grep -on 'https\?://...'`: exactly 1 match, `https://api.notion.com/v1` (the `NOTION_API_BASE` constant). Only imports: Python stdlib (`json`, `os`, `re`, `sys`, `urllib.error`, `urllib.request`) + `notion_job_page_blocks` (existing repo module) — no browser-automation or third-party HTTP library capable of contacting another host. |
| AC6 | Malformed entries reported, never fabricated/dropped | PASS | QA's own malformed-variety input (`/tmp/qa_nic56_ac6_malformed.txt`: missing-company, missing-role, double-pipe, no-pipe) → all 4 reported individually by line number and specific reason (`"missing company"`, `"missing role"`, `"found 2 separator(s)"`, `"found 0 separator(s)"`); 0 cards created from this run — confirms no guessing/fabrication across multiple malformation shapes, not just the single case Builder tested. |
| AC7 | Test-artifact discipline; 5 real cards untouched | PASS | QA captured its own before-run baseline (`POST /v1/data_sources/{id}/query {}` → 5 real cards, ids/names/`last_edited_time` recorded) and after-run query following all 9 of QA's own test-card creations + archives. `diff` of the two captured JSON outputs returns **zero differences** — real cards byte-identical (`page_id`, `Name`, `last_edited_time`, `archived`) before and after. All 9 QA-created test cards (7 from AC1, 1 dedup seed, 1 from AC4) individually archived via `PATCH {"archived": true}`, each response confirmed `"archived": true`. |

### Tests executed

- `python3 -m py_compile scripts/notion_import_saved_jobs.py` → exit 0, no errors.
- Static grep for `linkedin` (case-insensitive) and for `https?://` literals in the script — see AC5/AC8 above.
- Live Notion API baseline query before any QA work: 5 real production cards recorded (`Senior PM`, `Staff CSM`, `Freelance` ×2, `Implementation Manager - Strategic Accounts`), matching Builder's own recorded baseline exactly (`page_id`s/`last_edited_time`s identical) — confirms no drift since Builder's own verification session.
- Fresh run 1: `python3 scripts/notion_import_saved_jobs.py /tmp/qa_nic56_ac1.txt` (7 entries + 1 malformed, no `--all`) → 5 created, 2 skipped-limit, 1 malformed.
- Fresh run 2: `python3 scripts/notion_import_saved_jobs.py /tmp/qa_nic56_ac1.txt --all` (same file) → 2 new created, 5 correctly reported as duplicates.
- Seed dedup card via direct Notion API call (`3d805073-c5b0-8187-912c-d8e3c4a2cd6c`, `QA-TEST Acme`/`PM`).
- Dedup test: `python3 scripts/notion_import_saved_jobs.py /tmp/qa_nic56_ac4_dupe.txt --all` → 1 created, 1 correctly skipped as duplicate.
- Malformed-variety test: `python3 scripts/notion_import_saved_jobs.py /tmp/qa_nic56_ac6_malformed.txt --all` → 0 created, 4 malformed lines reported individually.
- `GET /v1/pages/{page_id}` + `GET /v1/blocks/{page_id}/children` on QA's own created card `3d805073-c5b0-815a-820a-fd33b76438c8` — see AC2/AC3.
- Archived all 9 QA-created test cards via `PATCH /v1/pages/{id}` `{"archived": true}`, each independently confirmed.
- Before/after `POST /v1/data_sources/{id}/query {}` diff on the 5 real production cards — zero differences (see AC7).
- No visual/UI surface involved in this ticket (script + API only) — no screenshot evidence applicable per the "Visual evidence" policy; all evidence above is quoted command/API output.

### Defects

None found.

### Severity

N/A — no defects.

### Release recommendation

**PASS. Safe to release / mark Done.** All 8 acceptance criteria independently re-verified with QA's own fresh test data (distinct page_ids from Builder's own verification run, so this is genuinely independent evidence, not a re-statement of Builder's numbers). Architecture stays Notion-as-system-of-record + a plain script reusing the existing `build_job_page_children()` convention — no bespoke web app, no new backend platform, no unapproved LinkedIn automation introduced. The 5 real production Notion cards are confirmed byte-identical before and after this review. Documentation (PRD §6.1.a, ARCHITECTURE "NIC-56" section, PLAN NIC-56 entry) is present and accurate.

Per FACTORY_PROTOCOL.md, QA Reviewer does not move the Linear ticket state — Boss will move NIC-56 to Done.

---

## NIC-62 — Real PDF generation for tailored CV / cover letter

**Verdict: PASS**
**Reviewer:** QA Reviewer (Bot)
**Date:** 2026-09-12

### Scope reviewed

- New script `scripts/render_markdown_to_pdf.py` against `docs/handoffs/NIC-62-product-planner-scope-validation.md` §7 AC1–AC10.
- Docs: `docs/ARCHITECTURE.md` "NIC-62" section (~line 528-602), `docs/PLAN.md` "NIC-62" section (~line 235-259) — present, read in full, and cross-checked against QA's own independently-derived evidence below (not accepted on Builder's word alone).
- Protected scripts confirmed called unmodified: `scripts/notion_cv_attachment.py`, `scripts/notion_cover_letter_attachment.py`, `scripts/notion_attachment_naming.py`, `scripts/notion_job_page_blocks.py`.
- All evidence below is QA's own independently re-derived evidence this session (fresh render, fresh visual/text inspection, fresh adversarial run, and — the single most important check per Boss's explicit instruction — a brand-new, live, real Notion round-trip performed by QA itself, not a re-inspection of Builder's prior `/tmp/nic62_e2e_evidence.json`/`run.log`).

### Acceptance criteria results

| # | Criterion | Result | QA's own evidence |
|---|---|---|---|
| AC1 | CV PDF: distinct header, section/sub-heading hierarchy, real bulleted lists, no literal markdown | PASS | Fresh render (`.venv/bin/python3 scripts/render_markdown_to_pdf.py .../cv-v2.md --kind cv -o /tmp/qa_nic62/qa_cv.pdf`, exit 0, 37610 bytes — byte-identical to Builder's own claimed size). `pdftoppm` → PNG page 1, inspected via `vision_analyze`: confirmed large bold name header ("Nicolas Wajs — CV") with a distinct smaller bold subtitle line beneath it; blue bold `##` section heading ("Expériences") visually distinct from bold-but-smaller `###` sub-headings (e.g. "Product Management, Data & IA — Indépendant"); genuine indented `•`-bulleted list items, each on its own line, not a run-on blob; zero literal `#`/`##`/`**`/`- ` characters visible anywhere on the page. |
| AC2 | Cover-letter PDF: paragraph spacing, salutation/closing distinguishable, no visible raw markdown | PASS | Fresh render of `outreach-v2.md` (`--kind cover-letter`, exit 0, 17407 bytes — byte-identical to Builder's claim). `pdftoppm` + `vision_analyze` on page 1: salutation ("Madame, Monsieur,") visually separated by blank-line spacing from the body; each of 5 body paragraphs rendered as its own visually separated block; closing ("Cordialement, Nicolas Wajs") separated with extra spacing; zero literal markdown syntax visible. |
| AC3 | Cover-letter PDF contains only the cover letter, not recruiter-email/LinkedIn sections | PASS | `pdftotext` on QA's own freshly-rendered cover-letter PDF, then `grep -n -E "Objet :\|Message LinkedIn\|Lettre de motivation\|Cover Letter\|^---$"` → **zero matches** (grep exit code 1). Full extracted text manually reviewed: only the letter body/salutation/closing present, no recruiter-email or LinkedIn-message text. |
| AC4 | Valid, non-corrupt PDF output | PASS | `pdfinfo` on both of QA's own freshly-rendered PDFs: CV — `Encrypted: no`, `Pages: 3`, `PDF version: 1.4`; Cover letter — `Encrypted: no`, `Pages: 1`, `PDF version: 1.4`. |
| AC5 | Real PDF attaches via unmodified `attach_final_cv()`/`attach_final_cover_letter()` with zero intermediate transformation | PASS | QA imported and called both functions directly (`from notion_cv_attachment import attach_final_cv`, `from notion_cover_letter_attachment import attach_final_cover_letter`) against QA's own freshly-rendered PDF file paths, no wrapping/monkeypatching/renaming. `cv_attach["upload_result"]["put_status"] == 200`, `cl_attach["upload_result"]["put_status"] == 200`. New `file` blocks: CV `3d905073-c5b0-8110-901e-d83ea26d1094`, Cover Letter `3d905073-c5b0-812b-9932-cee00735e782`. |
| AC6 | NIC-48 naming convention respected | PASS | Filenames computed via the unmodified `build_attachment_filename("NEXTON", "Product Owner IA Générative", "CV"/"Cover Letter")` → `"NEXTON - Product Owner IA Générative - CV.pdf"` / `"...- Cover Letter.pdf"`. `GET /v1/blocks/{page_id}/children` confirmed both Notion `file` block `name` fields match these computed strings exactly. |
| AC7 | At least one full real end-to-end run (real markdown → real PDF → real attach → downloadable/viewable) | PASS | **Full fresh live cycle performed by QA this session** (not a re-inspection of Builder's prior run): real `/home/nicow/cv-job-match/applications/2026-09-01_NEXTON_Product-Owner-IA-Generative/cv-v2.md` + `outreach-v2.md` → real PDFs rendered by QA (37610/17407 bytes) → new test page created by QA (`page_id 3d905073-c5b0-81f2-8299-f575296f3601`, `Name: "TEST NIC-62 QA verification - NEXTON"`, `Company: NEXTON`, `Role: Product Owner IA Generative`, `Status: selected`, `children = build_job_page_children()` unmodified) → both PDFs attached via the unmodified attach functions → `GET /v1/blocks/{page_id}/children` confirms `total_blocks: 14`, `file_block_count: 2` → **both presigned S3 URLs fetched directly by QA**: `HTTP 200`, `Content-Type: application/pdf`, `Content-Length` 37610/17407 exactly matching local file size, and **SHA-256 of fetched bytes identical to SHA-256 of local file** for both PDFs (stronger check than the AC's own byte-count requirement) → test card archived (`PATCH {"archived": true}` → `archived_response: true`) → follow-up `GET /v1/pages/{page_id}` independently confirms `archived: true`. |
| AC8 | No production Notion card modified during testing | PASS | QA captured its own before-run baseline (`POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query {}` → 5 real cards recorded: Staff CSM, Freelance ×2, Senior PM, Implementation Manager - Strategic Accounts) and an after-run query following QA's own create+attach+archive cycle. Programmatic diff: **all 5 real cards' `page_id`/`Name`/`last_edited_time`/`archived` values byte-identical** before and after (zero mismatches); QA's own test card does not appear in either query result set (correctly excluded once archived). |
| AC9 | Documentation updated (NIC-46/47 "synthetic PDF" limitation closed or noted) | PASS | Confirmed by direct read: `docs/ARCHITECTURE.md` "NIC-62" section (~line 528-602) present with design decision, parser/extractor logic, real E2E evidence trail, and AC1–AC10 evidence summary table; `docs/PLAN.md` "NIC-62" section (~line 235-259) present with definition-of-done checklist and dependencies/follow-ups. |
| AC10 | Zero changes to the three protected scripts (+ `notion_job_page_blocks.py`) and no v1-repo file changes | PASS | `sha256sum` of all four scripts (QA's own run, this session): `notion_cv_attachment.py` `56eb5974...93c0`, `notion_cover_letter_attachment.py` `9f757580...97664`, `notion_attachment_naming.py` `ec2f76b6...0a56`, `notion_job_page_blocks.py` `56eb107a...55bce` — identical to the hashes already on record from Builder's own AC10 evidence and from NIC-48's original evidence. `git diff` for all four scripts returns empty. `git status --porcelain` in `/home/nicow/cv-job-match` (v1 repo), checked by QA both before and after this session's read-only file access: identical pre-existing dirty state (`M .claude/skills/run-my-week/SKILL.md`, `M tracker/job-tracker-model.md`, plus pre-existing untracked folders) — no entry attributable to QA's read-only markdown consumption. |

### Tests executed

- `.venv/bin/python3 scripts/render_markdown_to_pdf.py .../cv-v2.md --kind cv -o /tmp/qa_nic62/qa_cv.pdf` → exit 0, 37610 bytes.
- `.venv/bin/python3 scripts/render_markdown_to_pdf.py .../outreach-v2.md --kind cover-letter -o /tmp/qa_nic62/qa_cl.pdf` → exit 0, 17407 bytes.
- `pdfinfo` on both rendered PDFs — see AC4.
- `pdftotext` + `grep` on the cover-letter PDF — see AC3.
- `pdftoppm -png` to rasterize both PDFs, then `vision_analyze` on the page images — see AC1/AC2.
- Adversarial edge case: `.venv/bin/python3 scripts/render_markdown_to_pdf.py /home/nicow/cv-job-match/applications/2026-08-28_UpSlide_Senior-Product-Manager/outreach-v1.md --kind cover-letter -o /tmp/qa_nic62/qa_adversarial.pdf` (this file uses the older, unnumbered `## Cover Letter` heading format, not the `## 1. Lettre de motivation` format the extractor recognizes) → **failed loudly as designed**: `CoverLetterBoundaryError` raised, exit code 3, no output file written. Confirmed this is documented expected behavior (scope doc §9 risk table, ARCHITECTURE.md "Known limitations"), not a defect.
- `sha256sum` + `git diff` on all four protected scripts — see AC10.
- `git status --porcelain` in `/home/nicow/cv-job-match` (v1 repo) — see AC10.
- Live Notion API baseline query before QA's own work: 5 real production cards recorded, matching Builder's own recorded baseline exactly.
- Full live Notion round-trip performed by QA this session (create test page → attach CV PDF → attach cover-letter PDF → `GET /v1/blocks/{page_id}/children` → direct presigned-URL fetch with SHA-256 verification for both files → archive → follow-up `GET` → before/after `data_sources` query diff) — see AC5/AC6/AC7/AC8 above. Full machine-readable evidence: `/tmp/qa_nic62/qa_e2e_evidence.json`.

### Defects

None found.

### Severity

N/A — no defects.

### Release recommendation

**PASS. Safe to release / mark Done.** All 10 acceptance criteria independently re-verified with QA's own fresh evidence, generated this session, including — per Boss's explicit instruction that this was the single most important check — a brand-new, live, real Notion round-trip (not a re-inspection of Builder's prior evidence file): a genuinely new test page (`page_id 3d905073-c5b0-81f2-8299-f575296f3601`, distinct from Builder's own prior test page `3d805073-c5b0-8100-816c-f3d9669dc376`), fresh PDF renders, fresh attach calls, and SHA-256-exact byte verification of both files fetched directly from Notion's presigned S3 URLs — stronger than the AC's own "byte-exact Content-Length" requirement. The test card was archived immediately after evidence capture and independently confirmed archived. All 5 real production Notion cards are confirmed byte-identical (`page_id`/`Name`/`last_edited_time`/`archived`) before and after this review. The three protected attachment/naming scripts plus `notion_job_page_blocks.py` are confirmed byte-for-byte unmodified (sha256sum match, empty git diff), and the v1 repo shows no changes attributable to this review's read-only file access. The adversarial edge case (older unnumbered write-outreach heading format) correctly fails loudly rather than silently mis-extracting, consistent with the documented "fail loudly, never guess" design.

Per FACTORY_PROTOCOL.md, QA Reviewer does not move the Linear ticket state — Boss will move NIC-62 to Done.

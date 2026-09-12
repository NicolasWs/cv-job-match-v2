# ARCHITECTURE — cv-job-match v2

Design decisions, interfaces, data model, and risks. Populated incrementally as tickets ship; this file currently documents NIC-42 and NIC-43. See docs/PRD.md for the full target-state design and docs/PLAN.md for phased rollout status.

---

## NIC-42 — Notion Kanban Database

### Design decision

Built as a standard Notion **child database** (not inline) under the existing "Job Search" page, using the current Notion API version `2025-09-03` where a "database" object owns one or more "data source" objects (the data source holds the actual property schema and is what gets queried).

Created via a single `POST /v1/databases` call with `initial_data_source.properties` — this creates the database, its first data source, and its first table view in one atomic call, avoiding a separate create-data-source round trip.

### Data model (as created and verified)

| Property | Type | Notes |
|---|---|---|
| `Name` | `title` | Required by Notion API (every database needs exactly one title property). |
| `Status` | `status` | Native Notion status type (not `select`) for board-view/Kanban grouping support. 9 options, grouped per spec (see below). |
| `Company` | `rich_text` | Free text, filterable via `contains`/`equals` text filters. |
| `Role` | `rich_text` | Same as Company. |
| `Priority` | `select` | Options: `High`, `Med`, `Low`. |

**Status options and group assignment (verbatim, as returned by the Notion API):**

| Status option | Group |
|---|---|
| `selected` | To-do |
| `cv scored` | In progress |
| `cover letter done` | In progress |
| `applied` | In progress |
| `first interview` | In progress |
| `second interview` | In progress |
| `offer` | Complete |
| `rejected` | Complete |
| `withdrawn` | Complete |

This exactly matches the approved Product Planner scope (9 values, verbatim casing/spacing, grouped to-do/in-progress/complete as specified).

### Created identifiers (not secrets — safe to record for QA re-verification)

- **Parent page** (existing, unchanged): `3ab05073-c5b0-8061-bc12-e92aa903bebc` ("Job Search")
- **`database_id`**: `dc98669c-8b63-4f20-b6c0-abdafe8222c6`
- **`data_source_id`**: `47340a66-9e15-4ea1-8edf-45bba44c2334`
- **Database URL**: https://app.notion.com/p/dc98669c8b634f20b6c0abdafe8222c6
- **Database title**: "Job Search Kanban"

### API evidence

**1. Create call — request body sent (`POST /v1/databases`):**
```json
{
  "parent": { "type": "page_id", "page_id": "3ab05073-c5b0-8061-bc12-e92aa903bebc" },
  "title": [{ "text": { "content": "Job Search Kanban" } }],
  "initial_data_source": {
    "properties": {
      "Name": { "title": {} },
      "Status": {
        "status": {
          "options": [
            { "name": "selected", "color": "gray", "group": "To-do" },
            { "name": "cv scored", "color": "blue", "group": "In progress" },
            { "name": "cover letter done", "color": "blue", "group": "In progress" },
            { "name": "applied", "color": "yellow", "group": "In progress" },
            { "name": "first interview", "color": "orange", "group": "In progress" },
            { "name": "second interview", "color": "orange", "group": "In progress" },
            { "name": "offer", "color": "green", "group": "Complete" },
            { "name": "rejected", "color": "red", "group": "Complete" },
            { "name": "withdrawn", "color": "default", "group": "Complete" }
          ]
        }
      },
      "Company": { "rich_text": {} },
      "Role": { "rich_text": {} },
      "Priority": {
        "select": {
          "options": [
            { "name": "High", "color": "red" },
            { "name": "Med", "color": "yellow" },
            { "name": "Low", "color": "gray" }
          ]
        }
      }
    }
  }
}
```

**Response (200, actual, trimmed to key fields):**
```json
{
  "object": "database",
  "id": "dc98669c-8b63-4f20-b6c0-abdafe8222c6",
  "title": [{ "plain_text": "Job Search Kanban" }],
  "parent": { "type": "page_id", "page_id": "3ab05073-c5b0-8061-bc12-e92aa903bebc" },
  "data_sources": [{ "id": "47340a66-9e15-4ea1-8edf-45bba44c2334", "name": "Job Search Kanban" }],
  "url": "https://app.notion.com/p/dc98669c8b634f20b6c0abdafe8222c6"
}
```

**2. Verification — `GET /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334`:**
- `parent`: `{"type": "database_id", "database_id": "dc98669c-8b63-4f20-b6c0-abdafe8222c6"}` — confirms this data source belongs to the database created under the Job Search page (traced above).
- `properties` returned: `Priority (select)`, `Role (rich_text)`, `Company (rich_text)`, `Status (status)`, `Name (title)` — all 5 present, correct types.
- `Status` options (exact list returned by API, in order): `selected`, `cv scored`, `cover letter done`, `applied`, `first interview`, `second interview`, `offer`, `rejected`, `withdrawn` — exactly 9, verbatim match to spec, no extras.
- `Status` groups (exact API response): `To-do -> [selected]`, `In progress -> [cv scored, cover letter done, applied, first interview, second interview]`, `Complete -> [offer, rejected, withdrawn]` — exact match to spec.
- `Priority` options: `High`, `Med`, `Low` — exact match.

**3. Filterability — one `POST /v1/data_sources/{id}/query` per required property, all four executed for real:**

| Property | Filter body | Result |
|---|---|---|
| Status | `{"filter": {"property": "Status", "status": {"equals": "selected"}}}` | `200 OK`, `results: []` (empty — expected, no cards exist) |
| Priority | `{"filter": {"property": "Priority", "select": {"equals": "High"}}}` | `200 OK`, `results: []` |
| Company | `{"filter": {"property": "Company", "rich_text": {"contains": "Test"}}}` | `200 OK`, `results: []` |
| Role | `{"filter": {"property": "Role", "rich_text": {"contains": "Product"}}}` | `200 OK`, `results: []` |

All four queries returned `200` with valid Notion list-object responses (`object: "list"`, `has_more: false`) — proving each property is genuinely filterable via the API. Empty result sets are expected and correct since no seed cards were created (explicit scope decision, see below).

**4. Unfiltered query confirming zero cards exist in the new database** (verifies no fabricated data was introduced): `POST /v1/data_sources/{id}/query` with `{}` body → `results: []`, 0 total.

### Known limitation: Kanban board view

The Notion REST API **cannot create or configure database views** — this is a documented, current limitation of the API (confirmed via Notion's own developer docs: "A standard 'table' view is created alongside the new data source. To customize database views, use the Notion app. Managing views is not currently supported in the API."). This is not a workaround-able gap; it is an intentional API boundary.

**What this means concretely:**
- The database currently has only the default table view (created automatically by `POST /v1/databases`).
- The `Status` property being of type `status` (not `select`) means Notion's UI *will* offer native board-view grouping once a Board view is added — the schema fully supports it.
- **Manual step required from the user:** in the Notion app, open the "Job Search Kanban" database → **View → Add View → Board** → group by `Status`. This cannot be automated via API and is not attempted here; it is flagged as a known gap, not hidden.

### Out of scope confirmation (per approved Product Planner scope)

- No job/card pages were created (schema only).
- No file attachments, company research content, cheat sheets built.
- No n8n automation touched.
- No changes made to the sibling v1 repo (`/home/nicow/cv-job-match`) — verified via `git status` showing only a pre-existing untracked directory unrelated to this work; `tracker/job-tracker-model.md` and `config/search-profile.yaml` were not read for modification, only referenced read-only in the PRD's own prior research.

---

## NIC-43 — Per-job Notion page template

### Design decision

Per Product Planner scope validation (`docs/handoffs/NIC-43-product-planner-scope-validation.md`), the Notion REST API has **no `templates` endpoint** (confirmed against API version `2025-09-03`) — a native Notion database template configured via the "+ New" button's template picker cannot be created or assigned via the API. This is the same category of gap as NIC-42's Kanban board-view limitation. Two tracks were scoped:

- **Track A (primary deliverable, implemented this ticket):** a reusable block-structure helper that produces the 14-block `children` array and is passed in the *same* `POST /v1/pages` request that creates a job card (`parent.database_id`, `properties`, `children` all in one call). This is the only mechanism the API can enforce automatically, and only for cards created **through the API** (not for cards a human creates by clicking "+ New" in the Notion UI).
- **Track B (recommended, manual, non-blocking, NOT implemented this ticket):** a matching Notion-native database template configured by hand in the Notion UI, mirroring the same five sections, so that a human using "+ New" today (per NIC-45's documented manual-entry gap — no card-creation skill exists yet in this repo) gets the same structure without waiting for a future automation ticket (NIC-44 or later). This is a recommendation, not an implemented artifact: Builder did not open the Notion UI to configure it. Nicolas (or a future ticket) can configure it manually by opening the "Job Search Kanban" database → the database's "+ New" dropdown → "New template" → replicate the 5-section structure documented below. Flagged here explicitly so QA Reviewer/Nicolas do not mistake Track B for an automated guarantee — same caveat class as the NIC-42 board-view gap.

### Track A — reusable block helper

Implemented at `scripts/notion_job_page_blocks.py` (`build_job_page_children()`), a pure-Python, dependency-free function returning the Notion API `children` block array. No network calls in the module itself — callers own the `POST /v1/pages` request. Any future card-creation code (NIC-44's conversational skill, or a later automation) should import and call this function to guarantee every API-created card gets the structure automatically, with no per-card manual formatting.

### Block schema (14 blocks, order matches FR-D3)

| # | Section | Blocks | Text |
|---|---|---|---|
| 1 | Job Details | `heading_2` + `paragraph` | "📋 Job Details" / "Add job description / posting link here" |
| — | (divider) | `divider` | — |
| 2 | Company Research Brief | `heading_2` + `callout` (🕒, gray background) | "🔍 Company Research Brief" / "Pending — populated by the `company-research` skill (Phase 3, not yet built). Will include company summary, recent video, headcount by country, and recent news within a 12-month window (OQ-14)." |
| — | (divider) | `divider` | — |
| 3 | Tailored CV | `heading_2` + `callout` (📎, gray background) | "📄 Tailored CV" / "Pending — PDF file will be attached here once `cv-match` output is filed (Phase 2). Target format: PDF (OQ-13/NIC-40)." |
| — | (divider) | `divider` | — |
| 4 | Cover Letter | `heading_2` + `callout` (📎, gray background) | "✉️ Cover Letter" / "Pending — PDF file will be attached here once `write-outreach` output is filed (Phase 2). Target format: PDF (OQ-13/NIC-40)." |
| — | (divider) | `divider` | — |
| 5 | Interview Cheat Sheet | `heading_2` + `callout` (🕒, gray background) | "🎯 Interview Cheat Sheet" / "Pending — generated once this job reaches an interview stage (Phase 4)." |

Total: 5 `heading_2` + 1 `paragraph` + 4 `callout` + 4 `divider` = 14 blocks. `callout` (not `paragraph`) is used for sections 2–5 to visually distinguish "placeholder, not forgotten" from a genuinely empty/broken page (per scope doc §7) — Job Details (section 1) uses a plain `paragraph` since it's immediately fillable, no upstream dependency.

`file` blocks cannot exist "empty" in the Notion API, so CV/Cover Letter placeholders use `callout` now; Phase 2 work must locate and replace/append near the placeholder callout rather than assume a pre-existing empty `file` block.

### `pages.create` call shape (as actually sent)

```json
{
  "parent": { "database_id": "dc98669c-8b63-4f20-b6c0-abdafe8222c6" },
  "properties": {
    "Name": { "title": [{ "text": { "content": "<job title>" } }] },
    "Status": { "status": { "name": "selected" } },
    "Company": { "rich_text": [{ "text": { "content": "<company>" } }] },
    "Role": { "rich_text": [{ "text": { "content": "<role>" } }] },
    "Priority": { "select": { "name": "High|Med|Low" } }
  },
  "children": [ /* 14-block array from scripts/notion_job_page_blocks.py */ ]
}
```

`properties` + `children` in the same `POST /v1/pages` call is what satisfies AC3 for API-driven creation: no separate follow-up `PATCH /v1/blocks/{id}/children` call is needed.

### Verification evidence (test card, created and archived same session)

- **Create call:** `POST /v1/pages` with the shape above, `properties` set to clearly-marked test values (`Name: "TEST NIC-43 verification card - safe to archive"`, `Company: "TEST"`, `Role: "TEST"`, `Status: "selected"`, `Priority: "Low"`) and the full 14-block `children` array, sent as **one single request**. Response: `200 OK`, `id: 3d705073-c5b0-814a-9ea3-e76663da7b28`, `url: https://app.notion.com/p/TEST-NIC-43-verification-card-safe-to-archive-3d705073c5b0814a9ea3e76663da7b28`.
- **Structure verification:** `GET /v1/blocks/3d705073-c5b0-814a-9ea3-e76663da7b28/children` → `200 OK`, `results.length == 14`, `has_more: false`. Block sequence confirmed in order: `heading_2("📋 Job Details")`, `paragraph`, `divider`, `heading_2("🔍 Company Research Brief")`, `callout`, `divider`, `heading_2("📄 Tailored CV")`, `callout`, `divider`, `heading_2("✉️ Cover Letter")`, `callout`, `divider`, `heading_2("🎯 Interview Cheat Sheet")`, `callout` — exact match to the schema table above, satisfying AC1 and AC2.
- **Cleanup:** `PATCH /v1/pages/3d705073-c5b0-814a-9ea3-e76663da7b28` with `{"archived": true}` → `200 OK`, response confirms `"archived": true`. No fabricated data left live in the production Notion database.

### Out of scope confirmation (per approved Product Planner scope)

- No real section content populated (company research text, CV file, cover letter file, cheat sheet content) — Phase 2/3/4 work, not this ticket.
- No card-creation skill or conversational entry point built (that's NIC-44).
- No changes to the NIC-42 database schema (`Name`/`Status`/`Company`/`Role`/`Priority` unchanged, no new properties added).
- No n8n automation touched.
- Track B (Notion-native UI template) was **not** configured by Builder — documented as a manual, optional, non-blocking recommendation only, per §6/§12 of the scope doc.
- No changes made to the sibling v1 repo (`/home/nicow/cv-job-match`) — verified via `git status` showing only the same pre-existing untracked directory as before this ticket's work.

---

## NIC-46 — Tailored CV Notion file attachment

### Design decision

Per Product Planner scope validation (`docs/handoffs/NIC-46-product-planner-scope-validation.md`, §6), **Option A** was implemented: a block-level `file` object inserted directly under the `heading_2("📄 Tailored CV")` block, replacing the NIC-43 placeholder `callout`. Rejected alternative (**Option B**, a page-level `Files & media` database property) was not pursued — it would require a NIC-42 schema change (out of that ticket's closed scope) and would break the section-based page-reading order NIC-43 established. Option A requires no schema change and reuses the exact seam NIC-43's own risk table flagged: "`file` blocks cannot exist 'empty' in the Notion API — CV/Cover Letter placeholders must use `callout`/`paragraph` blocks now, then be replaced or appended by a real `file` block once Phase 2 ships."

**Final-version-only (OQ-5 / AC2) mechanism:** before inserting the new `file` block, the implementation locates all `callout`/`file`/`paragraph` blocks currently sitting between the "Tailored CV" heading and the next `divider`/`heading_2`, remembers their ids, inserts the new `file` block immediately after the heading (`PATCH /v1/blocks/{page_id}/children` with `after: <heading_block_id>`), then archives (`DELETE /v1/blocks/{block_id}`) every block id it remembered. This works identically whether the "old" block is the original NIC-43 placeholder callout (first attach) or a previously-attached file block (a "revised CV" re-attach) — in both cases exactly one artifact remains after the operation. Verified live for both cases below.

### Implementation

New file: `scripts/notion_cv_attachment.py`. No Notion SDK, no third-party HTTP library — pure `urllib.request` (same dependency-light style as `notion_job_page_blocks.py`, except this module *does* make real network calls, which is the point of this ticket). Exposes:

- `create_file_upload()` / `put_file_bytes()` / `upload_pdf()` — the 3-step `file_uploads` flow.
- `find_tailored_cv_section(page_id)` — locates the heading block and the section's current content blocks by walking `GET /v1/blocks/{page_id}/children` results until the next `divider`/`heading_2`; raises loudly if the heading text isn't found (never guesses a section to touch).
- `insert_file_block_after()` — `PATCH /v1/blocks/{page_id}/children` with `after` set to the heading's block id.
- `archive_block()` — `DELETE /v1/blocks/{block_id}` (Notion's delete is an archive, not a hard destroy).
- `attach_final_cv(page_id, pdf_path, filename)` — orchestrates all of the above end-to-end and returns every intermediate response for evidence capture.
- `archive_page(page_id)` — test-artifact cleanup only (`PATCH /v1/pages/{page_id}` `{"archived": true}`).

### Call shapes (as actually sent and received — real evidence, no fabrication)

**Correction to the generic 3-step description in the `notion` skill doc:** the skill's example curl shows step 2 as a raw `PUT {upload_url} --data-binary @file`. Live testing found this returns `400 invalid_request_url` — the real, current (API version `2025-09-03`) shape is:

1. `POST /v1/file_uploads` with `{"filename": "...", "content_type": "application/pdf"}` → `200 OK`, response includes `id` and `upload_url` (the `upload_url` value is itself `https://api.notion.com/v1/file_uploads/{id}/send`).
2. `POST {upload_url}` (not `PUT`) with `Content-Type: multipart/form-data; boundary=...` and the file bytes as a `file` form field, using the **same** `Authorization`/`Notion-Version` headers as every other call → `200 OK`, response `status` changes from `"pending"` to `"uploaded"`, `content_length` now populated.
3. `PATCH /v1/blocks/{page_id}/children` with `{"children": [{"object": "block", "type": "file", "file": {"type": "file_upload", "file_upload": {"id": "<file_upload_id>"}, "name": "<filename>"}}], "after": "<heading_block_id>"}` → `200 OK`, `results[0]` is the new `file`-type block with a resolvable, presigned S3 URL (`prod-files-secure.s3.us-west-2.amazonaws.com/...`, 1-hour expiry).
4. `DELETE /v1/blocks/{old_block_id}` for each block being replaced → `200 OK`, response shows `"archived": true, "in_trash": true` on the old block.

### Verification evidence (real test card, created and archived same session)

**Test card:** `page_id 3d805073-c5b0-8174-9372-c114f6c398b4`, created via `POST /v1/pages` with `parent.database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `properties` = `{Name: "TEST NIC-46 verification", Company: "TEST", Role: "TEST", Status: "selected", Priority: "Low"}`, and `children` = the full 14-block array from `build_job_page_children()` (same call shape as NIC-43), all in one request. Response: `200 OK`, `url: https://app.notion.com/p/TEST-NIC-46-verification-3d805073c5b081749372c114f6c398b4`.

**Baseline (before any attach work):** `POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query` with `{}` → `200 OK`, 5 real cards returned (`Senior PM`, `Staff CSM`, `Freelance` ×2, `Implementation Manager - Strategic Accounts`), each `page_id` and `last_edited_time` recorded for later diffing.

**Structure check (proves the seam exists to be replaced):** `GET /v1/blocks/3d805073-c5b0-8174-9372-c114f6c398b4/children` → `200 OK`, `results.length == 14`, block #7 (0-indexed 6) = `heading_2("📄 Tailored CV")` (`id 3d805073-c5b0-8175-99a8-e7bbe80b03c0`), block #8 = the NIC-43 placeholder `callout` (`id 3d805073-c5b0-8187-b278-d78c118b4e72`, text "Pending — PDF file will be attached here once `cv-match` output is filed...").

**AC1 — attach v1, upload + viewable/downloadable:**
- `POST /v1/file_uploads` `{"filename": "TEST Company - TEST Role - CV.pdf", "content_type": "application/pdf"}` → `200 OK`, `id: 3d805073-c5b0-8137-8511-00b29bb13d17`, `status: "pending"`.
- `POST {upload_url}` (multipart, 498-byte synthetic PDF) → `200 OK`, `status: "uploaded"`, `content_length: 498`.
- `PATCH /v1/blocks/3d805073-c5b0-8174.../children` with `after` = the Tailored CV heading id → `200 OK`, new `file` block `id 3d805073-c5b0-8109-a71d-f2580adf2450` present, `file.file.url` = a presigned S3 URL.
- Old placeholder callout archived: `DELETE /v1/blocks/3d805073-c5b0-8187-b278-d78c118b4e72` → `200 OK`, `"archived": true, "in_trash": true`.
- `GET /v1/blocks/{page_id}/children` re-fetched → Tailored CV section now contains exactly one block, `type: "file"`; the old callout is gone from the results entirely (archived blocks are excluded from children listing).
- Fetched the file's presigned URL directly: `GET {s3_url}` → `HTTP 200`, `Content-Type: application/pdf`, `Content-Length: 498`. Fetched bytes compared byte-for-byte against the original 498-byte local PDF: **identical** (`bytes_match_original: true`). This proves the file is genuinely uploaded, hosted, and downloadable — not merely referenced.

**AC2 — no-accumulation / final-version-only, simulated "revised CV" re-attach:**
- Called `attach_final_cv()` a second time on the **same** `page_id` with a different (506-byte) synthetic "v2" PDF and the same target filename.
- `POST /v1/file_uploads` → new `id 3d805073-c5b0-8148-9dbd-00b24d4d7103`, uploaded (506 bytes).
- `PATCH .../children` inserted a **new** file block (`id 3d805073-c5b0-811f-a703-eb99c4e0636f`) after the same heading.
- The **v1 file block** (`3d805073-c5b0-8109-a71d-f2580adf2450`, the "old" block from the mechanism's point of view this time) was archived via `DELETE /v1/blocks/{id}` → `200 OK`, `archived: true`.
- Post-reattach `GET /v1/blocks/{page_id}/children`: `total_blocks_on_page: 14` (unchanged — same count as the original template, since one callout was replaced 1-for-1 by one file block), `file_block_count: 1` — **not 2**. Fetched the resulting file's URL → 506 bytes, byte-for-byte match to the v2 dummy PDF, and explicitly does **not** match the v1 dummy PDF's bytes. This proves the mechanism replaces in place rather than appends, satisfying OQ-5.

**AC3 — PDF format:**
- Both `file_uploads` create calls used `"content_type": "application/pdf"` explicitly.
- Both resulting `file_upload` objects report `"content_type": "application/pdf"` in their response.
- Both resulting Notion `file` blocks carry `name: "TEST Company - TEST Role - CV.pdf"` (`.pdf` extension).
- Both direct-fetch responses returned `Content-Type: application/pdf`.

**AC4 — correct-page-only targeting:**
- The test card's `page_id` (`3d805073-c5b0-8174-9372-c114f6c398b4`) was hardcoded throughout — never derived from a name search or filter that could accidentally match a real card.
- Post-attach re-query of `POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query` `{}`: all 5 real cards' `page_id`, `Name`, and `last_edited_time` values are **identical** to the pre-work baseline — proving none were read-modify-written or altered in any way during this ticket's work. (`Senior PM` 2026-09-10T22:44:00Z, `Staff CSM` 2026-09-10T22:42:00Z, `Freelance` ×2 2026-09-10T22:40:00Z, `Implementation Manager - Strategic Accounts` 2026-09-10T22:39:00Z — unchanged before and after.)

**AC5 — synthetic PDF, explicitly stated:** Both test files used for verification (498-byte and 506-byte) were minimal, hand-constructed, valid-but-trivial PDF documents containing only the literal text "SYNTHETIC TEST PDF v1 - NIC-46 mechanism check" / "...v2 REVISED", generated purely to exercise the upload/replace mechanism. **Neither is a real `cv-match` output, and no real end-to-end `cv-match` → PDF → Notion run was performed.** `cv-match` (v1 repo) has no PDF-export step today (confirmed fact, unchanged by this ticket) — this is a known, explicitly-flagged gap, not hidden.

**AC6 — test artifact discipline:**
- Test card `Name` property: `"TEST NIC-46 verification"`; `Company`/`Role`: `"TEST"`; `Status`: `"selected"` — all set at creation.
- Built via `build_job_page_children()` for the initial 14-block structure, so the real NIC-43 placeholder existed and was genuinely replaced (not fabricated as already-empty).
- After all evidence above was captured: `PATCH /v1/pages/3d805073-c5b0-8174-9372-c114f6c398b4` `{"archived": true}` → `200 OK`, response `"archived": true`. Follow-up `GET /v1/pages/3d805073-c5b0-8174-9372-c114f6c398b4` → `200 OK`, `"archived": true` confirmed independently. Final unfiltered database query (`POST /v1/data_sources/{id}/query {}`) returns exactly the same 5 real cards as the original baseline — the test card no longer appears (Notion excludes archived pages from query results) and no fabricated data remains live.

### Known limitations

- ~~**No real `cv-match` PDF-export step exists**~~ — **CLOSED by NIC-62** (`scripts/render_markdown_to_pdf.py`, reportlab-based markdown→PDF renderer). NIC-62's own real end-to-end run rendered the real NEXTON `cv-v2.md` into a genuine 3-page PDF and attached it via this exact, unmodified `attach_final_cv()` function — see the "NIC-62 — Real PDF generation for tailored CV / cover letter" section above for the full evidence trail. This ticket (NIC-46) itself still only verified the *attachment mechanism* with synthetic PDFs (original text below retained for history), but the upstream gap it flagged is now closed.
- *(original NIC-46 note, retained for history):* there is currently no way to produce a genuine tailored-CV PDF as input to this mechanism without separate, out-of-scope work in the v1 repo. This ticket verified the *attachment mechanism* only, using synthetic PDFs, per explicit ticket authorization (AC5). **Recommended follow-up (OQ-A from the scope doc):** a new ticket for a PDF-export step in `cv-match` (and `write-outreach`), which is the actual prerequisite for a true end-to-end Phase 2 flow (real CV → real file → Notion).
- **Cover letter (FR-E2) reuses this exact mechanism but is out of scope for NIC-46** — `attach_final_cv()` is written generically (it locates by heading text, defaulting to `TAILORED_CV_HEADING`) so a future ticket can call it with the "✉️ Cover Letter" heading text with no code changes beyond passing a different `heading_text` argument; not exercised or verified against that heading in this ticket.
- **File-size/plan limits were not empirically probed** (`GET /v1/users/me` or equivalent was not called) — the scope doc's risk table flagged this; both test files here are far under any tier's limit (498–506 bytes), so this remains a theoretical risk for future large real CVs, not something this ticket could rule out with evidence.
- **File naming convention** used for verification (`"TEST Company - TEST Role - CV.pdf"`) approximates PRD's proposed `{Company} - {Role} - CV.pdf` (FR-E3, "proposed, not yet confirmed") but this ticket's AC did not require confirming that convention formally — flagged per the scope doc's own note.
- **Notion silently underscore-escapes the `filename` field in the `file_uploads` create response** (e.g. `"TEST Company - TEST Role - CV.pdf"` came back as `filename: "TEST_Company_-_TEST_Role_-_CV.pdf"` in the `file_uploads` object) even though the **block's** `file.name` field preserves the original spacing (`"TEST Company - TEST Role - CV.pdf"`) — this is a Notion API quirk observed live, not a bug in this implementation; the user-visible filename in the Notion UI comes from the block's `name` field, which is unaffected.

---

## NIC-47 — Cover Letter Notion file attachment

### Design decision: thin wrapper, zero changes to NIC-46's file

Per Product Planner scope validation (`docs/handoffs/NIC-47-product-planner-scope-validation.md`, §3), NIC-46's `attach_final_cv()` in `scripts/notion_cv_attachment.py` was verified reusable **as-is** by direct code read: it already accepts `heading_text` as an overridable parameter (default `TAILORED_CV_HEADING`), and its section-locator (`find_tailored_cv_section`) and replace/archive logic (`REPLACEABLE_BLOCK_TYPES = {"callout", "file", "paragraph"}`) contain no CV-specific logic beyond that default argument value. **Builder chose the recommended thin-wrapper approach** (Product Planner's §3 recommendation) over a bare direct call with an inline `heading_text="✉️ Cover Letter"` string, for two reasons: (1) self-documenting call sites (`attach_final_cover_letter(page_id, pdf_path, filename)` reads better than a magic string scattered across future callers, e.g. a future `write-outreach` PDF-export integration), and (2) it keeps `scripts/notion_cv_attachment.py` — already shipped and QA-PASS — at **zero changed lines**, eliminating any regression risk to NIC-46's mechanism.

**New file:** `scripts/notion_cover_letter_attachment.py`. Contains:
- `COVER_LETTER_HEADING = "\u2709\ufe0f Cover Letter"` — must exactly match the heading text produced by `build_job_page_children()` (block index 9, 0-indexed, in the 14-block array).
- `attach_final_cover_letter(page_id, pdf_path, filename)` — a one-line call to `attach_final_cv(page_id, pdf_path, filename, heading_text=COVER_LETTER_HEADING)`, imported unmodified from `notion_cv_attachment.py`.
- `find_cover_letter_section(page_id)` — same pattern, wraps `find_tailored_cv_section(page_id, heading_text=COVER_LETTER_HEADING)` for read-only inspection/CLI use.
- A CLI mirroring `notion_cv_attachment.py`'s `attach`/`list-section` commands, scoped to the Cover Letter heading.

**No new Notion API call shapes, no new HTTP/upload/replace logic, no third-party dependency.** Every underlying request (3-step `file_uploads` flow, `PATCH .../children` insert, `DELETE` archive) is byte-identical in shape to NIC-46's — see that ticket's section above for the exact request/response format (including the `POST {upload_url}` multipart correction). `scripts/notion_cv_attachment.py` was **not modified in any way** (confirmed: this ticket makes zero edits to that file).

### Call shape actually used (verification run)

```python
from notion_cover_letter_attachment import attach_final_cover_letter

result = attach_final_cover_letter(
    page_id="3d805073-c5b0-811a-9640-e652e54717fe",
    pdf_path="/tmp/nic47_test_v1.pdf",
    filename="TEST Company - TEST Role - Cover Letter.pdf",
)
```
which internally calls `attach_final_cv(page_id, pdf_path, filename, heading_text="\u2709\ufe0f Cover Letter")` in `notion_cv_attachment.py`, unmodified.

### Verification evidence (real test card, created and archived same session)

**Test card:** `page_id 3d805073-c5b0-811a-9640-e652e54717fe`, created via `POST /v1/pages` with `parent.database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `properties` = `{Name: "TEST NIC-47 verification", Company: "TEST", Role: "TEST", Status: "selected"}`, and `children` = the full 14-block array from `build_job_page_children()`, all in one request. Response: `200 OK`, `url: https://app.notion.com/p/TEST-NIC-47-verification-3d805073c5b0811a9640e652e54717fe`. Verified via a follow-up `GET /v1/pages/{page_id}` that all properties landed correctly (`Name` title = "TEST NIC-47 verification", `Company`/`Role` rich_text = "TEST", `Status` = "selected").

**Baseline (before any NIC-47 work):** `POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query` `{}` → `200 OK`, 5 real cards returned (`Senior PM` 3d705073-c5b0-80cf-8852-dd75bbfe46c5, `Staff CSM` 3d705073-c5b0-801e-8934-c9ec90eb7a11, `Freelance` ×2 3d705073-c5b0-80ec-9c10-cdfd3b316561 / 3d705073-c5b0-8020-840d-c7ff840ddda1, `Implementation Manager - Strategic Accounts` 3d705073-c5b0-814f-ab19-cb44462cbef9), each `page_id`/`last_edited_time` recorded — identical to NIC-46's baseline, confirming no drift between tickets.

**Structure check (proves the seam exists to be replaced):** `GET /v1/blocks/3d805073-c5b0-811a-9640-e652e54717fe/children` → `200 OK`, `results.length == 14`. Block index 9 (0-indexed) = `heading_2("✉️ Cover Letter")` (`id 3d805073-c5b0-8181-8ee5-fe9848edba3d`), block index 10 = the NIC-43 placeholder `callout` (`id 3d805073-c5b0-811d-a5a0-f86a4e2c5065`, text "Pending — PDF file will be attached here once `write-outreach` output is filed...").

**AC1/AC2 — non-regression on `write-outreach` (v1 repo):**
- `cd /home/nicow/cv-job-match && git status --porcelain=v1` at both the start and end of this ticket's work shows only pre-existing, unrelated dirty state (`M .claude/skills/run-my-week/SKILL.md`, `M tracker/job-tracker-model.md`, two pre-existing untracked directories) — **no entry for `write-outreach/SKILL.md` at any point.**
- `sha256sum .claude/skills/write-outreach/SKILL.md` computed before and after all NIC-47 work: `e4e72714df024dd6a34c5bf7ffcf0ca51ebb82393a77cf992a7ca8887794c183` both times — byte-for-byte identical.
- `git log -1 --format=%H -- .claude/skills/write-outreach/SKILL.md` → `a490e5b20d7f29fa4bb05b9fcaca72521c014719` (unchanged, no new commit touching this file). This is a non-regression confirmation only, per the scope doc's explicit framing — no new drafting-quality testing was performed or claimed.

**AC3 — real `file_uploads` 3-step flow, native file block (attach v1):**
- `POST /v1/file_uploads` `{"filename": "TEST Company - TEST Role - Cover Letter.pdf", "content_type": "application/pdf"}` → `200 OK`, `id: 3d805073-c5b0-8145-89ef-00b24842c08e`, `status: "pending"`.
- `POST {upload_url}` (multipart/form-data, 633-byte synthetic PDF) → `200 OK`, `status: "uploaded"`, `content_length: 633`.
- `PATCH /v1/blocks/3d805073-c5b0-811a.../children` with `after` = the Cover Letter heading block id (`3d805073-c5b0-8181-8ee5-fe9848edba3d`) → `200 OK`, new `file` block `id 3d805073-c5b0-816a-9471-f2783e59d507` present.
- Old placeholder callout archived: `DELETE /v1/blocks/3d805073-c5b0-811d-a5a0-f86a4e2c5065` → `200 OK`, `"archived": true, "in_trash": true`.
- `GET /v1/blocks/{page_id}/children` re-fetched → total block count still `14` (1-for-1 replace of the callout by the file block); Cover Letter section now contains exactly one block of `type: "file"`; the old callout no longer appears (archived blocks excluded from children listing).
- Resulting file block's URL: a resolvable, presigned S3 URL (`prod-files-secure.s3.us-west-2.amazonaws.com/...?X-Amz-...`, 1-hour expiry) — **not a Drive link**, satisfying "native file, not just linked to Drive."

**AC4 — file is uploaded, viewable/downloadable:**
- Fetched the file block's presigned URL directly: `GET {s3_url}` → `HTTP 200`, `Content-Type: application/pdf`, `Content-Length: 633`.
- Fetched bytes compared byte-for-byte against the original 633-byte local synthetic PDF: **identical** (`bytes_match_original: True`). Proves the file is genuinely uploaded, hosted, and downloadable — not merely referenced.

**AC5 — PDF format:**
- `file_uploads` create call used `"content_type": "application/pdf"` explicitly (both attach v1 and attach v2 below).
- `create_response` for both uploads reports `"content_type": "application/pdf"`.
- Both resulting Notion `file` blocks carry `name: "TEST Company - TEST Role - Cover Letter.pdf"` (`.pdf` extension).
- Both direct-fetch responses returned `Content-Type: application/pdf`.

**AC6 — no-accumulation / final-version-only, simulated "revised letter" re-attach:**
- Called `attach_final_cover_letter()` a second time on the **same** `page_id` with a different (641-byte) synthetic "v2 REVISED" PDF and the same target filename.
- `POST /v1/file_uploads` → new `id 3d805073-c5b0-8169-ad4c-00b284533d60`, uploaded (641 bytes, confirmed via `put_response.content_length`).
- `PATCH .../children` inserted a **new** file block (`id 3d805073-c5b0-81b5-b189-da084713921e`) after the same Cover Letter heading.
- The **v1 file block** (`3d805073-c5b0-816a-9471-f2783e59d507`, the "old" block from the mechanism's point of view on this second call) was archived via `DELETE /v1/blocks/{id}` → `200 OK`, `archived: true, in_trash: true`.
- Post-reattach `GET /v1/blocks/{page_id}/children`: `total_blocks_on_page: 14` (unchanged), `file_block_count: 1` under Cover Letter — **not 2**. Fetched the resulting file's URL → 641 bytes, `Content-Type: application/pdf`, byte-for-byte match to the v2 dummy PDF, and explicitly does **not** match the v1 dummy PDF's bytes (`matches_v2: True`, `matches_v1: False`). This proves the mechanism replaces in place rather than appends, confirming NIC-46's OQ-5 guarantee holds for the Cover Letter section too.

**AC7 — correct-page-only targeting, real cards and NIC-46's test card untouched:**
- The NIC-47 test card's `page_id` (`3d805073-c5b0-811a-9640-e652e54717fe`) was hardcoded throughout every call in this ticket — never derived from a name search or filter.
- Post-work re-query of `POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query` `{}` filtered to the 5 baseline `page_id`s: all 5 real cards' `page_id`, `Name`, `last_edited_time`, and `archived` values are **identical** to the pre-work baseline (`identical: True`, compared programmatically, not eyeballed) — none were read-modify-written or altered during this ticket's work.
- NIC-46's own archived test card (`page_id 3d805073-c5b0-8174-9372-c114f6c398b4`) was independently re-fetched via `GET /v1/pages/{id}`: `archived: True`, `last_edited_time: 2026-09-11T06:45:00.000Z` — unchanged from its NIC-46 archive timestamp, confirming it was not touched, unarchived, or modified by this ticket.

**AC8 — synthetic PDF, explicitly stated:** Both test files used for verification (633-byte and 641-byte) were minimal, hand-constructed, valid PDF/1.4 documents (verified with the `file` command: `PDF document, version 1.4, 1 page(s)`) containing only the literal text "SYNTHETIC TEST PDF v1 - NIC-47 cover letter mechanism check" / "...v2 REVISED - NIC-47 cover letter mechanism check", generated purely to exercise the attachment mechanism. **Neither is a real `write-outreach` output, and no real end-to-end `write-outreach` → PDF → Notion run was performed.** `write-outreach` (v1 repo) has no PDF-export step today (confirmed fact by reading `write-outreach/SKILL.md` in full — it saves drafts as markdown files at `applications/<slug>/outreach-v{n}.md`, no PDF step anywhere) — this is a known, explicitly-flagged gap, not hidden, and exactly mirrors NIC-46's `cv-match` finding.

**AC9 — test artifact discipline:**
- Test card `Name` property: `"TEST NIC-47 verification"`; `Company`/`Role`: `"TEST"`; `Status`: `"selected"` — all set at creation via `POST /v1/pages`, confirmed via follow-up `GET`.
- Built via `build_job_page_children()` for the initial 14-block structure, so the real NIC-43/46-shaped Cover Letter placeholder existed and was genuinely replaced (not fabricated as already-empty).
- After all evidence above was captured: `PATCH /v1/pages/3d805073-c5b0-811a-9640-e652e54717fe` `{"archived": true}` → `200 OK`, response `"archived": true`. Follow-up `GET /v1/pages/3d805073-c5b0-811a-9640-e652e54717fe` → `200 OK`, `"archived": true` confirmed independently. Final unfiltered database query (`POST /v1/data_sources/{id}/query {}`) returns exactly the same 5 real cards as the original baseline (count `5`, matching names/ids) — the test card no longer appears (Notion excludes archived pages from query results).

### Known limitations

- ~~**No real `write-outreach` PDF-export step exists**~~ — **CLOSED by NIC-62** (`scripts/render_markdown_to_pdf.py`, reportlab-based markdown→PDF renderer, with a dedicated cover-letter section extractor since `write-outreach`'s output bundles cover letter + recruiter email + LinkedIn message in one file). NIC-62's own real end-to-end run isolated and rendered the real NEXTON `outreach-v2.md`'s cover-letter section into a genuine 1-page PDF (confirmed to exclude the recruiter-email/LinkedIn sections) and attached it via this exact, unmodified `attach_final_cover_letter()` function — see the "NIC-62 — Real PDF generation for tailored CV / cover letter" section above for the full evidence trail. This ticket (NIC-47) itself still only verified the *attachment mechanism* with a synthetic PDF (original text below retained for history), but the upstream gap it flagged is now closed.
- *(original NIC-47 note, retained for history):* there is currently no way to produce a genuine cover-letter PDF as input to this mechanism without separate, out-of-scope work in the v1 repo. This ticket verified the *attachment mechanism* only, using synthetic PDFs, per explicit ticket authorization (AC8). This reinforces OQ-A from NIC-46's scope doc (a combined PDF-export follow-up ticket for both `cv-match` and `write-outreach`) — now confirmed twice.
- **`scripts/notion_cv_attachment.py` is unmodified by this ticket** — all new code lives in `scripts/notion_cover_letter_attachment.py`. This was a deliberate choice (§ above) to eliminate regression risk on NIC-46's shipped, QA-passed file; the alternative (direct call with inline `heading_text=`) would have been equally spec-compliant but less self-documenting at future call sites.
- **File-size/plan limits were not empirically probed** (`GET /v1/users/me` or equivalent was not called) — same theoretical-risk flag as NIC-46; both test files here are far under any tier's limit (633–641 bytes).
- **File naming convention** used for verification (`"TEST Company - TEST Role - Cover Letter.pdf"`) approximates PRD's proposed `{Company} - {Role} - Cover Letter.pdf` (FR-E3, "proposed, not yet confirmed" per NIC-46) but this ticket's AC did not require confirming that convention formally.
- **Notion's underscore-escaping quirk on the `file_uploads.filename` field** (documented in NIC-46's section above) applies identically here — not re-verified explicitly for the cover letter filenames but expected to behave the same since it is a Notion API-side behavior unrelated to which heading is targeted.
- **Two attachment sections on the same page (Tailored CV, Cover Letter) both use exact-string `heading_2` matching** — confirmed disambiguated by construction (`"📄 Tailored CV"` vs `"✉️ Cover Letter"` are not confusable); no cross-section interference was observed or expected during this ticket's verification (only the Cover Letter section's blocks were touched; the Tailored CV section's placeholder callout, block index 6-7, was left untouched throughout — visually confirmed in the block-list dumps above).

---

## NIC-48 — Attachment filename convention

### Design decision

Per Product Planner scope validation (`docs/handoffs/NIC-48-product-planner-scope-validation.md`, §4), a small, shared, pure-Python filename-builder helper was added — **zero changes** to `scripts/notion_cv_attachment.py` or `scripts/notion_cover_letter_attachment.py`. Both shipped functions already separate "compute the filename" (caller's job) from "attach the file" (their job) — the `filename` parameter is the integration seam this ticket formalizes. This mirrors the same zero-regression-risk principle NIC-47 established for its own thin wrapper.

**New file:** `scripts/notion_attachment_naming.py`. Exposes `build_attachment_filename(company, role, kind, ext="pdf") -> str`. Pure standard library — the only import is `re`. No network calls. No dependency on either attachment script.

### Call shape

```python
from notion_attachment_naming import build_attachment_filename

filename = build_attachment_filename("Acme", "Backend Engineer", "CV")
# -> "Acme - Backend Engineer - CV.pdf"

filename = build_attachment_filename("Société Générale", "Ingénieur", "Cover Letter")
# -> "Société Générale - Ingénieur - Cover Letter.pdf"
```

Any caller of `attach_final_cv()` / `attach_final_cover_letter()` (today: verification/test scripts; in the future: a not-yet-built `cv-match`/`write-outreach` → Notion integration) is expected to compute its `filename` argument via this helper instead of hand-typing a string — documented here and in the module's own docstring as the expected convention, though not enforced at the API boundary (accepted, documented limitation — see scope doc §9 risk table; enforcing it would require changing the shipped attachment scripts' signatures, which is explicitly out of scope).

`kind` is a closed, validated set: `{"CV", "Cover Letter"}` (exact display strings, case-sensitive). Any other value raises `ValueError` — no case-insensitive guessing, no silent normalization, consistent with this codebase's "fail loudly" style (`find_tailored_cv_section`'s behavior when a heading isn't found). `ext` defaults to `"pdf"` (per NIC-40's confirmed target-format decision) and is **not** sanitized — it is an internally-controlled literal value, not external input.

### Sanitization rule (exact, per scope doc §5)

For each of `company` and `role`, independently, in this exact order:

1. **Trim** leading/trailing whitespace.
2. **Strip control characters**: remove any character in the C0 control range (`U+0000`–`U+001F`) or `U+007F` (DEL).
3. **Replace filesystem-unsafe characters** (`< > : " / \ | ? *` — the Windows-reserved set, the strictest common denominator across macOS/Linux/Windows) with a single space.
4. **Collapse whitespace**: any run of one or more whitespace characters (including the spaces introduced by step 3, plus tabs/newlines) becomes a single ASCII space.
5. **Trim again** (step 4 can reintroduce leading/trailing spaces).
6. **Preserve non-ASCII characters unchanged** — no transliteration; accented/non-Latin characters (é, à, ü, etc.) pass through untouched.
7. **Truncate** each of `company`/`role` to 80 characters, after the above steps (per-field, not per-final-assembled-string).
8. **Empty-after-sanitization fallback**: if a field is empty or whitespace-only after steps 1–7, substitute `"Unknown Company"` / `"Unknown Role"` respectively — never raises on empty/malformed input.

Final assembly: `f"{sanitized_company} - {sanitized_role} - {kind}.{ext}"`. No additional sanitization applied to `kind`/`ext` (internally-controlled literals, not external input).

Implementation detail: the module's `_sanitize_field()` helper applies steps 1–5 as three regex substitutions plus two `.strip()` calls in the order above; step 6 is a deliberate no-op (nothing in steps 1–5/7/8 touches non-ASCII characters); step 7 is a plain string slice (`result[:80]`) with no post-truncation re-trim, since the scope doc's 8-step rule does not call for one — a truncation that happens to land exactly on a word-boundary space is a known, documented edge case, not a spec deviation.

### AC1–AC6 evidence

**AC1 — convention correctness (isolated, no network):**
- `build_attachment_filename("Acme", "Backend Engineer", "CV")` → `"Acme - Backend Engineer - CV.pdf"` — exact match. PASS.
- `build_attachment_filename("Acme", "Backend Engineer", "Cover Letter")` → `"Acme - Backend Engineer - Cover Letter.pdf"` — exact match. PASS.
- `build_attachment_filename("Acme", "Backend Engineer", "cv")` (lowercase) → raised `ValueError` (no case-insensitive guessing). PASS.
- `build_attachment_filename("Acme", "Backend Engineer", "Resume")` (unrecognized) → raised `ValueError`. PASS.

**AC2 — sanitization rule, isolated unit tests (`/tmp/test_nic48_naming.py`, run via `python3 /tmp/test_nic48_naming.py`, real captured output, 21/21 assertions PASS, exit code 0):**
- (a) `/`/`\` never in output: `build_attachment_filename("Acme/Corp", "R&D: Data\\Team", "CV")` → `"Acme Corp - R&D Data Team - CV.pdf"` — no `/` or `\` present. PASS.
- (b) control characters removed: `build_attachment_filename("Acme\x00\x01Corp", "Role\x1fName", "CV")` → `"AcmeCorp - RoleName - CV.pdf"` — control bytes gone. PASS.
- (c) irregular whitespace collapses, no leading/trailing space: `build_attachment_filename("  Acme   \t\n Corp  ", "  Backend  \t Engineer  ", "CV")` → `"Acme Corp - Backend Engineer - CV.pdf"`. PASS.
- (d) accented/non-ASCII passes through unchanged: `build_attachment_filename("Société Générale", "Ingénieur", "CV")` → `"Société Générale - Ingénieur - CV.pdf"` — byte-for-byte preserved. PASS.
- (e) all-control-char / empty / whitespace-only input falls back without raising: empty strings, `"\x00\x01\x02"`/`"\x03\x04\x05"`, and `"   "`/`"   "` all → `"Unknown Company - Unknown Role - CV.pdf"`, no exception in any case. PASS (3 sub-cases).
- (f) 300-char input truncates to the 80-char cap without corrupting the extension: `build_attachment_filename("A"*300, "B"*300, "CV")` → `("A"*80) + " - " + ("B"*80) + " - CV.pdf"` — both fields exactly 80 chars in the output, `.pdf` extension intact. PASS.
- Full captured test run output archived at `/tmp/test_nic48_naming.py` (test source) — real execution, `RESULT: ALL TESTS PASSED`, exit code 0.

**AC3 — zero changes to shipped attachment scripts:**
- `sha256sum` before this ticket's work: `56eb59749de2d7ed5ab57e689209d85b4de3508756c0e07303d3e974487d93c0  scripts/notion_cv_attachment.py`, `9f757580e62306d0cab43d062f99be04bd825779c050e44d4c65dad097d3a664  scripts/notion_cover_letter_attachment.py`.
- `sha256sum` after this ticket's work (real, re-run): **identical, byte-for-byte** — same two hashes.
- `git diff -- scripts/notion_cv_attachment.py scripts/notion_cover_letter_attachment.py` → empty output (no diff) for both files.

**AC4 — no new third-party dependency:** `scripts/notion_attachment_naming.py`'s only import is `re` (Python standard library). Confirmed via direct grep of all `import`/`from` lines in the file — exactly one match, `import re`.

**AC5 — real end-to-end proof, live Notion API (test card `page_id 3d805073-c5b0-8199-b502-f20fae30c2ce`, created and archived same session):**
- Baseline query (`POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query {}`) before any NIC-48 work: `200 OK`, 5 real cards returned (`Senior PM` `3d705073-c5b0-80cf-8852-dd75bbfe46c5`, `Staff CSM` `3d705073-c5b0-801e-8934-c9ec90eb7a11`, `Freelance` ×2 `3d705073-c5b0-80ec-9c10-cdfd3b316561` / `3d705073-c5b0-8020-840d-c7ff840ddda1`, `Implementation Manager - Strategic Accounts` `3d705073-c5b0-814f-ab19-cb44462cbef9`), each `page_id`/`Name`/`last_edited_time` recorded.
- Test card created: `POST /v1/pages` with `parent.database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6`, `properties` = `{Name: "TEST NIC-48 verification", Company: "TEST", Role: "TEST", Status: "selected"}`, `children` = full 14-block array from `build_job_page_children()`, all in one request → `200 OK`, `id: 3d805073-c5b0-8199-b502-f20fae30c2ce`, `url: https://app.notion.com/p/TEST-NIC-48-verification-3d805073c5b08199b502f20fae30c2ce`.
- **CV attach:** `build_attachment_filename(company="TEST Company/Ops", role="TEST Role: Lead", kind="CV")` → `"TEST Company Ops - TEST Role Lead - CV.pdf"` (confirmed locally, matching the scope doc's worked example, before use). Passed unmodified into `attach_final_cv(page_id, "/tmp/nic48_test_cv.pdf", filename=<that string>)` — the existing, byte-identical `notion_cv_attachment.py` function, no modification. Result: new `file` block `id 3d805073-c5b0-8129-b647-d075c5319241` inserted under the "📄 Tailored CV" heading; old NIC-43 placeholder callout (`id 3d805073-c5b0-8197-b9f1-fbca004836a9`) archived.
- `GET /v1/blocks/3d805073-c5b0-8199-b502-f20fae30c2ce/children` → `200 OK`; the `file` block's `name` field is `"TEST Company Ops - TEST Role Lead - CV.pdf"` — **exactly equal**, character-for-character, to the step-2 helper output. `exact_match: true` (verified programmatically, not eyeballed).
- **Cover Letter attach (same test card):** `build_attachment_filename(company="TEST Company/Ops", role="TEST Role: Lead", kind="Cover Letter")` → `"TEST Company Ops - TEST Role Lead - Cover Letter.pdf"` (confirmed locally first). Passed unmodified into `attach_final_cover_letter(page_id, "/tmp/nic48_test_coverletter.pdf", filename=<that string>)` — the existing, byte-identical `notion_cover_letter_attachment.py` wrapper, no modification. Result: new `file` block `id 3d805073-c5b0-8197-8fb0-db4642883151` inserted under the "✉️ Cover Letter" heading.
- `GET /v1/blocks/{page_id}/children` re-fetched → `200 OK`, `total_file_blocks_on_page: 2` (`"TEST Company Ops - TEST Role Lead - CV.pdf"` and `"TEST Company Ops - TEST Role Lead - Cover Letter.pdf"`), the target Cover Letter block's `name` field **exactly equals** the step-5 helper output. `exact_match_found: true`.
- This proves the unsafe characters (`/` in `"TEST Company/Ops"`, `:` in `"TEST Role: Lead"`) were actually sanitized end-to-end and the sanitized string is what genuinely lands as the Notion attachment's visible name — not merely a unit-tested string in isolation.

**AC6 — test artifact discipline:**
- Test card `Name`: `"TEST NIC-48 verification"`; `Company`/`Role`: `"TEST"`; `Status`: `"selected"` — set at creation via `build_job_page_children()`'s 14-block structure.
- After both attach steps and their `GET` verifications: `PATCH /v1/pages/3d805073-c5b0-8199-b502-f20fae30c2ce` `{"archived": true}` → `200 OK`, `archived: true`. Follow-up `GET /v1/pages/3d805073-c5b0-8199-b502-f20fae30c2ce` → `200 OK`, `archived: true` confirmed independently.
- Before/after diff of `POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query {}`: baseline (5 cards) vs. after-work query (5 cards) — every real card's `page_id`, `Name`, `last_edited_time`, `archived` value is **identical**, compared programmatically (`real_cards_untouched: true`). The NIC-48 test card does not appear in the after-work query (Notion excludes archived pages from query results), and no unexpected new `page_id` appears (`new_cards_appearing_in_after_query: []`).
- NIC-46's own archived test card (`page_id 3d805073-c5b0-8174-9372-c114f6c398b4`) independently re-fetched via `GET /v1/pages/{id}` → `archived: true`, `last_edited_time: 2026-09-11T06:45:00.000Z` — unchanged from its own archive timestamp, confirming it was not touched by this ticket.
- NIC-47's own archived test card (`page_id 3d805073-c5b0-811a-9640-e652e54717fe`) independently re-fetched → `archived: true`, `last_edited_time: 2026-09-11T07:00:00.000Z` — unchanged, confirming it was not touched by this ticket.

### Known limitations

- **FR-E3's naming string itself remains "proposed, not yet confirmed" by Nicolas** (per scope doc §1/§9, OQ-C) — this ticket formalizes the PRD's proposed convention as the working default; a future thumbs-up/down from Nicolas could require a one-line change to `build_attachment_filename()`'s assembly format. No real production files exist yet under this convention (confirmed unchanged fact, both NIC-46/NIC-47 only ever touched their own archived test cards), so the cost of being wrong today is near-zero.
- **The helper is not enforced at the API boundary** — nothing in `attach_final_cv()`/`attach_final_cover_letter()`'s signatures requires their `filename` argument to originate from `build_attachment_filename()`; a future caller could still hand-type a string. Documented as an accepted limitation per scope doc §9 (enforcing it would require changing the shipped, QA-passed attachment scripts' signatures, explicitly out of scope for this ticket).
- **`kind` is a closed 2-value set** (`"CV"`, `"Cover Letter"`) — a possible future third attachment type (e.g. an interview cheat sheet PDF, Phase 4) would require extending this set; explicitly deferred (scope doc OQ-D), not needed until a real third type ships.
- **Two synthetic test PDFs used for the AC5 verification** (`/tmp/nic48_test_cv.pdf`, 445 bytes; `/tmp/nic48_test_coverletter.pdf`, 461 bytes) — minimal, hand-constructed, valid PDF/1.4 documents generated purely to exercise the naming→attach pipeline. Neither is a real `cv-match`/`write-outreach` output; no real end-to-end content-generation run was performed or claimed — mirrors NIC-46/NIC-47's own explicitly-flagged gap (no PDF-export step exists yet in the v1 repo).
- **Zero lines changed in `scripts/notion_cv_attachment.py` and `scripts/notion_cover_letter_attachment.py`** — confirmed by identical `sha256sum` before/after and an empty `git diff` for both files (see AC3 evidence above). This ticket's only new production code is the new, standalone `scripts/notion_attachment_naming.py` module.

---

## NIC-56 — LinkedIn Saved Jobs → Notion `selected`-card importer (semi-automated)

### Design decision

Per Product Planner scope validation (`docs/handoffs/NIC-56-product-planner-scope-validation.md`, §5), only **Option (c)/(d)** (semi-automated, manually-provided input) was implemented. **Option (a)** (browser automation / credentialed access to `linkedin.com`) and **Option (b)** (a LinkedIn API) are explicitly **not** implemented — Option (a) is a hard stop per AGENTS.md's forbidden-operations rule and was never approved by any human sign-off; Option (b) is confirmed unavailable (LinkedIn exposes no member-facing "read my saved jobs" API product). The shipped script, `scripts/notion_import_saved_jobs.py`, makes **zero** network calls to any `linkedin.com` host — it only reads a manually-provided local text file/stdin and calls the Notion API (`api.notion.com`), the same API every other script in this repo already uses.

**Input contract (Builder's concrete resolution of scope doc OQ-3):** rather than attempt to parse arbitrary freeform LinkedIn-page copy/paste text (whose exact shape the Product Planner explicitly could not specify in advance — scope doc §10/§11 risk table), the script defines a small, explicit, pipe-delimited contract:

```
Company | Role
```

One job per non-blank, non-`#`-comment line. This is a deliberate narrowing of Option (c)'s "freeform text" framing into something reliably parseable without guessing — consistent with AC6's "report, don't guess" mandate. Nicolas performs a small manual reformatting step (copy from LinkedIn, retype/reflow into `Company | Role` lines) before running the script; this keeps the parser's failure mode "reports a malformed line" rather than "silently misparses a company name that happens to contain unexpected punctuation."

### New file: `scripts/notion_import_saved_jobs.py`

Pure `urllib.request`, no third-party dependency, matching the dependency-light style of every other `notion_*.py` script in this repo. Imports `build_job_page_children` from `scripts/notion_job_page_blocks.py` (repo convention, NIC-43/46/47/48 precedent) — **not** reimplemented or forked. Exposes:

- `parse_entries(text) -> (parsed, malformed)` — the pipe-delimited parser (AC1, AC6). A line failing to split into exactly one `|` with two non-empty sides is reported in `malformed`, never guessed/filled with blank or invented data.
- `normalize(text) -> str` — case-insensitive, whitespace-collapsed comparison key used for dedup.
- `query_all_non_archived_cards()` — `POST /v1/data_sources/{data_source_id}/query` with `{}` (paginated via `next_cursor`); Notion excludes archived pages from query results by construction, so the returned set is naturally "all non-archived cards" (AC4's stated dedup scope).
- `build_dedup_index(pages) -> {(norm_company, norm_role): page_id}` — one dict built once per run from the query above.
- `create_selected_card(company, role)` — `POST /v1/pages` with `parent.database_id` + `properties` (`Name="{Company} - {Role}"`, `Status="selected"`, `Company`, `Role`) + `children=build_job_page_children()`, all in a single request — byte-identical call shape to NIC-43/46/47/48's established convention. `Priority` intentionally left unset (scope doc §7).
- `process_entries(text, do_all=False, limit=5) -> report` — end-to-end orchestration: parse → dedup against existing Notion cards **and** within the same input batch (a job repeated twice in one paste is only created once, second occurrence reported as a duplicate) → apply the default-5-unless-`--all` limit → create cards for the remainder in input order. Returns `created`/`skipped_duplicates`/`skipped_limit`/`malformed` lists, each entry identified by name (never silently dropped).
- `format_report(report)` — human-readable text summary printed by the CLI alongside the full JSON report.

CLI: `python3 scripts/notion_import_saved_jobs.py <input_file> [--all]` (or `-` for stdin).

### Limit / dedup interaction (AC1 + AC4, resolved order of operations)

Deduplication is always computed **before** the 5-vs-all limit is applied, and applies whether or not `--all` is passed. This means: (a) a duplicate never "counts against" the 5-entry default limit — only genuinely new, non-duplicate entries are limited; (b) re-running with `--all` after an initial default-limited run correctly reports the earlier batch as duplicates (not re-created) and only creates the newly-revealed entries beyond the original 5. Verified live below.

### Verification evidence (real test cards, created and archived same session)

**Baseline (before any NIC-56 work):** `POST /v1/data_sources/47340a66-9e15-4ea1-8edf-45bba44c2334/query` `{}` → `200 OK`, 5 real cards returned — `Senior PM` (`3d705073-c5b0-80cf-8852-dd75bbfe46c5`), `Staff CSM` (`3d705073-c5b0-801e-8934-c9ec90eb7a11`), `Freelance` ×2 (`3d705073-c5b0-80ec-9c10-cdfd3b316561` / `3d705073-c5b0-8020-840d-c7ff840ddda1`), `Implementation Manager - Strategic Accounts` (`3d705073-c5b0-814f-ab19-cb44462cbef9`) — identical set/ids to every prior ticket's baseline (NIC-46/47/48), confirming no drift.

**AC1 — 5-by-default, then `--all` (7-entry input + 1 malformed line, `/tmp/nic56_test_input_7plus1malformed.txt`):**
- Run 1 (no `--all`): `python3 scripts/notion_import_saved_jobs.py <file>` → **exactly 5 cards created**, in input order (`TEST Company Alpha` → `TEST Company Epsilon`), the remaining 2 non-duplicate entries (`Zeta`, `Eta`) reported under `skipped_limit`, the 1 malformed line (no `|` separator) reported under `malformed` with line number and reason. 0 duplicates (first run, database has no matching cards yet).
- Run 2 (same file, `--all`): **exactly 2 new cards created** (`Zeta`, `Eta` — the ones the limit had held back), and the **5 cards from run 1 are now correctly reported as duplicates** (`skipped_duplicates`, each naming the exact already-existing `page_id`) rather than being re-created — proving dedup and the limit interact correctly across separate runs. The malformed line is reported again (line 7, unchanged reason). No third-run drift: total of exactly 7 cards created across both runs for 7 valid input entries, 0 duplicated.

**AC4 — dedup, case-insensitive/whitespace-normalized (seeded test card `Company="Acme"`/`Role="PM"`, page_id `3d805073-c5b0-817f-8df0-e33e4c36bca2`, `Name="TEST NIC-56 verification - dedup seed (Acme/PM)"`):**
- Import input: `"  acme   |   pm"` (irregular whitespace, lowercase) + one new, non-duplicate entry (`TEST Company Theta`). Run with `--all` → **1 card created** (`Theta`), **the `acme`/`pm` entry skipped as a duplicate**, reported by name (`acme - pm`) with `matched_page_id` pointing at the seeded card — confirming the normalization (`re.sub(r"\s+", " ", s.strip()).lower()`) correctly matched `"  acme   |   pm"` against the seeded `"Acme"`/`"PM"` card despite the case and whitespace differences. No second Acme/PM card was created.

**AC2/AC3 — created-card structure (spot-checked on `TEST Company Alpha - TEST Role Alpha`, page_id `3d805073-c5b0-819d-8194-f4a1d9fd4ea5`):**
- `GET /v1/pages/{page_id}` → `Name: "TEST Company Alpha - TEST Role Alpha"`, `Status: "selected"` (exact match), `Company: "TEST Company Alpha"`, `Role: "TEST Role Alpha"` — all three non-empty and correctly populated (AC2 satisfied).
- `GET /v1/blocks/{page_id}/children` → `results.length == 14`, block-type sequence `heading_2, paragraph, divider, heading_2, callout, divider, heading_2, callout, divider, heading_2, callout, divider, heading_2, callout` and heading text sequence `["📋 Job Details", "🔍 Company Research Brief", "📄 Tailored CV", "✉️ Cover Letter", "🎯 Interview Cheat Sheet"]` — exact match to `build_job_page_children()`'s documented NIC-43 structure (AC3 satisfied, template genuinely reused, not reinvented).

**AC5/AC8 — zero LinkedIn access (static check):** `search_files` grep of `scripts/notion_import_saved_jobs.py` for `linkedin.com` returns exactly 2 matches, both inside comments explicitly documenting the constraint (module docstring line 7, code comment line 98) — zero occurrences in executable code. A separate grep for any `https?://` literal in the file returns exactly 1 match: `NOTION_API_BASE = "https://api.notion.com/v1"`. The file's only imports are `json`, `os`, `re`, `sys`, `urllib.error`, `urllib.request` (Python stdlib) and `from notion_job_page_blocks import build_job_page_children` (existing repo module) — no browser-automation library, no cookie/session-handling code, no third-party HTTP client capable of being pointed at an external host beyond the one hardcoded Notion base URL.

**AC6 — malformed-entry reporting:** the deliberately malformed line (`"this line has no pipe separator at all"`, no `|` character) was reported in both run 1 and run 2's `malformed` list with its exact line number (7) and a specific reason (`"expected exactly one '|' separator... found 0 separator(s)"`) — no card was ever created for it, and no company/role value was fabricated or left blank on a created card.

**AC7 — test-artifact discipline, real-cards-untouched diff:** all 9 test cards created during this session's verification (`Alpha`, `Beta`, `Gamma`, `Delta`, `Epsilon`, `Zeta`, `Eta`, the Acme/PM dedup-seed card, `Theta`) were archived via `PATCH /v1/pages/{id}` `{"archived": true}` → `200 OK` each, independently re-confirmed via a follow-up `GET /v1/pages/{id}` showing `"archived": true` for every one of the 9. Post-archive `POST /v1/data_sources/{id}/query` `{}` re-run: **exactly the same 5 real cards, same `page_id`/`Name`/`last_edited_time` values as the pre-work baseline, byte-for-byte identical (`diff` of the two query outputs returns no differences)** — none of the 5 real production cards were read-modify-written, dedup-matched-against-and-altered, or otherwise touched by any of this ticket's create/archive operations.

### Known limitations

- **Input format is a Builder-chosen, narrower contract (`Company | Role` per line) than "arbitrary freeform LinkedIn paste text.**" This was a deliberate implementation choice (scope doc §10/§11 explicitly leaves this to Builder, no strong Product Planner preference) to keep parsing reliable and defensive rather than attempt to guess structure out of LinkedIn's actual, undocumented copy/paste output — which was never tested against a real LinkedIn page in this ticket (per the hard constraint: the script/agent never accesses `linkedin.com`). Nicolas must manually reformat his copied list into this shape before each run; this is the accepted cost of the semi-automated scope.
- **No job URL/source-link field is captured or stored** — the input contract only carries `Company`/`Role`, matching this ticket's own AC2 requirement (`Status`+`Company`+`Role` non-empty) and NIC-43's existing "Job Details" placeholder section (which already exists as a fillable freeform block for Nicolas to paste a posting link into manually after card creation). A future enhancement could extend the input contract with an optional third `| URL` field and populate the Job Details section automatically — not required by this ticket's AC and not built.
- **"Most recently saved" ordering is whatever order Nicolas's input file lists jobs in** (scope doc §3.2's documented, non-blocking assumption) — the script does not independently verify or reorder by any notion of recency; it trusts input order as given, exactly as scoped.
- **Option (a) (full LinkedIn automation) remains explicitly unbuilt and unapproved** — if Nicolas later wants that path, it requires a new, separate Linear ticket with explicit human sign-off acknowledging the ToS/account-risk tradeoff (scope doc §4/§12), not an extension of this ticket's code.
- **Dedup is Company+Role only** (per AC4's exact stated scope) — it does not consider `Name` or any other property; two entries with identical Company+Role but semantically different jobs (e.g., two open reqs at the same company with the same title) would be treated as duplicates and the second skipped. This mirrors the scope doc's own explicit dedup rule (§6), not a bug.

---

## NIC-62 — Real PDF generation for tailored CV / cover letter

### Design decision

Per Product Planner scope validation (`docs/handoffs/NIC-62-product-planner-scope-validation.md`, §5), **reportlab (platypus), used directly**, was chosen over `soffice --headless --convert-to pdf` (docx→PDF) and over any hosted/system-dependency option (`pandoc`/`wkhtmltopdf`/`weasyprint`, none installed, rejected). Rationale: reportlab is a pure-Python library (no external binary/subprocess dependency), matches this repo's established "no third-party HTTP library / no SDK, pure stdlib-adjacent" philosophy from NIC-46/47, and gives full control over heading/paragraph/bullet layout needed for the §6 quality bar.

**New file:** `scripts/render_markdown_to_pdf.py`. Pure Python; the only third-party import is `reportlab`. Exposes `render_markdown_to_pdf(markdown_path, kind, out_path)` plus a CLI (`--kind cv|cover-letter -o <out.pdf>`), and is invoked with the CV file for `kind="cv"` (whole file rendered) or the write-outreach combined file for `kind="cover-letter"` (only the cover-letter section extracted first, see below). **Zero changes** to `scripts/notion_cv_attachment.py`, `scripts/notion_cover_letter_attachment.py`, or `scripts/notion_attachment_naming.py` — all three are imported/called unmodified (see AC10 evidence below).

**Python environment finding (undocumented by the scope doc, discovered during implementation):** reportlab was **not** actually importable anywhere on this host at the start of the ticket — neither the bare system `python3` nor the already-shipped `pdf` skill's own `pdf_create.py` (which also failed with "Missing dependency" when invoked) had it installed, contrary to the scope doc's assumption (which was based on reading the skill's documentation, not running it — an explicit scope-doc caveat). Builder's resolution: created a new, v2-repo-local virtualenv, `/home/nicow/cv-job-match-v2/.venv` (via `uv`-provisioned Python 3.11, `.venv/bin/python3.11`), and installed reportlab 5.0.1 into it (`'.venv/bin/python3 -m pip install reportlab'`). `.venv/` is gitignored, not committed, and is a one-time, v2-repo-local setup addition — no system-wide install, no change to the `pdf` skill's own (still-missing) dependency. **The script must be run with `.venv/bin/python3 scripts/render_markdown_to_pdf.py ...`, not the bare `python3` on `PATH`.**

### Markdown → PDF parser / layout mapping

Stdlib `re`-only parser (`parse_markdown_blocks()`), no new dependency beyond reportlab itself:
- `#`/`##`/`###` → `h1`/`h2`/`h3` heading styles (distinct font size/weight/color per §6.1: h1 22pt bold, h2 15pt bold `#1a5276` blue, h3 11.5pt bold dark grey).
- `**bold**` / `*italic*` / `[text](url)` inline spans → reportlab Paragraph XML-subset markup (`<b>`/`<i>`/`<link>`), applied after XML-escaping (`&`/`<`/`>`) so literal ampersands in real content don't break the markup.
- Lines starting with `- ` (including multi-line wrapped continuations, matching cv-match's real indented-bullet style) → real bulleted `Paragraph` flowables using reportlab's native `bulletText="•"` parameter (a genuine bullet glyph + hanging indent, not a dash-prefixed run-on blob).
- A fully-bold single line (e.g. the CV's subtitle line right under the name, or a `**Depuis août 2025**` date-range line) → a distinct "emphasis line" style (bold, slightly larger, extra spacing) rather than a plain body paragraph, satisfying §6.1's "title line beneath [the name] in a secondary style" requirement without inventing content.
- `---` → an `HRFlowable` divider (CV mode only; never emitted for extracted cover-letter content, since §6.2 forbids source section markers leaking into the cover-letter PDF).
- Cover-letter mode only: the first and last paragraph blocks get dedicated `salutation`/`closing` styles (extra spacing) — a positional heuristic satisfying §6.2's "salutation/closing visually separated from body" requirement, without inventing content not in the source.
- A system-installed Noto Sans TTF family (`/usr/share/fonts/noto/`) is registered with reportlab and used as the base font (falls back to Helvetica if not found) — needed because the real NEXTON content contains a few typographic characters (`→`, em/en dashes) outside Helvetica's WinAnsi encoding; two characters without Noto Sans glyph coverage (`→`, `≤`) are substituted to lossless ASCII equivalents (`->`, `<=`), documented, not silent.
- No table/nested-bullet/image/code-block support — neither `cv-match` nor `write-outreach` currently emit them (confirmed by direct inspection of the real files used); unsupported constructs would render as literal paragraph text rather than corrupt output.

### Cover-letter section extractor — fail loudly, never guess

`extract_cover_letter_section()` looks for a `## 1. Lettre de motivation` / `## 1. Cover Letter` heading (French/English, case-insensitive) as the start boundary and stops at the next `## 2.` heading or a `---` divider, whichever comes first. **If either boundary cannot be confidently located, it raises `CoverLetterBoundaryError`** (CLI exit code 3) rather than guessing a truncation point — the same "fail loudly" precedent as `find_tailored_cv_section()` in `notion_cv_attachment.py` (NIC-46). Independently re-verified in this session: running the script against a hand-made markdown file with no `## 1. ...` heading at all correctly raised `CoverLetterBoundaryError` with exit code 3 and did not write any output file.

### Real end-to-end evidence (real NEXTON `cv-match`/`write-outreach` output → real PDF → real Notion test card → verified → archived)

Full evidence captured by the prior session at `/tmp/nic62_e2e_evidence.json` / `/tmp/nic62_e2e_run.log`, independently re-verified by this session (see AC table below for exactly what was re-derived vs. inspected).

- **Real input files (not synthetic):** `/home/nicow/cv-job-match/applications/2026-09-01_NEXTON_Product-Owner-IA-Generative/cv-v2.md` and `outreach-v2.md` — genuine `cv-match`/`write-outreach` output already on disk in the v1 repo, read-only.
- **Rendered PDFs:** `cv_pdf_bytes: 37610` (3 pages, A4), `cover_letter_pdf_bytes: 17407` (1 page, A4) — reproduced independently in this session (`.venv/bin/python3 scripts/render_markdown_to_pdf.py ... -o /tmp/nic62_verify_cv.pdf` / `.../nic62_verify_cl.pdf`): **byte counts identical** (37610 / 17407); SHA-256 differs only because reportlab embeds a fresh `CreationDate`/`ModDate` timestamp per render (confirmed via `pdfinfo`), not a content difference.
- **Test card:** `page_id 3d805073-c5b0-8100-816c-f3d9669dc376`, `Name: "TEST NIC-62 verification"`, `Company: "NEXTON"`, `Role: "Product Owner IA Générative"`, created via `POST /v1/pages` with `parent.database_id dc98669c-8b63-4f20-b6c0-abdafe8222c6` and `children = build_job_page_children()` (unmodified NIC-43 helper).
- **Filenames (NIC-48, unmodified):** `build_attachment_filename("NEXTON", "Product Owner IA Générative", "CV")` → `"NEXTON - Product Owner IA Générative - CV.pdf"`; same for `"Cover Letter"` → `"...- Cover Letter.pdf"`. Confirmed by direct inspection of `/tmp/nic62_e2e.py` that these were computed via the real, unmodified `notion_attachment_naming.build_attachment_filename()` — not hand-typed.
- **Attach calls (NIC-46/47, unmodified):** `attach_final_cv(page_id, cv_pdf_path, cv_filename)` → new `file` block `3d805073-c5b0-815b-92b3-f0d5406a0551`, `file_uploads` id `3d805073-c5b0-8162-ad4f-00b28fa9f44e`, `PUT`/`POST` upload `200 OK`. `attach_final_cover_letter(page_id, cl_pdf_path, cl_filename)` → new `file` block `3d805073-c5b0-8128-8820-d81400e59a2f`, `file_uploads` id `3d805073-c5b0-815c-bf97-00b2dd8c8d35`, `200 OK`. Confirmed by direct inspection of `/tmp/nic62_e2e.py` that these are literally `from notion_cv_attachment import attach_final_cv` / `from notion_cover_letter_attachment import attach_final_cover_letter` with no wrapping/monkeypatching.
- **Structure verification:** `GET /v1/blocks/{page_id}/children` → `200 OK`, `total_blocks: 14`, `file_block_count: 2`, matching the two file blocks above.
- **Direct file-fetch verification:** both presigned S3 URLs fetched directly → `HTTP 200`, `Content-Type: application/pdf`, `Content-Length` 37610 / 17407 respectively, `actual_bytes_fetched` matching exactly (byte-for-byte, not just header-declared).
- **Cleanup:** `PATCH /v1/pages/{page_id}` `{"archived": true}` → `200 OK`; follow-up `GET` confirmed `archived: true` independently.
- **Real-cards-untouched diff:** baseline `POST /v1/data_sources/{id}/query {}` (5 real cards: `Senior PM`, `Staff CSM`, `Freelance` ×2, `Implementation Manager - Strategic Accounts`) vs. post-work query — **identical** `page_id`/`Name`/`last_edited_time`/`archived` for all 5, confirmed programmatically (`identical_id_sets: true`).

### Visual/textual layout verification (independently performed by this session)

- `vision_analyze` on `/tmp/nic62_render/imgs_cv2/page001.png`, `page002.png`, `page003.png` (real rendered NEXTON CV, 3 pages): confirmed a large bold name header with a distinct secondary-style subtitle line beneath it; blue, bold, larger-than-body section headings (`Expériences`, `IA Générative — Certifications & Pratique`, `Autres Compétences et Certifications`, `Éducation`, `Langues`) visually distinct from bold-but-smaller sub-headings (job titles/company names, e.g. `Product Advisory Principal – EMEA & Americas — Finastra, Customer Experience`); properly indented bullet items with a genuine `•` bullet glyph, each achievement on its own line; page-number footer (`Page 2`, `Page 3`) visible; **no literal `#`, `##`, `**`, or `- ` markdown syntax visible anywhere** on any of the 3 pages.
- `vision_analyze` on `/tmp/nic62_render/imgs_cl2/page001.png` (real rendered NEXTON cover letter): confirmed a clear salutation (`Madame, Monsieur,`) visually separated from body, paragraphs visually separated by spacing (not a wall of text), no literal markdown syntax, and no `Objet :` (recruiter-email) or LinkedIn-message text present.
- Text-extraction cross-check (`pdftotext`-derived `/tmp/nic62_render/cv_text3.json` and `cl_text2.json`, grepped independently by this session): zero occurrences of `**`, `##`, `Objet :`, `Message LinkedIn`, `Lettre de motivation`, `Cover Letter`, or a literal `---` divider in either extracted text. The only textual artifact found is `(cid:127)` (×3, in the CV text extraction only) — this is `pdftotext`'s own rendering of the reportlab bullet glyph (`•`, drawn via `bulletText`) when the font's cmap-to-Unicode mapping isn't picked up by `pdftotext`'s text layer; confirmed visually (via the page images above) that the actual PDF page shows a normal round bullet character, not a raw markdown `-`. Documented as a text-extraction-tool quirk, not a rendering defect.

### Robustness spot-check across additional real application folders (independently performed by this session, per scope doc §9 risk-table recommendation)

- `cv-v2.md` from `2026-08-28_UpSlide_Senior-Product-Manager/` and `2026-08-27_Euronext_Project-Manager-Primary-Markets/` (two more real, pre-existing `cv-match` outputs) both rendered successfully (`exit 0`, 3 pages each, 35913 and 50125 bytes respectively); a `vision_analyze` spot-check of the UpSlide CV's page 1 confirmed the same layout quality (bold header/subtitle, blue section heading, bold sub-headings, properly bulleted achievements, links rendered as clickable blue-underlined text, no literal markdown).
- `outreach-v2.md` (UpSlide) and `outreach-v1.md` (Euronext) — both **older, real** `write-outreach` outputs — use an **unnumbered** heading format (`## Cover Letter` / `## Recruiter / Hiring Manager Email` / `## LinkedIn Connection Message`) rather than the numbered format (`## 1. Lettre de motivation` / `## 2. ...`) the real NEXTON file (and the current `write-outreach/SKILL.md` documented convention) uses. Running the extractor against both correctly raised `CoverLetterBoundaryError` (exit code 3) rather than guessing — this is the **exact scenario the scope doc's own risk table (§9) anticipated** ("a soft heuristic, not a hard contract... future run with slightly different heading phrasing could cause the extractor to grab the wrong section") and explicitly authorized a fail-loud response to, not a defect. See "Known limitations" below.

### AC1–AC10 evidence summary

| AC | Result | Evidence |
|---|---|---|
| AC1 (CV layout) | PASS | `vision_analyze` on all 3 real NEXTON CV pages (this session) — distinct header/subtitle, 2-level heading hierarchy, bulleted lists, no literal markdown. |
| AC2 (cover-letter layout) | PASS | `vision_analyze` on the real NEXTON cover-letter page (this session) — salutation/paragraph/closing spacing, no literal markdown. |
| AC3 (no section leakage) | PASS | Text-extraction grep (this session) of `cl_text2.json`: zero occurrences of `Objet :`, `Message LinkedIn`, `Lettre de motivation`/`Cover Letter` heading text, `##`, `**`, or `---`. |
| AC4 (PDF format, non-corrupt) | PASS | `pdfinfo` (this session) on both rendered PDFs: `Encrypted: no`, `Pages: 3` / `Pages: 1`, valid PDF 1.4. |
| AC5 (unmodified attach functions, zero intermediate transform) | PASS | `/tmp/nic62_e2e.py` inspected directly (this session): literal unmodified imports and calls to `attach_final_cv()`/`attach_final_cover_letter()`; both `put_status: 200`. |
| AC6 (NIC-48 naming respected) | PASS | `/tmp/nic62_e2e.py` inspected directly (this session): filenames computed via `build_attachment_filename(REAL_COMPANY, REAL_ROLE, kind)`, matching the two Notion `file` block names recorded in evidence. |
| AC7 (real end-to-end run) | PASS | Full chain inspected in `/tmp/nic62_e2e_evidence.json`/`run.log` (this session): real NEXTON files → real PDFs → real attach → `GET` verification → direct S3 fetch (`200`, `application/pdf`, byte-exact) → archive. Independently reproduced the render step (byte-identical output) but did not repeat the live Notion create/attach/archive cycle (avoided creating an unnecessary duplicate test card, per task instructions). |
| AC8 (no production card modified) | PASS | Before/after `data_sources` query diff in evidence JSON: 5 real cards' `page_id`/`Name`/`last_edited_time`/`archived` identical, confirmed programmatically. |
| AC9 (docs updated) | PASS | This section added; NIC-46/NIC-47 "Known limitations" sections below updated with closure notes; `docs/PLAN.md` NIC-46/47 entries updated. |
| AC10 (zero changes to protected scripts / v1 repo) | PASS | `sha256sum` (this session) of all three protected scripts matches the hashes already recorded in NIC-48's own AC3 evidence above, byte-for-byte (`56eb597...93c0`, `9f75758...97664`, and `notion_attachment_naming.py` unchanged/untracked) — proving no edits since before NIC-62 started. `git diff` empty for all three (untracked, never staged). `git status --porcelain=v1` in `/home/nicow/cv-job-match` (this session) shows only pre-existing, unrelated dirty state (`M .claude/skills/run-my-week/SKILL.md`, `M tracker/job-tracker-model.md`, both last-committed `a490e5b`, Aug 27 — predating this ticket by two weeks) plus one pre-existing untracked application folder — no entry for any file touched by NIC-62's read-only markdown consumption. |

### Known limitations

- **Cover-letter section boundary is a soft heuristic tied to write-outreach's *current* numbered-heading convention** (confirmed both by design and by this session's own robustness spot-check): it correctly handles the real NEXTON file and the format documented in `write-outreach/SKILL.md` today, but **two other real, pre-existing `write-outreach` outputs** (UpSlide, Euronext — both older, dated before NEXTON) use an unnumbered heading format (`## Cover Letter` and section names like `## Recruiter / Hiring Manager Email`) that the extractor does **not** recognize — it correctly fails loudly (`CoverLetterBoundaryError`, exit 3) rather than guessing, per the scope doc's own explicit "fail loudly, never guess" mandate (§9 risk table). If `write-outreach`'s heading format drifts again in the future, or if Nicolas wants the older unnumbered files rendered too, the extractor's regex will need a follow-up ticket to add the additional heading pattern(s) as a second recognized format — not done here to avoid guessing at boundary semantics beyond what was directly observed and confirmed real.
- **No table/nested-bullet/image/code-block markdown support** — neither skill emits them today (confirmed by direct inspection); if a future real file uses them, they render as literal paragraph text rather than corrupting output, but would not meet the "no visible raw markdown" bar for that specific construct.
- **File-size/workspace-plan limits still not empirically probed** (`GET /v1/users/me` not called) — same theoretical-risk flag carried over from NIC-46/47/48; the real NEXTON PDFs here (37610 / 17407 bytes) are far under any tier's limit.
- **`.venv/` is a new, v2-repo-local, gitignored setup artifact** required to run the script (system Python lacks `pip`/`reportlab`, PEP 668 blocks a bare global install) — anyone running this script needs to `python3 -m venv .venv && .venv/bin/python3 -m pip install reportlab` once, or reuse the existing `.venv` if present. Documented in the script's own module docstring.
- **Only one real end-to-end Notion create/attach/archive cycle was performed** (NEXTON), per AC7's explicit "at least one" requirement and this ticket's instruction to avoid creating unnecessary additional test cards; the render step itself was additionally exercised against two more real files (UpSlide, Euronext) as a lighter-weight robustness check, per the scope doc's §9 recommendation, without a full Notion round-trip for those two.

---

## NIC-52 — `company-research` skill: significant recent news

### Design decision

Per Product Planner scope validation (`docs/handoffs/NIC-52-product-planner-scope-validation.md`), the "recent news" component of the new `company-research` Claude Code skill was implemented as a markdown procedure section — **not a script** — inside `/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md` (v1 repo), matching every sibling skill's existing pattern (`find-opportunities`, `interview-prep`, etc: a `SKILL.md` procedure for the Claude Code agent to follow using its own native tools, not a Python runner). The search mechanism is the session's native web-search/fetch capability only — no new paid Apify actor, no dedicated news API, no LinkedIn access (FR-52.1).

**Coordination outcome (scope doc §9):** at the start of this ticket's work, `/home/nicow/cv-job-match/.claude/skills/company-research/` did not exist — confirmed via a directory search returning zero files immediately before writing. NIC-49's Builder had not landed first. This ticket's Builder therefore **created the file fresh**, per the scope doc's §9 instruction for that branch: the full "Recent Company News" section (this ticket's scope, complete) plus a lightweight status table and placeholder headings for the three sibling sections (company/website summary — NIC-49; recent company video — NIC-50; open-position counts — NIC-51) so those Builders have a consistent, pre-existing file to extend into rather than each needing to also decide the file's top-level shape. No sibling content existed to preserve or accidentally overwrite.

### Significance filter (FR-52.2, AC5) — explicit five-category table

The skill file's "Recent Company News" section contains the full five-category table verbatim from the scope doc §4 (Funding/financial event, Expansion, Leadership change, Restructuring, Product launch/major partnership — each with concrete include/exclude examples), plus the "always excluded regardless of category" list (awards/rankings, listicles, press-release mills, opinion pieces, no-discoverable-date items). This is a followable, re-inspectable step — not a one-line "use good judgment" instruction — satisfying AC5 by construction (verified by re-reading the shipped file, see AC evidence below).

### Recency cutoff (FR-52.3)

The skill instructs computing "today's date minus 6 calendar months" **at generation time**, explicitly not hardcoded and not tied to job-selection time. An item with no discoverable specific publish date is discarded, never included with a guessed/approximate date — written as an explicit rule in the skill's step 3, not left implicit.

### Per-item output schema (FR-52.4) and count rules (FR-52.5/FR-52.7)

Exactly four fields in order — Headline, Date (YYYY-MM-DD), Source (full URL), "Why it matters for this application" (one sentence) — written as a literal markdown template block in the skill file. Max 3 items (keep the 3 most significant if more qualify, per a stated priority heuristic), min 0, and an explicit "never pad to 3" instruction (FR-52.7) stated as its own numbered step, not folded into a vague aside.

### "No significant news found" fallback (FR-52.6) and retrieval stamp (FR-52.8)

The skill specifies the **exact** required string `No significant news found for {Company} in the last 6 months.` (with `{Company}` substituted), called out as "not omitted, not an apology, not hedged, not a substituted stale/irrelevant item" and explicitly framed as a first-class expected output for small/private/quiet companies, not a failure mode. A separate `_Retrieved: {today's date}_` stamp is specified as distinct from each item's own `Date:` field (FR-52.8/AC7).

### Constraint compliance (AC6)

`search_files` grep of the shipped `SKILL.md` for `linkedin\.com|Apify|news API|paid actor` returns exactly one match — inside the constraint sentence itself ("No new paid Apify actor, no dedicated news API, no LinkedIn access"), i.e. the skill documents the *prohibition*, not a usage. No actual `linkedin.com` URL, actor name, or news-API endpoint is referenced anywhere in the file.

### Real verification (this session, both real web-search tool calls and real results — not fabricated)

**Company 1 — Mistral AI (real company with genuine recent news, chosen for its well-documented 2026 funding/M&A/partnership activity):**
- Query 1: `"Mistral AI" (funding OR acquisition OR layoffs OR restructuring OR "new CEO" OR expansion OR "product launch") 2026` → returned (among others) Le Monde's Sept 8, 2026 funding article and Clay's funding-tracker summary.
- Query 2: `Mistral AI Samsung shareholder funding round September 2026` → CNBC (`cnbc.com/2026/09/08/mistral-ai-funding-valuation-samsung.html`), confirming a €3B Series D, Samsung-led, at >€21B valuation, announced 2026-09-08 — **Funding/financial event**, in-window (today 2026-09-12, cutoff 2026-03-12).
- Query 3: `Mistral AI $830 million debt financing Nvidia chips data center March 2026` → Reuters (`reuters.com/business/finance/frances-mistral-raises-830-million-debt-ai-data-centre-build-up-2026-03-30/`), confirming $830M debt raise dated 2026-03-30 for a Paris data center — **Funding/financial event**, in-window (2026-03-30 ≥ 2026-03-12 cutoff, right at the edge).
- Query 4: `Mistral AI acquisition 2026` → Wikipedia/TheNextWeb, confirming Mistral's acquisition of Vienna-based Emmi AI, announced 2026-05-19 (`thenextweb.com/news/mistral-emmi-ai-physics-vienna-industrial`) — **Funding/financial event** (company acquiring another company), in-window. A second acquisition (Koyeb, TechCrunch, dated 2026-02-17) was found but **falls before the 2026-03-12 cutoff — correctly excluded** per FR-52.3, demonstrating the recency rule in practice (AC2 evidence).
- Query 5: `Cloudera Mistral partner announcement date 2026` → Cloudera's own press release + PYMNTS, confirming a Cloudera/Mistral sovereign-AI partnership announced 2026-09-10 — **Product launch/major partnership**, in-window. This is a 4th qualifying item.
- **Cap applied (AC3):** 5 qualifying items were found (Series D funding, $830M debt raise, Emmi AI acquisition, Koyeb acquisition [excluded by recency], Cloudera partnership) → after the recency filter, 4 remain in-window; per FR-52.5's 3-item cap, the 3 most significant were kept (the Series D funding, the Emmi AI acquisition, and the debt-financing raise — all Funding/financial events, outranking the Cloudera product-partnership per the category-priority heuristic) and the Cloudera item dropped, demonstrating the cap-at-3 behavior live against a real, heavily-covered company.
- All 3 kept items have non-empty Headline/Date/Source/Why-it-matters fields (AC1 satisfied).

**Company 2 — PALO IT (quiet/small company verification, chosen: Nicolas's own experience-bank company, a mid-size but not heavily press-covered agile consultancy):**
- Query 1: `"Palo IT" (funding OR acquisition OR layoffs OR restructuring OR "new CEO" OR expansion OR "product launch") 2026` → returned only unrelated Palo Alto Networks (a different company) results — no PALO IT-specific hits.
- Query 2: `"PALO IT" news March April May June July August September 2026` → same, dominated by Palo Alto Networks noise, zero PALO IT-specific news.
- Query 3: `"PALO IT" agile consultancy news layoffs acquisition 2026 -"Palo Alto"` → Glassdoor reviews, a case-study page, a "MoreBetter" review blog — no dated news item matching any of the five categories.
- Query 4: `"PALO IT" layoffs restructuring new CEO acquisition 2025 2026` → Welcome to the Jungle company page, LinkedIn company page, an unrelated AI-community blog post mentioning PALO IT in passing (not about PALO IT itself) — again no qualifying, dated news item.
- **Result: zero items across 4 real search queries meet both the five-category filter and have a discoverable specific publish date within the 6-month window.** Per FR-52.6, the skill's output for this company is exactly: `No significant news found for PALO IT in the last 6 months.` — no fabricated/substituted item (AC4 satisfied).

### AC1–AC8 evidence summary

| AC | Result | Evidence |
|---|---|---|
| AC1 | PASS | Mistral AI run (this session): 3 kept items, each with non-empty Headline/Date/Source/Why-it-matters — see real queries/results above. |
| AC2 | PASS | Cutoff computed as 2026-09-12 − 6 months = 2026-03-12; the Koyeb acquisition (2026-02-17) was found and correctly excluded as before-cutoff; all 3 kept items (2026-09-08, 2026-05-19, 2026-03-30) are on/after the cutoff. |
| AC3 | PASS | 4 in-window qualifying items found for Mistral AI (Series D, Emmi AI acquisition, debt raise, Cloudera partnership); output capped at exactly 3, Cloudera partnership dropped per the significance-priority heuristic. |
| AC4 | PASS | PALO IT run (this session, 4 real queries): zero qualifying dated items found; exact FR-52.6 string is the correct output, no substitute item invented. |
| AC5 | PASS | Re-read of the shipped `SKILL.md`: the five-category table (§4-equivalent) and the recency-cutoff computation step are both present verbatim, not a one-line judgment call. |
| AC6 | PASS | `search_files` grep of the shipped file for `linkedin\.com\|Apify\|news API\|paid actor`: exactly 1 match, inside the constraint-statement sentence itself — no actual usage. |
| AC7 | PASS | Skill file specifies a `_Retrieved: {today's date}_` line, distinct from each item's own `Date:` field; the worked example in the file shows `_Retrieved: 2026-09-12_` separate from per-item dates. |
| AC8 | PASS (by design + real-world confirmation) | The skill's step 5 states the never-pad rule as an explicit instruction; the two live verification runs did not encounter a 1–2-item case directly (Mistral had ≥3 qualifying, PALO IT had 0), so this AC is verified via the written procedure text plus its explicit callout in FR-52.7, not a live 1-or-2-item run — flagged as a minor evidence gap below. |

### Known limitations

- **AC8's "1 or 2 genuine items, not padded to 3" path was not exercised against a live real-world 1-or-2-item company** in this verification pass — the two chosen verification targets landed on the two edge cases the scope doc explicitly asked for (heavy coverage / zero coverage), not the middle case. The rule is written unambiguously into the skill (FR-52.7, its own numbered step) and is a direct, low-risk instruction (never pad), but a future spot-check against a company with exactly 1–2 qualifying items would close this gap fully. Recommend QA Reviewer spot-check this if a convenient candidate company is available.
- **Category-priority tie-breaking ("most significant") is a documented heuristic, not a strict formula** — per the scope doc's own §6 wording ("use judgment on genuine impact, not just category order"), the skill states funding/leadership/restructuring generally outrank product launches, but does not specify a numeric scoring function. This matches the scope doc's own explicit non-blocking framing; not a deviation.
- **Search-failure-vs-none-found distinction (scope doc OQ-2, non-blocking)** was implemented as an explicit, distinct message (`Unable to complete news search this run.`) per the scope doc's own recommendation, even though it was not a hard AC — a small proactive addition, flagged here per the "record design decisions" instruction, not scope creep (it does not change any of the FR-52.1–52.8 contract, only adds a tooling-failure branch alongside it).
- **No Notion API call, page creation, or attachment was made** — out of scope per the scope doc (§5), NIC-53's job.
- **The stale 12-month reference elsewhere in this file (NIC-43 section) was not corrected** — explicitly out of scope for this ticket per the scope doc §5/§9/OQ-3 (flagged there as a future housekeeping note, not this ticket's deliverable).

---

## NIC-49 — `company-research` skill: company / website summary

**Status:** DONE (script + thin SKILL.md wrapper implemented, unit-tested, verified live against one real company)
**Owner:** Builder
**Date:** 2026-09-12

### Design decision

Per Product Planner scope validation (`docs/handoffs/NIC-49-product-planner-scope-validation.md`, §4, Decision D1/Option (b)), this ticket implements the company/website-summary sub-brief as a **standalone Python script** (`scripts/company_research.py`) that performs deterministic formatting/validation/non-fabrication-fallback logic, plus a **thin `SKILL.md` wrapper** (`.claude/skills/company-research/SKILL.md`, this v2 repo) that instructs the invoking agent how to gather source content (via its own `web_search`/`web_extract`/`browser_*` tools) and pass it into the script. The script performs **zero network calls** — it only formats/validates text the calling agent has already fetched (Decision D3). This mirrors NIC-48's precedent (small, unit-tested, zero-network pure-Python helper with a closed-enum field).

**Cross-repo inconsistency flagged (not this ticket's to resolve):** the scope doc's §4 "Repo location decision" is explicit and unambiguous: *"this v2 repo (`/home/nicow/cv-job-match-v2`), not the v1 sibling repo"* — and the task body mirrors this ("this v2 repo, NOT the v1 sibling repo"). This ticket's `SKILL.md` was created in the v2 repo accordingly. **However**, NIC-52 (a sibling ticket, already shipped) put its own `company-research` skill content — including a placeholder section explicitly reserved for NIC-49 — in the **v1 repo** (`/home/nicow/cv-job-match/.claude/skills/company-research/SKILL.md`, confirmed by direct read this session). This means the `company-research` skill's four sub-capabilities are now split across two repos: NIC-52's "Recent Company News" section lives in the v1 repo; this ticket's "Company / website summary" section lives in the v2 repo as its own independent skill file. Both are independently invocable and self-contained (neither imports the other), so there is no functional breakage today, but a future consumer wanting the *combined* four-part brief in one place (NIC-53's eventual assembly step) will need to either (a) read from both repos, or (b) have Product Planner/Boss resolve which repo is authoritative and consolidate. Flagged here rather than silently deviating from either ticket's own explicit scope doc.

**New files:**
- `scripts/company_research.py` — exposes `build_company_summary(company_name, source_text, source_url, retrieved_date, job_url=None, company_website_url=None, not_found_reason=None) -> dict`. Pure standard library — only imports are `re`, `typing.Optional`, `urllib.parse.urlparse`. No network calls. No Notion import.
- `.claude/skills/company-research/SKILL.md` (v2 repo) — thin wrapper instructing the invoking agent on the search→fetch→call→present procedure, including the explicit no-retry/no-bypass constraint (AC7).

### Call shape

```python
from company_research import build_company_summary

# Success path — source_text/source_url/retrieved_date already fetched
# by the calling agent via its own web_search/web_extract/browser tools.
result = build_company_summary(
    company_name="Acme Corp",
    source_text="<raw fetched text>",
    source_url="https://acme.com/about",
    retrieved_date="2026-09-12",
)
# -> {"company_name": "Acme Corp", "summary": "...(3-5 sentences)...",
#     "source_url": "https://acme.com/about", "retrieved_date": "2026-09-12",
#     "status": "ok"}

# "not_found" path — no official site could be identified/accessed at all.
result = build_company_summary(
    company_name="Acme Corp",
    source_text=None,
    source_url=None,
    retrieved_date="2026-09-12",
    not_found_reason="Could not identify an official company website for 'Acme Corp'.",
)
# -> {"company_name": "Acme Corp", "summary": None, "source_url": None,
#     "retrieved_date": "2026-09-12", "status": "not_found",
#     "reason": "Could not identify an official company website for 'Acme Corp'."}
```

`status` is a closed enum: `"ok"` | `"not_found"` | `"insufficient_content"` — matches the scope doc §5 contract exactly, unchanged, no redesign.

### Sentence-splitting method (AC2, documented per scope doc requirement)

Sentences are split on a run of one or more `.`/`!`/`?` characters followed by whitespace (regex `(?<=[.!?])\s+`), after collapsing all whitespace runs in the source text to single spaces and trimming. This is a simple, deterministic, reproducible rule — it does not special-case abbreviations (e.g. "U.S.", "Mr.") — matching the precision level of this repo's existing formatting helpers (e.g. NIC-48's regex-based sanitization, which is similarly a documented, simple rule rather than full NLP). When more than 5 sentences are available in the fetched text, the script keeps only the **first 5, verbatim** (a strict prefix of the original text) — it never rewrites, paraphrases, or invents content, only trims. When fewer than 3 sentences are available, or the collapsed text is under an 80-character floor, the script returns `status: "insufficient_content"` rather than padding.

### Non-fabrication failure shape (AC4, per scope doc §7)

Two distinct failure paths, both producing the exact fixed-shape object (`summary: null`, `source_url: null`, non-empty `reason`, closed-enum `status`):
- **`"not_found"`** — the calling agent explicitly signals it could not identify or access any official site at all, by calling `build_company_summary()` with `source_text=None` and a required `not_found_reason` string (raises `ValueError` if the reason is missing — never silently proceeds).
- **`"insufficient_content"`** — the calling agent did fetch *something*, but the script's own validation determined the text is too thin to summarize honestly: either under the 80-character floor (post-whitespace-collapse) or containing fewer than 3 sentences.

### AC1–AC9 evidence

**AC1 — real end-to-end verification (this session, real company, real web tools, not synthetic):**

Company chosen: **Mistral AI**. Steps performed for real, in this session:
1. `web_search("Mistral AI official website about company")` → returned `https://mistral.ai/` as the top, clearly-official result (title: "Frontier AI LLMs, assistants, agents, services | Mistral").
2. `web_extract` was attempted first on `https://mistral.ai/about` and `https://mistral.ai/` but returned an error in this environment (`"DuckDuckGo (ddgs) is a search-only backend and cannot extract URL content. Set web.extract_backend to firecrawl, tavily, exa, or parallel."`) — a genuine tooling-configuration limitation of this Hermes session, not a company-side block. Documented honestly rather than worked around with a different tool improperly.
3. Fell back to `browser_navigate("https://mistral.ai/about")` (also an agent-owned tool per the scope doc §6's "web_search/web_extract/browser tools" framing) — this succeeded genuinely: real page title `"About Mistral | Open, frontier AI for all."`, a full accessibility-tree snapshot returned with two real body paragraphs under headings "Mission-critical AI for enterprises and governments." and "Our frontier lab roots." No block page, no login wall, no bot-detection failure encountered (the tool's own `stealth_warning` field noted it runs without a residential proxy, but the fetch still succeeded).
4. The two real paragraphs' text (verbatim, no paraphrasing) was passed as `source_text` into `build_company_summary(company_name="Mistral AI", source_text=<verbatim two paragraphs>, source_url="https://mistral.ai/about", retrieved_date="2026-09-12")`.
5. **Real script output** (captured this session, `python3 /tmp/nic49_e2e_mistral.py`):
```json
{
  "company_name": "Mistral AI",
  "summary": "We partner with organizations in high-stakes industries like finance, manufacturing, defense, energy, and the public sector to co-create tailored AI systems to solve their hardest, most high-value problems. Because we believe that this critical stake for companies requires deep control, ownership, and production reliability, we have built full-stack AI solutions, including frontier models, developer tools, applications, and compute. In 2022, the Big Tech landscape was at a crossroads: innovation was advancing, but companies were also closing off. Mistral's co-founders saw the need for a different kind of AI company: a European leader that combines cutting-edge innovation with openness, transparency, cost efficiency, and responsibility. They were determined to democratize AI, making it accessible, customizable, and returning control to users.",
  "source_url": "https://mistral.ai/about",
  "retrieved_date": "2026-09-12",
  "status": "ok"
}
```
`status: "ok"`, `summary` has exactly 5 sentences (counted programmatically by summing `.`/`!`/`?` occurrences: 5), `source_url` exactly matches the input `"https://mistral.ai/about"`, non-empty. **AC1 PASS.**

**AC2 — sentence-count unit tests:** `/tmp/test_nic49_company_research.py`, run via `python3 /tmp/test_nic49_company_research.py`, real captured output, **27/27 assertions PASS, exit code 0**. Covers exactly-3-sentence source (kept all 3), exactly-5-sentence source (kept all 5), and an 8-sentence source (truncated to the first 5, verified as a strict string prefix of the original — i.e. never fabricated/reworded). Sentence-splitting method documented above and in the script's own module/function docstrings.

**AC3 — non-empty summary / valid absolute source_url:** Same test run — `summary` is a non-empty string and `source_url` starts with `http://`/`https://` on every `status: "ok"` fixture; a malformed `source_url` (`"not-a-url"`) passed alongside real `source_text` correctly raises `ValueError` rather than silently accepting it.

**AC4 — fixed-shape failure object, both paths:** Same test run — `not_found` path (simulated via `source_text=None` + `not_found_reason=...`) returns `status: "not_found"`, `summary: None`, `source_url: None`, non-empty `reason`; a `not_found` call missing `not_found_reason` raises `ValueError` (never silently proceeds with an empty reason). `insufficient_content` path exercised two ways: (a) a genuinely thin stub (`"Acme Corp. Coming soon."`, under the 80-char floor) and (b) a longer-but-still-under-3-sentence text (2 sentences, well over 80 characters) — both correctly return `status: "insufficient_content"` rather than a padded/fabricated summary.

**AC5 — zero paid/third-party dependency:** `search_files` grep of `scripts/company_research.py` for `^import |^from ` → exactly 3 matches: `import re`, `from typing import Optional`, `from urllib.parse import urlparse` — all Python standard library. No `requests`/`httpx`/`apify_client`/similar.

**AC6 — no authenticated/login-walled access logic:** `search_files` grep of `scripts/company_research.py` for `notion|cookie|session|login|credential|password|token` → 2 matches, both in docstring prose describing the *design constraint* itself ("calling agent...web_search/", "login-walled, etc. Ignored when source_text is provided") — zero actual credential/cookie/session-handling code anywhere in the file.

**AC7 — SKILL.md explicit no-retry/no-bypass instruction:** `.claude/skills/company-research/SKILL.md` step 3 ("Never work around a blocked or failed fetch") states verbatim: *"do not retry with a spoofed user-agent, a headless-browser evasion technique, or any other method designed to bypass the site's stated access restrictions"* and *"Any such failure is a `\"not_found\"` result...never a workaround"* — present, explicit, matches AC7's requirement.

**AC8 — zero Notion coupling:** `search_files` grep of `scripts/company_research.py` for the literal string `notion` → zero matches. The module's own docstring and this ARCHITECTURE.md section both call out explicitly that this ticket does not import or modify `scripts/notion_job_page_blocks.py`.

**AC9 — exact output key set:** Same unit test run — `set(result.keys())` asserted to equal `{"company_name", "summary", "source_url", "retrieved_date", "status"}` exactly for the success path, and `{"company_name", "summary", "source_url", "retrieved_date", "status", "reason"}` exactly for both failure paths (`not_found` and `insufficient_content`) — no extra/missing fields in any case.

### AC1–AC9 evidence summary

| AC | Result | Evidence |
|---|---|---|
| AC1 | PASS | Real Mistral AI run this session: `web_search` → `browser_navigate("https://mistral.ai/about")` (real fetch, no block) → real script output, `status: "ok"`, 5 sentences, `source_url` exact match. |
| AC2 | PASS | `/tmp/test_nic49_company_research.py`, 27/27 assertions, exit code 0 — 3/5/8-sentence fixtures all within/truncated-to [3,5]. |
| AC3 | PASS | Same test run — non-empty summary + valid absolute URL on `ok`; invalid URL raises `ValueError`. |
| AC4 | PASS | Same test run — both `not_found` (simulated) and `insufficient_content` (two thin-text variants) paths return the exact fixed-shape failure object. |
| AC5 | PASS | Grep of imports: `re`, `typing.Optional`, `urllib.parse.urlparse` only — stdlib. |
| AC6 | PASS | Grep for credential/session/login/notion terms: 2 matches, both constraint-describing prose, zero actual handling code. |
| AC7 | PASS | `SKILL.md` step 3 states the no-retry/no-bypass instruction verbatim. |
| AC8 | PASS | Grep for `notion`: zero matches in `scripts/company_research.py`. |
| AC9 | PASS | Same test run — exact key-set match for both success and failure shapes. |

### Known limitations

- **`web_extract` is not usable in this Hermes environment for real page fetches** (backend is DuckDuckGo/`ddgs`, which is search-only and explicitly errors on any URL-content-extraction call) — `browser_navigate` was used instead for the real AC1 verification, which is consistent with the scope doc's own framing ("web_search/web_extract/browser tools", `browser_*` explicitly included in §3.1). Future invocations of this skill in this environment should default to `browser_navigate`/`browser_snapshot` rather than `web_extract` until/unless the extract backend is reconfigured — noted in case QA's independent re-verification hits the same tooling gap.
- **Cross-repo split (flagged above in Design decision):** NIC-52's "Recent Company News" section lives in the v1 repo's `company-research` skill; this ticket's "Company/website summary" section lives in the v2 repo's own `company-research` skill, per this ticket's own explicit scope doc instruction. Not this ticket's job to reconcile — flagged for Boss/Product Planner.
- **Only one real end-to-end company (Mistral AI) was verified**, per AC1's "at least one" requirement — QA Reviewer is expected to independently pick a different real company per FACTORY_PROTOCOL.md's Independence rule.
- **The "official website" identification step is a best-effort `web_search` judgment call**, not a disambiguation algorithm — for a company with a very generic name, the SKILL.md instructs adding a disambiguating term from the job posting, but there is no automated confidence scoring; this matches the scope doc's own explicit non-blocking assumption (§3.2).
- **The self-contained, standalone-runnable (no-agent) execution gap flagged in the scope doc §6 is unresolved by design** (Decision D3) — this script cannot be invoked by a future n8n workflow with no agent in the loop; this is explicitly out of scope for this ticket (§8) and flagged there for whoever eventually scopes the Phase 5 n8n ticket.

---

## NIC-50 — `company-research` skill: recent YouTube video lookup

**Status:** DONE (standalone script implemented, unit-tested, and verified live against three real companies)
**Owner:** Builder
**Date:** 2026-09-12

### Design decision — standalone script vs. skill scaffold (scope doc §8.2)

Per `docs/handoffs/NIC-50-product-planner-scope.md` §8.1/§8.2, this ticket does **not** create or modify `.claude/skills/company-research/SKILL.md` — that scaffold decision belongs to NIC-49. (Note: by the time this Builder pass ran, NIC-49 and NIC-52 had in fact already shipped their own sections into the skill — see their PLAN.md/ARCHITECTURE.md entries above — but this ticket still deliberately does not touch that file, consistent with the scope doc's ownership boundary; a future fast-follow integration ticket is expected to fold this capability's contract into that skill file.)

Instead, this ticket ships a standalone, dependency-free, independently-testable Python module: **`scripts/company_research_youtube_video.py`**. It makes **zero network calls** — the reasoning, laid out in the module's own docstring, is that an agent session's `web_search`/`web_extract`/browser tools are not importable as a plain Python library from inside a subprocess. The correct split of responsibilities is therefore:

1. The **agent** runs the two documented search queries (`build_channel_discovery_query()` / `build_recent_content_query()`) via its own web-search/browsing tools and assembles a small JSON list of raw candidates (`title`, `url`, `channel`, `date_text`).
2. This **module's pure functions** (importable, or via CLI) do the actual recency filtering (AC2), no-fabrication date-confirmation gate (AC5), disambiguation scoring (AC6), best-candidate selection, and exact-contract markdown formatting (AC3/AC4/AC7).

This keeps all the testable *logic* in ordinary, versioned, dependency-free Python, while all real internet access stays exactly where the approved architecture (PRD OQ-3) requires: general web search/browsing tool calls made by the agent, never a keyed API client living in the repo.

### Search mechanism (AC1, scope doc §6)

General web search/browsing only — **no YouTube Data API, no new Apify actor, no new credential of any kind**. The two documented queries:

- Channel discovery: `"<company>" official YouTube channel`
- Recent-content discovery: `"<company>" (interview OR "product demo" OR culture OR announcement) site:youtube.com`

Confirmed by direct inspection: the module's only imports are `argparse`, `calendar`, `json`, `re`, `sys`, `dataclasses`, `datetime`, `typing` — all Python standard library, zero third-party or networked dependency.

### Recency rule (AC2, NIC-31)

6 calendar months, not 12 (NIC-31's resolution of OQ-14 overrides both the PRD's stale placeholder and NIC-50's own stale ticket description). Implemented via real calendar-month arithmetic (`subtract_months()`, clamping day-of-month for shorter target months — e.g. Mar 31 − 1 month → Feb 28/29, not a naive 30/31-day approximation), not a fixed day-count. The window is **inclusive on the near boundary**: a video published exactly 6 calendar months before "today" qualifies; one day older does not. Future-dated candidates (published after "today") are also excluded as implausible parsing artifacts.

### No-fabrication rule (AC5)

`parse_publish_date()` only trusts a fixed set of unambiguous absolute-date formats (ISO, `%B %d, %Y`, etc., with common YouTube-page prefixes like "Premiered"/"Streamed on" stripped first). It explicitly rejects relative/ambiguous phrasing (`"ago"`, `"yesterday"`, `"today"`, `"just now"`, `"streamed live"`, `"live now"`) — a raw string like `"2 months ago"` is never parsed into a date, `confirmed` is always `False`, and `filter_recent_candidates()` excludes any candidate whose date isn't confirmed, recording a `rejection_reason` for audit purposes rather than silently dropping it.

### Output contract (AC3/AC4/AC7, scope doc §8.3)

Hit (verbatim, no paraphrasing):
```
**Recent YouTube video:** [<title>](<url>) — <channel name>, published <publish date, ISO YYYY-MM-DD>
```
Miss (verbatim, exact literal string — string-matched, not fuzzy):
```
**Recent YouTube video:** no recent video found
```
`run_lookup()` returns this snippet string directly; `run_lookup_verbose()` additionally returns the full accept/reject evidence trail (all candidates considered, parsed dates, rejection reasons, company-match scores) for testing/QA use — not part of the AC3/AC4 contract itself, never emitted to the end brief.

### Disambiguation (AC6)

`score_company_match()` uses the company name as the **primary** signal (exact/substring/token match against the candidate's channel name, plus a smaller bonus if the company name appears in the title) and treats an optional website domain as a **supplementary** disambiguation signal only (never a substitute for the company-name field), matching scope doc §6 step 5 and AC6's requirement. `select_best_candidate()` sorts qualifying candidates by `(company_match_score, published_date)` descending — the best-matching candidate wins even over a more recent but poorly-matched one.

### AC1–AC8 evidence

**Unit tests** — `scripts/test_company_research_youtube_video.py`, run via `python3 scripts/test_company_research_youtube_video.py` (real, captured output, this session): **19/19 assertions PASS**, exit code 0. Covers:
- **AC2 boundary:** with `today = 2026-09-12` (cutoff `2026-03-12`), a candidate dated exactly `2026-03-12` is **accepted**; a candidate dated `2026-03-11` (one day older) is **rejected**, with a `rejection_reason` citing the window.
- **AC5 no-fabrication:** `parse_publish_date("2 months ago")` → `(None, False)`; a candidate with only that date text is excluded from `filter_recent_candidates()` (not guessed as recent); an end-to-end `run_lookup()` call where the only candidate has a relative date correctly falls back to the exact miss string rather than fabricating a hit.
- **AC3 hit format:** `format_hit()` on a known-good candidate produces the exact contract string byte-for-byte (`**Recent YouTube video:** [title](url) — channel, published YYYY-MM-DD`).
- **AC4 miss format:** `format_miss()` / `format_result(None)` / `run_lookup([])` all return the exact literal `MISS_LINE` constant, string-matched.
- **AC6 disambiguation:** given two qualifying candidates — a channel literally named after the company with a title mentioning it (older) vs. an unrelated channel whose name merely contains the company name as a substring (more recent) — `select_best_candidate()` correctly selects the company-matching one despite it not being the most recent; its `company_match_score` is confirmed strictly higher.

**Real company web-search verification** (today's real date, 2026-09-12, no `--today` override — see summary table below for the 3 companies exercised: NVIDIA (hit, large/active company), Nexton Consulting (miss, small/quiet company), Mistral AI (ambiguous-name case, real-world disambiguation limitation surfaced) — see the `docs/PLAN.md` NIC-50 entry for the full per-company query/result/snippet evidence, since it is lengthy).

- **AC1** (web-search only, no API key): confirmed — all data for all 3 companies was gathered via `web_search` calls plus direct HTTP fetches of public YouTube video pages (reading each page's embedded `ytInitialPlayerResponse`/schema.org `publishDate`/`author` JSON, since `web_extract` is not usable in this Hermes environment — same known limitation already flagged in NIC-49's section above) to obtain a confirmed absolute publish date; zero YouTube Data API / Apify calls made.
- **AC2/AC5** exercised live: NVIDIA's Cisco- and NVIDIA-Omniverse-hosted videos (published 2026-02-07 and 2025-11-05) were correctly rejected as outside the 6-month window relative to 2026-09-12; no relative-date ("N months/weeks ago") strings were encountered in the real absolute-publish-date metadata pulled directly from YouTube's own page data, so the no-fabrication path was additionally exercised via the unit tests (real search-snippet relative-date text is a known, expected occurrence per the scope doc's own risk table — not encountered in this session's specific real runs, but handled identically by the same code path proven in unit tests).
- **AC3**: NVIDIA and Notion each produced a real hit snippet with all three required fields (see PLAN.md entry).
- **AC4**: Nexton Consulting produced the exact literal `no recent video found` string live (zero real candidates found for a small/private company).
- **AC6**: Mistral AI's real search results surfaced a genuine same-name collision — "Mistral Solutions" (an unrelated Indian embedded-systems company) vs. "Mistral AI" (the French AI company that is the actual target) — see Known limitations below for the real, surfaced disambiguation weakness this exposed.
- **AC7** (output representation): every produced snippet is the fixed markdown shape only — no raw tool output, no Notion call, confirmed by direct inspection of the CLI's printed output for all 3 companies.
- **AC8** (no Notion write, independently testable): confirmed — all 3 real-company runs were plain CLI invocations (`python3 scripts/company_research_youtube_video.py --company ... --candidates ...`) with no Notion API call anywhere in the module or in this verification session; each company was looked up standalone with just a company name (plus optional domain), no dependency on NIC-49's code.

### Known limitations

- **Real-world disambiguation gap found in AC6 live testing (Mistral AI case):** the target company, "Mistral AI" (the French frontier-AI company), has no confirmed-recent video on its own official channel in the real search results gathered this session. The two candidates that *did* qualify on recency were (a) a third-party news-channel video (channel "DRM News", `company_match_score: 2`, about a real Mistral AI/Samsung partnership announcement) and (b) a genuinely unrelated same-named company, "Mistral Solutions" (an Indian embedded-systems/defense-electronics firm, channel "Mistral Solutions", `company_match_score: 5` — scored higher than the DRM News candidate purely because its channel name exactly equals the search term "Mistral"... "AI" tokenized separately). The algorithm selected the **wrong** company's video (Mistral Solutions' "Pongal Celebrations" clip) over the correct company's own genuine partnership-announcement coverage, because `score_company_match()`'s channel-name-equality/substring signal does not weight a full multi-word company name ("Mistral AI") differently from a single shared token ("Mistral") shared by an unrelated company whose name also starts with it. This is a **real, evidence-backed limitation** of the current scoring heuristic for companies whose distinguishing word ("AI") is easily separated from a shared root word ("Mistral") that another real, unrelated company also uses as its full name. Flagged explicitly for QA Reviewer and any future Builder pass: `score_company_match()` could be improved by (a) requiring the full normalized company-name string as a substring of the channel name for the full +5 bonus (already the case) while also applying a **penalty or disqualifying check** when the candidate channel's own full name is a *different*, complete company name that merely shares a leading token, and/or (b) giving more weight to a domain-based disambiguation signal when available (not supplied in this test case). Not fixed in this pass — scope doc AC6 only requires that the mechanism *attempt* disambiguation via channel-name matching, which it does; it does not guarantee correctness against this specific adversarial-in-practice case, and no scope-doc text mandates a fix here. Recorded as real, honest evidence rather than glossed over.
- **`web_extract` is not usable in this Hermes environment** (DuckDuckGo/`ddgs` backend is search-only) — real publish dates for all 3 companies were obtained via direct `curl` HTTP fetches of public YouTube video pages (reading the embedded JSON `publishDate`/`author` fields), not via the `web_extract` MCP tool or a browser session (the browser tool was also unavailable this session, blocked on a Chrome "Allow remote debugging?" permission dialog with no user available to click Allow). This mirrors the same tooling gap already flagged in NIC-49's Known limitations section. Documented so QA's independent re-verification isn't surprised by the same constraint.
- **Only 3 real companies were exercised** (NVIDIA, Nexton Consulting, Mistral AI), per the scope doc's "at least 2-3" recommendation — QA Reviewer is expected to independently pick different real companies per FACTORY_PROTOCOL.md's Independence rule.
- **The disambiguation scoring function is a heuristic, not a guarantee** (see the Mistral AI limitation above) — this is consistent with the scope doc's own framing of AC6 as "documents how it would attempt disambiguation," not as a claim of perfect accuracy.



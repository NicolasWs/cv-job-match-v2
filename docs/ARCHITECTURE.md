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

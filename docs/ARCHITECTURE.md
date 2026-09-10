# ARCHITECTURE — cv-job-match v2

Design decisions, interfaces, data model, and risks. Populated incrementally as tickets ship; this file currently documents NIC-42 only. See docs/PRD.md for the full target-state design and docs/PLAN.md for phased rollout status.

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

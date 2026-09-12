# NIC-49 — Product Planner Scope Validation

**Ticket:** NIC-49 — "P3-T1 — New company-research skill: company/website summary"
**Traces to:** FR-A1, FR-A2, US-4
**Author:** Product Planner (delegated Bot)
**Date:** 2026-09-12
**Role boundary respected:** no code/implementation performed; this is scope definition only. No network calls were made against any company site during this investigation — the technical-mechanism recommendation is decided by reading this repo's code/docs and this Hermes environment's tool availability, not by running a live company-research pass.

---

## 1. Problem restatement

Nicolas has no systematic way to research a target company beyond what's in a job description before applying or interviewing (PRD §2.1). Section 6.1 of the PRD resolves this via a brand-new `company-research` skill; this ticket (NIC-49) is the **first** of five sibling Phase-3 tickets and covers only the narrowest, foundational slice of that skill: given a company (name, and ideally a job URL), produce a 3–5 sentence company/website summary with a cited source URL, or explicitly state that one could not be produced — never fabricate. The other four sub-capabilities (recent YouTube video = NIC-50, open-position counts = NIC-51, recent news = NIC-52) and the Notion-attachment/assembly step (NIC-53) are explicitly **not** this ticket's job.

## 2. Goal

Ship the smallest possible vertical slice that:
1. Establishes the concrete shape (script + thin SKILL.md wrapper — see §3) that the remaining four Phase-3 tickets will follow, so NIC-50/51/52 don't have to re-litigate "is this a script or pure-agent-instruction" and NIC-53 can programmatically consume this ticket's output without a redesign.
2. Satisfies FR-A1/FR-A2 for the company/website summary sub-brief only, with a testable, QA-reproducible no-fabrication fallback.
3. Does not touch Notion, does not touch n8n, does not introduce a new paid API/actor, and does not scrape anything requiring login.

## 3. Facts, assumptions, and decisions (separated explicitly)

### 3.1 Facts (verified this session by reading code/docs)

- **No existing `company-research` skill or script exists anywhere in this repo.** `scripts/` contains exactly 6 Python files (`render_markdown_to_pdf.py`, `notion_import_saved_jobs.py`, `notion_attachment_naming.py`, `notion_cover_letter_attachment.py`, `notion_cv_attachment.py`, `notion_job_page_blocks.py`) — none perform web search/company research. Confirmed via `search_files` glob on `scripts/*.py`.
- **`scripts/notion_job_page_blocks.py`'s `build_job_page_children()` already reserves a "🔍 Company Research Brief" placeholder** — block index 3–4 of the 14-block template (`heading_2("🔍 Company Research Brief")` + a `callout` reading "Pending — populated by the `company-research` skill (Phase 3, not yet built)..."). This confirms the intended eventual consumer of this ticket's output, but **NIC-53, not NIC-49, does the actual placeholder replacement** (verified: the callout text and code comments explicitly say "Phase 3, not yet built" with no NIC-49-specific wiring present).
- **PRD §6.1 explicitly resolves the retrieval mechanism**: "Built via general web search/browsing (no new paid Apify actor for v1)" — this is stated as a scoping decision, not an open question. PRD §10 Dependencies confirms: "**[RESOLVED: general web search/browsing, no new Apify actor for v1]**."
- **FR-A1/FR-A2 (PRD §7) are the literal, only acceptance criteria this ticket traces to**, and are reproduced verbatim in the Linear ticket description (re-fetched fresh via GraphQL this session, `issue(id: "85b3a223-...")`, ticket confirmed still in state `In Progress` with only the `Boss` label present before this session's label swap).
- **PRD §8 Non-Functional Requirements** state: "Data integrity: No fabricated facts anywhere in generated content"; "Traceability: ... Every company research data point must cite its source and retrieval date"; "Recency: Company research data (news, headcount) should show a retrieval date so staleness is visible."
- **PRD §11 Risks table** rows on open-position-count/news reliability explicitly recommend "Always cite source + retrieval date... never present a single number as definitive without its source" and "Allow explicit 'no significant news found' as a valid output, consistent with the existing 'never fabricate' rule" — the same pattern this ticket must apply to the website summary (cite source, allow explicit "not found").
- **OQ-3 is resolved** (general web search/browsing, no Apify actor) — reproduced in PRD §10's "Resolved during scoping Q&A" table. **OQ-14 (recency window for "recent" video/news) is still open** but is explicitly not this ticket's concern — FR-A2 (company/website summary) carries no recency-window language; only FR-A3 (YouTube) and FR-A6 (news) do. OQ-14 is NIC-50/NIC-52's problem, not NIC-49's.
- **This Hermes environment's Product Planner/Builder/QA profiles have `web_search`, `web_extract`, and `browser_*` MCP tools available** (confirmed: these are tools directly available in this session's own tool schema) — these are conversational-session tools, not something a standalone Python script can invoke on its own without an agent driving it, or without adding a new HTTP-based search API dependency of its own.
- **Every prior shipped ticket in this repo (NIC-42/43/46/47/48/56) that involved a testable mechanism was implemented as a standalone Python script** (`scripts/*.py`), independently unit-testable and/or live-verifiable by both Builder and QA, per the ARCHITECTURE.md evidence trails read this session. There is no existing precedent in this repo for a "pure-instruction, no-script" skill.
- **The sibling v1 repo (`/home/nicow/cv-job-match/.claude/skills/`)** hosts `find-opportunities`, `cv-match`, `write-outreach`, `interview-prep`, `run-my-week` — all are SKILL.md-driven Claude Code skills. Per the ticket body's own framing, `company-research` is a brand-new skill with no existing code to reuse; this ticket does not touch the v1 repo.
- **AGENTS.md forbidden-operations rule**: "No contacting third parties (emails, external APIs with side effects, messages) without explicit human approval." A `GET` request to a company's own public website is a passive, read-only fetch with no side effects on the target — this is categorically different from NIC-56's LinkedIn-authenticated-scrape risk (no login, no session, no account-linked action) and does not require a separate human-approval gate under this rule as written. Search-engine queries (via `web_search`) are likewise passive reads. This is a Product Planner judgment call, flagged explicitly in §3.3.

### 3.2 Assumptions (explicit, not verified live)

- Assumed: for "given a company name (and ideally a job URL)," the primary required input is the **company name as a string**; the job URL is an optional enrichment input (e.g., to help disambiguate the company or pull its site link from a job posting's own "About us" boilerplate) but is not required to produce a summary. Not independently confirmed with Nicolas — flagged as OQ-1 below (non-blocking; the ticket description's own phrasing already supports this reading).
- Assumed: "the company's own site content" (FR-A2) means the summary must be built from the company's **official website** (e.g., `acme.com`, not `linkedin.com/company/acme` or a news aggregator), consistent with FR-A2's literal text ("Summary reflects the company's own site content"). A LinkedIn company page or Crunchbase profile is not an acceptable substitute source for this specific sub-requirement, even if easier to find.
- Assumed: "3–5 sentences" (FR-A2) is a hard, mechanically-checkable bound (sentence count, not word count), consistent with how FR-A2 is phrased ("in 3–5 sentences"). Not re-confirmed with Nicolas as a literal count-based gate versus a looser "short paragraph" guideline — flagged as OQ-2 below (non-blocking; the literal PRD text supports the strict reading and this scope doc adopts it as the testable AC).
- Assumed: this ticket does not need to resolve "which company website is authoritative" disambiguation logic beyond a best-effort search (e.g., companies sharing a generic name) — if the search process cannot confidently identify the official site, that is itself a valid "could not access/identify" failure case per §7 below, not a blocking design problem to solve exhaustively in v1.

### 3.3 Decisions this scope doc makes (Product Planner judgment calls, flagged as such)

- **Decision D1 — Skill shape: Option (b), a standalone script + thin SKILL.md wrapper**, living in **this v2 repo** (`/home/nicow/cv-job-match-v2/scripts/company_research.py` + `.claude/skills/company-research/SKILL.md` in this same repo, NOT the v1 repo). Reasoning in §4 below.
- **Decision D2 — Output contract is structured JSON**, not a markdown blob, specifically so NIC-53 can assemble four tickets' outputs mechanically without re-parsing prose. Full shape in §5.
- **Decision D3 — Web-access mechanism for v1 is agent-driven** (an agent — Builder, then later whichever Bot invokes the shipped skill — uses its own `web_search`/`web_extract` MCP tools to gather raw page content and passes it to the script's summarization/formatting logic), **not** a self-contained script that opens its own HTTP connections to arbitrary company websites. Reasoning and the standalone-execution gap this creates are both flagged explicitly in §6.
- **Decision D4 — the non-fabrication failure path is a specific, fixed-shape JSON object** (not free text), so QA can pattern-match it mechanically. Exact shape in §7.

## 4. Skill-shape options (evaluated, with recommendation)

| Option | Mechanism | Testability / reproducibility | Consistency with repo convention | Verdict |
|---|---|---|---|---|
| (a) Pure Claude Code skill directory only (`SKILL.md` in this v2 repo or the v1 repo), agent-invoked conversationally, **no new script** | A markdown instruction file tells an agent how to research a company using its own tools each time it's invoked | **Low** — every invocation re-derives its own logic from prose instructions; QA cannot re-run a deterministic command to reproduce Builder's exact output-shape validation; small instruction-wording drift between runs is possible | **Breaks precedent** — no prior ticket in this repo (NIC-42/43/46/47/48/56) shipped as instruction-only; all have a script with a fixed, importable function/CLI surface QA can independently invoke | Not recommended |
| (b) Standalone Python script (`scripts/company_research.py`) that defines the **output-shape validation, formatting, and no-fabrication-fallback logic** in testable, pure-Python functions, with a **thin SKILL.md wrapper** instructing an agent to gather raw source content (via its own web_search/web_extract tools) and pass it through the script's formatting/validation functions | Agent does the retrieval (search + fetch), script does deterministic formatting/validation (sentence-count check, URL-presence check, JSON-shape enforcement, fallback-object construction) | **High** — the script's pure-Python functions (shape validation, fallback construction, sentence counting) are unit-testable with **zero network calls**, exactly like NIC-48's `build_attachment_filename()` precedent; QA can independently re-run the script against captured/fresh source text and verify the JSON shape mechanically | **Matches every prior ticket's convention** exactly (script-based, unit-testable core + a documented call shape) | **Recommended** |
| (c) Pure agent-instruction-only, SKILL.md tells the agent "use your web_search/browse tools directly, format the output yourself, no script" | No new file besides SKILL.md; agent free-forms the entire pipeline (search, extract, summarize, validate its own sentence count, build fallback JSON) every time | **Lowest** — sentence-count/URL-citation/JSON-shape compliance depends entirely on the agent's in-context adherence to prose instructions each run, with no deterministic function QA can call to check compliance mechanically; NIC-53's later assembly step would have no fixed contract to import against | Breaks precedent (same reasoning as (a), compounded — no fixed output-shape logic at all, only prose) | Not recommended |
| (d) A standalone script that does everything itself, including making its own HTTP requests to search engines/company sites (no agent-tool dependency at all) | Script directly performs HTTP `GET`s / calls a search API | Highest *standalone* reproducibility (no Hermes/Claude-Code session needed at all) | Introduces a **new network dependency** (an HTTP client + either a paid search API key or ad hoc scraping of a search engine's results page, which most search engines' ToS restrict for automated querying) not currently present in this repo's `scripts/*.py`. Not required by OQ-3's resolution ("general web search/browsing" was resolved as agent-driven browsing, not a new API integration) | **Not recommended for v1** — would silently reintroduce exactly the kind of "new paid API/actor" dependency OQ-3 explicitly ruled out, or an unauthenticated scraping approach LinkedIn's OQ-3 discussion context (and this ticket's own instructions) explicitly warn against generalizing without a clear approval |

**Recommendation: Option (b).** It is the only option that (1) matches this repo's unbroken script-based precedent across six prior tickets, (2) gives QA a deterministic, network-free way to re-verify output-shape compliance (sentence count, URL presence, JSON schema) independent of whatever specific search results a live run happens to produce, and (3) avoids introducing any new network dependency or paid API, honoring OQ-3's resolution literally. Option (b) does **not** eliminate the standalone-execution gap (§6) — that gap is real and is flagged, not hidden, in Section 6 below.

**Repo location decision:** this v2 repo (`/home/nicow/cv-job-match-v2`), not the v1 sibling repo. Reasoning: PRD §6.1 frames `company-research` as new v2-scoped work ("this does not exist in the current repo today"); all five Phase-3 tickets' natural home is this repo, consistent with every prior Phase 1–2 ticket (NIC-42/43/46/47/48/56) shipping here; the v1 repo is explicitly flagged elsewhere in this repo's own docs (NIC-45's PLAN.md entry) as "active production" requiring separate human approval to touch — there's no reason to create that approval burden for a brand-new skill with no v1 precedent to preserve.

## 5. Input/output contract (concrete, for NIC-53 reuse)

**Script:** `scripts/company_research.py` (working name; final naming at Builder's discretion following the `notion_*`/`render_*` naming convention already in `scripts/`, though this script is not Notion-specific so a `company_research_summary.py` or similar name may be clearer — Builder's call).

**Input (function signature, illustrative — Builder finalizes exact parameter names):**
```
build_company_summary(
    company_name: str,               # required
    job_url: str | None = None,      # optional, used only as a disambiguation hint
    company_website_url: str | None = None,  # optional, if already known — skips search-driven site discovery
    source_text: str,                # required — raw text/markdown already fetched by the calling agent via web_search/web_extract from the identified company site
    source_url: str,                 # required — the URL that source_text came from
    retrieved_date: str,             # required, ISO 8601 date, supplied by the calling agent at fetch time
) -> dict
```
The **script itself does not fetch anything over the network** — see Decision D3 / §6. The calling agent (Builder during implementation/verification; whichever Bot invokes the shipped skill in production) is responsible for: (1) identifying the company's official website (via web_search, optionally aided by `job_url`/`company_website_url` if provided), (2) fetching its content (via web_extract or browser tools), and (3) passing the raw text + its source URL + a retrieval date into the script. The script's job is deterministic formatting, validation, and non-fabrication-fallback construction — the part that must be reproducible and unit-testable.

**Output shape (structured JSON/dict, for both success and failure paths):**
```json
{
  "company_name": "Acme Corp",
  "summary": "Acme Corp builds ... (3-5 sentences).",
  "source_url": "https://acme.com/about",
  "retrieved_date": "2026-09-12",
  "status": "ok"
}
```
On failure (§7):
```json
{
  "company_name": "Acme Corp",
  "summary": null,
  "source_url": null,
  "retrieved_date": "2026-09-12",
  "status": "not_found",
  "reason": "Could not identify or access an official company website for 'Acme Corp'."
}
```
`status` is a closed enum: `"ok"` | `"not_found"` (no site could be identified/accessed) | `"insufficient_content"` (site found and accessed, but content too thin/generic to summarize in good faith). This mirrors NIC-48's closed-enum (`kind: {"CV", "Cover Letter"}`) precedent for validated, non-guessable fields.

This exact shape (`company_name`, `summary`, `source_url`, `retrieved_date`, `status`, optional `reason`) is what NIC-53 is expected to import/merge with the analogous outputs from NIC-50 (video), NIC-51 (headcount), NIC-52 (news) into one assembled brief — Builder should not redesign this shape without flagging the change back through Product Planner, since three other sibling tickets' outputs will need an equally-shaped contract for NIC-53's assembly step to be straightforward.

## 6. Web-access mechanism for v1 — concrete, with the standalone-execution gap flagged

**What actually performs the search/fetch during Builder's implementation and QA's independent re-verification:** the `web_search` and `web_extract` (or `browser_*`) MCP tools available in this Hermes environment, driven by whichever agent (Builder, then QA independently) is running the session. This satisfies PRD §6.1/OQ-3's "general web search/browsing, no new paid Apify actor" resolution literally and without introducing any new dependency.

**Real, current gap (flagged explicitly, same pattern as NIC-56 flagging LinkedIn automation as out of scope):** the shipped `scripts/company_research.py` **cannot run standalone outside a Hermes/Claude-Code session** (e.g., invoked directly by a future n8n workflow or cron job with no agent in the loop) because it has no built-in web-fetching capability by design (Decision D3, Option (b) in §4) — it only formats/validates pre-fetched text. This is a real limitation for the Phase 5 n8n automation layer (FR-G) described in the PRD, which is explicitly built last and is not this ticket's concern, but Boss/Nicolas should be aware: **when FR-G's n8n polling automation is eventually built, it will need either (a) an agent-in-the-loop invocation pattern (n8n triggers a Claude Code/Hermes session that runs the full search→fetch→format pipeline), or (b) a future re-scoping of this script to add its own network-fetching capability (a new, larger ticket, potentially reopening the Option (d) discussion in §4).** This scope doc does not resolve that now — it only makes sure the gap is visible and not silently discovered later.

**Sites requiring login/authentication:** explicitly out of scope — the script/skill must never attempt to access any page behind a login wall. If a company's official site happens to require a login for its "About" content (rare, but possible for some B2B/enterprise sites), that is a `"not_found"` case (§7), not a workaround.

**Per-site ToS/bot-blocking risk (flagged explicitly, same pattern as NIC-56's LinkedIn ToS flag):** some corporate websites block automated `GET` requests (via `robots.txt`, WAF/Cloudflare bot-detection, or IP-based rate limiting) even for benign, unauthenticated, single-request reads. **Recommendation: on any fetch failure (HTTP error, block page, empty response, robots.txt disallow), the calling agent must record it as a `"not_found"`/`"insufficient_content"` result and move on — never retry with a spoofed user-agent, a headless-browser workaround designed to evade detection, or any technique intended to bypass a site's stated access restrictions.** This is the same "graceful, explicit failure over a workaround" pattern NIC-56 applied to LinkedIn's ToS risk, generalized to "any site that says no." This is a hard constraint carried into the HANDOFF TO BUILDER section (§11).

## 7. Non-fabrication requirement — literal required failure-path shape

Per FR-A1 ("failure to find a data point is stated explicitly, never fabricated"), when a company's official website cannot be found, cannot be reached, or its content is too thin/generic to build a genuine 3–5 sentence summary from:

- The script **must not** invent, guess, infer-without-basis, or pad out a summary from generic industry knowledge about the company (e.g., must not fall back on "Acme is presumably a technology company because most companies named Acme in tech job postings are" — that is fabrication).
- The script **must** return the fixed-shape failure object defined in §5 (`status: "not_found"` or `"insufficient_content"`, `summary: null`, `source_url: null`, a human-readable `reason` string).
- The calling agent, when this failure object is returned, must present it to the user/downstream consumer as an explicit "could not find/access a company website for X" statement — never silently omit the section or fill it with placeholder prose that reads like a real summary.

## 8. Scope boundaries

**In scope for NIC-49:**
- `scripts/company_research.py` (or Builder's chosen filename) with the pure-Python formatting/validation/fallback-construction logic described in §5, unit-testable with zero network calls.
- A thin `.claude/skills/company-research/SKILL.md` wrapper in this v2 repo instructing an agent how to invoke the script (gather source text via web_search/web_extract, pass it in, handle both `status` outcomes).
- The company/website summary sub-brief only: `company_name`, `summary` (3–5 sentences), `source_url`, `retrieved_date`, `status`, optional `reason`.
- Documentation: `docs/ARCHITECTURE.md` new "NIC-49" section, `docs/PLAN.md` new NIC-49 entry, both per established repo convention.

**Explicitly out of scope for NIC-49:**
- Recent YouTube video (FR-A3) — **NIC-50**.
- Open-position counts, France + HQ country (FR-A4/FR-A5) — **NIC-51**.
- Significant recent news (FR-A6) — **NIC-52**.
- Any Notion API call, page read, or block write of any kind (FR-A7, the actual "Company Research Brief" placeholder replacement in `build_job_page_children()`'s 14-block template) — **NIC-53**, which depends on NIC-49/50/51/52 all being Done.
- Any n8n involvement — Phase 5, built last, not touched by any Phase 3 ticket.
- The recency-window question (OQ-14) — irrelevant to FR-A2 (no recency language in that requirement); relevant only to NIC-50 (video) and NIC-52 (news).
- A self-contained, standalone-runnable (no-agent) version of the script — flagged as a real, current gap in §6, not solved by this ticket.
- Any change to `scripts/notion_job_page_blocks.py`'s placeholder callout text — that remains NIC-53's job to replace at Notion-attachment time.

## 9. Acceptance criteria (numbered, testable)

| # | Criterion | Testable check |
|---|---|---|
| AC1 | Given a `source_text`/`source_url`/`retrieved_date` derived from a **real, actual company's official website** (not a synthetic/mocked string), the script produces a `status: "ok"` result with a `summary` of exactly 3–5 sentences and a non-empty `source_url` field matching what was passed in. | Builder (and independently, QA) must run the script against at least one REAL company — pick any real company (e.g., a company from one of the 5 existing real Notion job cards, or any other real company) and capture actual evidence: the real `web_search`/`web_extract` result used as `source_text`, and the real script output, both included in ARCHITECTURE.md's NIC-49 evidence section (mirrors this repo's zero-fabrication evidence culture, per NIC-42/43/46/47/48/56 precedent). No synthetic-only "it should work" claim is acceptable for this AC. |
| AC2 | Sentence count in `summary` is mechanically within [3, 5] inclusive. | Unit test (no network): feed the script pre-canned source text fixtures of varying length; assert the returned `summary`'s sentence count (by a defined, documented sentence-splitting rule — e.g., split on `. `/`! `/`? ` boundaries, Builder documents the exact method) is between 3 and 5 inclusive for every `status: "ok"` case; assert the function raises/rejects or truncates-with-a-flag if raw generation logic would produce fewer than 3 or more than 5 (Builder documents which behavior is implemented). |
| AC3 | `summary` field, when `status: "ok"`, is never empty/null, and `source_url` is always a syntactically valid absolute URL (starts with `http://` or `https://`). | Unit test: assert non-empty `summary` string and a passing `urllib.parse`-based URL-shape check on `source_url` for every `status: "ok"` fixture case. |
| AC4 | When no official company website can be identified/accessed, or content is too thin to summarize honestly, the script returns the exact fixed-shape failure object from §5/§7 (`status` ∈ {`"not_found"`, `"insufficient_content"`}, `summary: null`, `source_url: null`, non-empty `reason` string) — never a fabricated or generic filler summary. | Unit test (no network): call the script with an explicit "simulate not-found" input path/flag (Builder's implementation choice for how the caller signals "I could not fetch anything") and assert the exact failure shape is returned; separately, feed source text that is empty/near-empty (e.g., a 10-word stub page) and assert `status: "insufficient_content"` is returned rather than a padded-out summary. |
| AC5 | The shipped code contains zero references to any paid search/scraping API or new third-party HTTP client library beyond Python's standard library — confirms OQ-3's "no new paid Apify actor" resolution is honored. | Code review / static check: `scripts/company_research.py`'s imports are limited to the Python standard library (mirrors NIC-48's `AC4` "only import is `re`" precedent); no `requests`/`httpx`/`apify_client`/similar new dependency is added to this ticket's script. |
| AC6 | The shipped code never attempts to access, and contains no logic branching on, any authenticated/login-walled resource. | Code review: confirm no credential/cookie/session-handling code exists anywhere in `scripts/company_research.py` or the SKILL.md wrapper's instructions. |
| AC7 | The SKILL.md wrapper explicitly instructs the invoking agent to (a) never retry a blocked/failed fetch with a spoofed identity or robots.txt-bypassing technique, and (b) treat any such failure as a `"not_found"` case per §6/§7. | Read `company-research/SKILL.md`'s text and confirm this instruction is present verbatim or in clearly equivalent language — a documentation-presence check, not a runtime test. |
| AC8 | The script makes zero Notion API calls and imports no Notion-related module from this repo (e.g., does not import `notion_job_page_blocks`). | Code review / static grep: zero `notion` string matches in `scripts/company_research.py`'s import statements or logic (mirrors NIC-56's AC5 zero-`linkedin.com` grep precedent, generalized to "zero Notion coupling" for this ticket). |
| AC9 | Output dict/JSON exactly matches the field set in §5 for both the success and failure shapes — no extra undocumented fields, no missing required fields (`company_name`, `summary`, `source_url`, `retrieved_date`, `status` always present; `reason` present only on failure). | Unit test: assert `set(result.keys())` matches the documented field set exactly for both a success-path and a failure-path fixture run. |

## 10. Effort estimate

**S — approximately 2.5–3.5 hours.** Reasoning: this is a net-new script + net-new SKILL.md (no existing code to extend, unlike NIC-46/47/56's reuse of prior mechanisms), but the hardest part of "company research" — actually finding and fetching the right web page — is delegated to the calling agent's existing MCP tools rather than built from scratch inside the script (Decision D3), so the script itself is a comparatively small, pure-Python formatting/validation/fallback layer, closer in size to NIC-48's `build_attachment_filename()` helper (~2–3 hours, unit-tested, zero network) than to NIC-46/47's file-upload-flow complexity. Breakdown: output-shape + validation + fallback-object logic (~45–60 min, genuinely new but small), sentence-count/URL-shape validation functions + unit tests (~45 min, mirrors NIC-48's unit-test pattern), SKILL.md wrapper authoring (~20–30 min), one real end-to-end verification run against a real company using the agent's own web_search/web_extract tools + evidence capture (~30–45 min), documentation (~15–20 min).

This estimate assumes Option (b) only (§4) — if a self-contained, standalone-runnable version (§6's flagged gap, or Option (d)) is later separately requested, that would be a distinct, larger ticket (M: new HTTP client dependency or search-API integration, ToS-compliance research for automated search-engine querying, no longer "general web search/browsing" as originally resolved) — not an extension of this estimate.

## 11. Open questions

- **OQ-1 (not blocking):** Is the job URL truly optional-only (used solely as a disambiguation hint), or should Builder attempt to extract a company's official website URL directly from job-posting boilerplate ("About [Company]" sections common on job boards) as a first-choice input before falling back to a fresh web search? This scope doc assumes optional/hint-only (§3.2) since neither FR-A1 nor the Linear ticket description mandates job-URL-derived site extraction — recommend Boss/Nicolas confirm only if Builder's exploration during implementation suggests the job-URL path is meaningfully more reliable.
- **OQ-2 (not blocking):** Is "3–5 sentences" (FR-A2) a hard mechanical gate (this scope doc's assumption, §3.2) or a loose stylistic guideline that a slightly-off count (e.g., 6 short sentences) would still satisfy in spirit? This scope doc adopts the strict reading as the testable AC2 because it's the only version QA can mechanically re-verify; recommend Boss/Nicolas flag if a looser reading was actually intended.
- **OQ-3 (not blocking, restated from §6):** The standalone-execution gap (script cannot run without an agent in the loop) is real and will need resolving before Phase 5's n8n automation (FR-G) can trigger company-research automatically on a Kanban status change. Not blocking for this ticket; flagged for whoever eventually scopes the Phase 5 n8n ticket.
- **No blockers to starting Builder work on the recommended Option (b) scope.** No third-party credential/authentication risk, no new paid API, no Notion touch-point exists in this ticket's scope that would require a separate human-approval gate under AGENTS.md.

## 12. Go/no-go recommendation

**GO.** Builder should proceed directly on Option (b) (script + thin SKILL.md wrapper, §4) with the input/output contract in §5, the agent-driven web-access mechanism and its explicitly-flagged standalone-execution gap in §6, the non-fabrication failure shape in §7, and the numbered AC1–AC9 in §9 (including the mandatory real-company end-to-end evidence requirement, AC1). No human-approval gate beyond this scope doc's own Product Planner approval is required to start (per FACTORY_PROTOCOL.md's Approval gates section) — this ticket involves no third-party authenticated access, no paid API, no data deletion, and no Notion writes.

---

## HANDOFF TO BUILDER

**Objective:** Implement the `company-research` skill's foundational company/website-summary capability: a new `scripts/company_research.py` module providing deterministic, unit-testable formatting/validation/no-fabrication-fallback logic for a company/website summary, plus a thin `.claude/skills/company-research/SKILL.md` wrapper instructing an agent to gather source content (via its own web_search/web_extract tools) and pass it through the script.

**Context and relevant files:**
- Repo: `/home/nicow/cv-job-match-v2`.
- `scripts/notion_job_page_blocks.py` — for context only; do NOT import or modify (AC8). Its `build_job_page_children()`'s "🔍 Company Research Brief" placeholder callout is what NIC-53 (a later, separate ticket) will eventually replace with this ticket's output — not this ticket's job.
- `docs/PRD.md` §6.1 (In scope), FR-A1/FR-A2 (§7), NFRs (§8: data integrity, traceability, recency), Risks (§11), Dependencies (§10, OQ-3 resolution) — the requirements source of truth.
- This document (`docs/handoffs/NIC-49-product-planner-scope-validation.md`) for full rationale, the recommended skill-shape decision (§4), input/output contract (§5), web-access mechanism and its flagged gap (§6), non-fabrication shape (§7), scope (§8), and testable AC (§9).
- `docs/handoffs/NIC-48-product-planner-scope-validation.md` / NIC-48's ARCHITECTURE.md section — precedent pattern for a small, unit-tested, zero-network pure-Python helper with a closed-enum field and documented sanitization/validation rules; NIC-49's script should follow the same testing rigor (isolated unit test file, all assertions logged, exit code reported).

**Constraints:**
- **Hard stop: no new paid search/scraping API, no new third-party HTTP client library** beyond Python's standard library in the script itself (AC5) — the script performs no network calls; all fetching is done by the calling agent's own web_search/web_extract/browser MCP tools.
- **Hard stop: no access to any login-walled/authenticated resource, ever** (AC6) — a fetch failure of any kind (blocked, login-walled, error, empty) is a `"not_found"`/`"insufficient_content"` result, never a workaround.
- **Hard stop: never retry a blocked fetch with a spoofed user-agent or any robots.txt-bypassing technique** — must be stated explicitly in the SKILL.md wrapper (AC7).
- **Hard stop: zero Notion API calls or Notion-module imports** in this ticket (AC8) — Notion attachment is NIC-53's job.
- Must implement the exact output-shape contract in §5 (`company_name`, `summary`, `source_url`, `retrieved_date`, `status`, optional `reason`) — do not redesign without flagging back to Product Planner, since NIC-50/51/52/53 depend on a consistent shape.
- Must run at least one REAL end-to-end verification against an actual company (AC1) using this environment's own web_search/web_extract tools, and capture the real search/fetch evidence and real script output in ARCHITECTURE.md — no synthetic-only claim of correctness is acceptable for this AC, consistent with this repo's zero-fabrication evidence culture (NIC-42/43/46/47/48/56 precedent).
- No deployment, no data deletion, no third-party contact requiring credentials/login, without explicit human approval (AGENTS.md forbidden-operations rule).
- Do not touch `scripts/notion_job_page_blocks.py`'s placeholder text or any Notion API — out of scope (NIC-53).

**Acceptance criteria:** AC1–AC9 in §9 above.

**Files likely to touch:**
- New file: `scripts/company_research.py` (or Builder's preferred equivalent naming within the existing `scripts/` convention).
- New file: `.claude/skills/company-research/SKILL.md` (thin wrapper, this v2 repo).
- `docs/ARCHITECTURE.md` — new "NIC-49" section (design decision, call shape, real-company verification evidence per AC1).
- `docs/PLAN.md` — new NIC-49 entry, mirroring the existing format (NIC-42/43/46/47/48/56 precedent).

**Recommended next action:** Builder implements Option (b) (script + thin SKILL.md wrapper), writes an isolated unit test file (no network) covering AC2/AC3/AC4/AC9, runs one real end-to-end verification against an actual company using web_search/web_extract (AC1), documents evidence in ARCHITECTURE.md/PLAN.md, and hands off to QA Reviewer. QA Reviewer must independently re-run the unit tests and independently attempt at least one real company lookup of its own choosing (not simply re-running Builder's exact same company/inputs) to confirm the mechanism generalizes, per FACTORY_PROTOCOL.md's Independence rule ("QA re-derives its own evidence").

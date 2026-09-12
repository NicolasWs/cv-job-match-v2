---
name: company-research
description: Research a target company's official website and produce a sourced, dated 3-5 sentence summary via scripts/company_research.py — never fabricates when no site can be found/accessed. Use when the user asks to "research this company", "summarize {Company}'s website", or before an application/interview when a company/website brief is needed.
---

# Company Research — Company / Website Summary (NIC-49)

Produces the company/website-summary sub-brief for the `company-research`
skill (this is one of four sub-capabilities described in the sibling v1
repo's `.claude/skills/company-research/SKILL.md`; this ticket, NIC-49,
implements only the company/website-summary section). Output is always
sourced, dated, and JSON-shaped — "could not find/access a website" is
always a valid, explicit result. Never fabricate a summary.

## What this skill does NOT do

This skill/script performs **zero network calls of its own**. It is a
thin wrapper: the invoking agent (you) does all searching/fetching with
your own `web_search` / `web_extract` / `browser_*` tools, then passes
the raw text into `scripts/company_research.py`'s `build_company_summary()`
function, which does the deterministic formatting, validation, and
non-fabrication-fallback construction. This script never calls the
Notion API and is not wired into `scripts/notion_job_page_blocks.py` —
that assembly step is a separate ticket (NIC-53), not this skill's job.

## Procedure

1. **Identify the company's official website.**
   - If the calling context already supplies `company_website_url`,
     use it directly and skip search-driven discovery.
   - Otherwise, use `web_search` with a query like `"{Company Name}"
     official website` (add a disambiguating term from the job posting —
     industry, HQ city — if the company name is generic/ambiguous).
   - Prefer the company's own domain (e.g. `acme.com`) over a LinkedIn
     company page, Crunchbase profile, or news aggregator — those are
     not acceptable substitute sources for this specific sub-brief.
   - If no confident official site can be identified, stop here and go
     to step 5 (not_found path) — do not guess at a domain.

2. **Fetch the site's "About"/homepage content.**
   - Use `web_extract` (or `browser_navigate` + a snapshot) on the
     identified official site — prefer an "About" or "Company" page if
     one is discoverable; fall back to the homepage otherwise.
   - Record the exact URL you fetched from (`source_url`) and today's
     date in ISO 8601 form (`retrieved_date`) — both are required inputs
     to the script.

3. **Never work around a blocked or failed fetch.** This is a hard
   constraint:
   - If the fetch fails (HTTP error, empty response, a bot-detection/
     block page, a `robots.txt` disallow, or any login/authentication
     wall), **do not retry with a spoofed user-agent, a headless-browser
     evasion technique, or any other method designed to bypass the
     site's stated access restrictions.**
   - **Any such failure is a `"not_found"` result** (or
     `"insufficient_content"` if a page loaded but had essentially no
     usable text) — never a workaround, never a fabricated fallback
     summary based on general knowledge about the company or its
     industry.
   - This mirrors the same "graceful, explicit failure over a
     workaround" pattern this repo already applies to LinkedIn's ToS
     risk (NIC-56) and to authenticated/login-walled resources in
     general — a passive `GET` that a site declines to serve is a
     result to report honestly, not a barrier to engineer around.

4. **Call the script with the fetched content.**
   ```python
   import sys
   sys.path.insert(0, "scripts")
   from company_research import build_company_summary

   result = build_company_summary(
       company_name="Acme Corp",
       source_text=fetched_text,       # raw text from web_extract/browser
       source_url="https://acme.com/about",
       retrieved_date="2026-09-12",    # today's date, ISO 8601
   )
   ```
   The script validates the fetched text, builds a 3-5 sentence summary
   (truncating to the first 5 sentences if more are available — it never
   invents or paraphrases content not present in `source_text`), and
   returns `{"status": "ok", ...}` on success, or the fixed-shape failure
   object (`status: "insufficient_content"`) if the fetched text turns
   out to be too thin to summarize honestly (e.g. a near-empty stub page).

5. **The "not_found" path — no official site could be identified or
   accessed at all.** Call the script with `source_text=None` and a
   `not_found_reason` describing what happened:
   ```python
   result = build_company_summary(
       company_name="Acme Corp",
       source_text=None,
       source_url=None,
       retrieved_date="2026-09-12",
       not_found_reason="Could not identify an official company website for 'Acme Corp' after a web search.",
   )
   ```

6. **Present the result honestly.** On `status: "ok"`, present the
   `summary` with its `source_url` and `retrieved_date` cited. On
   `status: "not_found"` or `"insufficient_content"`, present the
   `reason` as an explicit "could not find/access a company website for
   X" statement — never silently omit the section, and never substitute
   placeholder prose that reads like a real summary.

## Output contract

```json
{"company_name": "Acme Corp", "summary": "...(3-5 sentences)...", "source_url": "https://acme.com/about", "retrieved_date": "2026-09-12", "status": "ok"}
```
```json
{"company_name": "Acme Corp", "summary": null, "source_url": null, "retrieved_date": "2026-09-12", "status": "not_found", "reason": "Could not identify or access an official company website for 'Acme Corp'."}
```
`status` is a closed enum: `"ok"` | `"not_found"` | `"insufficient_content"`.
This exact shape is documented in `docs/handoffs/NIC-49-product-planner-scope-validation.md`
section 5, and is what NIC-53's later assembly step expects — do not
redesign it here without flagging the change back through Product
Planner.

## Hard constraints (never violate)

- No new paid search/scraping API, no new third-party HTTP client
  library — the script performs zero network calls; only your own
  `web_search`/`web_extract`/`browser_*` tools are used.
- Never access, or design a fallback for, any login-walled/authenticated
  resource. Any such case is `"not_found"`.
- Never retry a blocked/failed fetch with a spoofed identity or any
  `robots.txt`-bypassing technique — treat the failure as `"not_found"`
  and move on (step 3 above).
- Zero Notion API calls from this skill — Notion attachment is a
  separate ticket (NIC-53).

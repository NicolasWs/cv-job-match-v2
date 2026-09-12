#!/usr/bin/env python3
"""NIC-46: Notion file-attachment mechanism for tailored CVs.

Implements Option A (block-level `file` object) from
docs/handoffs/NIC-46-product-planner-scope-validation.md section 6:

1. Upload a final tailored-CV PDF to Notion using the real 3-step
   `file_uploads` flow (POST /v1/file_uploads -> PUT bytes to the returned
   `upload_url` -> reference `file_upload_id` in a `file` block).
2. Locate the "Tailored CV" section on a job's Notion page (the
   `heading_2("\U0001F4C4 Tailored CV")` block produced by
   `build_job_page_children()` in scripts/notion_job_page_blocks.py, followed
   originally by a placeholder `callout` block).
3. Insert the new `file` block immediately after that heading, then
   archive/delete any pre-existing `callout`/`file` blocks that were in the
   section -- so exactly one artifact (the file) ever remains under the
   heading, satisfying OQ-5 / AC2 (final-version-only, no draft
   accumulation).

No Notion SDK dependency: uses only the Python standard library
(`urllib.request`) for HTTP, matching the dependency-light style of
`notion_job_page_blocks.py`. Unlike that module, THIS module DOES make real
network calls -- that is the point of NIC-46.

Requires the `NOTION_API_KEY` environment variable (same credential used
throughout this repo's Notion tooling). Never logs or prints the key itself.

Usage as a library:
    from notion_cv_attachment import attach_final_cv, TAILORED_CV_HEADING

    result = attach_final_cv(
        page_id="...",
        pdf_path="/path/to/tailored-cv.pdf",
        filename="Acme - Backend Engineer - CV.pdf",
    )
    # result["file_block_id"], result["removed_block_ids"], result["upload_id"]

CLI (for manual/scripted verification runs only -- never invoked against a
real production job card by name-matching; caller must supply an explicit,
already-known page_id):
    python3 scripts/notion_cv_attachment.py attach <page_id> <pdf_path> [filename]
    python3 scripts/notion_cv_attachment.py list-section <page_id>
"""
import json
import mimetypes
import os
import sys
import urllib.error
import urllib.request

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"

# Must exactly match the heading text produced by
# scripts/notion_job_page_blocks.py's build_job_page_children() (block index
# 6, 0-indexed, in the 14-block array).
TAILORED_CV_HEADING = "\U0001F4C4 Tailored CV"

# Block types that count as "old placeholder or previous file" content
# inside the Tailored CV section and must be removed once a new file block
# is inserted, so exactly one artifact remains (OQ-5 / AC2).
REPLACEABLE_BLOCK_TYPES = {"callout", "file", "paragraph"}


def _api_key() -> str:
    key = os.environ.get("NOTION_API_KEY")
    if not key:
        raise RuntimeError("NOTION_API_KEY environment variable is not set")
    return key


def _request(method: str, url: str, body: dict | None = None, extra_headers: dict | None = None) -> dict:
    """Low-level JSON HTTP request against the Notion API. Returns parsed JSON.

    Raises RuntimeError with the response body on non-2xx status so callers
    get real, unfiltered error detail (never swallowed/fabricated).
    """
    headers = {
        "Authorization": f"Bearer {_api_key()}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {url} -> HTTP {e.code}: {err_body}") from None


def _multipart_body(field_name: str, filename: str, data: bytes, content_type: str) -> tuple:
    """Builds a minimal multipart/form-data body (single file field) using
    only the standard library. Returns (body_bytes, boundary)."""
    boundary = "----NIC46NotionUploadBoundary7f3a9c"
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="{field_name}"; filename="{filename}"\r\n'.encode()
    )
    parts.append(f"Content-Type: {content_type}\r\n\r\n".encode())
    parts.append(data)
    parts.append(f"\r\n--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def _send_file_upload(upload_url: str, data: bytes, filename: str, content_type: str) -> tuple:
    """Step 2 (actual Notion API shape, confirmed live 2026-09-11): the
    `upload_url` returned by `POST /v1/file_uploads` is itself
    `POST /v1/file_uploads/{id}/send` -- it must be called with `POST`
    (not `PUT`), `multipart/form-data` (not a raw binary body), and the
    SAME `Authorization`/`Notion-Version` headers as every other Notion API
    call. (The generic 3-step description in the `notion` skill doc's
    curl example omits these two details -- a raw `PUT` with a binary body
    returns `400 invalid_request_url`, confirmed by real API evidence, see
    docs/ARCHITECTURE.md "NIC-46" section.)

    Returns (status_code, parsed_json_or_raw_text).
    """
    body, boundary = _multipart_body("file", filename, data, content_type)
    req = urllib.request.Request(upload_url, data=body, method="POST")
    req.add_header("Authorization", f"Bearer {_api_key()}")
    req.add_header("Notion-Version", NOTION_VERSION)
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    try:
        with urllib.request.urlopen(req) as resp:
            raw = resp.read()
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw.decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        raw = e.read()
        raise RuntimeError(
            f"POST {upload_url} -> HTTP {e.code}: {raw.decode('utf-8', errors='replace')}"
        ) from None


# ---------------------------------------------------------------------------
# Step (a): the 3-step file_uploads flow
# ---------------------------------------------------------------------------

def create_file_upload(filename: str, content_type: str = "application/pdf") -> dict:
    """Step 1: POST /v1/file_uploads. Returns the full JSON response
    (includes `id` and `upload_url`)."""
    body = {"filename": filename, "content_type": content_type}
    return _request("POST", f"{NOTION_API_BASE}/file_uploads", body=body)


def put_file_bytes(upload_url: str, file_path: str, filename: str, content_type: str = "application/pdf") -> tuple:
    """Step 2: send the file's bytes to the upload_url returned by step 1
    (a `POST .../send` multipart/form-data call -- see `_send_file_upload`
    docstring for why this isn't a plain `PUT`)."""
    with open(file_path, "rb") as f:
        data = f.read()
    return _send_file_upload(upload_url, data, filename, content_type)


def upload_pdf(pdf_path: str, filename: str) -> dict:
    """Runs steps 1+2 together. Returns the file_uploads create response
    (dict with at least `id`, `status`)."""
    create_resp = create_file_upload(filename=filename, content_type="application/pdf")
    upload_url = create_resp["upload_url"]
    put_status, put_resp = put_file_bytes(upload_url, pdf_path, filename, content_type="application/pdf")
    return {
        "create_response": create_resp,
        "put_status": put_status,
        "put_response": put_resp,
        "file_upload_id": create_resp["id"],
    }


# ---------------------------------------------------------------------------
# Step (b): locate the Tailored CV placeholder section for a given page_id
# ---------------------------------------------------------------------------

def get_block_children(block_id: str, page_size: int = 100) -> list:
    """GET /v1/blocks/{block_id}/children -- returns the full `results` list
    (single page is sufficient for the 14-block job-page structure; loops
    over `next_cursor` defensively in case content has grown)."""
    results = []
    cursor = None
    while True:
        url = f"{NOTION_API_BASE}/blocks/{block_id}/children?page_size={page_size}"
        if cursor:
            url += f"&start_cursor={cursor}"
        resp = _request("GET", url)
        results.extend(resp.get("results", []))
        if resp.get("has_more"):
            cursor = resp.get("next_cursor")
        else:
            break
    return results


def _block_plain_text(block: dict) -> str:
    btype = block.get("type")
    payload = block.get(btype, {})
    rich_text = payload.get("rich_text", [])
    return "".join(rt.get("plain_text", rt.get("text", {}).get("content", "")) for rt in rich_text)


def find_tailored_cv_section(page_id: str, heading_text: str = TAILORED_CV_HEADING) -> dict:
    """Locates the Tailored CV heading_2 block and the section-content
    blocks that follow it (everything up to, but excluding, the next
    `divider` or `heading_2` block).

    Returns:
        {
            "heading_block_id": str,
            "section_block_ids": [str, ...],       # all blocks in the section
            "replaceable_block_ids": [str, ...],   # callout/file/paragraph blocks to remove
            "all_blocks": [...],                    # full page block list (for evidence/logging)
        }

    Raises RuntimeError if the heading is not found (fail loudly rather than
    silently operate on the wrong section).
    """
    all_blocks = get_block_children(page_id)

    heading_index = None
    for i, block in enumerate(all_blocks):
        if block.get("type") == "heading_2" and _block_plain_text(block) == heading_text:
            heading_index = i
            break

    if heading_index is None:
        raise RuntimeError(
            f"Could not find heading_2({heading_text!r}) on page {page_id}; "
            "refusing to guess a section to modify."
        )

    heading_block = all_blocks[heading_index]
    section_blocks = []
    for block in all_blocks[heading_index + 1:]:
        if block.get("type") in ("divider", "heading_2"):
            break
        section_blocks.append(block)

    replaceable_ids = [b["id"] for b in section_blocks if b.get("type") in REPLACEABLE_BLOCK_TYPES]

    return {
        "heading_block_id": heading_block["id"],
        "section_block_ids": [b["id"] for b in section_blocks],
        "replaceable_block_ids": replaceable_ids,
        "all_blocks": all_blocks,
    }


# ---------------------------------------------------------------------------
# Step (c): insert new file block + remove old block(s) -- final-version-only
# ---------------------------------------------------------------------------

def _file_block(file_upload_id: str, filename: str) -> dict:
    return {
        "object": "block",
        "type": "file",
        "file": {
            "type": "file_upload",
            "file_upload": {"id": file_upload_id},
            "name": filename,
        },
    }


def insert_file_block_after(page_id: str, after_block_id: str, file_upload_id: str, filename: str) -> dict:
    """PATCH /v1/blocks/{page_id}/children with `after` set to the heading
    block id, so the new file block lands immediately below the heading."""
    body = {"children": [_file_block(file_upload_id, filename)], "after": after_block_id}
    return _request("PATCH", f"{NOTION_API_BASE}/blocks/{page_id}/children", body=body)


def archive_block(block_id: str) -> dict:
    """DELETE /v1/blocks/{block_id} -- Notion's block delete is an archive
    (sets `archived: true`), not a hard destroy."""
    return _request("DELETE", f"{NOTION_API_BASE}/blocks/{block_id}")


def attach_final_cv(page_id: str, pdf_path: str, filename: str, heading_text: str = TAILORED_CV_HEADING) -> dict:
    """End-to-end: locate section -> upload PDF -> insert file block ->
    remove any pre-existing callout/file blocks in that section, so exactly
    one artifact remains (OQ-5 / AC2). Idempotent/safe to call repeatedly on
    the same page_id to simulate a "revised CV" re-attach.

    `heading_text` defaults to the Tailored CV heading but the whole
    mechanism is heading-agnostic -- a future ticket (e.g. FR-E2 cover
    letter attachment) can reuse this function unmodified by passing
    heading_text="\u2709\ufe0f Cover Letter" (not exercised or verified for
    that heading by this ticket -- NIC-46's own AC/verification is scoped
    to the Tailored CV section only).

    Returns a dict with every intermediate response for evidence capture.
    """
    section_before = find_tailored_cv_section(page_id, heading_text=heading_text)
    old_replaceable_ids = section_before["replaceable_block_ids"]

    upload_result = upload_pdf(pdf_path, filename)

    insert_response = insert_file_block_after(
        page_id=page_id,
        after_block_id=section_before["heading_block_id"],
        file_upload_id=upload_result["file_upload_id"],
        filename=filename,
    )
    new_file_block_id = insert_response["results"][0]["id"]

    archive_responses = []
    for old_id in old_replaceable_ids:
        archive_responses.append({"block_id": old_id, "response": archive_block(old_id)})

    section_after = find_tailored_cv_section(page_id, heading_text=heading_text)

    return {
        "page_id": page_id,
        "heading_block_id": section_before["heading_block_id"],
        "old_replaceable_block_ids": old_replaceable_ids,
        "upload_result": upload_result,
        "insert_response": insert_response,
        "new_file_block_id": new_file_block_id,
        "archive_responses": archive_responses,
        "section_after": section_after,
    }


def archive_page(page_id: str) -> dict:
    """PATCH /v1/pages/{page_id} with {"archived": true} -- test-artifact
    cleanup (AC6). Not used for real job cards by this module's callers."""
    return _request("PATCH", f"{NOTION_API_BASE}/pages/{page_id}", body={"archived": True})


def get_page(page_id: str) -> dict:
    return _request("GET", f"{NOTION_API_BASE}/pages/{page_id}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main():
    if len(sys.argv) < 3:
        print(__doc__)
        sys.exit(1)

    cmd = sys.argv[1]
    page_id = sys.argv[2]

    if cmd == "attach":
        pdf_path = sys.argv[3]
        filename = sys.argv[4] if len(sys.argv) > 4 else os.path.basename(pdf_path)
        result = attach_final_cv(page_id, pdf_path, filename)
        print(json.dumps(result, indent=2, default=str))
    elif cmd == "list-section":
        section = find_tailored_cv_section(page_id)
        print(json.dumps({
            "heading_block_id": section["heading_block_id"],
            "section_block_ids": section["section_block_ids"],
            "replaceable_block_ids": section["replaceable_block_ids"],
        }, indent=2))
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    _main()

# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "mcp>=1.2.0,<2",
#   "google-api-python-client>=2.100.0",
#   "google-auth-oauthlib>=1.2.0",
#   "google-auth-httplib2>=0.2.0",
# ]
# ///
"""
Read-only Gmail MCP server for the recruiting tracker.

Scope is locked to `gmail.readonly` -- this server CANNOT send, delete, label,
or modify anything. It exposes three read tools; the `/inbox` skill drives them.

One-time setup (see tools/gmail-mcp/README.md for the full walkthrough):
  1. Create an OAuth client (Desktop app) in Google Cloud, download the JSON,
     save it as  ~/.gmail-mcp/gcp-oauth.keys.json
  2. Authorize once:   uv run --script tools/gmail-mcp/server.py auth
     (opens a browser, caches a token at ~/.gmail-mcp/token.json)
  3. Restart Claude Code so it picks up the server from .mcp.json

Secrets (client keys + token) live under ~/.gmail-mcp/ and never touch the repo.
"""

import base64
import re
import sys
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from mcp.server.fastmcp import FastMCP

# Read-only. Do not widen this scope. Sending/deleting is impossible with it.
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

CONFIG_DIR = Path.home() / ".gmail-mcp"
CREDS_FILE = CONFIG_DIR / "gcp-oauth.keys.json"
TOKEN_FILE = CONFIG_DIR / "token.json"

RECRUITING_LABEL = "Recruiting"
MAX_BODY_CHARS = 20000  # keep tool output within a sane context budget

mcp = FastMCP("gmail-recruiting")


# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #
def _load_credentials():
    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        TOKEN_FILE.write_text(creds.to_json())
        return creds
    return None


def _run_auth():
    if not CREDS_FILE.exists():
        sys.stderr.write(
            f"Missing OAuth client file: {CREDS_FILE}\n"
            "Create a Desktop-app OAuth client in Google Cloud, download the JSON, "
            "and save it at that path. See tools/gmail-mcp/README.md.\n"
        )
        sys.exit(1)
    flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
    creds = flow.run_local_server(port=0)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_text(creds.to_json())
    sys.stderr.write(f"Authorized. Token saved to {TOKEN_FILE}\n")


def _service():
    creds = _load_credentials()
    if not creds:
        raise RuntimeError(
            "Not authenticated. Run once from the project root:\n"
            "  uv run --script tools/gmail-mcp/server.py auth"
        )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


# --------------------------------------------------------------------------- #
# Parsing helpers
# --------------------------------------------------------------------------- #
def _decode(data: str) -> str:
    return base64.urlsafe_b64decode(data.encode("utf-8")).decode("utf-8", errors="replace")


def _strip_html(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    return re.sub(r"[ \t]*\n[ \t]*", "\n", re.sub(r"[ \t]+", " ", html)).strip()


def _extract_body(payload: dict) -> str:
    mime = payload.get("mimeType", "")
    body = payload.get("body", {})
    if mime == "text/plain" and body.get("data"):
        return _decode(body["data"])
    parts = payload.get("parts", []) or []
    for p in parts:
        if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
            return _decode(p["body"]["data"])
    for p in parts:
        found = _extract_body(p)
        if found:
            return found
    if mime == "text/html" and body.get("data"):
        return _strip_html(_decode(body["data"]))
    return ""


def _headers(msg: dict) -> dict:
    return {
        h["name"].lower(): h["value"]
        for h in msg.get("payload", {}).get("headers", [])
    }


def _list(query: str, max_results: int) -> list[dict]:
    svc = _service()
    resp = svc.users().messages().list(
        userId="me", q=query, maxResults=max_results
    ).execute()
    out = []
    for m in resp.get("messages", []):
        full = svc.users().messages().get(
            userId="me",
            id=m["id"],
            format="metadata",
            metadataHeaders=["From", "Subject", "Date"],
        ).execute()
        h = _headers(full)
        out.append({
            "id": m["id"],
            "threadId": full.get("threadId"),
            "from": h.get("from", ""),
            "subject": h.get("subject", ""),
            "date": h.get("date", ""),
            "snippet": full.get("snippet", ""),
        })
    return out


# --------------------------------------------------------------------------- #
# Tools (all read-only)
# --------------------------------------------------------------------------- #
@mcp.tool()
def list_recruiting(query: str = "", max_results: int = 25) -> list[dict]:
    """List messages in the "Recruiting" Gmail label, newest first (metadata only).

    Read-only. Returns id, threadId, from, subject, date, and a short snippet for
    each message. Pass an optional Gmail search fragment in `query` to narrow
    (e.g. "newer_than:14d", "is:unread", "from:lever.co"); it is ANDed with the
    label filter. Use read_message(id) to pull a full body.
    """
    q = f"label:{RECRUITING_LABEL}" + (f" {query}" if query.strip() else "")
    return _list(q, max_results)


@mcp.tool()
def read_message(message_id: str) -> dict:
    """Return the full plaintext body and headers of one message. Read-only.

    `body` is the decoded text/plain part (HTML stripped to text if that is all
    that exists), truncated to a sane length.
    """
    svc = _service()
    msg = svc.users().messages().get(
        userId="me", id=message_id, format="full"
    ).execute()
    h = _headers(msg)
    return {
        "id": msg["id"],
        "threadId": msg.get("threadId"),
        "from": h.get("from", ""),
        "to": h.get("to", ""),
        "cc": h.get("cc", ""),
        "subject": h.get("subject", ""),
        "date": h.get("date", ""),
        "labels": msg.get("labelIds", []),
        "body": _extract_body(msg.get("payload", {}))[:MAX_BODY_CHARS],
    }


@mcp.tool()
def search(query: str, max_results: int = 25) -> list[dict]:
    """Arbitrary read-only Gmail search across the whole mailbox (metadata only).

    Use for anything outside the Recruiting label (e.g. finding a recruiter's
    earlier thread: "from:jane@acme.com"). Returns the same shape as
    list_recruiting. Read-only: it can never send, label, or delete.
    """
    return _list(query, max_results)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "auth":
        _run_auth()
    else:
        mcp.run()

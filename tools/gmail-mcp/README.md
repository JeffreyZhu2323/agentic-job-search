# Gmail MCP server (read-only) — recruiting inbox

A tiny local MCP server that lets the `/inbox` skill read your recruiting email.
It is **read-only**: OAuth scope is locked to `gmail.readonly`, so the token
cannot send, delete, label, or modify anything. Secrets live under
`~/.gmail-mcp/` and never enter the repo.

Exposed tools: `list_recruiting`, `read_message`, `search` (all read-only).

## One-time setup

### 1. Create the OAuth client in Google Cloud
1. Go to <https://console.cloud.google.com/> → create a project (any name).
2. **APIs & Services → Library →** enable **Gmail API**.
3. **APIs & Services → OAuth consent screen:** User type **External**, fill the
   required fields, and under **Test users** add your own Gmail address. Leave it
   in **Testing** (no verification needed for personal use).
4. **APIs & Services → Credentials → Create credentials → OAuth client ID →**
   Application type **Desktop app**. Download the JSON.
5. Save that file as:
   ```
   ~/.gmail-mcp/gcp-oauth.keys.json
   ```
   (`mkdir -p ~/.gmail-mcp` first if needed.)

### 2. Authorize once (caches a token)
From the project root:
```bash
uv run --script tools/gmail-mcp/server.py auth
```
A browser opens; sign in and grant read-only access. A token is cached at
`~/.gmail-mcp/token.json`. The server refreshes it automatically after that.

### 3. Load the server in Claude Code
The server is registered in the project `.mcp.json`. **Restart Claude Code** so
it picks it up. On first project use Claude Code will ask you to approve the
project MCP server — approve `gmail-recruiting`. Verify with:
```bash
claude mcp list
```
`uv` installs the Python dependencies on first launch (cached afterward), so the
very first start may take a few seconds.

## Using it
Just run `/inbox` in Claude Code. The skill reads new messages in your
**Recruiting** Gmail label and proposes recruiting actions; nothing is sent.

## Notes
- Nothing here is secret; the OAuth client keys and token live in `~/.gmail-mcp/`
  (outside the repo). Do not move them into the project.
- To revoke access anytime: <https://myaccount.google.com/permissions>, or delete
  `~/.gmail-mcp/token.json` and re-run the `auth` step.

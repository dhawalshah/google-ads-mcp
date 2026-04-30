# Google Ads MCP

A Model Context Protocol (MCP) server for Google Ads. Connect Claude (or any MCP-compatible AI client) directly to your Google Ads accounts to query campaign performance, analyse keywords, inspect budgets, review search terms, and more — all in natural language.

The server speaks the [MCP authorization spec (2025-06-18)](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization), so it works as a remote connector anywhere Claude supports custom MCP servers — claude.ai (personal), Claude Desktop, and Claude Teams. Add **one URL**, click "Connect", sign in with Google, done. For a Teams plan, the org owner adds the URL once and each member individually authenticates on first use.

## What you can do

### Account Management
- List all accessible accounts including nested MCC sub-accounts
- Run custom GAQL queries against any account

### Campaign & Ad Analytics
- Get campaign, ad group, and individual ad performance metrics
- Keyword performance including quality scores and impression share
- Search terms report — see what searches triggered your ads
- Asset performance for responsive search ads (headlines, descriptions)

### Reporting
- Budget report with daily spend and month-to-date cost
- Geographic performance breakdown by country and location type
- Device performance split (mobile, desktop, tablet)
- Conversion actions — list all configured conversion tracking

### Keyword Research
- Generate keyword ideas with search volume, competition, and bid estimates

---

## How auth works

There are **two** modes. Pick one.

### Mode A — Local STDIO (one user, no server)
Use this if you only want it on your own machine. `setup_local_auth.py` runs the Google OAuth flow once and stores your token in `~/.config/google-ads-mcp/token.json`. Claude Desktop launches `server.py` as a subprocess. No Firestore, no Cloud Run, no public URL.

### Mode B — Remote HTTP server (Claude Teams, claude.ai, multi-user)
The MCP server is also an OAuth 2.1 authorization server. When Claude connects:

1. Claude discovers our metadata at `/.well-known/oauth-protected-resource` and `/.well-known/oauth-authorization-server`.
2. Claude registers itself via Dynamic Client Registration (`POST /oauth/register`).
3. Claude redirects the user to `/oauth/authorize`. We delegate identification to Google OAuth.
4. After Google login, we issue our **own** opaque bearer token to Claude — Google credentials never leave the server.
5. On each `/mcp` request Claude sends our bearer; we map it server-side to the right user's stored Google credentials and call the Google Ads APIs.

The `?user=email` query string from older versions is **gone** — there are no per-user URLs to copy around.

---

## Prerequisites

- Python 3.10+
- A Google Ads account with at least one accessible customer
- A [Google Cloud](https://console.cloud.google.com/) project

---

## Step 1 — Get Google Ads API access

1. Sign in to [Google Ads](https://ads.google.com/).
2. **Tools & Settings → Setup → API Center**.
3. Apply for a **Developer Token**:
   - A **Test token** is available immediately and works with test accounts.
   - A **Production token** requires approval (2–5 business days) and grants access to live accounts.
4. Note your **Developer Token** — you'll need it below.

> If you use a **Manager (MCC) account**, note the 10-digit Manager Account ID too. You'll use it as `manager_id` when querying sub-accounts.

---

## Step 2 — Set up Google Cloud

### 2a. Create a project and enable the Google Ads API
1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create or select a project and note the **Project ID**.
3. **APIs & Services → Library**, search for **Google Ads API**, click **Enable**.

### 2b. Create OAuth 2.0 credentials
1. **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**.
2. Application type: **Web application**.
3. Add **Authorized redirect URIs**:
   - `http://localhost:8080/auth/callback` *(local dev / setup_local_auth.py)*
   - `https://YOUR-CLOUD-RUN-URL/auth/callback` *(remote deployment — add after deploy)*
4. Click **Create**, then **Download JSON** → save as `client_secret.json` in the project root *(gitignored)*. You can also copy the Client ID / Client Secret straight into env vars.

### 2c. OAuth consent screen
1. **APIs & Services → OAuth consent screen**.
2. Choose **Internal** for a Google Workspace org (recommended for teams), or **External** for personal/individual use.
3. Add the scope: `https://www.googleapis.com/auth/adwords`.
4. If using **External** in Testing mode, add each user's email under **Test users**.

### 2d. Enable Firestore *(Mode B only)*
The server stores OAuth bearer tokens and per-user Google credentials in Firestore.
1. In Cloud Console, **Firestore → Create database → Native mode**, pick a region.
2. Grant the Cloud Run service account **Cloud Datastore User** role under **IAM & Admin → IAM**.

---

## Step 3 — Install

```bash
git clone https://github.com/dhawalshah/google-ads-mcp
cd google-ads-mcp
pip install -r requirements.txt
cp .env.example .env       # fill in values
```

---

## Step 4 — Mode A: Local STDIO

```bash
python setup_local_auth.py
```

A browser opens, you sign in with Google, the script writes `~/.config/google-ads-mcp/token.json`.

Then add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS):

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "python",
      "args": ["/absolute/path/to/google-ads-mcp/server.py"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "your_developer_token",
        "OAUTH_CONFIG_PATH": "/absolute/path/to/client_secret.json",
        "MCP_USER_EMAIL": "you@yourcompany.com"
      }
    }
  }
}
```

Restart Claude Desktop. You're done — skip the rest.

---

## Step 4 — Mode B: Remote HTTP server (Claude Teams / claude.ai)

### Deploy to Cloud Run

```bash
gcloud run deploy google-ads-mcp \
  --source . \
  --region YOUR_REGION \
  --project YOUR_PROJECT_ID \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_ADS_DEVELOPER_TOKEN=your_dev_token,GCP_PROJECT_ID=your-project-id,BASE_URL=https://YOUR-SERVICE-URL.run.app,GOOGLE_CLIENT_ID=...,GOOGLE_CLIENT_SECRET=...,ALLOWED_DOMAINS=yourcompany.com"
```

> **Recommended:** store `GOOGLE_CLIENT_SECRET` as a [Cloud Run secret](https://cloud.google.com/run/docs/configuring/services/secrets) rather than a plain env var.

After it's up, go back to **APIs & Services → Credentials → your OAuth client** and add the live callback URL:

```
https://YOUR-SERVICE-URL.run.app/auth/callback
```

### Connect from Claude

**Claude Teams (org owner adds it once for everyone):**
- Settings → Connectors → Add custom connector
- URL: `https://YOUR-SERVICE-URL.run.app/mcp`
- Each member clicks **Connect**, signs in with Google, done.

**claude.ai personal:**
- Settings → Connectors → Add custom connector
- URL: `https://YOUR-SERVICE-URL.run.app/mcp`

**Claude Desktop with a remote server:**
```json
{
  "mcpServers": {
    "google-ads": {
      "url": "https://YOUR-SERVICE-URL.run.app/mcp"
    }
  }
}
```
Claude Desktop will run the OAuth dance the first time you use it.

---

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Yes | Developer token from Google Ads → Tools & Settings → API Center. |
| `BASE_URL` | Mode B | Public URL of this service. Used for OAuth metadata and as the canonical resource URI tokens are bound to. |
| `GCP_PROJECT_ID` | Mode B | GCP project hosting Firestore. |
| `GOOGLE_CLIENT_ID` | Mode B† | Google OAuth client ID. |
| `GOOGLE_CLIENT_SECRET` | Mode B† | Google OAuth client secret. |
| `OAUTH_CONFIG_PATH` | Mode B† | Alternative to the two above: path to `client_secret.json`. |
| `GOOGLE_REDIRECT_URI` | No | Override the Google callback URL. Defaults to `${BASE_URL}/auth/callback`. |
| `ALLOWED_DOMAINS` | No | Comma-separated email domain allowlist (e.g. `acme.com,beta.com`). Empty = no restriction. |
| `MCP_USER_EMAIL` | Mode A | Your email — set in Claude Desktop config. |
| `PORT` | No | HTTP port (default `8080`). |
| `LOG_LEVEL` | No | Python log level (default `INFO`). |

† Set **either** `GOOGLE_CLIENT_ID` + `GOOGLE_CLIENT_SECRET` **or** `OAUTH_CONFIG_PATH`.

---

## Available Tools

| Tool | Description |
| --- | --- |
| `list_accounts` | List all accessible Google Ads accounts including nested MCC sub-accounts |
| `run_gaql` | Execute a raw GAQL query against any account |
| `run_keyword_planner` | Generate keyword ideas with search volume, competition, and bid estimates |
| `get_campaign_performance` | Impressions, clicks, cost, CTR, CPC, and conversions by campaign |
| `get_ad_group_performance` | Performance metrics broken down by ad group |
| `get_ad_performance` | Performance metrics for individual ads/creatives |
| `get_keyword_performance` | Keyword metrics including quality score and search impression share |
| `get_search_terms_report` | Actual searches that triggered your ads — find negatives and opportunities |
| `get_budget_report` | Campaign budgets and month-to-date spend |
| `get_geographic_performance` | Performance breakdown by country and location type |
| `get_device_performance` | Performance split by device: mobile, desktop, tablet |
| `get_conversion_actions` | List all conversion actions configured on the account |
| `get_asset_performance` | Responsive search ad headline/description performance labels |

---

## Example Prompts

```
Show me campaign performance for the last 30 days

Which keywords have the lowest quality scores?

What search terms triggered the most spend last month?

Show me the budget vs spend for all active campaigns

Which device gets the best conversion rate?

Generate keyword ideas for "project management software"

What countries are driving the most clicks?

Which ad headlines are performing best?
```

---

## OAuth endpoint reference (Mode B)

For developers who want to verify the implementation or write their own MCP client.

| Endpoint | Spec | Purpose |
| --- | --- | --- |
| `GET /.well-known/oauth-protected-resource` | RFC 9728 | Advertises the canonical resource URI and authorization server. |
| `GET /.well-known/oauth-authorization-server` | RFC 8414 | Authorization server metadata. |
| `POST /oauth/register` | RFC 7591 | Dynamic Client Registration. |
| `GET /oauth/authorize` | OAuth 2.1 | Starts the auth code flow with PKCE; redirects to Google. |
| `GET /auth/callback` | — | Google redirects here; we mint our authorization code and bounce back to the MCP client. |
| `POST /oauth/token` | OAuth 2.1 | Authorization code + refresh token grants. |

A `GET /mcp` without a valid bearer returns `401` with a `WWW-Authenticate: Bearer resource_metadata="…"` header pointing at the protected-resource metadata document, which is how a standards-compliant MCP client discovers the rest.

---

## Attribution

Forked from [gomarble-ai/google-ads-mcp-server](https://github.com/gomarble-ai/google-ads-mcp-server), with additions:
- Multi-user HTTP server mode acting as an OAuth 2.1 authorization server (DCR + PKCE + RFC 8707 resource indicators)
- Per-user OAuth token storage in Firestore
- Local STDIO mode with token stored in `~/.config/google-ads-mcp/token.json`
- `setup_local_auth.py` — one-shot local auth script
- Google Cloud Run deployment support
- Expanded read-only toolset (10 additional tools)

---

## License

MIT

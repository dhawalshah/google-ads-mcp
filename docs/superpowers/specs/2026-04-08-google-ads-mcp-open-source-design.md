# Google Ads MCP — Open Source Release Design

Date: 2026-04-08
Author: Dhawal Shah

## Overview

Prepare `google-ads-mcp` for public release at `github.com/dhawalshah/google-ads-mcp`. The project is forked from `gomarble-ai/google-ads-mcp-server` and extended with a multi-user server mode (FastAPI + Firestore token storage + Google Cloud Run). The release involves security cleanup, a richer read-only toolset, and a comprehensive README following the pattern established by `linkedin-ads-mcp`.

---

## 1. Security & Metadata Cleanup

### Files to change

- **`.gitignore`** — already updated to include `client_secret.json`, `*_token.json`, `google_ads_token.json`, `.DS_Store`
- **`.dockerignore`** — add `client_secret.json` so real credentials are never baked into Docker images
- **`client_secret.json`** — never committed; add `client_secret.json.example` as a template showing the expected JSON shape with placeholder values
- **`manifest.json`** — update author from GoMarble to Dhawal Shah (`github.com/dhawalshah`); update repo URL
- **`README_OAUTH.md`** — delete; content absorbed into new `README.md`

---

## 2. New Read-Only Tools

All new tools are implemented in `server.py` as `@mcp.tool` decorated functions. They wrap GAQL queries with named parameters so Claude can call them directly without writing raw GAQL.

| Tool | Resource queried | Key parameters |
|---|---|---|
| `get_campaign_performance` | `campaign` | `customer_id`, `date_range`, `manager_id` |
| `get_ad_group_performance` | `ad_group` | `customer_id`, `campaign_id` (optional), `date_range`, `manager_id` |
| `get_ad_performance` | `ad_group_ad` | `customer_id`, `campaign_id` (optional), `date_range`, `manager_id` |
| `get_keyword_performance` | `keyword_view` | `customer_id`, `campaign_id` (optional), `date_range`, `manager_id` |
| `get_search_terms_report` | `search_term_view` | `customer_id`, `campaign_id` (optional), `date_range`, `manager_id` |
| `get_budget_report` | `campaign_budget` | `customer_id`, `manager_id` |
| `get_geographic_performance` | `geographic_view` | `customer_id`, `date_range`, `manager_id` |
| `get_device_performance` | `campaign` + `segments.device` | `customer_id`, `date_range`, `manager_id` |
| `get_conversion_actions` | `conversion_action` | `customer_id`, `manager_id` |
| `get_asset_performance` | `asset_field_type_view` | `customer_id`, `date_range`, `manager_id` |

### Common parameter patterns

- `date_range`: string accepting GAQL date range keywords (`LAST_7_DAYS`, `LAST_30_DAYS`, `LAST_MONTH`, `THIS_MONTH`, `LAST_YEAR`) — defaults to `LAST_30_DAYS`
- `customer_id`: 10-digit string, passed through `format_customer_id()`
- `manager_id`: optional MCC login customer ID
- All tools return a dict with `results`, `total_rows`, and the query used

### API version

Verify current version via Context7 before implementation; update `API_VERSION` constant in `oauth/google_auth.py` if a newer stable version is available (currently `v23` in code, `v19` was latest as of mid-2025 — check at implementation time).

---

## 3. README Structure

Single `README.md` replacing `README_OAUTH.md`. Follows the same structure and tone as `linkedin-ads-mcp/README.md`.

```
# Google Ads MCP

One-line description.

## What you can do
  (bullets by category: Account Management, Campaign Analytics,
   Keyword Research, Reporting)

---

## Prerequisites

## Step 1: Get Google Ads API Access
  - Sign into Google Ads → Tools & Settings → API Center
  - Apply for Developer Token (test vs production)
  - Note: test token works with test accounts only

## Step 2: Set Up Google Cloud
  - Create/select GCP project
  - Enable Google Ads API (APIs & Services → Library)
  - Create OAuth 2.0 Client ID (Web Application type)
    - Add authorized redirect URI: https://YOUR-SERVICE-URL/auth/callback
    - Download JSON → save as client_secret.json locally (gitignored)
  - For team/Cloud Run mode only:
    - Enable Firestore (Native mode)
    - Create a service account with Firestore Editor role
    - Cloud Run uses the default compute service account — grant it Firestore access

## Step 3: Local Setup
  - git clone, pip install -r requirements.txt
  - Copy .env.example → .env and fill in values
  - Copy client_secret.json.example → client_secret.json and fill in values

## Step 4: Authenticate
  - Run locally: python main.py, then visit http://localhost:8080/auth/login
  - Sign in with your Google account
  - Tokens are stored in Firestore automatically

## Usage Options

  ### Option A: Local (Claude Desktop — single user)
    - Run: python server.py (STDIO mode)
    - Claude Desktop config snippet

  ### Option B: Team on Google Cloud Run
    - Deploy: gcloud run deploy command with env vars
    - Each team member visits https://YOUR-URL/auth/login once
    - Claude Desktop / claude.ai config snippet using the Cloud Run URL

## Environment Variables (table)

## Available Tools (table — all 13 tools)

## Example Prompts

## Attribution
  Forked from gomarble-ai/google-ads-mcp-server, with additions:
  multi-user HTTP server mode, Firestore token storage, Google Cloud Run deployment,
  and an expanded read-only toolset.

## License
  MIT
```

---

## 4. Files Changed / Created Summary

| File | Action |
|---|---|
| `.gitignore` | Updated (done) |
| `.dockerignore` | Add `client_secret.json` |
| `client_secret.json.example` | Create (template, no real values) |
| `.env.example` | Create (documents all env vars) |
| `manifest.json` | Update author, repo URL, tool list |
| `server.py` | Add 10 new `@mcp.tool` functions |
| `README.md` | Create (comprehensive, LinkedIn-style) |
| `README_OAUTH.md` | Delete |

---

## 5. Out of Scope

- Write operations (create/update/pause campaigns, ad groups, keywords) — deferred to a future release
- Code restructuring into separate tool modules — not needed at this scale
- Authentication changes — existing Firestore-based multi-user flow is correct and stays as-is

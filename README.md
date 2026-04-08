# Google Ads MCP

A Model Context Protocol (MCP) server for Google Ads. Connect Claude (or any MCP-compatible AI client) directly to your Google Ads accounts to query campaign performance, analyse keywords, inspect budgets, review search terms, and more — all in natural language.

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

## Prerequisites

- Python 3.11+
- A Google Ads account with at least one accessible customer
- A [Google Cloud](https://console.cloud.google.com/) project

---

## Step 1: Get Google Ads API Access

1. Sign in to [Google Ads](https://ads.google.com/)
2. Go to **Tools & Settings** → **Setup** → **API Center**
3. Apply for a **Developer Token**
   - A **Test token** is available immediately and works with test accounts
   - A **Production token** requires approval (2–5 business days) and grants access to live accounts
4. Note your **Developer Token** — you'll need it in Step 3

> If you use a **Manager (MCC) account**, note the 10-digit Manager Account ID too. You'll use it as `manager_id` when querying sub-accounts.

---

## Step 2: Set Up Google Cloud

### 2a. Create a project and enable the Google Ads API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select an existing one) and note the **Project ID**
3. Navigate to **APIs & Services → Library**, search for **Google Ads API**, and click **Enable**

### 2b. Create OAuth 2.0 credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth 2.0 Client IDs**
3. Choose **Web application**
4. Name it (e.g. `Google Ads MCP Server`)
5. Under **Authorized redirect URIs**, add:
   - `http://localhost:8080/auth/callback` (for local development)
   - `https://YOUR-CLOUD-RUN-URL/auth/callback` (for team/Cloud Run deployment — add after deploy)
6. Click **Create**, then **Download JSON**
7. Save the downloaded file as `client_secret.json` in your project root (this file is gitignored)

### 2c. Configure the OAuth consent screen

1. Go to **APIs & Services → OAuth consent screen**
2. Choose **Internal** if everyone who will use this is in your Google Workspace org (recommended for teams), or **External** for personal use
3. Fill in App Name (e.g. `Google Ads MCP`), support email, and developer contact
4. Add the scope: `https://www.googleapis.com/auth/adwords`
5. If using External and the app is in Testing mode, add each user's email under **Test users**

### 2d. Enable Firestore (team/Cloud Run mode only)

The server stores OAuth tokens in Firestore so each user authenticates once and the token persists across container restarts.

1. In Google Cloud Console, go to **Firestore**
2. Click **Create database**, choose **Native mode**, and select a region
3. The default Cloud Run service account needs Firestore access — grant it the **Cloud Datastore User** role under **IAM & Admin → IAM**

---

## Step 3: Local Setup

```bash
git clone https://github.com/dhawalshah/google-ads-mcp
cd google-ads-mcp
pip install -r requirements.txt
```

Copy and fill in your environment variables:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token_here
OAUTH_CONFIG_PATH=./client_secret.json
GCP_PROJECT_ID=your-gcp-project-id
ALLOWED_DOMAIN=yourcompany.com
BASE_URL=http://localhost:8080
SESSION_SECRET_KEY=change-me-to-a-long-random-string
```

Copy your OAuth credentials file (downloaded in Step 2b):

```bash
cp /path/to/downloaded-credentials.json client_secret.json
```

---

## Step 4: Authenticate

Start the server locally and complete the OAuth flow:

```bash
python main.py
```

Open your browser to `http://localhost:8080/auth/login` and sign in with your Google account. On success you'll see a confirmation page and your token is saved to Firestore.

> Each team member who wants to use the MCP completes this step once from their own browser.

---

## Usage Options

### Option A: Local (Claude Desktop — single user)

Run the server in STDIO mode for direct Claude Desktop integration:

```bash
python server.py
```

Add to your Claude Desktop config at `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "google-ads": {
      "command": "python",
      "args": ["/absolute/path/to/google-ads-mcp/server.py"],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "your_developer_token",
        "OAUTH_CONFIG_PATH": "/absolute/path/to/client_secret.json",
        "GCP_PROJECT_ID": "your-gcp-project-id",
        "ALLOWED_DOMAIN": "yourcompany.com",
        "BASE_URL": "http://localhost:8080",
        "SESSION_SECRET_KEY": "your-session-secret"
      }
    }
  }
}
```

Restart Claude Desktop.

---

### Option B: Team on Google Cloud Run

One deployment, always-on, each team member authenticates once via their browser.

**Prerequisites:** [Google Cloud CLI](https://cloud.google.com/sdk/docs/install) installed and authenticated (`gcloud auth login`).

**1. Deploy to Cloud Run:**

```bash
gcloud run deploy google-ads-mcp \
  --source . \
  --region YOUR_REGION \
  --project YOUR_PROJECT_ID \
  --platform managed \
  --port 8080 \
  --allow-unauthenticated \
  --set-env-vars "GOOGLE_ADS_DEVELOPER_TOKEN=your_dev_token,GCP_PROJECT_ID=your-project-id,ALLOWED_DOMAIN=yourcompany.com,SESSION_SECRET_KEY=your-secret-key,BASE_URL=https://YOUR-SERVICE-URL.run.app,OAUTH_CONFIG_PATH=/app/client_secret.json"
```

Replace `YOUR_REGION` (e.g. `asia-south1`), `YOUR_PROJECT_ID`, and `YOUR-SERVICE-URL`.

> **Recommended:** Store `client_secret.json` as a [Cloud Run secret](https://cloud.google.com/run/docs/configuring/services/secrets) rather than baking it into the image. Mount it at `/app/client_secret.json`.

**2. Add the Cloud Run callback URL to your OAuth credentials:**

Go back to Google Cloud Console → **APIs & Services → Credentials → your OAuth client** and add:

```
https://YOUR-SERVICE-URL.run.app/auth/callback
```

**3. Each team member authenticates once:**

```
https://YOUR-SERVICE-URL.run.app/auth/login
```

**4. Connect via Claude Desktop:**

```json
{
  "mcpServers": {
    "google-ads": {
      "url": "https://YOUR-SERVICE-URL.run.app/mcp?user=you@yourcompany.com"
    }
  }
}
```

---

## Environment Variables

| Variable | Required | Description |
| --- | --- | --- |
| `GOOGLE_ADS_DEVELOPER_TOKEN` | Yes | Developer token from Google Ads API Center |
| `OAUTH_CONFIG_PATH` | Yes | Path to `client_secret.json` |
| `GCP_PROJECT_ID` | Yes | GCP project ID for Firestore token storage |
| `ALLOWED_DOMAIN` | Yes | Only `@ALLOWED_DOMAIN` emails can authenticate (e.g. `yourcompany.com`) |
| `BASE_URL` | Yes | Public URL of this service (e.g. `https://your-service.run.app`) |
| `SESSION_SECRET_KEY` | Yes | Secret for signing session cookies — use a long random string |
| `PORT` | No | HTTP port (default: `8080`) |

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

## Attribution

Forked from [gomarble-ai/google-ads-mcp-server](https://github.com/gomarble-ai/google-ads-mcp-server), with additions:
- Multi-user HTTP server mode (FastAPI + session middleware)
- Per-user OAuth token storage in Firestore
- Google Cloud Run deployment support
- Expanded read-only toolset (10 additional tools)

---

## License

MIT

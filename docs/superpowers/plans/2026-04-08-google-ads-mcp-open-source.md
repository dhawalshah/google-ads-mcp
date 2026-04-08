# Google Ads MCP — Open Source Release Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare the google-ads-mcp project for public release at `github.com/dhawalshah/google-ads-mcp` with security cleanup, 10 new read-only tools, and a comprehensive README.

**Architecture:** All new tools are `@mcp.tool` functions added to `server.py`, each wrapping a GAQL query with named parameters. Auth and HTTP server wiring are unchanged. No new files needed in the Python source — just additions to `server.py` and documentation/config files.

**Tech Stack:** Python 3.11, FastMCP 2.x, FastAPI, Google Ads REST API (v19+), Firestore, Google Cloud Run, Docker

---

## Files Changed

| File | Action |
|---|---|
| `.gitignore` | Already updated |
| `.dockerignore` | Add `client_secret.json` |
| `client_secret.json.example` | Create — template with placeholder values |
| `.env.example` | Create — documents all required env vars |
| `manifest.json` | Update author, repo URL, tool list |
| `oauth/google_auth.py` | Update `API_VERSION` constant if needed |
| `server.py` | Add 10 new `@mcp.tool` functions |
| `README.md` | Create — comprehensive, LinkedIn-style |
| `README_OAUTH.md` | Delete |

---

## Task 1: Security & Metadata File Cleanup

**Files:**
- Modify: `.dockerignore`
- Create: `client_secret.json.example`
- Create: `.env.example`

- [ ] **Step 1: Add `client_secret.json` to `.dockerignore`**

Read the current `.dockerignore`:

```
# existing content
.env
.git
__pycache__
*.pyc
.DS_Store
```

Add to it so the final file reads:

```
.env
.git
__pycache__
*.pyc
.DS_Store
client_secret.json
*_token.json
```

- [ ] **Step 2: Create `client_secret.json.example`**

Create `/Users/dhawal/src/team-mcp/google-ads-mcp/client_secret.json.example`:

```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "project_id": "YOUR_GCP_PROJECT_ID",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR_CLIENT_SECRET",
    "redirect_uris": ["https://YOUR-CLOUD-RUN-URL/auth/callback"]
  }
}
```

- [ ] **Step 3: Create `.env.example`**

Create `/Users/dhawal/src/team-mcp/google-ads-mcp/.env.example`:

```bash
# Google Ads Developer Token
# Obtain from: Google Ads Console → Tools & Settings → API Center
GOOGLE_ADS_DEVELOPER_TOKEN=your_developer_token_here

# Path to your OAuth 2.0 client credentials JSON file
# Copy client_secret.json.example → client_secret.json and fill in values
OAUTH_CONFIG_PATH=./client_secret.json

# Your Google Cloud Project ID (used for Firestore token storage)
GCP_PROJECT_ID=your-gcp-project-id

# The Google Workspace domain allowed to log in (e.g. yourcompany.com)
# Only users with @ALLOWED_DOMAIN emails can authenticate
ALLOWED_DOMAIN=yourcompany.com

# Public URL of this service (used for OAuth redirect URIs)
# Local: http://localhost:8080
# Cloud Run: https://your-service-name-xxxx.run.app
BASE_URL=http://localhost:8080

# Session secret key — use a long random string in production
# Generate one: python -c "import secrets; print(secrets.token_hex(32))"
SESSION_SECRET_KEY=change-me-to-a-long-random-string
```

- [ ] **Step 4: Commit**

```bash
cd /Users/dhawal/src/team-mcp/google-ads-mcp
git add .dockerignore client_secret.json.example .env.example
git commit -m "chore: add example config files and harden dockerignore"
```

---

## Task 2: Check Google Ads API Version

**Files:**
- Modify: `oauth/google_auth.py` (line 7: `API_VERSION`)

- [ ] **Step 1: Check latest stable API version via Context7**

Use the `mcp__plugin_context7_context7__resolve-library-id` tool with query "Google Ads API", then fetch docs. Look for the latest stable version number in the REST API reference. As of early 2026, check whether anything newer than `v19` is stable and not sunset.

- [ ] **Step 2: Update `API_VERSION` in `oauth/google_auth.py` if needed**

Current value is `v23` at line 7. If Context7 confirms a newer stable version, update:

```python
API_VERSION = "v19"  # replace with confirmed latest stable version
```

Also update the two hardcoded version strings in `server.py`:
- `list_accounts` tool: `url = "https://googleads.googleapis.com/v23/customers:listAccessibleCustomers"`
- `run_keyword_planner` tool: `url = f"https://googleads.googleapis.com/v23/customers/{formatted_customer_id}:generateKeywordIdeas"`

Change both `v23` references to match `API_VERSION`. To avoid drift, import and use the constant:

At top of `server.py`, after the existing imports, add:
```python
from oauth.google_auth import format_customer_id, get_headers_with_auto_token, execute_gaql, API_VERSION
```

Then replace both hardcoded `v23` strings with `{API_VERSION}`:
```python
url = f"https://googleads.googleapis.com/{API_VERSION}/customers:listAccessibleCustomers"
url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{formatted_customer_id}:generateKeywordIdeas"
```

- [ ] **Step 3: Commit**

```bash
git add oauth/google_auth.py server.py
git commit -m "fix: use API_VERSION constant consistently, verify latest stable version"
```

---

## Task 3: Add Campaign & Ad Group Performance Tools

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Add `get_campaign_performance` tool**

Insert after the `run_keyword_planner` function (before the `@mcp.resource` decorator) in `server.py`:

```python
VALID_DATE_RANGES = [
    "TODAY", "YESTERDAY", "LAST_7_DAYS", "LAST_BUSINESS_WEEK",
    "THIS_MONTH", "LAST_MONTH", "LAST_14_DAYS", "LAST_30_DAYS",
    "THIS_QUARTER", "LAST_QUARTER", "THIS_YEAR", "LAST_YEAR"
]

@mcp.tool
def get_campaign_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get performance metrics for all campaigns in an account.

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        date_range: Date range for metrics. One of: TODAY, YESTERDAY, LAST_7_DAYS,
            LAST_BUSINESS_WEEK, THIS_MONTH, LAST_MONTH, LAST_14_DAYS, LAST_30_DAYS,
            THIS_QUARTER, LAST_QUARTER, THIS_YEAR, LAST_YEAR (default: LAST_30_DAYS)
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Campaign performance metrics including impressions, clicks, cost, CTR, CPC, conversions
    """
    if date_range.upper() not in VALID_DATE_RANGES:
        raise ValueError(f"Invalid date_range '{date_range}'. Must be one of: {', '.join(VALID_DATE_RANGES)}")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.conversions_value,
            metrics.ctr,
            metrics.average_cpc,
            metrics.all_conversions
        FROM campaign
        WHERE segments.date DURING {date_range.upper()}
            AND campaign.status != 'REMOVED'
        ORDER BY metrics.cost_micros DESC
    """

    if ctx:
        ctx.info(f"Fetching campaign performance for {customer_id} ({date_range})...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        campaign = row.get("campaign", {})
        metrics = row.get("metrics", {})
        formatted.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "status": campaign.get("status"),
            "channel_type": campaign.get("advertisingChannelType"),
            "impressions": metrics.get("impressions", 0),
            "clicks": metrics.get("clicks", 0),
            "cost_micros": metrics.get("costMicros", 0),
            "cost": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
            "conversions": round(float(metrics.get("conversions", 0)), 2),
            "conversions_value": round(float(metrics.get("conversionsValue", 0)), 2),
            "ctr": round(float(metrics.get("ctr", 0)) * 100, 2),
            "average_cpc_micros": metrics.get("averageCpc", 0),
            "average_cpc": round(int(metrics.get("averageCpc", 0)) / 1_000_000, 2),
            "all_conversions": round(float(metrics.get("allConversions", 0)), 2),
        })

    return {
        "campaigns": formatted,
        "total_campaigns": len(formatted),
        "date_range": date_range.upper(),
        "customer_id": customer_id,
    }
```

- [ ] **Step 2: Add `get_ad_group_performance` tool**

Insert immediately after `get_campaign_performance`:

```python
@mcp.tool
def get_ad_group_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    campaign_id: str = "",
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get performance metrics broken down by ad group.

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        date_range: Date range for metrics (default: LAST_30_DAYS). See get_campaign_performance for valid values.
        campaign_id: Optional — filter results to a specific campaign ID
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Ad group performance metrics including impressions, clicks, cost, CTR, CPC, conversions
    """
    if date_range.upper() not in VALID_DATE_RANGES:
        raise ValueError(f"Invalid date_range '{date_range}'. Must be one of: {', '.join(VALID_DATE_RANGES)}")

    campaign_filter = f"AND campaign.id = {campaign_id}" if campaign_id else ""

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            ad_group.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM ad_group
        WHERE segments.date DURING {date_range.upper()}
            AND ad_group.status != 'REMOVED'
            {campaign_filter}
        ORDER BY metrics.cost_micros DESC
    """

    if ctx:
        ctx.info(f"Fetching ad group performance for {customer_id} ({date_range})...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        campaign = row.get("campaign", {})
        ad_group = row.get("adGroup", {})
        metrics = row.get("metrics", {})
        formatted.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "ad_group_id": ad_group.get("id"),
            "ad_group_name": ad_group.get("name"),
            "status": ad_group.get("status"),
            "impressions": metrics.get("impressions", 0),
            "clicks": metrics.get("clicks", 0),
            "cost_micros": metrics.get("costMicros", 0),
            "cost": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
            "conversions": round(float(metrics.get("conversions", 0)), 2),
            "ctr": round(float(metrics.get("ctr", 0)) * 100, 2),
            "average_cpc": round(int(metrics.get("averageCpc", 0)) / 1_000_000, 2),
        })

    return {
        "ad_groups": formatted,
        "total_ad_groups": len(formatted),
        "date_range": date_range.upper(),
        "customer_id": customer_id,
    }
```

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat: add get_campaign_performance and get_ad_group_performance tools"
```

---

## Task 4: Add Ad & Keyword Performance Tools

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Add `get_ad_performance` tool**

Insert after `get_ad_group_performance`:

```python
@mcp.tool
def get_ad_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    campaign_id: str = "",
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get performance metrics for individual ads/creatives.

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        date_range: Date range for metrics (default: LAST_30_DAYS)
        campaign_id: Optional — filter results to a specific campaign ID
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Ad-level performance metrics including impressions, clicks, cost, CTR, conversions
    """
    if date_range.upper() not in VALID_DATE_RANGES:
        raise ValueError(f"Invalid date_range '{date_range}'. Must be one of: {', '.join(VALID_DATE_RANGES)}")

    campaign_filter = f"AND campaign.id = {campaign_id}" if campaign_id else ""

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            ad_group_ad.ad.id,
            ad_group_ad.ad.type,
            ad_group_ad.ad.final_urls,
            ad_group_ad.ad.name,
            ad_group_ad.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM ad_group_ad
        WHERE segments.date DURING {date_range.upper()}
            AND ad_group_ad.status != 'REMOVED'
            {campaign_filter}
        ORDER BY metrics.impressions DESC
    """

    if ctx:
        ctx.info(f"Fetching ad performance for {customer_id} ({date_range})...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        campaign = row.get("campaign", {})
        ad_group = row.get("adGroup", {})
        ad = row.get("adGroupAd", {}).get("ad", {})
        ad_group_ad = row.get("adGroupAd", {})
        metrics = row.get("metrics", {})
        formatted.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "ad_group_id": ad_group.get("id"),
            "ad_group_name": ad_group.get("name"),
            "ad_id": ad.get("id"),
            "ad_name": ad.get("name"),
            "ad_type": ad.get("type"),
            "final_urls": ad.get("finalUrls", []),
            "status": ad_group_ad.get("status"),
            "impressions": metrics.get("impressions", 0),
            "clicks": metrics.get("clicks", 0),
            "cost": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
            "conversions": round(float(metrics.get("conversions", 0)), 2),
            "ctr": round(float(metrics.get("ctr", 0)) * 100, 2),
            "average_cpc": round(int(metrics.get("averageCpc", 0)) / 1_000_000, 2),
        })

    return {
        "ads": formatted,
        "total_ads": len(formatted),
        "date_range": date_range.upper(),
        "customer_id": customer_id,
    }
```

- [ ] **Step 2: Add `get_keyword_performance` tool**

Insert after `get_ad_performance`:

```python
@mcp.tool
def get_keyword_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    campaign_id: str = "",
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get performance metrics for keywords including quality scores.

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        date_range: Date range for metrics (default: LAST_30_DAYS)
        campaign_id: Optional — filter results to a specific campaign ID
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Keyword performance metrics including impressions, clicks, CTR, quality score, match type
    """
    if date_range.upper() not in VALID_DATE_RANGES:
        raise ValueError(f"Invalid date_range '{date_range}'. Must be one of: {', '.join(VALID_DATE_RANGES)}")

    campaign_filter = f"AND campaign.id = {campaign_id}" if campaign_id else ""

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            ad_group_criterion.keyword.text,
            ad_group_criterion.keyword.match_type,
            ad_group_criterion.quality_info.quality_score,
            ad_group_criterion.quality_info.search_predicted_ctr,
            ad_group_criterion.quality_info.ad_relevance,
            ad_group_criterion.quality_info.landing_page_experience,
            ad_group_criterion.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc,
            metrics.search_impression_share
        FROM keyword_view
        WHERE segments.date DURING {date_range.upper()}
            AND ad_group_criterion.status != 'REMOVED'
            {campaign_filter}
        ORDER BY metrics.impressions DESC
    """

    if ctx:
        ctx.info(f"Fetching keyword performance for {customer_id} ({date_range})...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        campaign = row.get("campaign", {})
        ad_group = row.get("adGroup", {})
        criterion = row.get("adGroupCriterion", {})
        keyword = criterion.get("keyword", {})
        quality = criterion.get("qualityInfo", {})
        metrics = row.get("metrics", {})
        formatted.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "ad_group_id": ad_group.get("id"),
            "ad_group_name": ad_group.get("name"),
            "keyword": keyword.get("text"),
            "match_type": keyword.get("matchType"),
            "status": criterion.get("status"),
            "quality_score": quality.get("qualityScore"),
            "search_predicted_ctr": quality.get("searchPredictedCtr"),
            "ad_relevance": quality.get("adRelevance"),
            "landing_page_experience": quality.get("landingPageExperience"),
            "impressions": metrics.get("impressions", 0),
            "clicks": metrics.get("clicks", 0),
            "cost": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
            "conversions": round(float(metrics.get("conversions", 0)), 2),
            "ctr": round(float(metrics.get("ctr", 0)) * 100, 2),
            "average_cpc": round(int(metrics.get("averageCpc", 0)) / 1_000_000, 2),
            "search_impression_share": metrics.get("searchImpressionShare"),
        })

    return {
        "keywords": formatted,
        "total_keywords": len(formatted),
        "date_range": date_range.upper(),
        "customer_id": customer_id,
    }
```

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat: add get_ad_performance and get_keyword_performance tools"
```

---

## Task 5: Add Search Terms & Budget Tools

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Add `get_search_terms_report` tool**

Insert after `get_keyword_performance`:

```python
@mcp.tool
def get_search_terms_report(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    campaign_id: str = "",
    limit: int = 100,
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get the search terms report — actual searches that triggered your ads.

    Useful for finding new keyword opportunities and negative keyword candidates.

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        date_range: Date range for metrics (default: LAST_30_DAYS)
        campaign_id: Optional — filter to a specific campaign ID
        limit: Max number of search terms to return (default: 100, max: 500)
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Search terms with impressions, clicks, cost, CTR, conversions, and match status
    """
    if date_range.upper() not in VALID_DATE_RANGES:
        raise ValueError(f"Invalid date_range '{date_range}'. Must be one of: {', '.join(VALID_DATE_RANGES)}")

    limit = min(max(1, limit), 500)
    campaign_filter = f"AND campaign.id = {campaign_id}" if campaign_id else ""

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            search_term_view.search_term,
            search_term_view.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM search_term_view
        WHERE segments.date DURING {date_range.upper()}
            {campaign_filter}
        ORDER BY metrics.impressions DESC
        LIMIT {limit}
    """

    if ctx:
        ctx.info(f"Fetching search terms report for {customer_id} ({date_range})...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        campaign = row.get("campaign", {})
        ad_group = row.get("adGroup", {})
        stv = row.get("searchTermView", {})
        metrics = row.get("metrics", {})
        formatted.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "ad_group_id": ad_group.get("id"),
            "ad_group_name": ad_group.get("name"),
            "search_term": stv.get("searchTerm"),
            "status": stv.get("status"),
            "impressions": metrics.get("impressions", 0),
            "clicks": metrics.get("clicks", 0),
            "cost": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
            "conversions": round(float(metrics.get("conversions", 0)), 2),
            "ctr": round(float(metrics.get("ctr", 0)) * 100, 2),
            "average_cpc": round(int(metrics.get("averageCpc", 0)) / 1_000_000, 2),
        })

    return {
        "search_terms": formatted,
        "total_search_terms": len(formatted),
        "date_range": date_range.upper(),
        "customer_id": customer_id,
    }
```

- [ ] **Step 2: Add `get_budget_report` tool**

Insert after `get_search_terms_report`:

```python
@mcp.tool
def get_budget_report(
    customer_id: str,
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get campaign budgets and current spend for all active campaigns.

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Campaign budget details including daily budget, spend period, and current month cost
    """
    query = """
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            campaign.advertising_channel_type,
            campaign_budget.id,
            campaign_budget.name,
            campaign_budget.amount_micros,
            campaign_budget.period,
            campaign_budget.type,
            campaign_budget.total_amount_micros,
            metrics.cost_micros
        FROM campaign
        WHERE campaign.status != 'REMOVED'
            AND segments.date DURING THIS_MONTH
        ORDER BY campaign_budget.amount_micros DESC
    """

    if ctx:
        ctx.info(f"Fetching budget report for {customer_id}...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        campaign = row.get("campaign", {})
        budget = row.get("campaignBudget", {})
        metrics = row.get("metrics", {})
        amount_micros = int(budget.get("amountMicros", 0))
        total_micros = int(budget.get("totalAmountMicros", 0)) if budget.get("totalAmountMicros") else None
        formatted.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "status": campaign.get("status"),
            "channel_type": campaign.get("advertisingChannelType"),
            "budget_id": budget.get("id"),
            "budget_name": budget.get("name"),
            "daily_budget": round(amount_micros / 1_000_000, 2),
            "budget_period": budget.get("period"),
            "budget_type": budget.get("type"),
            "total_budget": round(total_micros / 1_000_000, 2) if total_micros else None,
            "month_to_date_cost": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
        })

    return {
        "budgets": formatted,
        "total_campaigns": len(formatted),
        "customer_id": customer_id,
    }
```

- [ ] **Step 3: Commit**

```bash
git add server.py
git commit -m "feat: add get_search_terms_report and get_budget_report tools"
```

---

## Task 6: Add Geographic, Device & Conversion Tools

**Files:**
- Modify: `server.py`

- [ ] **Step 1: Add `get_geographic_performance` tool**

Insert after `get_budget_report`:

```python
@mcp.tool
def get_geographic_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get performance metrics broken down by geographic location.

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        date_range: Date range for metrics (default: LAST_30_DAYS)
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Geographic performance data including country, location type, impressions, clicks, cost
    """
    if date_range.upper() not in VALID_DATE_RANGES:
        raise ValueError(f"Invalid date_range '{date_range}'. Must be one of: {', '.join(VALID_DATE_RANGES)}")

    query = f"""
        SELECT
            geographic_view.country_criterion_id,
            geographic_view.location_type,
            campaign.id,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr
        FROM geographic_view
        WHERE segments.date DURING {date_range.upper()}
        ORDER BY metrics.cost_micros DESC
        LIMIT 100
    """

    if ctx:
        ctx.info(f"Fetching geographic performance for {customer_id} ({date_range})...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        geo = row.get("geographicView", {})
        campaign = row.get("campaign", {})
        metrics = row.get("metrics", {})
        formatted.append({
            "country_criterion_id": geo.get("countryCriterionId"),
            "location_type": geo.get("locationType"),
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "impressions": metrics.get("impressions", 0),
            "clicks": metrics.get("clicks", 0),
            "cost": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
            "conversions": round(float(metrics.get("conversions", 0)), 2),
            "ctr": round(float(metrics.get("ctr", 0)) * 100, 2),
        })

    return {
        "locations": formatted,
        "total_locations": len(formatted),
        "date_range": date_range.upper(),
        "customer_id": customer_id,
    }
```

- [ ] **Step 2: Add `get_device_performance` tool**

Insert after `get_geographic_performance`:

```python
@mcp.tool
def get_device_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get performance metrics broken down by device type (mobile, desktop, tablet).

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        date_range: Date range for metrics (default: LAST_30_DAYS)
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Device-level performance split by MOBILE, DESKTOP, TABLET, and CONNECTED_TV
    """
    if date_range.upper() not in VALID_DATE_RANGES:
        raise ValueError(f"Invalid date_range '{date_range}'. Must be one of: {', '.join(VALID_DATE_RANGES)}")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            segments.device,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.ctr,
            metrics.average_cpc
        FROM campaign
        WHERE segments.date DURING {date_range.upper()}
            AND campaign.status != 'REMOVED'
        ORDER BY metrics.cost_micros DESC
    """

    if ctx:
        ctx.info(f"Fetching device performance for {customer_id} ({date_range})...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        campaign = row.get("campaign", {})
        segments = row.get("segments", {})
        metrics = row.get("metrics", {})
        formatted.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "device": segments.get("device"),
            "impressions": metrics.get("impressions", 0),
            "clicks": metrics.get("clicks", 0),
            "cost": round(int(metrics.get("costMicros", 0)) / 1_000_000, 2),
            "conversions": round(float(metrics.get("conversions", 0)), 2),
            "ctr": round(float(metrics.get("ctr", 0)) * 100, 2),
            "average_cpc": round(int(metrics.get("averageCpc", 0)) / 1_000_000, 2),
        })

    return {
        "device_performance": formatted,
        "total_rows": len(formatted),
        "date_range": date_range.upper(),
        "customer_id": customer_id,
    }
```

- [ ] **Step 3: Add `get_conversion_actions` tool**

Insert after `get_device_performance`:

```python
@mcp.tool
def get_conversion_actions(
    customer_id: str,
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """List all conversion actions configured on the account.

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        manager_id: Manager ID if access type is 'managed'

    Returns:
        All conversion actions with their type, category, counting method, and default value
    """
    query = """
        SELECT
            conversion_action.id,
            conversion_action.name,
            conversion_action.status,
            conversion_action.type,
            conversion_action.category,
            conversion_action.counting_type,
            conversion_action.value_settings.default_value,
            conversion_action.value_settings.always_use_default_value,
            conversion_action.include_in_conversions_metric
        FROM conversion_action
        WHERE conversion_action.status != 'REMOVED'
        ORDER BY conversion_action.name ASC
    """

    if ctx:
        ctx.info(f"Fetching conversion actions for {customer_id}...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        ca = row.get("conversionAction", {})
        value_settings = ca.get("valueSettings", {})
        formatted.append({
            "id": ca.get("id"),
            "name": ca.get("name"),
            "status": ca.get("status"),
            "type": ca.get("type"),
            "category": ca.get("category"),
            "counting_type": ca.get("countingType"),
            "default_value": value_settings.get("defaultValue"),
            "always_use_default_value": value_settings.get("alwaysUseDefaultValue"),
            "include_in_conversions_metric": ca.get("includeInConversionsMetric"),
        })

    return {
        "conversion_actions": formatted,
        "total_conversion_actions": len(formatted),
        "customer_id": customer_id,
    }
```

- [ ] **Step 4: Add `get_asset_performance` tool**

Insert after `get_conversion_actions`:

```python
@mcp.tool
def get_asset_performance(
    customer_id: str,
    date_range: str = "LAST_30_DAYS",
    manager_id: str = "",
    ctx: Context = None
) -> Dict[str, Any]:
    """Get performance of responsive search ad assets (headlines and descriptions).

    Shows which headlines and descriptions are performing best, including Google's
    performance label (BEST, GOOD, LOW, LEARNING, PENDING).

    Args:
        customer_id: The Google Ads customer ID (10 digits, no dashes)
        date_range: Date range for metrics (default: LAST_30_DAYS)
        manager_id: Manager ID if access type is 'managed'

    Returns:
        Asset performance with text content, field type, performance label, impressions, clicks
    """
    if date_range.upper() not in VALID_DATE_RANGES:
        raise ValueError(f"Invalid date_range '{date_range}'. Must be one of: {', '.join(VALID_DATE_RANGES)}")

    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            ad_group.id,
            ad_group.name,
            asset.id,
            asset.name,
            asset.text_asset.text,
            asset.type,
            ad_group_ad_asset_view.field_type,
            ad_group_ad_asset_view.performance_label,
            metrics.impressions,
            metrics.clicks
        FROM ad_group_ad_asset_view
        WHERE segments.date DURING {date_range.upper()}
            AND ad_group_ad_asset_view.field_type IN ('HEADLINE', 'DESCRIPTION')
        ORDER BY metrics.impressions DESC
        LIMIT 100
    """

    if ctx:
        ctx.info(f"Fetching asset performance for {customer_id} ({date_range})...")

    result = execute_gaql(customer_id, query, manager_id)

    formatted = []
    for row in result.get("results", []):
        campaign = row.get("campaign", {})
        ad_group = row.get("adGroup", {})
        asset = row.get("asset", {})
        asset_view = row.get("adGroupAdAssetView", {})
        metrics = row.get("metrics", {})
        formatted.append({
            "campaign_id": campaign.get("id"),
            "campaign_name": campaign.get("name"),
            "ad_group_id": ad_group.get("id"),
            "ad_group_name": ad_group.get("name"),
            "asset_id": asset.get("id"),
            "asset_text": asset.get("textAsset", {}).get("text"),
            "asset_type": asset.get("type"),
            "field_type": asset_view.get("fieldType"),
            "performance_label": asset_view.get("performanceLabel"),
            "impressions": metrics.get("impressions", 0),
            "clicks": metrics.get("clicks", 0),
        })

    return {
        "assets": formatted,
        "total_assets": len(formatted),
        "date_range": date_range.upper(),
        "customer_id": customer_id,
    }
```

- [ ] **Step 5: Commit**

```bash
git add server.py
git commit -m "feat: add geographic, device, conversion actions, and asset performance tools"
```

---

## Task 7: Update `manifest.json`

**Files:**
- Modify: `manifest.json`

- [ ] **Step 1: Rewrite `manifest.json`**

Replace the full contents of `manifest.json` with:

```json
{
  "dxt_version": "0.1",
  "name": "google-ads-mcp",
  "display_name": "Google Ads MCP Server",
  "version": "1.0.0",
  "description": "A Python MCP server for Google Ads API integration with OAuth 2.0 authentication",
  "long_description": "Comprehensive Google Ads management via MCP. Connect Claude to your Google Ads accounts for campaign analytics, keyword research, search terms analysis, budget reporting, geographic and device breakdowns, conversion tracking, and ad asset performance — all via natural language. Supports single-user local mode and multi-user team deployments on Google Cloud Run.",
  "author": {
    "name": "Dhawal Shah",
    "email": "",
    "url": "https://github.com/dhawalshah"
  },
  "server": {
    "type": "python",
    "entry_point": "server.py",
    "mcp_config": {
      "command": "python",
      "args": [
        "${__dirname}/server.py"
      ],
      "env": {
        "GOOGLE_ADS_DEVELOPER_TOKEN": "${user_config.google_ads_developer_token}",
        "OAUTH_CONFIG_PATH": "${user_config.oauth_config_path}",
        "GCP_PROJECT_ID": "${user_config.gcp_project_id}",
        "PYTHONPATH": "${__dirname}/lib"
      },
      "cwd": "${__dirname}"
    }
  },
  "tools": [
    { "name": "list_accounts", "description": "List all accessible Google Ads accounts including nested sub-accounts" },
    { "name": "run_gaql", "description": "Execute a raw Google Ads Query Language (GAQL) query" },
    { "name": "run_keyword_planner", "description": "Generate keyword ideas with search volume and competition metrics" },
    { "name": "get_campaign_performance", "description": "Get impressions, clicks, cost, CTR, CPC, and conversions by campaign" },
    { "name": "get_ad_group_performance", "description": "Get performance metrics broken down by ad group" },
    { "name": "get_ad_performance", "description": "Get performance metrics for individual ads/creatives" },
    { "name": "get_keyword_performance", "description": "Get keyword metrics including quality scores and search impression share" },
    { "name": "get_search_terms_report", "description": "See the actual searches that triggered your ads" },
    { "name": "get_budget_report", "description": "View campaign budgets and month-to-date spend" },
    { "name": "get_geographic_performance", "description": "Performance breakdown by country and location type" },
    { "name": "get_device_performance", "description": "Performance split by device: mobile, desktop, tablet" },
    { "name": "get_conversion_actions", "description": "List all conversion actions configured on the account" },
    { "name": "get_asset_performance", "description": "Responsive search ad asset performance with Google's performance labels" }
  ],
  "resources": [
    {
      "name": "gaql://reference",
      "description": "Google Ads Query Language (GAQL) reference documentation and examples"
    }
  ],
  "keywords": [
    "google", "ads", "marketing", "analytics", "advertising",
    "campaigns", "gaql", "keyword-research", "oauth", "ppc"
  ],
  "license": "MIT",
  "user_config": {
    "google_ads_developer_token": {
      "type": "string",
      "title": "Google Ads Developer Token",
      "description": "Your Google Ads API Developer Token (obtain from Google Ads Console → Tools & Settings → API Center)",
      "required": true,
      "sensitive": true
    },
    "oauth_config_path": {
      "type": "string",
      "title": "OAuth Config Path",
      "description": "Full path to your client_secret.json file downloaded from Google Cloud Console",
      "required": true,
      "sensitive": false
    },
    "gcp_project_id": {
      "type": "string",
      "title": "GCP Project ID",
      "description": "Your Google Cloud project ID (used for Firestore token storage in team mode)",
      "required": false,
      "sensitive": false
    }
  },
  "compatibility": {
    "claude_desktop": ">=0.10.0",
    "platforms": ["darwin", "win32", "linux"],
    "runtimes": {
      "python": ">=3.10.0 <4"
    }
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add manifest.json
git commit -m "chore: update manifest.json author to Dhawal Shah, add all 13 tools"
```

---

## Task 8: Write README.md

**Files:**
- Create: `README.md`
- Delete: `README_OAUTH.md`

- [ ] **Step 1: Delete `README_OAUTH.md`**

```bash
rm /Users/dhawal/src/team-mcp/google-ads-mcp/README_OAUTH.md
```

- [ ] **Step 2: Create `README.md`**

Create `/Users/dhawal/src/team-mcp/google-ads-mcp/README.md` with the following content:

````markdown
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

**1. Encode your `client_secret.json` for passing as an env var:**

```bash
# You'll paste client_secret.json contents as OAUTH_CONFIG_INLINE (see below)
# Or mount it via Cloud Run secrets — see note below
```

**2. Deploy to Cloud Run:**

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

**3. Add the Cloud Run callback URL to your OAuth credentials:**

Go back to Google Cloud Console → **APIs & Services → Credentials → your OAuth client** and add:
```
https://YOUR-SERVICE-URL.run.app/auth/callback
```

**4. Each team member authenticates once:**

```
https://YOUR-SERVICE-URL.run.app/auth/login
```

**5. Connect via Claude Desktop:**

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
|---|---|---|
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
|---|---|
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

```text
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
````

- [ ] **Step 3: Commit**

```bash
git add README.md
git rm README_OAUTH.md
git commit -m "docs: add comprehensive README, remove README_OAUTH.md"
```

---

## Task 9: Create GitHub Repo and Push

- [ ] **Step 1: Initialize git and set remote**

```bash
cd /Users/dhawal/src/team-mcp/google-ads-mcp
git init   # skip if already a git repo
git remote add origin https://github.com/dhawalshah/google-ads-mcp.git
```

- [ ] **Step 2: Create the repo on GitHub**

```bash
gh repo create dhawalshah/google-ads-mcp \
  --public \
  --description "Google Ads MCP server — connect Claude to Google Ads for campaign analytics, keyword research, budget reporting, and more" \
  --homepage "https://github.com/dhawalshah/google-ads-mcp"
```

- [ ] **Step 3: Push**

```bash
git push -u origin main
```

Verify at `https://github.com/dhawalshah/google-ads-mcp` that `client_secret.json` is absent and `.env` is absent.

---

## Self-Review

**Spec coverage:**
- Security cleanup (gitignore done, dockerignore, examples) → Task 1 ✓
- API version check → Task 2 ✓
- 10 new read-only tools → Tasks 3–6 ✓
- manifest.json update → Task 7 ✓
- README.md (LinkedIn-style) → Task 8 ✓
- GitHub repo creation → Task 9 ✓

**Placeholder scan:** No TBDs. All tool functions have full GAQL queries and complete response formatting. README content is fully written inline.

**Type consistency:** All tools follow the same signature pattern: `(customer_id, date_range, ..., manager_id, ctx)`. All use `execute_gaql()` from `oauth.google_auth`. `VALID_DATE_RANGES` is defined once before the first new tool and reused by all subsequent tools. `format_customer_id` is already imported in `server.py`.

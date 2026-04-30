"""
Google Ads OAuth Authentication.

Supports two modes:
- HTTP server mode (team/Cloud Run): reads token from Firestore using the
  session user set by auth middleware in main.py.
- Local STDIO mode (Claude Desktop single-user): reads token from
  ~/.config/google-ads-mcp/token.json; set MCP_USER_EMAIL in env.
"""

import json
import os
import pathlib
import contextvars
import logging
from typing import Dict

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/adwords"]
API_VERSION = "v21"
LOCAL_TOKEN_PATH = pathlib.Path.home() / ".config" / "google-ads-mcp" / "token.json"

# Set by auth middleware in main.py for every request
current_user_email: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_user_email", default=None
)


def format_customer_id(customer_id: str) -> str:
    """Format customer ID to 10 digits without dashes."""
    customer_id = str(customer_id)
    customer_id = customer_id.replace('"', "").replace("'", "")
    customer_id = "".join(c for c in customer_id if c.isdigit())
    return customer_id.zfill(10)


def _load_local_token() -> Credentials | None:
    """Load credentials from the local token file (~/.config/google-ads-mcp/token.json)."""
    if not LOCAL_TOKEN_PATH.exists():
        return None
    try:
        creds = Credentials.from_authorized_user_info(
            json.loads(LOCAL_TOKEN_PATH.read_text()), SCOPES
        )
    except Exception:
        logger.warning("Could not read local token file")
        return None

    if creds.valid:
        return creds

    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            LOCAL_TOKEN_PATH.write_text(creds.to_json())
            return creds
        except RefreshError:
            logger.warning("Local token refresh failed — re-run setup_local_auth.py")
            return None

    return None


def get_headers_with_auto_token() -> Dict[str, str]:
    """
    Get API headers using the current user's stored token.

    In HTTP server mode the email comes from the session ContextVar.
    In local STDIO mode it comes from MCP_USER_EMAIL and the token
    is read from ~/.config/google-ads-mcp/token.json.
    """
    email = current_user_email.get()

    if email:
        # HTTP server mode — load from Firestore
        from .firestore_tokens import load_token
        creds = load_token(email, SCOPES)
        if not creds:
            raise ValueError(
                f"No valid token for {email}. "
                "Reconnect this MCP server in your client to re-run the Google sign-in."
            )
    else:
        # Local STDIO mode — fall back to MCP_USER_EMAIL + local token file
        email = os.environ.get("MCP_USER_EMAIL")
        if not email:
            raise ValueError(
                "No authenticated user found. "
                "For local use: set MCP_USER_EMAIL in your Claude Desktop config and run setup_local_auth.py. "
                "For team server: reconnect from your MCP client to run the OAuth flow."
            )
        creds = _load_local_token()
        if not creds:
            raise ValueError(
                "No valid local token. Run setup_local_auth.py to authenticate."
            )

    developer_token = os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "")
    if not developer_token:
        raise ValueError("GOOGLE_ADS_DEVELOPER_TOKEN environment variable not set")

    return {
        "Authorization": f"Bearer {creds.token}",
        "Developer-Token": developer_token.strip('"').strip("'"),
        "Content-Type": "application/json",
    }


def execute_gaql(customer_id: str, query: str, manager_id: str = "") -> Dict:
    """Execute GAQL using the non-streaming search endpoint."""
    import requests

    headers = get_headers_with_auto_token()
    formatted_id = format_customer_id(customer_id)
    url = f"https://googleads.googleapis.com/{API_VERSION}/customers/{formatted_id}/googleAds:search"

    if manager_id:
        headers["login-customer-id"] = format_customer_id(manager_id)

    resp = requests.post(url, headers=headers, json={"query": query})

    if not resp.ok:
        raise Exception(f"GAQL error: {resp.status_code} {resp.reason} - {resp.text}")

    data = resp.json()
    results = data.get("results", [])
    return {"results": results, "query": query, "totalRows": len(results)}

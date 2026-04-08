"""
Google Ads OAuth Authentication - multi-user server version.

Instead of reading a local token file, this reads each user's token
from Firestore using the currently logged-in user's email.
"""

import os
import contextvars
import logging
from typing import Dict

from .firestore_tokens import load_token

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/adwords"]
API_VERSION = "v21"

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


def get_headers_with_auto_token() -> Dict[str, str]:
    """
    Get API headers using the current user's stored token.
    Raises an error if no user is logged in.
    """
    email = current_user_email.get()

    if not email:
        raise ValueError(
            "No authenticated user found. "
            "Please visit /auth/login to connect your Google account."
        )

    creds = load_token(email, SCOPES)

    if not creds:
        raise ValueError(
            f"No valid token for {email}. "
            "Please visit /auth/login to reconnect your Google account."
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

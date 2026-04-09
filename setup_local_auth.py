"""
One-time local authentication for Claude Desktop (STDIO) mode.

Run this once to save your Google OAuth token to:
  ~/.config/google-ads-mcp/token.json

After authenticating, add MCP_USER_EMAIL to your Claude Desktop config:

  {
    "mcpServers": {
      "google-ads": {
        "command": "python",
        "args": ["/path/to/google-ads-mcp/server.py"],
        "env": {
          "OAUTH_CONFIG_PATH": "/path/to/client_secret.json",
          "GOOGLE_ADS_DEVELOPER_TOKEN": "your_developer_token",
          "MCP_USER_EMAIL": "you@yourcompany.com"
        }
      }
    }
  }

Usage:
  python setup_local_auth.py
"""

import json
import os
import pathlib
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
from google_auth_oauthlib.flow import Flow

load_dotenv()

SCOPES = ["https://www.googleapis.com/auth/adwords"]
TOKEN_PATH = pathlib.Path.home() / ".config" / "google-ads-mcp" / "token.json"
REDIRECT_URI = "http://localhost:8888/callback"
CLIENT_CONFIG_PATH = os.environ.get("OAUTH_CONFIG_PATH", "client_secret.json")

auth_code = None
auth_error = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code, auth_error
        params = parse_qs(urlparse(self.path).query)
        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Authentication successful! You can close this tab.</h2>")
        else:
            auth_error = params.get("error", ["unknown"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"<h2>Authentication failed: {auth_error}</h2>".encode())

    def log_message(self, format, *args):
        pass  # suppress request logs


def main():
    if not os.path.exists(CLIENT_CONFIG_PATH):
        print(f"Error: OAuth config not found at '{CLIENT_CONFIG_PATH}'")
        print("Set OAUTH_CONFIG_PATH in your .env or pass the path directly.")
        return

    flow = Flow.from_client_secrets_file(
        CLIENT_CONFIG_PATH,
        scopes=SCOPES,
        redirect_uri=REDIRECT_URI,
    )

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        prompt="consent",
    )

    server = HTTPServer(("localhost", 8888), CallbackHandler)
    thread = threading.Thread(target=server.handle_request)
    thread.start()

    print("Opening browser for Google login...")
    webbrowser.open(auth_url)
    print(f"If the browser didn't open, visit:\n  {auth_url}\n")

    thread.join()

    if auth_error:
        print(f"Authentication failed: {auth_error}")
        return

    flow.fetch_token(code=auth_code)
    creds = flow.credentials

    TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_PATH.write_text(creds.to_json())

    print(f"\nToken saved to {TOKEN_PATH}")
    print("\nNext step — add this to your Claude Desktop config:")
    print(json.dumps({
        "mcpServers": {
            "google-ads": {
                "command": "python",
                "args": [str(pathlib.Path(__file__).parent / "server.py")],
                "env": {
                    "OAUTH_CONFIG_PATH": CLIENT_CONFIG_PATH,
                    "GOOGLE_ADS_DEVELOPER_TOKEN": os.environ.get("GOOGLE_ADS_DEVELOPER_TOKEN", "your_developer_token"),
                    "MCP_USER_EMAIL": "you@yourcompany.com",
                }
            }
        }
    }, indent=2))


if __name__ == "__main__":
    main()

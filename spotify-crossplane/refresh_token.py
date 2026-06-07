import os
import base64
import subprocess
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from dotenv import load_dotenv

load_dotenv()

REDIRECT_URI = "http://127.0.0.1:3000/callback"
SCOPES = "playlist-modify-private playlist-modify-public playlist-read-private user-library-read"

SECRET_NAMESPACE = "crossplane-system"
SECRET_NAME = "spotify-access-token"


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None:
        raise Exception(f"{name} not found in .env file")
    return value


CLIENT_ID = _require("CLIENT_ID")
CLIENT_SECRET = _require("CLIENT_SECRET")


def _basic_auth_header() -> str:
    basic = base64.b64encode(f"{CLIENT_ID}:{CLIENT_SECRET}".encode()).decode()
    return f"Basic {basic}"


def refresh_access_token(refresh_token: str) -> dict:
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
        },
    )

    response.raise_for_status()
    return response.json()

_received: dict = {}


class _CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        query = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(query)
        _received.update({k: v[0] for k, v in params.items()})
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"You can close this tab and return to the terminal.")

    def log_message(self, *_):
        pass


def _wait_for_code() -> str:
    server = HTTPServer(("127.0.0.1", 3000), _CallbackHandler)
    while "code" not in _received and "error" not in _received:
        server.handle_request()
    if "error" in _received:
        raise Exception(f"Authorization failed: {_received['error']}")
    return _received["code"]


def _exchange_code(code: str) -> dict:
    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": _basic_auth_header(),
            "Content-Type": "application/x-www-form-urlencoded",
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
        },
    )
    response.raise_for_status()
    return response.json()


def write_access_token_secret(access_token: str) -> None:
    # provider-http's ProviderConfig (credentials.source: Secret) uses the
    # raw value of the "authorization" key as the Authorization header, so it
    # must already contain the "Bearer " prefix. access_token is kept too for
    # debugging / manual curl calls.
    manifest = (
        "apiVersion: v1\n"
        "kind: Secret\n"
        "metadata:\n"
        f"  name: {SECRET_NAME}\n"
        f"  namespace: {SECRET_NAMESPACE}\n"
        "type: Opaque\n"
        "stringData:\n"
        f"  access_token: {access_token}\n"
        f"  authorization: Bearer {access_token}\n"
    )
    subprocess.run(
        ["kubectl", "apply", "-f", "-"],
        input=manifest,
        text=True,
        check=True,
    )


def bootstrap_refresh_token() -> dict:
    auth_url = "https://accounts.spotify.com/authorize?" + urllib.parse.urlencode(
        {
            "client_id": CLIENT_ID,
            "response_type": "code",
            "redirect_uri": REDIRECT_URI,
            "scope": SCOPES,
        }
    )
    print(f"Opening browser. If it doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)
    code = _wait_for_code()
    return _exchange_code(code)


if __name__ == "__main__":
    refresh_token = os.getenv("REFRESH_TOKEN")
    if refresh_token is None:
        tokens = bootstrap_refresh_token()
        print("\nAdd this line to your .env, then re-run the script:\n")
        print(f"REFRESH_TOKEN={tokens['refresh_token']}")
    else:
        tokens = refresh_access_token(refresh_token)
        write_access_token_secret(tokens["access_token"])
        print(f"access_token written to Secret {SECRET_NAMESPACE}/{SECRET_NAME}")

#!/usr/bin/env python3
"""One-time Google OAuth consent for chief-of-staff (run once per account).

Opens a browser, you grant Calendar + Gmail scopes, prints the refresh token
as a `setx` line to paste. Setup-time only — NOT part of the headless runtime.

Usage:
    python google-consent.py --label personal
Requires GOOGLE_OAUTH_CLIENT_ID + GOOGLE_OAUTH_CLIENT_SECRET in env,
or pass --client-secrets path/to/client_secret.json.
"""
import argparse
import os
import sys

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
    "https://www.googleapis.com/auth/gmail.readonly",
]


def client_config_from_env():
    """Build an installed-app client config from env vars, or None if unset."""
    cid = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    csec = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not (cid and csec):
        return None
    return {
        "installed": {
            "client_id": cid,
            "client_secret": csec,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def build_flow(client_secrets):
    if client_secrets:
        return InstalledAppFlow.from_client_secrets_file(client_secrets, SCOPES)
    cfg = client_config_from_env()
    if not cfg:
        sys.exit(
            "Set GOOGLE_OAUTH_CLIENT_ID + GOOGLE_OAUTH_CLIENT_SECRET, "
            "or pass --client-secrets path/to/client_secret.json"
        )
    return InstalledAppFlow.from_client_config(cfg, SCOPES)


def main():
    ap = argparse.ArgumentParser(description="One-time Google consent per account.")
    ap.add_argument("--label", required=True, help="account label, e.g. personal or work")
    ap.add_argument("--client-secrets", help="path to client_secret.json (else uses env vars)")
    args = ap.parse_args()

    flow = build_flow(args.client_secrets)
    # Loopback redirect (OOB is deprecated). prompt=consent + offline forces a refresh token.
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        sys.exit(
            "No refresh token returned. Revoke prior consent at "
            "https://myaccount.google.com/permissions and re-run."
        )

    label_raw = args.label.strip()
    label = label_raw.upper()
    print("\n=== consent OK ===")
    print(f'setx GOOGLE_REFRESH_TOKEN_{label} "{creds.refresh_token}"')
    print(
        f"# then: setx GOOGLE_EMAIL_{label} \"<the account email>\" and append "
        f"'{label_raw}' to GOOGLE_ACCOUNTS"
    )


if __name__ == "__main__":
    main()

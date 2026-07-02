#!/usr/bin/env python
"""Mint a Google access token for a service-account (DWD) label and print it to stdout.

Used by references/google-auth.md Step 0 when GOOGLE_AUTH_KIND_<LABEL>=service_account.
The SA impersonates GOOGLE_EMAIL_<LABEL> via domain-wide delegation.
Only the token goes to stdout (no trailing newline); all diagnostics go to stderr.
"""
import argparse
import os
import sys

# MUST exactly equal the scope set authorized for the SA in the Workspace Admin Console
# (DWD token mint is all-or-nothing). calendar.events is pre-authorized for Phase C writes.
SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]


def die(msg, code=1):
    sys.stderr.write(msg.rstrip() + "\n")
    sys.exit(code)


def main():
    ap = argparse.ArgumentParser(description="Mint a DWD service-account access token for a label.")
    ap.add_argument("--label", required=True, help="the GOOGLE_ACCOUNTS label (e.g. work)")
    label = ap.parse_args().label

    key_path = os.environ.get(f"GOOGLE_SA_KEY_PATH_{label}")
    subject = os.environ.get(f"GOOGLE_EMAIL_{label}")
    if not key_path:
        die(f"config: GOOGLE_SA_KEY_PATH_{label} is unset — set it to the service-account JSON key path.")
    if not os.path.isfile(key_path):
        die(f"config: GOOGLE_SA_KEY_PATH_{label} points at a missing file: {key_path}")
    if not subject:
        die(f"config: GOOGLE_EMAIL_{label} is unset — set it to the domain user to impersonate.")

    try:
        from google.oauth2 import service_account
        from google.auth.transport.requests import Request
    except ImportError as e:
        die(f"deps: {e} — pip install google-auth (declared in requirements.txt).")

    try:
        creds = service_account.Credentials.from_service_account_file(
            key_path, scopes=SCOPES,
        ).with_subject(subject)
        creds.refresh(Request())
    except Exception as e:
        domain = subject.split("@")[-1]
        die(
            f"dwd: token mint failed for {subject} ({label}): {e}\n"
            f"     verify the SA's numeric client-id + these scopes are authorized in the "
            f"{domain} Admin Console (Security > Access & data control > API controls > Domain-wide Delegation)."
        )

    sys.stdout.write(creds.token)  # token only, NO trailing newline


if __name__ == "__main__":
    main()

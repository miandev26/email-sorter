#!/usr/bin/env python3
"""Google Drive OAuth2 (desktop/manual) + list root files.

Usage:
  1) Put your OAuth client JSON at: ./client_secrets.json
     (download from Google Cloud Console → APIs & Services → Credentials → OAuth 2.0 Client IDs)

  2) Run:
       python3 tools/drive_oauth_list_root.py --scopes drive.metadata.readonly

     First run prints an authorization URL. Open it in a browser, approve, then paste the code.
     The script stores credentials in ./token.json (contains refresh token).

  3) It will list files in Drive root.

Security:
  - Keep token.json private (refresh token grants access).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Iterable


DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/drive.metadata.readonly",
]


def _scope_aliases(scopes: Iterable[str]) -> list[str]:
    out: list[str] = []
    for s in scopes:
        if s == "drive.metadata.readonly":
            out.append("https://www.googleapis.com/auth/drive.metadata.readonly")
        elif s == "drive.readonly":
            out.append("https://www.googleapis.com/auth/drive.readonly")
        else:
            out.append(s)
    return out


def load_credentials(scopes: list[str], client_secrets_path: Path, token_path: Path):
    # Import lazily so repo works even without deps.
    from google.auth.transport.requests import Request  # type: ignore
    from google.oauth2.credentials import Credentials  # type: ignore
    from google_auth_oauthlib.flow import InstalledAppFlow  # type: ignore

    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), scopes)

    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())

    if not creds or not creds.valid:
        if not client_secrets_path.exists():
            raise FileNotFoundError(
                f"Missing {client_secrets_path}. Download OAuth client JSON and place it there."
            )

        # Console flow: prints URL, user pastes code.
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), scopes=scopes)
        creds = flow.run_console()

    token_path.write_text(creds.to_json(), encoding="utf-8")
    return creds


def list_root_files(creds, page_size: int = 100):
    from googleapiclient.discovery import build  # type: ignore

    service = build("drive", "v3", credentials=creds)
    q = "'root' in parents and trashed=false"
    fields = "nextPageToken, files(id, name, mimeType, modifiedTime, size)"

    token = None
    all_files = []
    while True:
        resp = (
            service.files()
            .list(q=q, fields=fields, pageSize=page_size, pageToken=token, orderBy="folder,name")
            .execute()
        )
        files = resp.get("files", [])
        all_files.extend(files)
        token = resp.get("nextPageToken")
        if not token:
            break

    return all_files


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--client-secrets",
        default="client_secrets.json",
        help="Path to OAuth client JSON (downloaded from Google Cloud Console)",
    )
    ap.add_argument(
        "--token",
        default="token.json",
        help="Where to store OAuth tokens (contains refresh token)",
    )
    ap.add_argument(
        "--scopes",
        nargs="+",
        default=["drive.metadata.readonly"],
        help="Scopes (aliases: drive.metadata.readonly, drive.readonly)",
    )
    ap.add_argument("--page-size", type=int, default=100)

    args = ap.parse_args()
    scopes = _scope_aliases(args.scopes)

    client_path = Path(args.client_secrets)
    token_path = Path(args.token)

    # Safety: if user provided only a client secret string, we can't proceed.
    if client_path.exists():
        try:
            raw = json.loads(client_path.read_text(encoding="utf-8"))
            # sanity check
            if "installed" not in raw and "web" not in raw:
                print(
                    "client_secrets.json exists but does not look like a Google OAuth client file."
                )
        except Exception:
            pass

    creds = load_credentials(scopes, client_path, token_path)
    files = list_root_files(creds, page_size=args.page_size)

    if not files:
        print("(root is empty)")
        return 0

    for f in files:
        size = f.get("size", "")
        print(f"{f['name']}\t{f['mimeType']}\t{f['id']}\t{size}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

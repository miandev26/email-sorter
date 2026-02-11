from __future__ import annotations

import imaplib
import os
from dataclasses import dataclass
from email import message_from_bytes
from email.message import Message
from typing import Any, Iterable


@dataclass
class GmailConn:
    host: str
    user: str
    password: str
    ssl: bool = True


def connect(cfg: GmailConn) -> imaplib.IMAP4:
    if cfg.ssl:
        imap: imaplib.IMAP4 = imaplib.IMAP4_SSL(cfg.host)
    else:
        imap = imaplib.IMAP4(cfg.host)
    imap.login(cfg.user, cfg.password)
    return imap


def env_config() -> GmailConn:
    host = os.environ.get("GMAIL_IMAP_HOST", "imap.gmail.com")
    user = os.environ.get("GMAIL_ADDRESS")
    pw = os.environ.get("GMAIL_APP_PASSWORD")
    if not user or not pw:
        raise RuntimeError("Set env: GMAIL_ADDRESS and GMAIL_APP_PASSWORD")
    return GmailConn(host=host, user=user, password=pw)


def select_inbox(imap: imaplib.IMAP4, mailbox: str = "INBOX") -> None:
    typ, data = imap.select(mailbox)
    if typ != "OK":
        raise RuntimeError(f"Cannot select mailbox {mailbox}: {data}")


def search_uids(imap: imaplib.IMAP4, criteria: str = "UNSEEN") -> list[str]:
    typ, data = imap.uid("search", None, criteria)
    if typ != "OK":
        raise RuntimeError(f"search failed: {data}")
    if not data or not data[0]:
        return []
    return data[0].decode().split()


def fetch_message(imap: imaplib.IMAP4, uid: str) -> Message:
    typ, data = imap.uid("fetch", uid, "(RFC822)")
    if typ != "OK":
        raise RuntimeError(f"fetch failed for uid={uid}: {data}")
    raw = data[0][1]
    return message_from_bytes(raw)


def set_flags(imap: imaplib.IMAP4, uid: str, flags: Iterable[str], add: bool = True) -> None:
    op = "+FLAGS" if add else "-FLAGS"
    fl = " ".join(flags)
    typ, data = imap.uid("store", uid, op, f"({fl})")
    if typ != "OK":
        raise RuntimeError(f"store flags failed uid={uid}: {data}")


def move_to_mailbox(imap: imaplib.IMAP4, uid: str, dest_mailbox: str) -> None:
    # Gmail supports UID MOVE in most accounts; fallback to COPY + delete.
    try:
        typ, data = imap.uid("MOVE", uid, dest_mailbox)
        if typ == "OK":
            return
    except Exception:
        pass

    typ, data = imap.uid("COPY", uid, dest_mailbox)
    if typ != "OK":
        raise RuntimeError(f"copy failed uid={uid} -> {dest_mailbox}: {data}")
    set_flags(imap, uid, ["\\Deleted"], add=True)
    imap.expunge()


def list_mailboxes(imap: imaplib.IMAP4) -> list[str]:
    typ, data = imap.list()
    if typ != "OK":
        return []
    out: list[str] = []
    for line in data:
        if not line:
            continue
        s = line.decode(errors="ignore")
        # last token is mailbox name, may be quoted
        name = s.split()[-1].strip('"')
        out.append(name)
    return out


def apply_action(imap: imaplib.IMAP4, uid: str, action: Any) -> None:
    if not action or action == "none":
        return
    if isinstance(action, str):
        # allow shorthand like "mark_read"
        if action == "mark_read":
            set_flags(imap, uid, ["\\Seen"], add=True)
        return

    if isinstance(action, dict):
        if action.get("mark_read"):
            set_flags(imap, uid, ["\\Seen"], add=True)
        dest = action.get("move_to")
        if dest:
            move_to_mailbox(imap, uid, dest)
        return

    raise ValueError(f"Unsupported action: {action!r}")

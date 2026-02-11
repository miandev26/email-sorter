from __future__ import annotations

import argparse
import asyncio
import os
import sys
from email.message import Message

from emailsorter.rules import decide, load_config


def _print_decision(uid: str, msg: Message, provider: str, rule_name: str, importance: str, action) -> None:
    subj = msg.get("Subject", "")
    frm = msg.get("From", "")
    print(f"[{provider}] uid={uid} importance={importance} rule={rule_name} action={action} from={frm!r} subject={subj!r}")


def cmd_gmail(args: argparse.Namespace) -> int:
    from emailsorter.providers.gmail_imap import apply_action, connect, env_config, fetch_message, search_uids, select_inbox

    cfg = load_config(args.config)
    imap = connect(env_config())
    try:
        select_inbox(imap, args.mailbox)
        uids = search_uids(imap, args.criteria)
        print(f"[gmail] mailbox={args.mailbox} criteria={args.criteria!r} uids={len(uids)}")
        for uid in uids[: args.limit]:
            msg = fetch_message(imap, uid)
            d = decide(msg, cfg, provider="gmail")
            _print_decision(uid, msg, "gmail", d.rule_name, d.importance, d.action)
            if args.apply:
                apply_action(imap, uid, d.action)
        return 0
    finally:
        try:
            imap.logout()
        except Exception:
            pass


def cmd_proton(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    # Playwright is optional. If missing, tell user how to install.
    try:
        import playwright  # noqa: F401
    except Exception:
        print("Playwright not installed. Install: pip install playwright && playwright install chromium", file=sys.stderr)
        return 2

    from emailsorter.providers import proton_playwright

    os.environ.setdefault("PROTON_ADDRESS", "jaclaw95@proton.me")
    return asyncio.run(proton_playwright.run(config=cfg, dry_run=not args.apply, headed=args.headed)) or 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="emailsort")
    sub = p.add_subparsers(dest="cmd", required=True)

    g = sub.add_parser("gmail", help="Sort Gmail via IMAP")
    g.add_argument("--config", required=True)
    g.add_argument("--mailbox", default="INBOX")
    g.add_argument("--criteria", default="UNSEEN")
    g.add_argument("--limit", type=int, default=50)
    g.add_argument("--apply", action="store_true", help="Apply actions (default: dry-run)")
    g.set_defaults(func=cmd_gmail)

    pr = sub.add_parser("proton", help="Sort Proton via Playwright UI")
    pr.add_argument("--config", required=True)
    pr.add_argument("--headed", action="store_true")
    pr.add_argument("--apply", action="store_true")
    pr.set_defaults(func=cmd_proton)

    args = p.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())

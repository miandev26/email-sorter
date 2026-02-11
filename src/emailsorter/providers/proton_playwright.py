from __future__ import annotations

import os
import re
from dataclasses import dataclass
from typing import Any


@dataclass
class ProtonCreds:
    address: str
    password: str


def env_creds() -> ProtonCreds:
    addr = os.environ.get("PROTON_ADDRESS")
    pw = os.environ.get("PROTON_PASSWORD")
    if not addr or not pw:
        raise RuntimeError("Set env: PROTON_ADDRESS and PROTON_PASSWORD")
    return ProtonCreds(address=addr, password=pw)


async def run(*, config: dict[str, Any], dry_run: bool, headed: bool) -> None:
    """Best-effort Proton Mail sorting via Playwright.

    This module intentionally avoids importing playwright unless used.

    Steps:
      - open mail.proton.me
      - login
      - for first N messages in Inbox: open, read headers, decide rule, optionally move.

    Proton UI changes often; selectors may require adjustment.
    """

    from playwright.async_api import async_playwright  # type: ignore

    creds = env_creds()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not headed)
        page = await browser.new_page()

        await page.goto("https://mail.proton.me", wait_until="domcontentloaded")

        # Login screen
        await page.get_by_label("Email or username").fill(creds.address)
        await page.get_by_label("Password").fill(creds.password)
        await page.get_by_role("button", name="Sign in").click()

        # Wait for mailbox
        await page.wait_for_url(re.compile(r".*mail\.proton\.me.*"), timeout=120_000)
        await page.wait_for_timeout(5_000)

        # Note: UI structure differs per account; snapshotting is helpful.
        # We process top messages in the list.
        rows = page.locator("[data-testid='message-list'] [data-testid='message-row']")
        count = await rows.count()
        max_n = min(count, 25)

        from emailsorter.rules import decide

        for i in range(max_n):
            row = rows.nth(i)
            await row.click()
            await page.wait_for_timeout(500)

            # Try to read From/Subject from header area
            subject = await page.locator("[data-testid='message-subject']").inner_text()
            from_text = await page.locator("[data-testid='message-header-from']").inner_text()

            # Create a minimal pseudo message dict for decision engine
            # (We don't have raw RFC822 without Bridge.)
            class Pseudo:
                def __init__(self, subject: str, from_text: str):
                    self._s = subject
                    self._f = from_text

                def get(self, k: str, default: str = ""):
                    if k.lower() == "subject":
                        return self._s
                    if k.lower() == "from":
                        return self._f
                    return default

                def is_multipart(self):
                    return False

            msg = Pseudo(subject, from_text)  # type: ignore
            d = decide(msg, config, provider="proton")

            print(f"[proton] {i+1}/{max_n} subject={subject!r} from={from_text!r} -> {d.importance} via {d.rule_name}")

            if dry_run or not d.action or d.action == "none":
                continue
            if isinstance(d.action, dict) and d.action.get("move_to"):
                folder = d.action["move_to"]
                # open move-to dialog
                await page.get_by_role("button", name="Move to").click()
                await page.get_by_role("menuitem", name=folder).click()
                await page.wait_for_timeout(400)

        await browser.close()

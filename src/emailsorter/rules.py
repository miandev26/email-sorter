from __future__ import annotations

import json
import re
from dataclasses import dataclass
from email.message import Message
from pathlib import Path
from typing import Any, Iterable


IMPORTANCE_ORDER = {"low": 0, "normal": 1, "high": 2}


@dataclass
class Action:
    # provider-specific actions
    gmail: dict[str, Any] | str | None = None
    proton: dict[str, Any] | str | None = None


@dataclass
class Decision:
    rule_name: str
    importance: str
    action: dict[str, Any] | str | None
    reason: str


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s or "").strip().lower()


def _extract_from(msg: Message) -> tuple[str, str]:
    # returns (display, address)
    raw = msg.get("From", "")
    # very small parser; fallback to raw
    m = re.search(r"<([^>]+)>", raw)
    if m:
        addr = m.group(1)
        display = raw.replace(m.group(0), "").strip(' "')
        return display, addr
    return "", raw.strip()


def _domain(addr: str) -> str:
    addr = addr.strip().lower()
    if "@" in addr:
        return addr.split("@", 1)[1]
    return ""


def load_config(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    data = json.loads(p.read_text(encoding="utf-8"))
    if "rules" not in data or not isinstance(data["rules"], list):
        raise ValueError("config must contain a list: rules")
    return data


def _header_exists(msg: Message, names: Iterable[str]) -> bool:
    for n in names:
        if msg.get(n) is not None:
            return True
    return False


def _keywords_in(text: str, keywords: Iterable[str]) -> bool:
    t = _norm(text)
    return any(_norm(k) in t for k in keywords)


def match_rule(msg: Message, rule: dict[str, Any]) -> tuple[bool, str]:
    match = rule.get("match", {}) or {}
    display, addr = _extract_from(msg)
    dom = _domain(addr)

    # from_addresses
    from_addrs = [a.lower() for a in match.get("from_addresses", [])]
    if from_addrs and addr.lower() not in from_addrs:
        return False, "from_addresses"

    # from_domains
    from_domains = [d.lower() for d in match.get("from_domains", [])]
    if from_domains and dom not in from_domains:
        return False, "from_domains"

    # subject_keywords
    subject_keywords = match.get("subject_keywords", [])
    if subject_keywords and not _keywords_in(msg.get("Subject", ""), subject_keywords):
        return False, "subject_keywords"

    # body_keywords (best-effort; only for text/plain parts)
    body_keywords = match.get("body_keywords", [])
    if body_keywords:
        body_texts: list[str] = []
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        body_texts.append(part.get_payload(decode=True).decode(errors="ignore"))
                    except Exception:
                        continue
        else:
            try:
                body_texts.append(msg.get_payload(decode=True).decode(errors="ignore"))
            except Exception:
                body_texts.append(str(msg.get_payload()))
        if not any(_keywords_in(t, body_keywords) for t in body_texts):
            return False, "body_keywords"

    # header_exists
    header_exists = match.get("header_exists", [])
    if header_exists and not _header_exists(msg, header_exists):
        return False, "header_exists"

    # header_regex
    header_regex = match.get("header_regex", {})
    if header_regex:
        for header, pattern in header_regex.items():
            val = msg.get(header, "")
            if not re.search(pattern, val or "", flags=re.IGNORECASE):
                return False, f"header_regex:{header}"

    return True, "matched"


def decide(msg: Message, config: dict[str, Any], provider: str) -> Decision:
    defaults = config.get("defaults", {}) or {}
    default_importance = defaults.get("importance", "normal")
    default_action = (defaults.get("action", {}) or {}).get(provider)

    best: Decision | None = None

    for rule in config.get("rules", []):
        ok, why = match_rule(msg, rule)
        if not ok:
            continue
        importance = (rule.get("set", {}) or {}).get("importance", default_importance)
        action = (rule.get("action", {}) or {}).get(provider, default_action)
        d = Decision(
            rule_name=rule.get("name", "unnamed"),
            importance=importance,
            action=action,
            reason=why,
        )
        if best is None:
            best = d
        else:
            if IMPORTANCE_ORDER.get(d.importance, 1) > IMPORTANCE_ORDER.get(best.importance, 1):
                best = d

    if best is None:
        return Decision(rule_name="default", importance=default_importance, action=default_action, reason="no_rule")
    return best

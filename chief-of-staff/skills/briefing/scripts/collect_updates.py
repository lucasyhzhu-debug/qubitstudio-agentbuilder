#!/usr/bin/env python3
"""Collect candidate news items for the briefing skill's optional Interests module.

This is a DETERMINISTIC, stdlib-only candidate collector. It reads the owner's
standing-interest list, fetches RSS / Atom / Google-News feeds for each interest,
filters to a recency window, and emits a flat list of candidates as JSON on
stdout. It ONLY collects: it never summarises, scores, ranks, dedups across
interests, or invents facts, dates, or quotes. The model (running the briefing
skill) does the source choice, relevance ranking, cross-source dedup, and
synthesis on top of these candidates.

Design constraints (see references/interest-beats.md and ../SKILL.md Step 5a):
  * No third-party dependencies. Stdlib only (urllib, xml.etree, json, argparse,
    datetime, html, re, email.utils) so it runs unchanged under `claude -p` on
    Windows (`python`) or elsewhere (`python3`).
  * Off by default: if the interests file is absent, emit
    {"interests_found": 0, ...} and exit 0 — the module stays silent.
  * Degrade gracefully: any fetch/parse error for a single feed is recorded in
    `unreachable` and the run continues. A bad feed never crashes the whole run.
  * No vault path is baked in. The interests file path is passed as an argument;
    `{{VAULT_PATH}}` is a placeholder that is NOT substituted inside a .py file,
    so callers must resolve it themselves and pass the concrete path.

Interface:
    python collect_updates.py --interests <path> [--window-hours 24]
                              [--max-per-interest 5] [--timeout 15]
                              [--no-google-news]

Output (JSON object on stdout):
    {
      "generated_at": "<ISO8601 UTC>",
      "window_hours": 24,
      "interests_found": <int>,
      "interests": [{"interest", "priority", "feeds", "angle"}, ...],
      "candidates": [{"interest", "title", "url", "source", "published"}, ...],
      "unreachable": [{"interest", "url", "error"}, ...]
    }

Origin: RSS/Atom parsing and the Google-News query builder are adapted from the
MIT-licensed `daily-interest-brief` skill by Nick Pinidiya
(github.com/Nicegarrry/claude-skills). MIT notice retained below.

    MIT License. Copyright (c) 2026 Nick Pinidiya.
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction... (full text: repo root LICENSE / the
    QubitStudio CHANGELOG provenance entry).

Security note: this parses untrusted feed XML with xml.etree.ElementTree, which
is subject to entity-expansion ("billion laughs") attacks. Only pass --interests
files and feed: URLs you trust, and treat every emitted candidate as material to
verify, never as ground truth.
"""

from __future__ import annotations

import argparse
import email.utils
import html
import json
import math
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


# A neutral, honest User-Agent. Some feed hosts reject empty/blank UAs.
USER_AGENT = "cos-briefing-interests/1.0 (+https://github.com/Nicegarrry/claude-skills)"


# --------------------------------------------------------------------------- #
# interests.md parsing
# --------------------------------------------------------------------------- #
#
# Item-17 canonical format (one interest per bullet, inline hints):
#
#     # Interests
#     - AI regulation — angle: policy impact for founders — feed:https://x/rss [priority]
#     - Formula 1 — angle: driver-market moves
#
# We ALSO tolerate the sibling `daily-interest-brief` shape (one interest per
# `##` heading with `angle:` / `feeds:` continuation lines) so the two skills can
# share the same meta/chief-of-staff/interests.md without one silently blanking
# the other:
#
#     ## AI regulation
#     angle: policy impact for founders
#     feeds: https://x/rss
#
# A lone top-level `#` title (e.g. "# Interests") is treated as a title, not an
# interest.

_BULLET_RE = re.compile(r"^[-*+]\s+(.*)$")
_HEADING_RE = re.compile(r"^(#{2,6})\s+(.*)$")          # ## .. ###### (not a lone #)
_CONT_RE = re.compile(r"^(angle|feeds?|feed)\s*:\s*(.+)$", re.IGNORECASE)
# Hint segments on a bullet are separated by an em/en dash or a `--` run.
_HINT_DELIM_RE = re.compile(r"\s+(?:—|–|--|;)\s+")
_FEED_TOKEN_RE = re.compile(r"feed:\s*(\S+)", re.IGNORECASE)
_PRIORITY_RE = re.compile(r"\[priority\]", re.IGNORECASE)
_URLISH_RE = re.compile(r"^https?://", re.IGNORECASE)


def _parse_bullet(content: str) -> dict[str, Any]:
    """Parse one inline-hint bullet into {interest, priority, feeds, angle}."""
    priority = bool(_PRIORITY_RE.search(content))
    content = _PRIORITY_RE.sub("", content).strip()

    feeds: list[str] = []
    angle_parts: list[str] = []

    # Split "interest — hint — hint" into segments; first segment is the interest.
    segments = _HINT_DELIM_RE.split(content)
    interest = segments[0].strip() if segments else content.strip()
    for seg in segments[1:]:
        seg = seg.strip()
        if not seg:
            continue
        feed_match = _FEED_TOKEN_RE.search(seg)
        if feed_match:
            feeds.append(feed_match.group(1).strip().rstrip(".,;"))
            continue
        if _URLISH_RE.match(seg):  # bare URL hint, no "feed:" prefix
            feeds.append(seg.rstrip(".,;"))
            continue
        # otherwise treat as angle text (strip a leading "angle:" label)
        angle_parts.append(re.sub(r"^angle:\s*", "", seg, flags=re.IGNORECASE))

    # A `feed:` token could also sit inside the interest segment itself.
    inline_feed = _FEED_TOKEN_RE.search(interest)
    if inline_feed:
        feeds.append(inline_feed.group(1).strip().rstrip(".,;"))
        interest = interest[: inline_feed.start()].strip(" —–-;")

    return {
        "interest": interest.strip(),
        "priority": priority,
        "feeds": feeds,
        "angle": " ".join(angle_parts).strip(),
    }


def parse_interests(path: str) -> list[dict[str, Any]]:
    """Parse interests.md into a list of interest dicts.

    Missing/unreadable file -> [] (caller reports interests_found: 0). Supports
    both the bullet form and the `##`-heading form (see module notes above).
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            lines = handle.read().splitlines()
    except (FileNotFoundError, IsADirectoryError, OSError):
        return []

    interests: list[dict[str, Any]] = []
    current: Optional[dict[str, Any]] = None  # a heading-form interest accepting continuations

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("<!--"):
            current = None
            continue

        bullet = _BULLET_RE.match(line)
        heading = _HEADING_RE.match(line)

        if bullet:
            # A bullet is a self-contained interest; it closes any open heading.
            current = None
            parsed = _parse_bullet(bullet.group(1))
            if parsed["interest"]:
                interests.append(parsed)
            continue

        if heading:
            title = heading.group(2).strip()
            parsed = _parse_bullet(title)  # reuse: heading can carry inline [priority]/feed:
            if parsed["interest"]:
                interests.append(parsed)
                current = parsed  # subsequent angle:/feeds: lines attach here
            else:
                current = None
            continue

        # Continuation line (angle: / feeds: / feed:) under a heading-form interest.
        cont = _CONT_RE.match(line)
        if cont and current is not None:
            key = cont.group(1).lower()
            val = cont.group(2).strip()
            if key.startswith("feed"):
                # `feeds:` may list several whitespace/comma-separated URLs.
                for token in re.split(r"[,\s]+", val):
                    token = token.strip().rstrip(".,;")
                    if _URLISH_RE.match(token):
                        current["feeds"].append(token)
            elif key == "angle":
                current["angle"] = (current["angle"] + " " + val).strip()
            continue

        # Any other prose line does not open/extend an interest.
        current = None

    return interests


# --------------------------------------------------------------------------- #
# feed fetching + RSS/Atom parsing
# --------------------------------------------------------------------------- #

def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)  # strip any inline HTML tags
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_date(value: str) -> Optional[str]:
    """Normalise an RSS pubDate / Atom updated string to ISO8601 UTC, or None."""
    if not value:
        return None
    try:  # RFC 822 (RSS pubDate), e.g. "Tue, 08 Jul 2026 10:00:00 GMT"
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:  # ISO8601 (Atom), e.g. "2026-07-08T10:00:00Z"
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        return None


def fetch_url(url: str, timeout: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def ns_name(tag: str) -> str:
    """Strip any XML namespace from a tag name and lowercase it."""
    return tag.split("}", 1)[-1].lower()


def child_text(parent: ET.Element, *names: str) -> str:
    wanted = {name.lower() for name in names}
    for child in list(parent):
        if ns_name(child.tag) in wanted and child.text:
            return clean_text(child.text)
    return ""


def child_link(parent: ET.Element) -> str:
    for child in list(parent):
        if ns_name(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        rel = child.attrib.get("rel", "alternate")
        if href and rel == "alternate":
            return href
        if child.text:
            return clean_text(child.text)
    return ""


def source_name(parent: ET.Element, fallback: str) -> str:
    for child in list(parent):
        if ns_name(child.tag) == "source":
            if child.text:
                return clean_text(child.text)
            title = child.find("./{*}title")
            if title is not None and title.text:
                return clean_text(title.text)
    return fallback


def parse_feed(raw: bytes, fallback_source: str) -> list[dict[str, Any]]:
    """Parse RSS <item> or Atom <entry> nodes into {title,url,source,published}."""
    root = ET.fromstring(raw)  # may raise ET.ParseError on malformed XML — caller guards
    items: list[dict[str, Any]] = []

    rss_items = root.findall(".//item")
    if rss_items:
        for item in rss_items:
            title = child_text(item, "title")
            link = child_link(item) or child_text(item, "guid")
            published = parse_date(child_text(item, "pubDate", "published", "updated"))
            if title and link:
                items.append(
                    {
                        "title": title,
                        "url": link,
                        "source": source_name(item, fallback_source),
                        "published": published,
                    }
                )
        return items

    for entry in root.findall(".//{*}entry"):  # Atom
        title = child_text(entry, "title")
        link = child_link(entry)
        published = parse_date(child_text(entry, "published", "updated"))
        if title and link:
            items.append(
                {
                    "title": title,
                    "url": link,
                    "source": source_name(entry, fallback_source),
                    "published": published,
                }
            )
    return items


# --------------------------------------------------------------------------- #
# candidate collection
# --------------------------------------------------------------------------- #

def google_news_url(query: str, window_hours: int, locale: str, region: str) -> str:
    """Build a Google News RSS search URL for an interest with a recency clause.

    Google News honours a `when:` operator; it takes hour granularity for short
    windows and day granularity otherwise. We add the coarse clause here and then
    filter precisely against the window cutoff after parsing.
    """
    language = locale.split("-")[0] if "-" in locale else locale
    ceid = f"{region}:{language}"
    if window_hours <= 0:
        clause = ""
    elif window_hours < 24:
        clause = f" when:{window_hours}h"
    else:
        clause = f" when:{max(1, math.ceil(window_hours / 24))}d"
    return (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode(
            {"q": f"{query}{clause}", "hl": locale, "gl": region, "ceid": ceid}
        )
    )


def within_window(item: dict[str, Any], cutoff: Optional[datetime]) -> bool:
    """Keep items newer than cutoff. Items with no parseable date are KEPT
    (undated is not a reason to drop a candidate — the model verifies)."""
    if cutoff is None or not item.get("published"):
        return True
    try:
        return datetime.fromisoformat(item["published"]) >= cutoff
    except Exception:
        return True


def dedup(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Drop obvious duplicates within a single interest by url then title."""
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        title_key = re.sub(r"\W+", "", item["title"].lower())[:80]
        key = item["url"] or title_key
        if key in seen or title_key in seen:
            continue
        seen.add(key)
        seen.add(title_key)
        unique.append(item)
    return unique


def collect_for_interest(
    interest: dict[str, Any],
    window_hours: int,
    max_per_interest: int,
    timeout: int,
    use_google_news: bool,
    locale: str,
    region: str,
    cutoff: Optional[datetime],
    candidates: list[dict[str, Any]],
    unreachable: list[dict[str, Any]],
) -> None:
    """Fetch every feed for one interest, appending results to the shared lists.

    A `feed:` hint, when present, is authoritative — we do NOT also hit Google
    News for that interest. Only when no feed is given do we fall back to a
    Google-News query built from the interest text.
    """
    name = interest["interest"]
    feeds: list[tuple[str, str]] = []
    for url in interest.get("feeds", []):
        feeds.append((url, urllib.parse.urlsplit(url).netloc or "RSS"))
    if not feeds and use_google_news:
        feeds.append((google_news_url(name, window_hours, locale, region), "Google News"))

    gathered: list[dict[str, Any]] = []
    for feed_url, fallback in feeds:
        try:
            raw = fetch_url(feed_url, timeout)
            for item in parse_feed(raw, fallback):
                if within_window(item, cutoff):
                    gathered.append(item)
        except Exception as exc:  # network error, HTTP error, XML parse error, ...
            # Skip THIS feed and keep going; never crash the whole run.
            unreachable.append({"interest": name, "url": feed_url, "error": str(exc)})

    gathered = dedup(gathered)
    # Newest first; undated items sort last.
    gathered.sort(key=lambda it: it.get("published") or "", reverse=True)
    for item in gathered[: max(0, max_per_interest)]:
        candidates.append(
            {
                "interest": name,
                "title": item["title"],
                "url": item["url"],
                "source": item["source"],
                "published": item.get("published"),
            }
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--interests",
        required=True,
        help="Path to interests.md (resolve {{VAULT_PATH}} yourself; not baked in).",
    )
    parser.add_argument("--window-hours", type=int, default=24, help="Recency window (default 24h).")
    parser.add_argument(
        "--max-per-interest", type=int, default=5, help="Cap candidates per interest (default 5)."
    )
    parser.add_argument("--timeout", type=int, default=15, help="Per-feed HTTP timeout in seconds.")
    parser.add_argument("--locale", default="en-US", help="Google News locale, e.g. en-US.")
    parser.add_argument("--region", default="US", help="Google News region, e.g. US.")
    parser.add_argument(
        "--no-google-news",
        action="store_true",
        help="Never fall back to Google News; use only explicit feed: URLs.",
    )
    args = parser.parse_args()

    interests = parse_interests(args.interests)
    cutoff = (
        datetime.now(timezone.utc) - timedelta(hours=args.window_hours)
        if args.window_hours > 0
        else None
    )

    candidates: list[dict[str, Any]] = []
    unreachable: list[dict[str, Any]] = []
    for interest in interests:
        collect_for_interest(
            interest,
            window_hours=args.window_hours,
            max_per_interest=args.max_per_interest,
            timeout=args.timeout,
            use_google_news=not args.no_google_news,
            locale=args.locale,
            region=args.region,
            cutoff=cutoff,
            candidates=candidates,
            unreachable=unreachable,
        )

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": args.window_hours,
        "interests_found": len(interests),
        # Lightweight metadata so the model can pick the top-3 (priority first).
        "interests": [
            {
                "interest": it["interest"],
                "priority": it.get("priority", False),
                "feeds": it.get("feeds", []),
                "angle": it.get("angle", ""),
            }
            for it in interests
        ],
        "candidates": candidates,
        "unreachable": unreachable,
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    # Always exit 0: an absent file or an unreachable feed is a graceful "off",
    # not an error. Only an unexpected crash (guarded above) would differ.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

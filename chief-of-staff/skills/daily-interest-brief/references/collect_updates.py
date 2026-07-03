#!/usr/bin/env python3
"""Collect recent RSS/Atom items for a morning-brief topic.

No third-party dependencies. The script is intentionally small so agents can run
it in ordinary Python environments (stdlib only; `python` on Windows, `python3`
elsewhere).

Origin: adapted from the MIT-licensed `daily-interest-brief` skill by Nick
Pinidiya (github.com/Nicegarrry/claude-skills). MIT notice retained below.

    MIT License. Copyright (c) 2026 Nick Pinidiya.
    Permission is hereby granted, free of charge, to any person obtaining a copy
    of this software and associated documentation files (the "Software"), to deal
    in the Software without restriction... (full text: repo root LICENSE / the
    QubitStudio CHANGELOG provenance entry).

Security note: this parses untrusted feed XML with the Python stdlib
(xml.etree.ElementTree), which is subject to entity-expansion ("billion laughs")
attacks. Only pass --feed URLs you trust, and treat all output as candidate
material to verify, never as ground truth.
"""

from __future__ import annotations

import argparse
import email.utils
import hashlib
import html
import json
import re
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


USER_AGENT = "daily-interest-brief/1.0 (+https://github.com/Nicegarrry/claude-skills)"


def text_of(node: Optional[ET.Element], default: str = "") -> str:
    if node is None or node.text is None:
        return default
    return clean_text(node.text)


def clean_text(value: str) -> str:
    value = html.unescape(value)
    value = re.sub(r"<[^>]+>", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def parse_date(value: str) -> Optional[str]:
    if not value:
        return None
    try:
        parsed = email.utils.parsedate_to_datetime(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).isoformat()
    except Exception:
        pass
    try:
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


def ns_name(name: str) -> str:
    return name.split("}", 1)[-1].lower()


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


def parse_feed(raw: bytes, feed_url: str, fallback_source: str) -> list[dict[str, Any]]:
    root = ET.fromstring(raw)
    items: list[dict[str, Any]] = []

    rss_items = root.findall(".//item")
    if rss_items:
        for item in rss_items:
            title = child_text(item, "title")
            link = child_link(item) or child_text(item, "guid")
            published = parse_date(child_text(item, "pubDate", "published", "updated"))
            summary = child_text(item, "description", "summary", "content")
            source = source_name(item, fallback_source)
            if title and link:
                items.append(item_record(title, link, source, feed_url, published, summary))
        return items

    for entry in root.findall(".//{*}entry"):
        title = child_text(entry, "title")
        link = child_link(entry)
        published = parse_date(child_text(entry, "published", "updated"))
        summary = child_text(entry, "summary", "content")
        source = source_name(entry, fallback_source)
        if title and link:
            items.append(item_record(title, link, source, feed_url, published, summary))
    return items


def item_record(
    title: str,
    url: str,
    source: str,
    feed_url: str,
    published_at: Optional[str],
    summary: str,
) -> dict[str, Any]:
    canonical = canonicalize_url(url)
    digest = hashlib.sha1((canonical or title.lower()).encode("utf-8")).hexdigest()[:16]
    return {
        "id": digest,
        "title": title,
        "url": url,
        "source": source,
        "feed_url": feed_url,
        "published_at": published_at,
        "summary": summary,
    }


def canonicalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parsed.query, keep_blank_values=True)
    filtered = [
        (key, value)
        for key, value in query
        if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid"}
    ]
    return urllib.parse.urlunsplit(
        (
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip("/"),
            urllib.parse.urlencode(filtered),
            "",
        )
    )


def google_news_url(query: str, days: int, locale: str, region: str) -> str:
    language = locale.split("-")[0] if "-" in locale else locale
    ceid = f"{region}:{language}"
    q = f"{query} when:{days}d" if days > 0 else query
    return (
        "https://news.google.com/rss/search?"
        + urllib.parse.urlencode({"q": q, "hl": locale, "gl": region, "ceid": ceid})
    )


def recent_enough(item: dict[str, Any], cutoff: Optional[datetime]) -> bool:
    if cutoff is None or not item.get("published_at"):
        return True
    try:
        published = datetime.fromisoformat(item["published_at"])
    except Exception:
        return True
    return published >= cutoff


def dedup(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for item in items:
        key = canonicalize_url(item["url"]) or re.sub(r"\W+", "", item["title"].lower())
        title_key = re.sub(r"\W+", "", item["title"].lower())[:80]
        combined = key or title_key
        if combined in seen or title_key in seen:
            continue
        seen.add(combined)
        seen.add(title_key)
        unique.append(item)
    return unique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", help="Topic or interest to brief")
    parser.add_argument("--feed", action="append", default=[], help="Additional RSS/Atom feed URL")
    parser.add_argument("--query", action="append", default=[], help="Additional Google News query")
    parser.add_argument("--days", type=int, default=1, help="Recency window for Google News and filtering")
    parser.add_argument("--max-items", type=int, default=25, help="Maximum items to emit")
    parser.add_argument("--locale", default="en-US", help="Google News locale, e.g. en-US")
    parser.add_argument("--region", default="US", help="Google News region, e.g. US")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP timeout in seconds")
    parser.add_argument("--no-google-news", action="store_true", help="Skip Google News RSS")
    args = parser.parse_args()

    feeds: list[tuple[str, str]] = []
    queries = [args.topic, *args.query]
    if not args.no_google_news:
        for query in queries:
            feeds.append((google_news_url(query, args.days, args.locale, args.region), "Google News"))
    for feed in args.feed:
        feeds.append((feed, urllib.parse.urlsplit(feed).netloc or "RSS"))

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days) if args.days > 0 else None
    all_items: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []

    for feed_url, fallback_source in feeds:
        try:
            raw = fetch_url(feed_url, args.timeout)
            all_items.extend(parse_feed(raw, feed_url, fallback_source))
        except Exception as exc:
            errors.append({"feed_url": feed_url, "error": str(exc)})

    items = [item for item in dedup(all_items) if recent_enough(item, cutoff)]
    items.sort(key=lambda item: item.get("published_at") or "", reverse=True)

    output = {
        "topic": args.topic,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "window_days": args.days,
        "feeds_checked": [feed_url for feed_url, _ in feeds],
        "items": items[: args.max_items],
        "errors": errors,
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0 if items or not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Tripwire for Meta Content Library documentation drift.

Fetches Meta's Content Library and API changelog, extracts the dated entries,
and compares them against the committed baseline. Implements the protocol in
SKILL.md section "Staying Current": the changelog is the single page checked,
and only a hit justifies reading the guides.

Usage:
    check_meta_docs.py --check     # compare, print a report, exit 1 on drift
    check_meta_docs.py --update    # rewrite the baseline from the live page

Exit codes:
    0  no drift
    1  new changelog entries found
    2  the check itself failed (fetch error, or the page no longer parses)

Exit 2 is deliberately distinct: a scraper that breaks and reports "no change"
is worse than no scraper at all.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

CHANGELOG_URL = (
    "https://developers.facebook.com/docs/content-library-and-api/changelog"
)
BASELINE = os.path.join(os.path.dirname(__file__), "..", "meta-docs-baseline.json")

# developers.facebook.com answers a bare curl with HTTP 400. It needs a
# browser-shaped request -- note `vary: Sec-Fetch-Site, Sec-Fetch-Mode` on the
# response. Verified 2026-08-25: without these headers, 400; with them, 200.
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-User": "?1",
    "Sec-Fetch-Dest": "document",
    "Upgrade-Insecure-Requests": "1",
}

MONTHS = {
    m: i + 1
    for i, m in enumerate(
        "January February March April May June July August September "
        "October November December".split()
    )
}
DATE_RE = re.compile(
    r"\b(" + "|".join(MONTHS) + r") ([0-9]{1,2}), (20[0-9]{2})\b"
)

# The page carried 19 dated entries on 2026-08-25. If a fetch yields far fewer,
# the page structure changed and the parse is no longer trustworthy -- that is a
# failure to report, not a clean result.
MIN_PLAUSIBLE_ENTRIES = 10


def fetch(url=None, timeout=60):
    # Read the module global at call time rather than freezing it as a default
    # argument -- otherwise the URL cannot be overridden to exercise the failure
    # paths, and an untested failure path is how a tripwire ends up silent.
    req = urllib.request.Request(url or CHANGELOG_URL, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status} from {url}")
        return resp.read().decode("utf-8", errors="replace")


def extract_dates(html):
    """Every 'Month D, YYYY' on the page, as ISO strings, newest first."""
    seen = set()
    for month, day, year in DATE_RE.findall(html):
        seen.add(f"{year}-{MONTHS[month]:02d}-{int(day):02d}")
    return sorted(seen, reverse=True)


def load_baseline():
    with open(BASELINE) as fh:
        return json.load(fh)


def save_baseline(entries):
    data = {
        "_comment": (
            "Tripwire state for .github/workflows/meta-docs-check.yml. This is "
            "the raw set of dated entries observed on Meta's changelog, not a "
            "restatement of the human-readable baseline in SKILL.md section "
            "'Staying Current' -- update both when a check finds drift."
        ),
        "source": CHANGELOG_URL,
        "checked": dt.date.today().isoformat(),
        "newest_entry": entries[0] if entries else None,
        "entries": entries,
    }
    with open(BASELINE, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--update", action="store_true")
    args = ap.parse_args()
    if not (args.check or args.update):
        ap.error("pass --check or --update")

    try:
        html = fetch(CHANGELOG_URL)
        entries = extract_dates(html)
    except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
        print(f"FETCH FAILED: {exc}", file=sys.stderr)
        return 2

    if len(entries) < MIN_PLAUSIBLE_ENTRIES:
        print(
            f"PARSE FAILED: only {len(entries)} dated entries found "
            f"(expected at least {MIN_PLAUSIBLE_ENTRIES}). The page structure "
            f"probably changed -- check it by hand.",
            file=sys.stderr,
        )
        return 2

    if args.update:
        data = save_baseline(entries)
        print(f"baseline updated: {len(entries)} entries, newest {data['newest_entry']}")
        return 0

    base = load_baseline()
    known = set(base.get("entries", []))
    new = [e for e in entries if e not in known]
    gone = [e for e in known if e not in set(entries)]

    print(f"baseline checked {base.get('checked')}, newest {base.get('newest_entry')}")
    print(f"live: {len(entries)} entries, newest {entries[0]}")

    if not new and not gone:
        print("NO DRIFT")
        return 0

    if new:
        print("NEW ENTRIES: " + ", ".join(new))
    if gone:
        print("ENTRIES NO LONGER PRESENT: " + ", ".join(gone))

    summary = os.environ.get("GITHUB_OUTPUT")
    if summary:
        with open(summary, "a") as fh:
            fh.write(f"new_entries={' '.join(new)}\n")
            fh.write(f"gone_entries={' '.join(gone)}\n")
            fh.write(f"newest={entries[0]}\n")
            fh.write(f"baseline_newest={base.get('newest_entry')}\n")
            fh.write(f"baseline_checked={base.get('checked')}\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())

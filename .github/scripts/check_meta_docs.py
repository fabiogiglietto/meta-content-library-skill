#!/usr/bin/env python3
"""Tripwire for Meta documentation drift.

Fetches each watched changelog, extracts the dated entries, and compares them
against the committed baseline. Implements the protocol in SKILL.md section
"Staying Current": changelogs are the only pages checked, and only a hit
justifies reading the guides.

Two sources are watched, and they are not equivalent -- see SOURCES below.

Usage:
    check_meta_docs.py --check              # compare, report, exit 1 on drift
    check_meta_docs.py --update             # rewrite the baseline, all sources
    check_meta_docs.py --check --only KEY   # one source (KEY from SOURCES)

Exit codes:
    0  no drift
    1  new changelog entries found
    2  the check itself failed (fetch error, or a page no longer parses)

Exit 2 is deliberately distinct: a scraper that breaks and reports "no change"
is worse than no scraper at all. With more than one source, 2 dominates 1 for
the process exit code -- but both conditions are reported independently through
GITHUB_OUTPUT, so a broken fetch on one source cannot swallow real drift on the
other.
"""

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

# Each source is one changelog page. `min_entries` is the parse-sanity floor for
# that page specifically -- a single global floor would either be too low to
# catch a half-parsed 19-entry page or too high to ever pass a 5-entry one.
SOURCES = [
    {
        "key": "content-library",
        "label": "Content Library and API",
        "url": "https://developers.facebook.com/docs/content-library-and-api/changelog",
        # 19 dated entries observed 2026-08-25.
        "min_entries": 10,
        "owner": (
            "API facts. Route with the page-to-file map in `SKILL.md` section "
            "\"Staying Current\"."
        ),
    },
    {
        "key": "researcher-platform",
        "label": "Secure Research Environment / Researcher Platform",
        "url": "https://developers.facebook.com/docs/researcher-platform/changelog",
        # 5 dated entries observed 2026-08-25, newest 2025-08-18. The floor is
        # 4 rather than half: with so few entries a half-parse would still clear
        # a proportional threshold, and changelog entries do not normally vanish.
        "min_entries": 4,
        "owner": (
            "Environment facts -- access, portals, export, storage. Most land in "
            "`references/utilities.md`. Anything about **driving** the SRE "
            "belongs in the client repo, not here."
        ),
    },
]

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


def fetch(url, timeout=60):
    req = urllib.request.Request(url, headers=HEADERS)
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


def read_source(src):
    """Fetch and parse one source. Raises RuntimeError on an untrustworthy parse."""
    entries = extract_dates(fetch(src["url"]))
    if len(entries) < src["min_entries"]:
        raise RuntimeError(
            f"only {len(entries)} dated entries found (expected at least "
            f"{src['min_entries']}); the page structure probably changed"
        )
    return entries


BASELINE_COMMENT = (
    "Tripwire state for .github/workflows/meta-docs-check.yml, one block per "
    "watched changelog. This is the raw set of dated entries observed on each "
    "page, not a restatement of the human-readable baseline in SKILL.md section "
    "'Staying Current' -- update both when a check finds drift. NOTE: watching "
    "changelogs catches announced changes only. Meta has shipped at least two "
    "unannounced ones (the S3 upload page's Meta-Content-Library exclusion, and "
    "the monthly data-deletion guide); neither appeared on either changelog."
)


def load_baseline():
    with open(BASELINE) as fh:
        data = json.load(fh)
    if "sources" not in data:
        # A pre-multi-source baseline. Refusing is the point: silently treating
        # an unreadable baseline as empty would report every entry as new, and
        # treating it as matching would report clean. Both are lies.
        raise RuntimeError(
            f"{BASELINE} has no 'sources' block -- it predates multi-source "
            f"checking. Regenerate it with --update."
        )
    return data


def save_baseline(blocks):
    """Write the baseline. `blocks` maps a source key to its stored block."""
    data = {
        "_comment": BASELINE_COMMENT,
        "checked": dt.date.today().isoformat(),
        "sources": {s["key"]: blocks[s["key"]] for s in SOURCES if s["key"] in blocks},
    }
    with open(BASELINE, "w") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    return data


def make_block(src, entries):
    return {
        "source": src["url"],
        "label": src["label"],
        "checked": dt.date.today().isoformat(),
        "newest_entry": entries[0] if entries else None,
        "entries": entries,
    }


def emit(path, lines):
    with open(path, "a") as fh:
        for line in lines:
            fh.write(line + "\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--update", action="store_true")
    ap.add_argument("--only", metavar="KEY",
                    choices=[s["key"] for s in SOURCES],
                    help="restrict to one source")
    ap.add_argument("--drift-body", default="drift_body.md",
                    help="where --check writes the per-source drift tables")
    args = ap.parse_args()
    if not (args.check or args.update):
        ap.error("pass --check or --update")

    sources = [s for s in SOURCES if not args.only or s["key"] == args.only]

    # --update must not write a partial baseline: a source that failed to fetch
    # would be dropped from the file, and next month every one of its entries
    # would read as new.
    if args.update:
        # With --only, start from what is already committed so the untouched
        # sources survive; without it, every source is refetched anyway.
        blocks = {}
        if args.only:
            try:
                blocks = dict(load_baseline()["sources"])
            except (OSError, ValueError, RuntimeError) as exc:
                print(f"BASELINE UNUSABLE: {exc}", file=sys.stderr)
                return 2
        for src in sources:
            try:
                blocks[src["key"]] = make_block(src, read_source(src))
            except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
                # Never write a partial baseline: a source dropped here would
                # have every one of its entries read as new next month.
                print(f"FAILED [{src['key']}]: {exc}", file=sys.stderr)
                return 2
        data = save_baseline(blocks)
        for key, block in data["sources"].items():
            print(f"{key}: {len(block['entries'])} entries, "
                  f"newest {block['newest_entry']}")
        return 0

    try:
        base = load_baseline()["sources"]
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"BASELINE UNUSABLE: {exc}", file=sys.stderr)
        return 2

    drifted, failed, body = [], [], []

    for src in sources:
        key, label = src["key"], src["label"]
        known_block = base.get(key)
        if known_block is None:
            failed.append((key, "not present in the baseline; run --update"))
            print(f"FAILED [{key}]: absent from the baseline", file=sys.stderr)
            continue

        try:
            entries = read_source(src)
        except (urllib.error.URLError, RuntimeError, TimeoutError) as exc:
            failed.append((key, str(exc)))
            print(f"FAILED [{key}]: {exc}", file=sys.stderr)
            continue

        known = set(known_block.get("entries", []))
        new = [e for e in entries if e not in known]
        gone = [e for e in known if e not in set(entries)]

        print(f"[{key}] baseline {known_block.get('checked')}, "
              f"newest {known_block.get('newest_entry')}; "
              f"live {len(entries)} entries, newest {entries[0]}")

        if not new and not gone:
            print(f"[{key}] NO DRIFT")
            continue

        drifted.append(key)
        if new:
            print(f"[{key}] NEW ENTRIES: " + ", ".join(new))
        if gone:
            print(f"[{key}] ENTRIES NO LONGER PRESENT: " + ", ".join(gone))

        body += [
            f"### {label}",
            "",
            f"[{src['url']}]({src['url']})",
            "",
            "| | |",
            "|---|---|",
            f"| Baseline last checked | `{known_block.get('checked')}` |",
            f"| Baseline newest entry | `{known_block.get('newest_entry')}` |",
            f"| Newest entry now | `{entries[0]}` |",
            f"| **New entries** | `{' '.join(new) or 'none'}` |",
            f"| Entries no longer present | `{' '.join(gone) or 'none'}` |",
            "",
            f"**Owns:** {src['owner']}",
            "",
        ]

    if body:
        with open(args.drift_body, "w") as fh:
            fh.write("\n".join(body))

    out = os.environ.get("GITHUB_OUTPUT")
    if out:
        emit(out, [
            f"drift={'true' if drifted else 'false'}",
            f"broken={'true' if failed else 'false'}",
            f"drifted_sources={' '.join(drifted)}",
            f"failed_sources={' '.join(k for k, _ in failed)}",
            f"failure_detail={'; '.join(f'{k}: {m}' for k, m in failed)}",
        ])

    if failed:
        return 2
    if drifted:
        return 1
    print("NO DRIFT")
    return 0


if __name__ == "__main__":
    sys.exit(main())

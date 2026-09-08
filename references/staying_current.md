# Staying current — the documentation check in full

`SKILL.md` § "Staying Current" holds the baseline (what the last check found),
the two rules for when to check, and the owner map from each of Meta's pages to
the file here that owns the fact. This file holds the rest of the procedure:
how to read the two changelog pages, what a clean run does and does not prove,
how to record the result, what to say when you cannot fetch, and how the source
repository automates the check.

## The check: two pages, then stop

**The changelogs are the tripwire.** Fetch only these:

| Page | Covers |
|---|---|
| <https://developers.facebook.com/docs/content-library-and-api/changelog> | the API — endpoints, fields, parameters, caps |
| <https://developers.facebook.com/docs/researcher-platform/changelog> | the environment — access, portals, storage, export |

Compare each one's topmost **dated** entry against the baseline in `SKILL.md`.
The second page is quiet — it had five entries in twenty months — but the
environment is half of what this skill asserts, and until 2026-08-25 nothing
watched it at all.

> **What this does not catch, and it matters.** Changelog-watching sees
> *announced* changes. Meta ships unannounced ones: the S3 upload page's
> "It is not supported for Meta Content Library" sentence and the whole
> `guides/data-deletion` page were both live and correct while **neither
> changelog mentioned them**. A clean run means "nothing was announced", not
> "nothing changed" — so a `[verified DATE]` observation still outranks any
> documented name, and a documentation-sourced claim is still the one to
> re-check before asserting it.

- **Same entry, nothing newer → done.** Total cost: one fetch.
- **Newer entries exist → read only the guides those entries name**, using the
  owner map in `SKILL.md` § "Staying Current". A full reconciliation of all 25
  guides is a day's work and is not what a monthly check is for.

Two things about the **Content Library** page that will otherwise waste a fetch: it interleaves
**dated** entries (no version number — the 2026 and 2025 changes) with
**versioned** ones (v5.0, v4.0…), and **v6.0 itself shipped as the undated
2025-11-10 "REST-ful API updates" entry**. So "is there a new version?" is the
wrong question; "is there a dated entry newer than the baseline?" is the right
one.

Meta's guide pages show every snippet under an **R tab and a Python tab**. A
change to one tab is a change to the matching language file here
(`languages/r/` or `languages/python/`); a change to the prose is a change to
the neutral owner.

## Record the result — including "nothing changed"

**A check that writes nothing down did not happen.** Next month's reader cannot
tell "checked, clean" from "never checked", and will pay for the fetch again.

- **Nothing new:** update the baseline date in `SKILL.md` and add one line to
  `CHANGELOG.md` — *"docs check 2026-09-25: newest dated entry still 2026-04-30,
  no action."* No version bump.
- **Something changed:** update the affected file, bump the baseline to the new
  entry, and follow the release checklist at the end of `CHANGELOG.md`.

## When you cannot fetch

Some surfaces this skill runs on have no web access. **Say so rather than
assuming the file is current**: "this skill's documentation baseline is
2026-08-25 and I can't check Meta's changelog from here — treat field names and
limits as of that date." Silence reads as currency, and that is the failure this
procedure exists to prevent.

## Who actually runs it

**In the source repo**, a monthly GitHub Action fetches both pages and opens an
issue when either changelog grows an entry — `.github/workflows/meta-docs-check.yml`,
with its state in `.github/meta-docs-baseline.json`. Drift and a broken fetch are
reported independently, so a 404 on one page cannot swallow real drift on the
other. Run it by hand from the Actions tab, or locally:

```
python3 .github/scripts/check_meta_docs.py --check    # 0 clean · 1 drift · 2 broken
python3 .github/scripts/check_meta_docs.py --update   # after reconciling
python3 .github/scripts/check_meta_docs.py --check --only researcher-platform
```

Sources are declared in `SOURCES` at the top of that script — one dict per page,
each with its own `min_entries` parse floor, because the two pages differ by a
factor of four in how many entries they carry and a single global floor would be
wrong for one of them.

**That Action does not travel with the skill.** A copy installed by zip upload,
or symlinked from a clone that never syncs, has the protocol above and no
scheduler — which is exactly why the protocol is written for you to execute
rather than delegated to CI. If you are reading this file and it is more than a
month past the baseline, the check is yours to offer.

The SRE's own operational state is not this skill's business either.

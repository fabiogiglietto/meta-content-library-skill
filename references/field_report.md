# Field report — how a session's findings travel back to this repository

A **field report** is the unit of contribution to this skill: one thing a live
MCL response taught that the skill did not know, written so that a maintainer
can verify it and edit the file that owns the fact. `SKILL.md` § "Contributing
Back" says *when* to write one and *where* it goes; this file owns its *shape*.

Two readers see a report. The maintainer, who needs enough to reproduce the
observation and locate the claim it corrects. And the next researcher, who will
read the resulting `[verified DATE]` stamp and trust it — so the report must be
about a real response, not a reading of the documentation.

> **No data.** A report carries error messages, `error_subcode` values,
> endpoint paths, parameter values, field names and counts. It never carries
> post text, user names, result rows, or anything else that is MCL content.
> That content does not leave the SRE, and a report is written to leave.

## The template

```markdown
# Field report — <the finding in one line>

| | |
|---|---|
| **Skill version** | <from the `SKILL.md` frontmatter, e.g. 2.0.0 (updated 2026-09-08)> |
| **API version** | v6.0 |
| **Environment** | SRE / SOMAR VDE / other |
| **Language** | R / Python / n.a. — the layer the call was made from; API facts themselves are language-neutral |
| **Observed on** | YYYY-MM-DD |
| **Endpoint** | METHOD path, e.g. `POST facebook/posts/search` |
| **Kind** | correction / promotion / addition / open |

## What the skill says
<file § section, quoted — e.g. `references/common_errors.md` § "Scope and Quota
Errors": "`until` is in the future, or `since` is not before `until`">

## What the API returned
<the verbatim message and `error_subcode`, or the response shape: field names
and counts. No rows.>

## How to reproduce
<the minimal request — parameters, or the R or Python call, with IDs as placeholders.
Budget cost if known, e.g. "estimate only" or "one LIVE job, ~400 rows".>

## Proposed change (optional)
<the edited sentence or table row, stamped `[verified YYYY-MM-DD]`, and the
file that owns it>
```

The header table and the four headings are the contract. Three things make a
report actionable, and a report missing any of them is not: the **skill
version** (from the `SKILL.md` frontmatter), the **date observed**, and the
**verbatim API response** — message and `error_subcode`, or the response's
field names. The **language** row says which mirror a stamp lands on. The issue form in the
repository (`.github/ISSUE_TEMPLATE/field-report.yml`) has one field per
heading, with the same names, so a drafted report pastes in section by section
and a tool can prefill the form from a URL.

## A filled example

This one is real: the observation behind the `3790079` row in
`references/common_errors.md`, reconstructed from the v1.16.0 changelog entry
and written the way it should have arrived.

```markdown
# Field report — "Invalid time range" (3790079) fires when `until` is today

| | |
|---|---|
| **Skill version** | 1.15.0 (updated 2026-08-27) |
| **API version** | v6.0 |
| **Environment** | SRE |
| **Language** | R |
| **Observed on** | 2026-08-29 |
| **Endpoint** | `POST facebook/posts/preview` (the run also used `estimate`) |
| **Kind** | addition |

## What the skill says
Nothing. `references/common_errors.md` § "Scope and Quota Errors" has no row for
subcode 3790079, and nothing in the skill says `until` must be before *now* —
only that `since` must be before `until`.

## What the API returned
HTTP 400, `error_subcode` 3790079, "Invalid time range". Verbatim message:
*"The since time must come before the until time, and the until time must come
before current_epoch_time."*

`until` was the current date at 00:00 — not in the future by the calendar, but
not strictly before the current epoch time either.

## How to reproduce
`since = "2026-08-22"`, `until = "2026-08-29"` (the day of the call), any
`surface_ids`, any `q`. Preview only; no budget spent.

## Proposed change
New row in `references/common_errors.md` § "Scope and Quota Errors": "Invalid time
range" (subcode 3790079) — **[verified 2026-08-29]** `until` must be strictly
**before the current epoch time**; a window ending "today or later" fails
outright. Owner: `references/common_errors.md`.
```

Notice what makes it usable: the version says which text was in front of the
model, the verbatim message is quoted rather than paraphrased, and the
reproduction names parameters without a single ID or row.

## Routes

The source repository is
**<https://github.com/fabiogiglietto/meta-content-library-skill>**. Three
routes; take the first that applies:

1. **You have a clone with git.** Branch (`fix/` or `docs/`, then a slug and
   the date), edit at the file that owns the fact, follow the release checklist
   at the end of `CHANGELOG.md`, and open a pull request whose body is the
   field report.
2. **GitHub is reachable but there is no clone.** Open an issue with the
   *Field report* form:
   <https://github.com/fabiogiglietto/meta-content-library-skill/issues/new?template=field-report.yml>.
   Its fields are the report's headings, so a drafted report pastes in section
   by section — or, if the session has GitHub tooling, it may file the issue
   itself, **after showing the researcher the complete body and getting an
   explicit yes**. Never silently.
3. **Neither** — inside the SRE, or a copy of this skill with no web access.
   Produce the report as markdown and hand it to the researcher to paste into
   the form later. The report is the deliverable; the route is only how it
   travels.

A pull request carries the change *and* the evidence: the report goes in the PR
body, the edit goes at the owning file with its `[verified DATE]` stamp, and the
`CHANGELOG.md` entry says it was **observed, not read** — "confirmed against a
live response on 2026-08-29" is worth more to the next reader than the corrected
value alone. Where a documented claim lost to an observation, say what the
document says, what was observed, and which one won, so nobody re-derives the
wrong answer from the same page.

## When it isn't settled

The `open` kind — one observation, possibly transient, possibly specific to one
account — becomes `docs/OPEN_QUESTION_<topic>.md` rather than a stamped fact.
`docs/OPEN_QUESTION_ASYNC_QUERIES_502.md` and
`docs/OPEN_QUESTION_LISTS_PRODUCERS_PAGINATION.md` are the exemplars. Five
parts:

1. **The question, and why it matters** — which code breaks, and how loudly.
2. **What has already been ruled out**, with sources, so nobody redoes it.
3. **The single observation that would settle it**, as runnable code, with its
   budget cost.
4. **A table of outcomes → actions**, so whoever gets the answer knows what to
   do without rereading everything.
5. **Any fix that is correct regardless of the answer** — and make that fix
   now rather than waiting.

Once answered, the file's own header says what to do: fold the answer into the
owning file with a `[verified DATE]` stamp, note it in `CHANGELOG.md`, and
delete the question.

## What happens to a report

The maintainer reproduces it where possible, edits the sentence at its owner
(one owner per fact — a pointer elsewhere, never a second copy), and follows the
release checklist at the end of `CHANGELOG.md`. The language row decides where
a stamp lands: a Python *promotion* stamps the mirrored section in
`languages/python/` `[verified DATE]` and leaves the R stamp untouched; a
Python *correction* whose cause is the API — not pandas, not the call — edits
the neutral owner and stamps both mirrors; one whose cause is the Python call
edits only `languages/python/`. A report that cannot be
reproduced is not discarded: it becomes an `open` question with the report as
its first ruled-out-nothing-yet observation.

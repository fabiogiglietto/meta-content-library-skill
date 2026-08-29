# Changelog

All notable changes to the `mcl-api-r` skill. This file is the single home for
the version history — `SKILL.md` and `README.md` link here rather than
maintaining their own copies.

## v1.16.0 (2026-08-29)

### The `link` parameter, run for the first time — and the guide is wrong both ways

`references/query_params.md` had carried one line about `link` since 2026-08-21,
tagged documented-not-tested. It has now been measured on 33 URLs across US
mainstream, Italian mainstream and Italian NewsGuard-problematic (score < 60)
publishers, entirely on `preview` / `estimate` / `openapi_spec` — **no async
budget spent**.

- **`link` works without `q`, and should be used that way.** Meta's guide says it
  "cannot be used without the q parameter". It can: `link` alone returned 90
  posts where `q` + the same link returned 16, a verified subset.
- **⚠ With `q` present, an unmatched `link` is silently ignored** — identical
  rows to `q` alone (J = 1.0), HTTP 200. `estimate` reproduces it: 3,000,000 for
  a mistyped URL vs 20 for the real one. Filed in `common_errors.md` under a new
  section, **"Failures that return HTTP 200"**.
- **⚠ Instagram accepts `link` and ignores it** — identical result sets with and
  without. Previously documented only as "there is no link filter".
- **It is an index lookup, not parameter stripping.** A *fabricated* parameter
  form matched nothing in **33 of 33** tests, while a really-posted one matched
  everything. Only host case, `www.` and percent-encoding are canonicalised;
  `http://`, trailing slash, `#fragment`, `m.` and truncated paths all fail.
  Querying the **parameter-free base URL** gathers every posted variant —
  one Il Fatto article was shared 43 times under 30 distinct strings, none of
  them the bare canonical, and the base query found all 43.
- **`n = 0` is ambiguous** — "not a known key", not "nobody shared it". False
  zeros: 1/9 mainstream, 1/18 problematic, 0/5 publisher-canonical.
- **Recall ceiling: text-carried URLs are invisible to `link`** — 4 of 4
  excluded while the index demonstrably held the URL. `link_attachment` is never
  populated on a non-link `content_type` (0 of 300).
- **Meta's `q=url` domain recipe does not work.** Its own example shape
  (`q="abcnews.com/Politics"`) returns 0; `q="nyti.ms"` returns 100 posts of
  which none link there. `q` searches post text and does not index URLs.

### Three facts this repo had wrong

- **`link` IS declared in the OpenAPI spec.** `field_reference.md` § "`fields` is
  not in the spec's parameter list" asserted it was absent from
  `/facebook/posts/preview`; it is the **first** parameter declared, on
  `preview`, `estimate` and `job`, typed `string` (settling that multiple URLs
  are unsupported). `fields` remains genuinely absent — that part stands.
- **`link_url` / `link_title` / `link_description` do not exist.**
  `field_reference.md` § "Link Fields" listed all three as retrievable; the spec
  returns FALSE for all three. v1.13.0 had already called `link_url` invented —
  this table was the surviving copy, exactly the second-copy failure the
  one-owner rule exists to prevent. Section replaced.
- **There is no `search_type` parameter** anywhere in the spec.

### Two more field states worth distinguishing

- **`link_attachment.caption` is served but undeclared** — absent from the spec's
  `LinkAttachment`, yet returned, carrying the resolved destination domain. It is
  the only shortener-resolution route inside the SRE.
- **`match_type` is declared but not served** — in the `FacebookPost` schema, no
  column returned. Distinct from both "declared and served" and "undeclared but
  served".

### Also

- **New subcode 3790079**, "Invalid time range": `until` must be strictly before
  the current epoch time. A window ending today or later fails outright.
- **`preview` pagination documented** — `paging$cursors$after`, fed back as
  `after`. Undocumented here until now, with a warning that a `limit = 100`
  preview is the top of a sort order, not a sample.
- `surfaces.md` `link_attachment.url` for channel messages **flagged as suspect**
  (posts and comments both use `.link`) but *not* corrected — that surface has
  still never been run.
- `docs/TESTING_PROCEDURE.md` gains **Test Suite 13**, including the
  null-filter control and the saturated-Jaccard trap that made the earlier
  scoring invalid.

## v1.15.0 (2026-08-27)

### Two comment fields were wrong, and both are now verified against live data

Settled during Stage 0b of the links-in-comments pilot, on
`facebook/posts/{id}/comments/preview` against an Italian page post with
25,616 comments. Both corrections share a failure mode: a wrong field name
yields **no column**, silently, because `fields` drops unknown names without
complaint.

- **`link_attachment.url` does not exist on comments — the field is
  `link_attachment.link`, exactly as on posts.** This file had asserted a
  posts/comments split (`link` vs `url`) that isn't real. The default
  projection returns `link_attachment.link`, `.name`, `.caption`; requesting
  `link_attachment{url,link,name,caption,description}` returned only `link`,
  `name`, `caption`, with the positive control `statistics{like_count}`
  surviving — which is what makes this a fact about the API rather than about
  the request. **Comment attachments have no `description` either.**
- **The reply pointer is `parent_comment_id`, not `parent_id`** — resolving
  the ⚠ section carried as unresolved since 2026-08-25. Meta's data dictionary
  was right and this file was wrong. It is also **conditional**: the column
  appears only when `fetch_all = TRUE`, and is **absent entirely** (not empty)
  on a top-level-only pull, so `"parent_comment_id" %in% names(df)` is the
  correct guard while `== ""` tests a `NULL`. Replies fetched through
  `/facebook/comments/{id}/replies/preview` carry **no** parent field at all —
  the caller must keep the linkage it already knows.

Also recorded from the same session:

- **`fields` is undeclared in the OpenAPI spec yet honoured.** Neither
  `/facebook/posts/preview` nor the comments preview declares a `fields`
  parameter at operation or path level, and the string is absent from the
  path subtree — but sending it returns exactly the requested projection.
  The positive-control discipline is not belt-and-braces; it is the only way
  to tell "field dropped" from "field empty".
- **`surface_countries` requires `surface_types`.** Sending
  `surface_countries` alone returns HTTP 400, *"Surface country filter can
  only be used when surface_types is set to page and/or profile"*,
  `error_subcode 3790191`.

## v1.14.0 (2026-08-26)

### The docs tripwire now watches the environment too

`.github/workflows/meta-docs-check.yml` fetched one page — Meta's Content Library
and API changelog. It now fetches two, adding
[the Secure Research Environment changelog](https://developers.facebook.com/docs/researcher-platform/changelog).
Half of what this skill asserts is about the environment rather than the API, and
nothing was watching that half.

Baseline for the new source, **observed 2026-08-25**: five dated entries, newest
**2025-08-18** (the Researcher Platform → Secure Research Environment rename).

Three things fell out of making it plural rather than adding a URL to a loop:

- **Parse floors are per source.** The Content Library page carries 19 dated
  entries and the new one carries 5. A single `MIN_PLAUSIBLE_ENTRIES = 10` would
  have failed the new page on every clean run.
- **Drift and breakage are now reported independently.** With one source they
  were mutually exclusive, so a single exit code sufficed. With two they are not:
  a 404 on one page must not swallow real drift on the other. The script still
  exits 2-over-1 for a human at a shell, but the workflow gates its two issues on
  separate outputs and can open both in one run.
- **A pre-multi-source baseline is refused, not adapted.** Reading the old flat
  shape would either report every entry as new or report clean; both are lies, so
  it exits 2 and says to run `--update`.

All four paths were exercised against the live pages before committing: clean,
drift on the new source only, one source 404 while the other drifts (both flags
set, exit 2), and a date-less page tripping the parse floor. `--update --only`
was checked to leave the other source's block byte-identical.

**What this still does not catch — recorded in the workflow, the baseline file
and `SKILL.md`, because a green run is otherwise easy to over-read.** Changelogs
carry *announced* changes. The two findings that prompted this work were both
unannounced: the S3 upload page's "It is not supported for Meta Content Library"
sentence, and the entire `guides/data-deletion` page. Neither appeared on either
changelog, and this tripwire would not have caught either one. It narrows the
window in which drift goes unnoticed; it does not close it, and it is not a
substitute for `[verified DATE]` provenance.

## Housekeeping (2026-08-26, no version bump)

- `README.md` now says v1.13.2 — the v1.13.2 release missed checklist rule 1's
  third place.
- `docs/SUPPORT_TICKET_DRAFT.md` → `docs/SUPPORT_TICKET_ML_MODELS.md`: the
  ticket is filed and answered, so "draft" was misleading. Live references in
  `SKILL.md` and `docs/OPEN_QUESTION_ASYNC_QUERIES_502.md` updated; entries
  below keep the old name as history.
- `references/ml_models_approved.md` added to the README key-files table.

## v1.13.2 (2026-08-26)

A support reply closed the last ML-models question — and collecting the evidence
for the follow-up caught a wrong repo id in this skill.

### Correction: entry #12 was not the repo this skill said it was

`references/ml_models_approved.md` recorded Meta's entry #12 ("Hugging Face
mDeBERTa v3 multilingual") as `microsoft/mdeberta-v3-base`, marked ✔ 9 files.
Meta's page links that entry to
**`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`** — an XNLI-finetuned
zero-shot classifier, not a base model.

**How a verified-looking claim was wrong.** The id was guessed from the entry's
*name*, and the guess resolved, earning a checkmark. But a successful
`hf_list_files()` proves an id is downloadable; it never proves the id belongs to
that row. The check and the claim were about different things. A researcher
following the skill for #12 got a base model where Meta's row points at a
classifier with an NLI head — different tools, and plausible enough in an MCL
pipeline that the substitution stayed silent.

**[verified by listing 2026-08-26: 13 files]** That repo does pass the allow-list.
It was worth probing rather than assuming — it is the only third-party repo on the
list, and being linked from Meta's page is not evidence the proxy accepts an id.
So the list is now **fully resolved: 13 entries, 13 repositories, every id matched
to Meta's own href and confirmed downloadable.**

### Meta's page carries the canonical repo ids in its hrefs

Every one of the thirteen entries links to its Hugging Face repository, even
though the visible text prints a bare, unprefixed name. The full mapping, read off
the live DOM on 2026-08-26, is now the baseline in
`references/ml_models_approved.md` — better evidence than prose summaries of the
page, and better than probing, which can confirm that a guessed id resolves but
never that it is the id Meta meant.

That reframes documentation issue 1 from a request into a one-line fix: **the page
already knows the org-qualified ids; it just doesn't show them.**

### #11 DeBERTaV3: mis-titled, not missing

Meta Support: *"the approved repository is `microsoft/mdeberta-v3-base`"* — which
is exactly what the page's own #11 href says. Support was consistent with the docs
all along. The entry is titled with the DeBERTaV3 paper and links to mDeBERTa, so
reading the name and trying `microsoft/deberta-v3-base` yields a 400. That is the
whole bug, and the path that produced the ticket.

**13 entries, 13 repositories.** The previous pass's reading — twelve repos behind
thirteen entries — is withdrawn. It was correctly tagged as an inference rather
than as Meta's word, and it was still wrong: it rested on this file's own bad #12.
Labelling uncertainty does not resolve it when the resolving evidence is one DOM
query away.

### The follow-up to Meta was rewritten before sending

The drafted reply had asked "is #11 a duplicate of #12, or is DeBERTaV3 meant to be
available?" — false on both branches. It was caught only because capturing the
screenshot Meta requested meant opening the page itself. Gathering evidence for a
claim is a chance to falsify it. `docs/SUPPORT_TICKET_DRAFT.md` now carries the
corrected follow-up, still marked **not yet sent**, plus
`docs/evidence/ml-models-page-2026-08-26.png`.

### Fixed: the frontmatter did not parse as YAML

`SKILL.md`'s `description:` was an unquoted scalar containing `VDE: ` — and a
colon-space inside a plain YAML scalar starts a nested mapping, so GitHub's web
view refused the whole block with *"mapping values are not allowed in this
context"*. Latent since the description was shortened in `1281aa0`; the loader
here was lenient enough to hide it, GitHub was not. The value is now quoted, with
its 198 characters unchanged. `SKILL.md` is the only file in the repo with
frontmatter, and it parses.

### Open / unresolved

Nothing this skill can settle by probing — question 8 of the ML-models inventory
closes completely. What remains is Meta's:

- **Documentation issues 1–3** (bare names as visible text; `400` for both
  unapproved and mistyped ids; the `huggingface.py` return annotations and
  `ZeroDivisionError`) — deferred by Meta: "we will let you know".
- **The `sentence-transformers` install request** — not acknowledged in the reply.

## v1.13.1 (2026-08-25)

Two promotions from **read** to **observed**, both from a single live researcher run
(top posts by views from a 211-page Facebook producer list, 7-day window, 583 rows
returned). No behaviour changes, no corrections — v1.13.0 was right about both. What
this release adds is the thing v1.13.0 could not supply, because it was a reading pass:
evidence.

### `fields` brace expansion verified on the ASYNC JOB endpoint

v1.13.0 established brace syntax against `facebook/posts/preview`
(`query_params.md` § "Field expansion", verified 2026-08-22). It behaves identically on
**`facebook/posts/job`** — confirmed with a nine-field projection
(`text,lang,surface{id,name,type},statistics{...}`) that came back complete on both the
preview and the 583-row job result, brace expansion and response flattening included.

**Why this one was worth verifying rather than assuming.** `text` is not in the
24-column default projection, so a job submitted without `fields` returns no post
bodies — and unlike a bad parameter, that failure is *silent and expensive*: it only
surfaces once the job has completed and been paid for, and a second job costs full
budget with no refund. The generalisation from `preview` to `job` was the plausible
one, but "plausible" and "the budget is already spent" are a bad pairing.

The habit that follows is now written down beside it: **`preview` the exact `fields`
string before submitting the job that uses it.** Previews are free, unknown field names
are dropped silently, and this converts an expensive post-hoc discovery into a free
pre-flight one.

### `estimated_results` given a magnitude

"Approximate count" now carries an observed number: an estimate of **700** preceded a
job returning **583** — **~20 % high**. One observation is not a bound and is not
presented as one, but it is enough to stop `estimated_results` being used as a
denominator for reported rates (use `nrow()`), and enough to treat an estimate sitting
just under a cap as *near* it. `expected_complete` was `TRUE` and honest: the job did
return everything.

### Also confirmed, no change needed

Job `status` returned **`COMPLETE`**, uppercase — the fifth live confirmation, against
Meta's 2025-11-10 "all enums now lowercase" changelog entry. `field_reference.md`
§ "Where the docs and this file disagree" already records this; the observation is
logged here rather than restated there.

## v1.13.0 (2026-08-25)

A **documentation reconciliation** pass: Meta's
[Content Library and API docs](https://developers.facebook.com/docs/content-library-and-api)
were read end to end — the 25 API guides, the data dictionary, the appendix, the
changelog — and this skill was checked against them field by field.

**There is no new API feature here.** The newest dated entry on Meta's changelog is
2026-04-30 (WhatsApp channels), which v1.12.0 already covered. Everything below is a
correction, a gap, or a conflict — which is the opposite failure mode from v1.12.0's:
that release found things by *running* the API, this one found things by *reading*.

Where a documented name contradicts something this skill verified against a live
response, **the observation stays operative** and both are recorded — see
`field_reference.md` § "Where the docs and this file disagree".

### BREAKING: `q` boolean operators are symbols, not words

`AND` / `OR` / `NOT` as words are **not documented operators**. Meta's
[Advanced search guidelines](https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/advanced-search)
give `&` **or a blank space** for AND, `|` for OR, and `-` for NOT, with
parentheses for grouping and precedence NOT → AND → OR.

Every version of this skill up to v1.12.0 taught `"climate OR environment"` and
`"vaccine NOT covid"`. No live test has been run, so this release does not assert that
the word forms fail — but it does state the direction of the error, which is enough:
whether `OR` is treated as an ordinary keyword (ANDed in) or dropped as a stopword, the
result is **narrower** than the union it looks like, and nothing errors. Anyone who
copied those examples has been running a different query than they thought.

`docs/TESTING_PROCEDURE.md` § Test 12.1 settles it with three free `estimate` calls.

Also added from the same pages: exact tokenization rules (no stemming — `cats` is not
`cat`), the per-endpoint list of which fields `q` actually searches, and Meta's own
search-quality figures (median recall 99 %, precision 98–99 %, tested 2024-12-01/05)
with the caveats that matter more than the headline.

### Corrected: the Instagram post field table was wrong throughout

`caption`, `producer_id` / `producer_username` / `producer_name` / `producer_type` /
`producer_verified`, `statistics.likes`, `statistics.comments`, `statistics.plays`,
`media_count`, `image_text` — **none of these appear in Meta's Instagram post
dictionary.** The documented shape is the same one Facebook was verified to have on
2026-08-24: `text`, `post_owner.{id,username,name,type}`, `statistics.like_count`,
`statistics.comment_count`, `statistics.views`, plus `hashtags`, `match_type`,
`is_verified`, `content_type`, `modified_time`.

The failure mode is the one that produced the `statistics.reactions` bug: `intersect()`
column selection drops unmatched names in silence, so the author and engagement columns
go quietly missing. The new table is documentation-sourced and explicitly **not**
verified — Test 12.3 is one free sync call that would settle it.

### Corrected: the v4.0 ID-parameter deprecations are scoped to `facebook/posts`

`page_ids`, `group_ids`, `profile_ids` and `event_ids` were deprecated **on the posts
endpoint** in favour of `surface_ids`. They are the current, documented ID parameters on
the producer-*search* endpoints (max 250 each), and `admin_countries` likewise survives
on `facebook/pages` and `facebook/profiles`. The previous blanket statement read as
"never use `page_ids`", which leaves no way to restrict a Page search to known Pages.

### Corrected: there is no `{platform}/comments/preview`

Sync comment reads hang off the parent — `facebook/posts/{id}/comments/preview`,
`facebook/comments/{id}/replies/preview` — and bulk reads go through
`{platform}/comments/job` with `parent_ids`. The Key Endpoints block advertised a flat
`/comments/preview` while the Nested Endpoints section used that same path as its
"✗ Wrong" example. The Facebook nested rows (previously Instagram-only) are now listed,
along with the general ID-based-retrieval pattern and the entity types that support it.

### Corrected: smaller field-name fixes

- **Facebook Pages**: `verification_status` (not a boolean `verified`),
  `page_categories` — a list of up to three (not `category`), and `about` and
  `description` are the short and long About paragraphs, not synonyms.
- **Facebook Events**: `event_start_time` / `event_end_time`, not `start_time` /
  `end_time`. Four date parameters, not two: `since`/`until` filter on scheduling,
  `event_since`/`event_until` on when the event ran.
- **Facebook Groups**: `privacy` and `admin_count` are not in Meta's dictionary —
  demoted to unconfirmed.
- **Facebook Profiles** gains a field table for the first time. `verification_status` is
  an enum (`not_verified` / `blue_verified`), so the truthiness test that works for a
  boolean is a bug here.
- **A fifth spelling of "verified"**: `instagram/posts` filters with
  `is_account_verified` — not the `is_verified` its own accounts endpoint uses, and not
  Facebook's `is_surface_verified`.

### Corrected: the Threads table was invented

Meta's dictionary documents Threads posts, profiles and replies with the **API field
column reading `N/A` on every row but one** (`is_account_verified`), and none of the 25
API guides covers Threads. The speculative table here (`statistics.likes`,
`statistics.reposts`, `is_reply`, …) is removed. Threads is still named in the API's
policy text, so this is "no published API field names", not "not part of the product".

### Added: features the skill never documented

- **API search IDs (`alias_id`)** — a whole feature. A UI search becomes
  `facebook/posts/preview/{alias_id}` or `facebook/posts/job/{alias_id}`, with
  `lists/shared-searches/{alias_id}` to read the filters an alias carries before running
  it, and appended parameters to override individual filters. This also explains the
  `/job/{alias_id}` paths that the 2026-08-22 spec read had spotted without an
  explanation.
- **`fetch_all` on comments jobs** — `TRUE` returns every reply level in one job.
  `FALSE` is the default, which means every comments job written against this skill so
  far returned top-level comments only. The two-pull pattern is retained as the cheaper
  route for fetching replies selectively.
- **`since` / `until` accept a UNIX timestamp**, on every endpoint that has them. That
  is a lever on the still-**[open]** until-boundary anomaly that neither previous run
  had: a timestamp names an exact second. Test 12.2 would close the question with one
  query.
- **Citation DOIs** — a research-facing skill with no citation guidance. v6.0's API and
  Library DOIs are now in SKILL.md, with the reason they are version-specific.
- **The monthly wipe.** Every 30 days the SRE deletes all cell outputs, **all
  non-notebook files** and **all query results, including async output in S3**;
  notebooks and their input cells survive, and JupyterHub is down for the first of the
  month. This is a different thirty-days from SNAPSHOT retention (server-side, up to a
  year) and the two are now stated side by side. It also breaks the
  `if (file.exists("jobs.rds"))` re-submission guard, since the guard file is wiped too.
- **Geographic and audience exclusions**: China, North Korea, South Korea and Togo are
  excluded outright; age-restricted content is excluded; location-restricted content is
  excluded on Instagram and WhatsApp, while on Facebook it depends on where the query is
  run from — so the collection location is part of the method.
- **"Downloading … by any means is not permitted"**, verbatim, next to the
  `multimedia{url}` section that describes media as retrievable in principle.
- **`activities.type` / `activities.name`** (`streaming`, `playing`) — the contents of
  the `activities` array the spec declares and never explains.
- **A third `match_type` value**, `multimedia_text`. Only two were ever observed.
- **Comment statistics** are richer than recorded: the full per-emoji reaction
  breakdown, plus `statistics.comment_count` (all replies, nested included) **and**
  `statistics.top_level_reply_count` (one level) — two different numbers that a
  "replies" column can silently swap.
- **WhatsApp channel updates**: `forwarded_update_info.*` (a directed channel-to-channel
  diffusion edge), `question_reply_attachment.*`, the `multimedia.*` sub-fields, and the
  fact that `statistics.top_reactions` is **truncated at five** and will not sum to
  `statistics.reactions_count`.
- **Sort defaults per endpoint**, and the reminder that a truncated result set is the
  *top* of the sort order — a `facebook/posts` query cut at 100,000 keeps the
  most-viewed posts, not the most recent.
- **Budget mechanics**: the `budgets` endpoint reports four numbers, and
  `preallocated_rows_for_running_queries` is *why* deleting a job does not refund it.
  The rolling window is "to the second". The multimedia budget (1,000 queries/week)
  applies to third-party cleanrooms, not the SRE.

### Open / unresolved

- **`parent_id` vs `parent_comment_id`** on comments — this skill says one, the
  dictionary says the other, and **neither is verified**. The dictionary also says the
  field is *absent* rather than empty on a top-level comment, which changes the correct
  guard from `== ""` to a `names()` check. Flagged prominently; Test 12.4 settles it.
- **`most_to_least_follower_count` (Pages) vs `most_to_least_followers_count`
  (Profiles)** — one letter apart in Meta's own docs. Possibly a typo; read the enum
  from the spec.
- **The `lists/producers` pagination question stays open.** The appendix page documents
  no pagination and no `limit` — a third weak signal, worth as little as the other two,
  since the guides also omit an `estimate` endpoint the spec declares. The unread cheap
  answer is `client$openapi_spec()$paths[["/lists/producers"]]$get$parameters`.

### Added: a way to notice this sooner next time

This pass existed because nothing in the skill said when its transcription was last
checked, or against what. **SKILL.md § "Staying Current"** now carries a dated baseline
(*"as of 2026-08-25 the newest dated entry was 2026-04-30"*), a one-page tripwire — the
changelog, not the 25 guides — and the **page-to-file map** derived during this
reconciliation, so a changelog hit goes straight to the file that owns the fact instead
of being re-derived. Checks that find nothing are recorded too, since an unrecorded clean
check is indistinguishable from no check at all.

A **monthly GitHub Action** (`.github/workflows/meta-docs-check.yml`) runs that tripwire
in this repo and opens a labelled issue when the changelog grows an entry, with the
page-to-file map and the docs-never-override-`[verified]` rule in the issue body. Three
outcomes are distinguished, because a tripwire that breaks and reports "no change" is
worse than none: exit 0 clean, 1 drift, **2 the check itself failed** — which gets its own
issue and fails the run rather than passing green. Verified against the live page: Meta
answers a bare request with HTTP 400 and needs browser-shaped `Sec-Fetch-*` headers, and
all three exit paths were exercised.

The Action does not travel with the skill — a zip upload or an unsynced clone gets the
protocol and no scheduler, which is why the protocol is written to be executed by whoever
reads the file.

### Files

`SKILL.md`, `README.md`, `references/query_params.md` (+70 %),
`references/field_reference.md` (+35 %), `references/surfaces.md`,
`references/utilities.md`, `references/collections.md`,
`docs/TESTING_PROCEDURE.md` (new Test Suite 12: five tests, four of them free),
`docs/OPEN_QUESTION_LISTS_PRODUCERS_PAGINATION.md`, and new
`.github/workflows/meta-docs-check.yml`, `.github/scripts/check_meta_docs.py`,
`.github/meta-docs-baseline.json`.

## v1.12.0 (2026-08-25)

Everything here came out of **one execution** — a top-10-by-views query over a union of
two producer lists, 2026-08-24 — rather than from re-reading Meta's documentation. Several
items are corrections to things this skill has asserted confidently for months. That is
the point of running the thing.

### Corrected: Facebook engagement field names were never right

`field_reference.md` listed `statistics.reactions`, `.comments`, `.shares`. The API
returns **`statistics.reaction_count`, `.comment_count`, `.share_count`**, plus a
per-emoji breakdown (`like/love/wow/haha/sad/angry/care_count`) that the bare `reactions`
name hid completely.

Nothing written against the documented names ever worked, and nothing ever said so:
column selection goes through `intersect()`, which drops unmatched names silently. The
symptom is a results table with every engagement column quietly missing.
A client that owns the browser automation surface inherited the bug from this file into
its top-N-by-views template and shipped it.

### Corrected: `async/jobs` wraps its payload in `jobs`, not `data`

The defensive idiom `if (!is.null(x$data)) x$data else x` **falls through silently** on
this endpoint — `$data` is NULL, the variable becomes the whole envelope, `$mode` is NULL,
and any summary computed from it is wrong *without erroring*. It reported `0 of 100
snapshot slots used` on an account holding 434 jobs; the real figure was 5.

Also: `creation_time`/`update_time` are **integer epochs** on a job (they are ISO strings
on a post — same field name, different type), and there is **no `name` column**, so a job
cannot be identified by the name it was submitted with.

### Added: the default post projection, and the permalink that does not exist

`facebook/posts/preview` with no `fields` returns exactly 24 columns, now listed. Notably
**`text` is not among them** — post bodies must be requested explicitly, and their absence
is the default rather than a fault.

**No post permalink field exists**, and this is now *verified* absent rather than merely
unstated: no URL field in the projection, and an `openapi_spec()` grep for
`permalink|post_url|content_url|share_url` returns zero. The Content Library **GUI** URL
that does work is documented instead, with the two controls that establish it — a bogus
id is rejected, and two posts by the same producer render differently, which is what rules
out the route resolving the *producer* rather than the post. Its dataset id is
account-scoped and cross-account resolution is untested.

Also adds **`statistics.views_date_last_refreshed`** (undocumented until now, and directly
relevant to views rankings since it dates the number being sorted on).

### Extended: resolve-by-name needs a tie-break, not just a guard

The documented case was two byte-identical lists. An account held **three** ids per name,
and the two generated the same day were identical while the five-month-old one was a
different population. `stopifnot(NROW(hit) == 1)` correctly refuses to guess and then
leaves the caller stuck, so the resolution procedure is now written down — including that
the listing carries **no producer count**, so telling candidates apart costs one GET each.

Also records that lists overlap heavily (89 shared producers between lists of 144 and 96),
so a union must be deduped before the ids are passed.

### Confirmed

- **The `since`/`until` boundary anomaly, on a 7-day window.** The until-day contributed
  19 rows ending `00:25:33` (previously: ending `00:59:52` on a 1-day window). Still
  **[open]** as to the exact boundary — two observations, neither pins it. What is new is
  the cost: the narrow window would have dropped **1,085 posts**, one seventh of the
  corpus, silently.
- **`get_status()` returns `COMPLETE` for a LIVE job too.** The 2026-08-21 result rested
  on four SNAPSHOT jobs, leaving open whether mode affected the casing. It does not.
- **Views coverage is a property of the corpus, not the API** — 5.5 % on 830 ordinary
  profiles, **88.8 %** on 130 pages + 21 profiles. Neither figure may be carried forward.
  Both runs found hundreds of `NA` and **exactly zero** real zeros, so coercing `NA` to `0`
  before ranking invents a result.

### Open questions filed

- `docs/OPEN_QUESTION_ASYNC_QUERIES_502.md` — `async/queries` returned 502 Bad Gateway
  while every other endpoint that session was fine. If persistent, it takes out all five
  documented query-management operations, and it is the only route to
  duplicate-submission detection now that jobs are known to carry no name.
- `docs/OPEN_QUESTION_LISTS_PRODUCERS_PAGINATION.md` — 80 lists returned with no paging
  key. The hazard is not missing data but a confident misdiagnosis: a zero-match resolve
  reading as "no API ID generated", which sends someone to regenerate an id that exists.

## v1.11.5 (2026-08-24)

### Install instructions that actually install the skill

The old Installation section offered a `{"skills": [{"source": "github:..."}]}`
config block. No such mechanism exists, and this repository is not packaged as a
plugin, so that block installed nothing. It is replaced by the two paths that
work: clone-and-symlink for Claude Code, and a zip upload under **Customize →
Skills** for claude.ai and Claude Desktop. The "download the latest release"
fallback is gone too — there are no releases to download.

The section now also says what happens when the skill is updated, because
nothing here auto-updates: `git pull` is the whole update story for a clone, a
pulled `SKILL.md` is picked up without restarting Claude Code but not inside a
conversation that already invoked the skill, and `references/` files are current
as soon as the pull lands. Zip installs are re-uploaded.

The frontmatter `description` is also cut from 446 characters to 198, to fit the
200-character limit that claude.ai applies to uploaded skills. It keeps the
platform names, the SRE/VDE scope and the five trigger nouns — async queries,
producer lists, SNAPSHOT mode, IDs, quotas — and drops the rest of the feature
list, which `README.md` § "What it covers" already carries.

## v1.11.4 (2026-08-24)

### Restores the SRE wording — v1.11.3 corrected the wrong thing

**v1.11.3 replaced every mention of the SRE with "the research environment".
That was the wrong target and this release reverts it in full** — all 40
occurrences are back, verbatim.

The SRE is Meta's own public term for the environment researchers run in. It is
what tells a reader whether a given rule applies to them, and the neutral
paraphrase was strictly vaguer: *"the research environment has no internet
access"* leaves a reader who works in the SOMAR VDE unsure whether it means
them, where the original did not.

**What genuinely should not appear here is the experimental client, by name.**
This skill is consumed by more than one surface, so pointing at one specific
unpublished client is wrong regardless of how the sentence is phrased. That part
of v1.11.3 is kept: four references named it, and they now describe it by what
it owns — which is the part that carried meaning.

- the ownership rationale for removing the browser-automation doc (v1.11.1)
- the provenance note in `docs/ML_MODELS_OPEN_QUESTIONS.md`
- a v1.10.x entry whose *"see …"* pointed into that client's run log. Replaced
  with the finding it pointed at: the ids did not exist yet and had to be
  generated — which is what a reader needed anyway.

The v1.11.3 entry below is left standing rather than edited. It describes what
that release did, and rewriting it to hide a wrong turn would be the same
mistake as deleting a changelog entry for a file that once existed.

## v1.11.3 (2026-08-24)

### Terminology: the environment is named once, and only once

Wording-only pass across ten files. Prose that named the execution environment
by its acronym, or pointed at the private client repo by name, now uses neutral
phrasing — "the research environment", "a live session", "a notebook cell". **No
fact changed**, and no fact was dropped: "the environment has no internet
access" says exactly what it said before.

The single place the environment is still named is the `SKILL.md` frontmatter
`description:`, deliberately. That field is what makes the skill discoverable —
it has to say *when to use this* in the reader's own vocabulary — so it stays as
the one definition the neutral prose everywhere else refers back to.

Three cross-repo pointers were rewritten rather than deleted, since each carried
a reason worth keeping: the ownership rationale for removing the
browser-automation doc (v1.11.1), the provenance note in
`docs/ML_MODELS_OPEN_QUESTIONS.md`, and a v1.10.x entry whose dangling "see"
became the finding itself — the ids did not exist yet and had to be generated.

Also corrects a stale note under v1.11.0 that told a future release to renumber
an unmerged branch. That branch was dropped; its API findings were salvaged into
v1.11.2.

## v1.11.2 (2026-08-24)

### Enum casing is settled — and it is not uniform

`docs/OPEN_QUESTION_ENUM_CASING.md` is **deleted**, as its own header instructed
once both halves were answered. The answers now live with the parameters they
describe, per release-checklist rule 4.

**[verified 2026-08-21]** Three castings, each established separately:

| Where | Casing | How |
|---|---|---|
| `sort` | lowercase — `most_to_least_views` | the 2025-11-10 REST-ful pass |
| `mode` | UPPERCASE — `"SNAPSHOT"` / `"LIVE"` | the `enum` in `client$openapi_spec()`, 5 occurrences |
| `status` (returned) | UPPERCASE — `COMPLETE` | `get_status()` on four live jobs |

This is a **confirmation** of what `SKILL.md` already carried from v1.7.0
testing, not a discovery. What is new is that the 2025-11-10 lowercasing pass
provably did **not** reach job status, and that `status` carries no `enum` in the
spec at all — only prose — so nothing but a live job could ever have settled it.
`mode`'s spec *description* meanwhile reads "snapshot mode" in lowercase while
its `enum` says `SNAPSHOT`: **prose casing does not predict enum casing**, which
is why `query_params.md` now carries a table rather than a rule.

**No code changes.** Every example already passed `"SNAPSHOT"`, and
`mcl_wait_for_job()` stays **case-insensitive on purpose** — one session on one
API version is not a contract, and the failure mode if it changes is silent.

### `since` / `until` is not a clean UTC day

**[verified 2026-08-21]** `since = "2026-08-20", until = "2026-08-21"` returned
`creation_time` from **2026-08-20 00:14:45Z through 2026-08-21 00:59:52Z** — 18
of 2,872 rows fell on the 21st. So `until` is **not** exclusive at UTC midnight.

The exact boundary is left **[open]** rather than guessed: only the first hour of
the 21st appeared, which is consistent with an offset of about an hour from UTC
but not distinguishable from other explanations on one observation.
`query_params.md` documents the workaround — request a day wider and filter
client-side on `creation_time`, which is correct under any boundary semantics.

### Two producer-list traps

**[verified 2026-08-21]** **List names are not unique.** One `lists/producers`
response held two lists with byte-identical names, same platform, same producer
count, same composition — one evidently a UI "Make a copy". Resolve-by-name
silently picks one, so `producer_lists.md` now carries a uniqueness assert.

**The UI and API disagree on producer count.** A list whose UI header read "50 of
832 producers" returned **830** from `lists/producers/{id}`. Cause **[open]**.
The API count is authoritative for batching arithmetic; sizing a loop from the UI
figure leaves it permanently short.

### ID handling: the scientific-notation rule has a scope

**[verified 2026-08-21]** It covers **post, producer and surface** ids, which are
16-digit numerics. It does **not** cover **async job ids** or **producer-list
ids**, which in v6.0 are date-slugs (`2026-08-21-nqw-ytm`, `2026-08-17-cwqm`) —
already strings, no hazard. `SKILL.md` § "ID Handling" says so explicitly now,
since the rule as written invited applying it to every id in the API.

## v1.11.1 (2026-08-23)

### Removed `docs/SRE_AUTOMATION_SURFACE.md` — it was a stale copy of someone else's fact

**Deleted, not moved.** The file was a 621-line snapshot, last touched
2026-08-22, of a document that had since grown to 1309 lines in the client repo
that owns it. Two copies, one owner: the copy here was already wrong about the
paste channel, about modifier keys, and about what the AppStream Functions
toolbar makes possible — every one of those settled *after* this snapshot was
taken. Nobody reading it here would have known.

This is release-checklist rule 4 enforced against the repo itself: *"check that
any new fact has exactly one owner; add a pointer elsewhere rather than a second
copy."* The rule was written for new facts and the violation was an old one.

**The scope line, stated so this cannot recur:** this skill holds only what is
needed to write reliable, functional code against the Meta Content Library
API — endpoints, parameters, schemas, ID handling, caps, error subcodes, and the
patterns that make them work. **How the SRE is driven is not an API fact.** It
belongs to the client that owns the browser automation surface, the driver
design and the egress policy. A fact that would still be true for a
different research question on a different corpus, and is about the API, lives
here; if it is about driving the enclave, it does not.

No pointer file replaces it. A stub about SRE automation would be the same
scope violation in miniature, and the client repo is not published, so a link
would dangle for anyone reading this repo on GitHub.

### Three inbound references rewritten to stand alone

All three cited the deleted file and would have dangled:

- `CHANGELOG.md` (the v1.11.0 ML-models entry) and
  `docs/ML_MODELS_OPEN_QUESTIONS.md` both borrowed the deleted file's
  four-tag sourcing convention. The four tags — **[verified]**,
  **[documented]**, **[inferred]**, **[open]** — are generic method, not an SRE
  fact, so they are now **stated inline** rather than cited across repos. This
  removes a cross-repo dependency the skill never needed.
- `docs/ML_MODELS_OPEN_QUESTIONS.md` § "Automation note" cross-referenced a
  section on reading the session by screenshot. Rewritten to record the
  *provenance* of that reading and to name the owner, without restating the
  driver fact.

## v1.11.0 (2026-08-22)

**Note:** an unmerged branch also claimed v1.11.0. This one merged first and
took the number; that branch was later dropped and its API findings salvaged
into v1.11.2.

### Deleting a job does not refund budget — learned at a cost of ~74,000 records

**[verified 2026-08-23, by the researcher]** A submission cell ran twice on an unstable SRE
stream, creating six SNAPSHOT jobs for three tiers. Deleting the duplicates **frees the
snapshot slots but does not return the records** — budget is consumed at submission and is
gone. `SKILL.md` § "SNAPSHOT vs LIVE Mode" now states this, with the one-line
`file.exists()` guard that would have made the re-run a no-op. **Every cell that submits a job
should carry that guard.** There is no cheap way to learn this fact; write it into the cell.

### CORRECTION: `link_attachment` works — four false negatives traced to one naming error

**[verified 2026-08-22]** An earlier entry in this changelog claimed
`link_attachment_fields` was documented but not served. **That was wrong.** The property is
**`link_attachment`**; `link_attachment_fields` is the data dictionary's *display label*, not a
field name. Requested correctly it returns `link_attachment.{description,link,name,caption}`.

**Link URLs, titles and captions are obtainable.** Co-sharing analysis, domain-level media-diet
measurement and URL-based diffusion **are** buildable on this API.

The root cause of four consecutive false negatives was transliterating display labels into field
names, compounded by `fields` dropping unknown names silently. **The fix is a rule, now the
opening of `field_reference.md`: take field names from
`client$openapi_spec()$components$schemas$FacebookPost$properties`, never from the data
dictionary's labels.** The spec is free, in-session, complete and deployment-specific.

The same read produced the full 16-property `FacebookPost` schema, the `LinkAttachment` and
`Multimedia` sub-schemas (`multimedia` also has `id` and `tags`), and three undocumented
parameters — notably **`surface_ids_to_exclude`**, which does server-side exclusion.

Also corrected: `is_verified` / `activity_type` / `activity_name` were likewise tested under
label-derived names. The schema has `activities` (array of `FacebookActivity`); there is no
`is_verified` property, though `is_surface_verified` exists as a *parameter*. Those earlier
negatives are withdrawn as unfounded rather than restated.

### `link_attachment_fields`: documented for Facebook posts, not served

**[verified 2026-08-22]** Meta's data dictionary lists `link_attachment_fields.{link,name,
caption,description}` as Facebook Post fields (entries 33–36). **The API does not return them.**

Established with a properly controlled test after three inadequate ones: brace syntax, a
positive control that passed, and `content_types = list("links")` so every sampled row actually
has an attachment. Three surfaces — page list, group, broad `q` search — 25/15/25 rows, all
`content_type = links`, and in every case the response was `id, content_type` only.

**Consequence: a shared link's URL cannot be obtained from a Facebook post.** Co-sharing
analysis, domain-level media-diet measurement and URL-based diffusion **cannot be built on this
API**. `shared_post_id` is the only artifact-identity field that actually arrives. Same status
for `is_verified`, `activity_type`, `activity_name`.

The three failed attempts are recorded in `field_reference.md` because each failure mode is
generic: invented names; right names in dot syntax; right names and syntax but a sample where
the field could not be populated (an all-`NULL` column is dropped, so absence-in-sample looks
exactly like absence-in-schema).

### Multimedia URLs and image-text matching ARE available — two earlier negatives reversed

**[verified 2026-08-22]** Careful reading of the data dictionary plus retesting with brace syntax
and a positive control overturned two conclusions this skill nearly recorded:

- **`multimedia{url}` works.** Sub-fields returned: `type`, `duration`, `url`. But the URLs are
  **presigned, ephemeral links** to `prod-fortapis-api-async-uploads.s3.amazonaws.com`, median
  **1,803 characters**. Media is therefore **retrievable in principle but the URL is not an
  identifier** — the same image in two posts yields two different URLs, so any dedup or
  diffusion analysis keyed on media URL is invalid.
- **`match_type` works — it just needs a `q` search.** With
  `search_scope = post_text_and_image_text`, a 25-row sample returned `image_text 5 |
  post_text 24`. Requesting `match_type` alongside `surface_ids` with no query returns nothing,
  which is an easy false negative. **In-image text is searchable and matching posts are
  identifiable, though the OCR text itself is never returned.**

Confirmed genuinely absent, with a passing control in the same request:
`link_attachment_fields`, `is_verified`, `activity_type`, `activity_name`.

**`post_owner` vs `surface`, and a withdrawn claim.** The owner is who *created* a post; the
surface is where it *appears*. They diverge on reshares — a Page resharing someone else's post
is the surface while the original creator remains the owner, with `shared_post_id` linking the
two. **`surface_ids` therefore selects by surface**, so a producer-list pull includes reshares
authored outside the list: a 14-page list returned 10,731 posts from 72 distinct owners.
`field_reference.md` now carries the filter table for author-vs-amplifier questions.

An earlier draft of this branch claimed Meta's docs omit groups from the surface-type
enumeration. **Withdrawn** — they list "Pages, profiles, groups and events"; the claim came from
a partial fetch, not from the docs.

### `fields` uses brace syntax — and drops unknown names silently

**[verified 2026-08-22]** Nested sub-fields are requested as `statistics{like_count,haha_count}`,
**not** `statistics.like_count`. The dots in the data dictionary are *naming*; the response comes
back flattened to dots again, but the request must use braces. New `query_params.md` § "Field
expansion" owns this, with Meta's own example.

**The more dangerous half: an unknown field name is not an error.** The call succeeds and the
column is simply missing — indistinguishable from the field being present but empty. In this
session that produced two unsound conclusions in a row (first from invented names `image_text`
and `link_url`, then from correct names in the wrong dot syntax).

**The fix is a positive control**: include a field known to work in the same request. With
`statistics{like_count,haha_count}` as control, the result is unambiguous —
`link_attachment_fields` and `match_type` return nothing while the control returns cleanly, so
those fields genuinely are not served. That discipline is now written into `query_params.md`.

### The data dictionary is segmented by product — and we read the wrong section

**[verified 2026-08-22]** Meta's post data dictionary covers several product surfaces on one
page, distinguished only by URL anchor. The `#dd-fb-post-3pcleanroom` section describes the
**Third-Party Cleanroom** schema. `link_attachment_fields.*`, `multimedia.url`,
`multimedia.user_tags` and `match_type` are documented there and are **not returned by the
Content Library API** — tested on group and page surfaces, in parent and dotted form.

The `fields` parameter **drops unknown names silently**, so asking for a cleanroom field yields
a successful response with fewer columns — indistinguishable from the field being empty. New
`field_reference.md` § "The data dictionary is segmented by product" owns this.

Two facts recovered from the same read:

- **`multimedia` sub-fields vary by item type.** A photo-heavy group corpus shows only
  `multimedia.type`; a video-heavy page corpus shows `type, duration`. **`multimedia.duration`
  is real** — do not conclude a sub-field is absent from a single sample.
- **`image_text` is a `match_type` value, not a returned field.** OCR text is **searchable but
  never retrievable**: `search_scope = post_text_and_image_text` makes `q` match text inside
  images, but no post surface returns an OCR column. Research designs that assume an
  `image_text` field to analyse are not implementable against this API.

### Spec-verified: producer lists are GET-only, and Marketplace has an `estimate`

`client$openapi_spec()` read live on 2026-08-22 settled three things that were
previously asserted without a source:

- **`/lists/producers` and `/lists/producers/{alias_id}` are `get` only.** There
  is **no POST**: producer lists cannot be created or modified through the API.
  `SKILL.md` and `producer_lists.md` already said so; that claim is now
  **verified** rather than inherited from Meta's prose. Worth stating plainly
  because every other collection-shaped resource here (`async/jobs`,
  `async/queries`, marketplace-listings jobs) *does* accept a POST — producer
  lists are the exception.
- **The path parameter is `{alias_id}`, not `{list_id}`** — wording consistent
  with the API ID being a snapshot *alias*, not a live pointer.
- **`/lists/shared-searches/{alias_id}` exists** (`get`), the saved-search
  analogue of a shared producer list. Previously undocumented here.

**Correction to `surfaces.md`: Marketplace DOES have an `estimate` endpoint.**
That file said "No `estimate` endpoint is documented for any of these surfaces."
The spec shows the full trio — `preview` / `estimate` / `job`, plus per-`alias_id`
variants and `/{mcl_id}`. The guides' silence was a documentation gap, not an API
one. The lesson generalises: **when the guides are silent, read the spec — it is
free, it is in-session, and it is the authority.** Claims about channels,
fundraisers and donations were not covered by this read and remain unverified.

### The API-ID flow, walked end to end and written down properly

The § "Share producer lists between the UI and the API" steps are now
**[verified]** rather than transcribed, having been driven to completion on two
real lists. Three things Meta's page does not tell you, each of which cost time:

- **The caret is to the RIGHT of `Share`** — Meta says only "adjacent". The
  control on the left is `···`, a different menu.
- **Its accessible label is `Copy`.** Searching for a control labelled "Open
  Dropdown" or "API" finds the wrong one, or nothing. Locate it by
  `aria-haspopup="menu"` sitting right of the `Share` button.
- **A bare `element.click()` does not open it.** The app requires a full pointer
  sequence (`pointerover → pointerdown → mousedown → pointerup → mouseup →
  click`). Worth knowing for anyone scripting the Content Library UI.

**And the id format is self-documenting.** Per the dialog: *"the today's date in
YYYY-MM-DD format, followed by a randomly generated string."* So the date in
`2026-08-17-cwqm` is **when the ID was generated — the snapshot date — not when
the list was created.** Combined with the snapshot semantics above, this means an
id carries its own provenance: a date long before your collection window is a
visible warning that the snapshot may be stale.

### The API ID step — a documented mechanism this skill was missing entirely

**A producer list created in the UI is invisible to the API until you generate an
API ID for it.** Not mis-addressed — *absent*: it does not appear in
`lists/producers` and it errors at `lists/producers/{id}`. The id is generated on
demand via *Producers lists* → *View* → the **down-arrow next to `Share`** →
**Create API list ID**.

`producer_lists.md` cross-referenced a section called "Share producer lists
between the UI and API" that **did not exist in the file** — a dangling
reference, so the one place a reader would look for this said nothing. The
section now exists and owns the fact. Source:
[Share a producer list](https://developers.facebook.com/docs/content-library-and-api/appendix/share-producer-list) (v4.0+).

This was found the expensive way: a live session could not resolve two lists that
were plainly visible in the UI, and the hypothesis under test — a GUI→API
propagation lag — was **wrong**: the ids did not exist yet and had to be
generated.

**The id is a SNAPSHOT of the list**, per Meta's own wording. It binds to the
list as it stood when the id was generated, so editing a list afterwards is not
guaranteed to be reflected. Curate first, generate second, and record the id with
its generation date — two analyses citing "the same list" under different ids may
not share the same producers, and nothing in the results would reveal it. New
`producer_lists.md` § "Share producer lists between the UI and the API" owns
this; `common_errors.md` gains two symptom rows; `SKILL.md` § endpoint summary
now mentions the step.

Also corrected: `common_errors.md` told readers the UI "shows the correct path
when you click the API ID button" — a button it never located, in a menu that
does not contain it. That sentence is gone.

Still open: whether `lists/producers` accepts a **POST**. Meta's docs show only
`GET`, and both `SKILL.md` and `producer_lists.md` assert UI-only creation, but
**neither has been checked against `client$openapi_spec()`**. Tagged as
documented-not-verified.

### Corrections to claims this skill was already making

**`Export`: the exported notebook is scrubbed — verified by exporting one.** `SKILL.md` and `README.md` said
export was "entire notebook only", which reads as *you get the notebook, results
included*. Meta's export page says otherwise: code, markdown and **images**
survive; **cell outputs, stdout, stderr and HTML are removed** — each replaced
by a literal `[NOTICE] N output(s) filtered out`. Numbers do not
leave as numbers — anything you need to keep must be rendered as an image, and
that is a decision to make before a long run, not after. New
`references/utilities.md` § "Getting Results Out" owns this. The S3-bucket
feature is not an alternative: its bucket is Secure-Research-Environment-owned,
and Meta states it is not supported for Meta Content Library.

**Inference from R is fine.** An earlier commit on this branch told readers that
inference was "easiest left in Python" because of `**kwargs` unpacking. Tested
and false: passing `input_ids`/`attention_mask` by name avoids the unpacking, and
mean pooling is ordinary reticulate arithmetic. A 384-dim embedding took 0.7 s
end to end. The working recipe replaced the discouragement.

**The first drift-check "change" was our own transcription.** Corrected in
`references/ml_models_approved.md` rather than left asserting a false edit date
on Meta's page.

### Added

**ML models in the SRE** — `references/utilities.md` § "Download Machine Learning
Models", now largely **[verified]** in a live session rather than transcribed:

- `fbri.package_managers.huggingface` imports from R-side reticulate; reticulate
  binds `/opt/conda/bin/python3` (3.11), the same conda env as the kernels.
- Downloads land at `~/huggingface/<repo>/<revision>`, org prefix kept — read
  from the module's source, then confirmed by downloading.
- **`output_dir` replaces the whole path**, so two models sharing one directory
  overwrite each other's `config.json`.
- **Both helpers return `None`** despite docstrings promising a path string.
- **`hf_list_files(repo, revision)`** — undocumented by Meta; probes a repo, and
  the approval gate, without downloading.
- **`hf_download_repo` pulls every file**: MiniLM's ~90 MB of weights cost
  **931 MB** because ONNX, OpenVINO, TensorFlow and Rust variants come too.
  Throughput ~16 MB/s.
- **The org prefix is mandatory.** Every bare legacy alias (`t5-small`,
  `bert-base-uncased`, `xlm-roberta-large`, …) returns 400 — the proxy does not
  follow Hugging Face's rename redirects, and those bare names are exactly what
  Meta's page prints.
- **400 vs 404**: 400 is repo-level and cannot distinguish "wrong id" from "not
  approved"; **404 means the repo resolved and passed the gate**, only the
  revision is wrong.
- **Revision pinning works** — full and 7-char SHAs, each getting its own
  directory beside `main/`. Pin by SHA for reproducible work.
- **No offline configuration needed**: `from_pretrained()` on a local path makes
  no hub call.
- **`sentence_transformers` is not installed**, though two approved models are
  Sentence-Transformers models; use `AutoModel` + manual mean pooling.

**GPU servers** — `references/utilities.md` § "CPU or GPU Server". CPU or GPU is
chosen when the notebook server starts and switchable mid-session via **File** >
**Hub Control Panel** without losing work. Verified real: `torch 2.4.0+cu118`,
CUDA available.

**`references/ml_models_approved.md`** — the approved list as a diff target,
with **12 of 13 repo ids resolved by probing**. #11 DeBERTaV3 resists:
`microsoft/mdeberta-v3-base` lists while `microsoft/deberta-v3-base` and
`-large` do not, so the org is right and the gate is per-model. A 400 cannot
separate "wrong id" from "not approved", so probing cannot settle it —
`docs/SUPPORT_TICKET_DRAFT.md` asks Meta.

**`docs/ML_MODELS_OPEN_QUESTIONS.md`** — the 20-question inventory and its
results log; 19 closed, all without spending MCL budget.

**A monthly drift check** — routine `trig_015jzBacsSw43Np7E23p3obe` re-fetches
Meta's model list, diffs it against the snapshot, and opens a PR only when
something changed. Paired with an at-use freshness check in `SKILL.md`: before
answering which models are available, re-fetch and compare.

## v1.10.0 (2026-08-21)

**Added: how to download machine learning models in the SRE**
(`references/utilities.md` § "Download Machine Learning Models"). The SRE has no
internet access, so `from_pretrained("facebook/mbart-...")` cannot reach
huggingface.co — an approved model must be downloaded first through
`fbri.package_managers.huggingface` (`hf_download_repo` for a whole repo,
`hf_download_file` for one file, filename before repo) and then loaded from
`~/huggingface/<REPO>/<REVISION>`, where `<REPO>` keeps its org prefix. The
section records the approved-model families as fetched 2026-08-21, the
restrictions (text models with open-source licenses only; unlisted models need a
support ticket), and the GPU-machine note.

This sits next to "Install R Packages" because the two are easy to confuse:
`fbrir`/`CRAN$new()` installs R packages from Meta's CRAN mirror,
`fbri.package_managers.huggingface` downloads models — different package, different
manager.

Sourcing follows the four-tag convention. The Python signatures,
paths and restrictions are **[documented]** from
[Machine Learning Models](https://developers.facebook.com/docs/researcher-platform/features/ml-models).
The reticulate wrapper is **[inferred]** and marked untested — `fbri` is a
different package from `metacontentlibraryapi`, so whether it imports from the
R-side reticulate Python is unverified; the section gives a Python-cell fallback
that works either way. `docs/TESTING_PROCEDURE.md` Test 1.6 settles it.
Inference is deliberately left in Python rather than translated to `do.call()`
and `py_get_item()`.

**Also:** `SKILL.md` § Environment gains a "No internet access" bullet — the fact
both package managers follow from.

## v1.9.1 (2026-08-21)

Patch release. No documented API behavior changed; this removes a silent-failure
class from the skill's own code and files the question behind it.

**Fixed: no status comparison is case-sensitive any more.** The sweep found nine,
failing in two directions. `SKILL.md`'s Async Query Template, `chunking.md` and
the example script used `while (status != "COMPLETE")`, which spins forever
against a lowercase `complete`. `common_patterns.md` used
`while (status == "IN_PROGRESS")`, which is worse — against `in_progress` it
exits on the first check and reads a half-written result as final. `utilities.md`
gated on `status == "COMPLETE"` and would misreport. `docs/TESTING_PROCEDURE.md`
held one of each plus a raw `get_status()` comparison — the worst place for them,
since a tester would have run the broken pattern while verifying the fix. All now
route through `mcl_wait_for_job()` (SKILL.md § "Waiting for a Job"), which
upper-cases and
trims before comparing, enforces a wall-clock timeout, raises on `FAILED`, and
treats an unrecognized status as "keep waiting" rather than as success. This is
correct under either casing, so it did not need the question below answered.

**Added: `docs/OPEN_QUESTION_ENUM_CASING.md`** — the casing question itself is
still open, now as documentation rather than as a live hazard. The file records
which public pages were checked and came back empty (there is no public
async-jobs page at all, and neither `get-api-code` nor `api-search-id` prints a
`mode` value), a Claude for Chrome prompt for sweeping what the check missed, and
a zero-budget in-SRE diagnostic that reads the OpenAPI enum and an
already-finished job rather than submitting anything.

**Corrected in the v1.9.0 entry below:** it claimed a fix to
`top_italian_politicians_week.R`, but that file is listed in `.gitignore` and has
never been tracked, so the fix was not in the release and the file does not exist
in this repository. The paragraph has been removed rather than left describing a
change no reader can see.

## v1.9.0 (2026-08-21)

Synced with the Meta Content Library changelog through 2026-04-30.

**Fixed: the follower threshold was three versions stale.** Four files said a
Facebook profile's posts are queryable only if it is verified or has **25,000+**
followers. That number predates v5.0. It went to 1,000 in v5.0 (2024-11-11) and
to **100** in v6.0 (2025-11-10), and the same 100-follower rule governs which
Instagram personal accounts are included. The stale figure was load-bearing:
`common_errors.md` used it to explain why a producer-list post query estimates
~0 results, which sent researchers looking for a fault in lists that were fine.
`field_reference.md` § "Data Scope" now carries the version history, and notes
that the 25,000 floor still documented for the ICPSR/CASD *downloadable* dataset
is a different product from the API. "Verified" now also covers paid Meta
Verified subscriptions.

**Added: `references/surfaces.md`** — the surfaces that arrived after the
endpoint list was last written: Facebook channels and channel messages
(2026-03-12), WhatsApp channels and channel updates (2026-04-30), Instagram
channels and channel messages, Marketplace listings, Facebook and Instagram
fundraisers, and Facebook donations. Parameters, filters, sort enums and node
fields for each. Flagged as documented-but-untested, in the style already used
for the Threads table — it is transcribed from Meta's guides and Data
dictionary, not confirmed against a live response.

**Fixed: the endpoint grammar no longer holds for every surface.** SKILL.md's
`/{resource}/{preview|job|estimate}` line would lead you to guess
`facebook/channels/job` and `facebook/marketplace/preview`; both 404. Async
message jobs hyphenate the resource at the platform root
(`facebook/channel-messages/job`, `whatsapp/channel-updates/job`) while the sync
read hangs off the parent channel node, and no `estimate` endpoint is documented
for any of the new surfaces.

**Added: the Facebook post filter set** to `query_params.md`, which had only
ever documented `q` / `since` / `until` / `limit` / `lang` / `country` and the ID
params. Notably `sort` now defaults to `most_to_least_views` rather than
newest-first, so an old query silently returns a different sample; `media_types`
is deprecated in favour of `content_types` (v1.8.0 dropped `media_type` as
unverifiable - this is its documented replacement, with a source); and
`search_scope = "post_text_and_image_text"` is how you reach text-in-images
search. Enum *values* are lowercase after the 2025-11-10 REST-ful pass.

**Clarified: two different caps were conflated as "1000".** A sync search pages
through 1000 results *in total*; the per-page `limit` maximum was separately cut
from 500 to 100 on 2025-07-15, and is 0-50 (default 10) for channel message and
update previews.

**Added: Test Suite 11** to `docs/TESTING_PROCEDURE.md` (five sync-only,
zero-async-budget tests) so the new surfaces can be promoted from documented to
verified in one SRE session. It also asks the tester to record whether `mode`
accepts a lowercase value and where the `limit` ceiling actually falls.

Not changed: `mode = "SNAPSHOT"` / `"LIVE"` stay uppercase. The 2025-11-10
"enums are now lowercase" note is real but demonstrably applies to value enums
like `sort` and `content_types`; the uppercase modes are what this skill has
tested, and rewriting dozens of samples on a documentation inference is exactly
the trade v1.8.0 refused.

## v1.8.0 (2026-08-18)

**Removed: examples using a client API that does not exist.** Three files
documented `MCLClient$new()`, `client$search_fb_posts()` /
`search_ig_posts()` / `search_fb_comments()`, `library(metacontentlibrary)`,
and cursor pagination via `response$paging$next_cursor`. None of these exist —
the real client is `client$get(path=, params=)` / `client$post(...)` via
reticulate, as `SKILL.md` has always documented. Code copied from those files
could not run.

Removed with them, as unverifiable rather than merely undocumented:
`min_reactions`, `min_shares`, `min_comments`, `min_views`, `search_fields`,
`producer_list_id`, `media_type` as a query filter, and `start_date` /
`end_date` (the API uses `since` / `until`). These were deliberately **not**
rewritten into correct-looking `client$get(params = ...)` form, which would have
made unverified guesses indistinguishable from tested behavior. Rediscover them,
if they exist, via `client$openapi_spec()`.

**Fixed: `statistics$reactions` → `statistics.reactions`.** `mcl_fromJSON()`
parses with `flatten = TRUE`, so engagement counts are flat columns, not a
nested list-column. Roughly a dozen snippets in `common_patterns.md` used the
nested form and would have failed on copy. Facebook posts also group by
`post_owner.type`, not `producer_type` (an Instagram field).

**Resolved contradictions:**
- `shared_from_id` removed from `field_reference.md`; `shared_post_id` (v1.7.0)
  is the verified field name for a reshare's original post.
- Two conflicting Instagram-account field tables reduced to one. The verified
  set (v1.2.0) lives in `producer_lists.md`; `field_reference.md` points to it.
  Note `biography` not `bio`, `is_verified` not `verified`.
- `get_id_param_name()` deleted from `producer_lists.md`. It returned `post_ids`
  for Instagram twenty lines after the auto-detect pattern returned
  `account_ids`. These are different jobs, not conflicting answers:
  `account_ids` filters posts **by account**, `post_ids` selects **specific
  posts**. Both files now say so.
- Instagram comment fields aligned to `owner.*`, matching the verified Facebook
  comment schema, and marked unverified.
- Threads: the querying claim is dropped from the skill description and README.
  No Threads endpoint path has been confirmed; the field table stays, flagged
  unverified.

**Consolidated — one owner per fact.** Duplicated content had already drifted
(Critical Requirements: 6 items in `SKILL.md` vs 13 in `README.md`; the
rate-limit table in `README.md` was missing the 100-snapshot row). Each fact now
has one home, and every other mention is a pointer. `SKILL.md` keeps the errors
that change how you write a *first* query; the diagnostic long tail moved to
`common_errors.md`.

**Structure:**
- `references/query_syntax.md` deleted. Its two verified sections — boolean
  operators, and the 3790184 no-double-quoted-phrases rule with the full error
  JSON — moved into `references/query_params.md` § "Query Syntax (`q`)".
- Version history extracted from `SKILL.md` and `README.md` into this file.
- `TESTING_PROCEDURE.md` moved to `docs/`, so it is no longer part of the skill
  payload. Suites testing removed content were dropped; the offline
  `mcl_fix_ids` unit test (Test 10.1) is kept.
- `SKILL.md` cut from 459 to ~300 lines. The two near-identical OpenAPI sections
  are merged into one.

## v1.7.0 (2026-08-18)

Consolidated verified API behaviors: MCL IDs != URL IDs (3790088); ID params
must be arrays; empty-params reticulate pitfall; no double-quoted phrases
(3790184); 100k single-query cap (3790057) -> date windows; SNAPSHOT cap
(3790172) vs LIVE + LIVE->SNAPSHOT conversion; profile post-inclusion thresholds
(verified/25k+ followers); comment (`owner.*`) vs post (`post_owner.*`) schemas;
replies require a second `parent_ids` pull; reshares carry `shared_post_id`
resolved via `post_ids`; producer-list CSV import format (`Producer URL`, max
1000).

## v1.6.0 (2026-08-17)

Documented that the API rejects double-quoted phrase searches (subcode 3790184)
even though the UI supports them; use single-word `OR` tokens.

## v1.5.0 (2026-08-17)

- Documented creating producer lists via the GUI CSV import: single `Producer URL`
  column of `https://www.facebook.com/<username>` URLs, max 1,000 producers, import
  is by URL not by MCL id. Added a recipe for building a list from active public
  commenters.
- Clarified that `surface_ids` / `account_ids` / `post_ids` must be passed as
  **arrays** (`as.list(ids)`); a scalar is rejected with "Invalid parameter",
  including a length-1 vector reticulate converts to a string. Updated every
  affected example.

## v1.4.0 (2026-08-16)

- **IMPORTANT**: All IDs (surface, post, comment, account, job, query) must be
  loaded as **character**. Added an "ID Handling" section with `mcl_fromJSON()` /
  `mcl_fix_ids()`, which combine `bigint_as_char = TRUE` (exactness above 2^53)
  with unconditional `sprintf("%.0f", ...)` coercion of every ID field (no
  scientific notation, no per-batch type drift).
- Folded ID coercion into `safe_get_data()` and switched every example in
  `SKILL.md` and the reference files from `fromJSON()` to `mcl_fromJSON()`.
- Prevents silent precision loss above 2^53, scientific notation in URLs and
  parameters (a second cause of subcode 3790088), and per-chunk `bind_rows()`
  type mismatches.
- Added error rows for scientific-notation 3790088, `bind_rows()` type mismatch,
  and silent precision loss in joins/dedup; added ID-hygiene guidance for joins,
  dedup, and CSV round-trips, plus offline and live ID tests in
  `TESTING_PROCEDURE.md`.

## v1.3.0 (2026-08-13)

**IMPORTANT**: Documented that MCL IDs are library-specific and differ from
Facebook/Instagram URL IDs. Added a "Finding Surface IDs" section with per-entity
lookup endpoints and error rows for subcode 3790088 and the empty-`params`
reticulate pitfall.

## v1.2.0 (2026-03-29)

- **BREAKING**: Fixed producer list endpoint: `lists/producers/{id}` not
  `producer-lists/{id}`
- **BREAKING**: Producer list response uses `$producers` data.frame (cols: id,
  name, type), not `$ids` vector
- Added safe response handling pattern for API responses (prevents `nrow()` on NULL)
- Added Instagram accounts response field documentation (id, name, username,
  biography, account_type, is_verified, follower_count, following_count,
  creation_date, website)
- Added cross-platform account matching workflow to `producer_lists.md`
- Added producer endpoint to Key Endpoints section
- Updated `common_errors.md` with 404 producer list, NULL response, and `nrow()`
  errors

## v1.1.0 (2025-01-04)

- Fixed Instagram parameter documentation (`post_ids` not `surface_ids`)
- Added nested endpoints documentation for Instagram comments/replies
- Added OpenAPI spec discovery pattern for debugging
- Added `common_errors.md` reference file
- Clarified platform-specific ID parameter differences

## v1.0.0 (2025-01-04)

- Initial release
- Core async query patterns with integer `L` suffix handling
- SNAPSHOT mode documentation
- Producer list support with platform auto-detection
- Quota monitoring from verified working code
- Package installation via `fbrir`
- Job retrieval patterns
- Large dataset chunking
- Collection management
- OpenAPI spec access

---

## Release checklist

When updating this skill:

1. Bump the version in **three** places: `SKILL.md` frontmatter `version:`, the
   `> **Skill Version:**` line below the `SKILL.md` title, and `README.md`.
2. Update the `updated:` date in the `SKILL.md` frontmatter.
3. Add an entry here — and only here.
4. Check that any new fact has exactly one owner (see `SKILL.md` § References);
   add a pointer elsewhere rather than a second copy.
5. Update `docs/TESTING_PROCEDURE.md` if behavior changed.
6. If the change came from reading Meta's documentation, update the **baseline**
   in `SKILL.md` § "Staying Current" — both the check date and the newest dated
   changelog entry it saw. A documentation check that found *nothing* also gets
   recorded: bump the baseline and add a one-line note here, with no version bump.

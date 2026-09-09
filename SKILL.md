---
name: mcl-api
description: "Meta Content Library (MCL) API v6.0 from R or Python. Use when querying Facebook, Instagram or WhatsApp content in Meta's SRE or the SOMAR VDE — async jobs, producer lists, SNAPSHOT mode, MCL IDs, quotas, error subcodes — whether the code is R via reticulate (the verified layer) or Python with the metacontentlibraryapi client and pandas (documented, not yet field-tested). Defaults to R when the language is not stated."
version: 2.0.1
updated: 2026-09-09
---

# Meta Content Library API v6.0 — R and Python

> **Skill Version:** 2.0.1 | **Updated:** 2026-09-09 | [Changelog](CHANGELOG.md)

## Environment

- **Platform**: Amazon WorkSpaces Secure Browser with JupyterLab — there are
  **two portals, United States and Ireland**; pick the one your access was
  granted for
- **Language**: R via reticulate, or Python. The MCL client is the Python
  package `metacontentlibraryapi`; R reaches it through reticulate. Both kernels
  share one interpreter, `/opt/conda/bin/python3` (3.11). See
  [Choosing the language](#choosing-the-language)
- **Export**: notebook only, and **its outputs are stripped** — code, markdown and
  **images** survive; cell outputs, stdout, stderr and HTML do not. Numbers do not
  leave as numbers. See `references/utilities.md` § "Getting Results Out"
- **No internet access** *(inside the SRE — not for you; see below)*: R packages
  come from a custom CRAN mirror, Python packages from a pip channel, and
  pre-trained ML models from an approved Hugging Face list — see
  `references/utilities.md`
- **Server type**: CPU or **GPU**, chosen when the notebook server starts and
  switchable mid-session without losing work — see `references/utilities.md` §
  "CPU or GPU Server"
- **Everything except your notebooks is deleted every month.** On the 1st of each
  month the SRE wipes all cell outputs, all non-notebook files and all query
  results, and JupyterHub is unavailable for the day. Notebooks (code and
  markdown) survive. Plan for it — `references/utilities.md` § "The monthly wipe"

**Everything in this skill is a dated transcription of a moving target.** The
no-internet constraint above binds the code you write for the SRE, **not you**:
you run on the researcher's machine and can check Meta's documentation yourself.
Two cases where you should, before answering:

- **Available ML models** — re-fetch
  [Meta's list](https://developers.facebook.com/docs/researcher-platform/features/ml-models)
  and compare against `references/ml_models_approved.md`; it grows. Procedure and
  fallback: `references/utilities.md` § "Download Machine Learning Models".
- **Anything marked `[documented]` rather than `[verified DATE]`**, once the
  baseline in [Staying Current](#staying-current) is more than a month old.

## Critical Requirements

1. **Always use async queries** (POST to `/job` endpoints) for research
2. **Integers are integers**: `limit`, `page_size` and every other integer
   parameter must arrive as an integer, not a float — in R that means the `L`
   suffix (`limit = 100L`); in Python a bare `100` already is one
3. **Always document**: Include `name`, `description`, `mode = "SNAPSHOT"` in every query
4. **Flush output** after every progress line in Jupyter so a polling loop shows
   its status as it happens (`flush.console()` in R; `print(..., flush=True)`)
5. **Safe response handling**: validate an API response before counting its rows
   — see [Safe Response Handling](#safe-response-handling)
6. **IDs are strings, always**: never let a JSON parser or a data frame turn an
   MCL ID into a float. Parse every MCL response with the language helper —
   see [ID Handling](#id-handling-ids-are-strings)

## Choosing the language

Every fact in this file and in `references/` holds for both languages; only the
call differs. Infer the language from context, in this order:

- **Python** — `.py` or `.ipynb` on a Python kernel, `pyproject.toml`,
  `requirements.txt`, `environment.yml`, a Python traceback, pandas or requests
  in the question, or the researcher saying so.
- **R** — `.R`, `.Rmd`, `.qmd`, an `.Rproj`, `renv.lock`, `library()` or dplyr
  in the question, an R error text, or the researcher saying so.
- **No signal** — write R and say why in one line: "R, the verified layer; say
  Python to switch." Ask only if the answer would change the code and nothing in
  the conversation decides it.

Then read `languages/r/` or `languages/python/`. The R layer is `[verified]`
where stamped. The Python layer is `[documented]` throughout: transcribed from
Meta's Python examples or mirrored from verified R calls, never run from a
Python kernel. When writing Python, say so once, and treat a successful call as
a field report waiting to be written ([Contributing Back](#contributing-back)).
A Python cell inside an R notebook is legitimate and the R layer says when
(`languages/r/utilities.md` § "Download Machine Learning Models").

The two layers mirror each other file by file and section by section, so a
reader of either can find the other's version under the same heading. Where a
section exists in one and not the other, the file says why.

## Core Concepts

```
Collection (folder for organization)
  └── Query (reusable search definition)
       ├── Job 1 (first execution)
       ├── Job 2 (second execution)
       └── Job 3 (third execution)
```

- **Query**: Created once, executed multiple times. Has `query_id`.
- **Job**: Single execution of a query. Has `id`, a status (IN_PROGRESS / COMPLETE / FAILED as of v1.7.0 testing), and a mode (LIVE/SNAPSHOT). **Never compare a status case-sensitively** — see [Waiting for a Job](#waiting-for-a-job).
- **Collection**: Folder to organize related queries.

## Setup

Import the client class from `metacontentlibraryapi` and pin the API version
with `set_default_version(LATEST_VERSION)`. Every method is called on the
class itself, never on an instance. Also define the language's ID-safe parser
and job-wait helper before anything else; every example in this skill assumes
them.

Code: `languages/r/setup.md` § "Load the client" · `languages/python/setup.md` § "Load the client"

## ID Handling (IDs Are Strings)

MCL IDs are 15–19 digit numbers, and some endpoints return them **unquoted** in
JSON. Any path that turns them into a float breaks two ways:

- **Silent precision loss** above 2^53 (~9.0e15): `17841400000000123` comes back
  as `17841400000000124`. Unrecoverable after parsing — no post-hoc coercion can
  restore the digits.
- **Scientific notation** below 2^53: the value is exact but prints/pastes as
  `9.6378e+14`, so a path built from it is garbage and the API answers *"Invalid
  Meta Content Library ID"* (subcode 3790088) — the same error you get from a
  raw URL ID.

Which path does that differs by language: in R, `jsonlite::fromJSON()` parses
unquoted IDs as doubles; in Python, `json.loads()` keeps them exact but a
pandas column with a single null becomes float64. Each layer has a helper that
closes its own hole — use it for **every** MCL response, whether from response
text or from a job's saved `.json` file.

**Scope note — [verified 2026-08-21].** This applies to **post, producer and
surface** ids, which are 16-digit numerics. It does **not** apply to **async job
ids** or **producer-list ids**, which in v6.0 are date-slugs of the form
`2026-08-21-nqw-ytm` and `2026-08-17-cwqm`. Those are already strings and carry
no scientific-notation hazard.

Rules that follow, in every language: keep IDs as strings in joins, de-duplication
and ID parameters; read CSVs with ID columns as strings; hard-code IDs as quoted
strings; and treat an ID that reached you as a float at or above 2^53 as already
corrupted, since re-fetching it from MCL is the only way back. Display settings
that hide scientific notation are not a fix — the value is still a float.

Code: `languages/r/ids.md` § "mcl_fromJSON" · `languages/python/ids.md` § "mcl_from_json"

## OpenAPI Spec

Retrieve the complete API spec programmatically (v6.0+) with the client's
`openapi_spec()` — use it to discover endpoints, parameters, and response
schemas, and to settle any question this skill does not answer. Its `paths`
are the endpoint list; each path's `get`/`post` entry carries `parameters`.

Code: `languages/r/query_params.md` § "Reading the OpenAPI spec" · `languages/python/query_params.md` § "Reading the OpenAPI spec"

## Key Endpoints (v6.0)

```
Facebook:  /facebook/{posts|pages|groups|events|profiles}/{preview|job|estimate}
           /facebook/comments/{job|estimate}          <- NO /comments/preview
           /facebook/{channels|fundraisers|marketplace-listings}/preview
Instagram: /instagram/{posts|accounts}/{preview|job|estimate}
           /instagram/comments/{job|estimate}         <- NO /comments/preview
           /instagram/{channels|fundraisers}/preview
WhatsApp:  /whatsapp/channels/preview
Utility:   /budgets, /async/jobs, /async/queries, /async/collections
Producer:  /lists/producers, /lists/producers/{list_id}
Shared:    /{platform}/posts/{preview|job}/{alias_id}, /lists/shared-searches/{alias_id}
```

**Comments break the `{resource}/{preview|job}` pattern.** There is no
`facebook/comments/preview` or `instagram/comments/preview`. Reading comments
**synchronously** goes through the *parent* — `facebook/posts/{post_id}/comments/preview`,
`facebook/comments/{comment_id}/replies/preview` — while reading them in bulk goes
through `{platform}/comments/job` with `parent_ids`. Guessing the flat sync path
is the single most common comments mistake, and it is why the "✗ Wrong" example
in [Nested Endpoints](#nested-endpoints) uses exactly that URL.

**The `{resource}/{preview|job}` pattern does not extend to every surface.**
Async message jobs hyphenate the resource and hang off the platform root —
`facebook/channel-messages/job`, `instagram/channel-messages/job`,
`whatsapp/channel-updates/job` — while the sync read hangs off the parent
channel node. `estimate` is documented only for the posts/comments/accounts
family, not for channels, Marketplace, fundraisers or donations. Parameters and
fields for all of these: `references/surfaces.md`.

Producer lists are **created in the Content Library UI**, not via the API, and
read with `lists/producers/{list_id}` — not `producer-lists/{id}`, which 404s.
**A list is invisible to the API until you generate an API ID for it** (UI:
*View* → the down-arrow next to *Share* → **Create API list ID**). That id is a
**snapshot** of the list, so curate first and generate second. See
`references/producer_lists.md` for the CSV import format, the API-ID step and its
snapshot semantics, the response shape, and batching.

- **preview** (GET): Sync, max 1000 results total - exploration only
- **job** (POST): Async, up to ~100,000 results - use for research
- **estimate** (GET): Check result count before querying

Two different caps hide behind "1000": a sync search pages through **1000
results in total**, and each page is capped by `limit`, whose maximum was cut
from 500 to **100** on 2025-07-15. Channel message and update previews are
tighter still — `limit` is 0-50, default 10.

**Paging a `preview`** — **[verified 2026-08-29]**: the response carries
`paging.cursors.after` (an opaque ~100-char string). Pass it back as the `after`
parameter for the next page; it is absent or empty on the last one.

**A preview is the top of a sort order, not a sample — at any depth.** The v5.0+
default is `most_to_least_views`, so one page is the most-viewed 100, and
**paginating does not fix it**: 1,000 rows is still the most-viewed 1,000.

Measured 2026-08-29: 500 links harvested from one producer list found **0** URLs
from two long-tail domains that the same frame's census records 206 and 158 post
links for. Re-running the **same** producers and window with `newest_to_oldest`
and `oldest_to_newest` and pooling gave 1,228 links, **79** of them from one of
those domains. Zero to 79 on a sort change alone.

**Set `sort` deliberately, and pool across sort orders when you need the tail.**
Any long-tail, low-credibility or small-publisher analysis built on a default
preview is measuring the head and calling it the distribution.

Code: `languages/r/query_params.md` § "Paging a preview" · `languages/python/query_params.md` § "Paging a preview"

## Nested Endpoints

Some resources require parent IDs in the URL path, not as query parameters:

| Resource | Pattern | Example |
|----------|---------|---------|
| Facebook post comments | `/facebook/posts/{post_id}/comments/preview` | Get comments on a post |
| Facebook comment replies | `/facebook/comments/{comment_id}/replies/preview` | Get replies to a comment |
| Instagram post comments | `/instagram/posts/{post_id}/comments/preview` | Get comments on a post |
| Instagram comment replies | `/instagram/comments/{comment_id}/replies/preview` | Get replies to a comment |
| Instagram channel messages | `/instagram/channels/{channel_id}/messages/preview` | Get channel messages |
| Instagram channel comments | `/instagram/channels/{channel_id}/comments/preview` | Get channel comments |
| Facebook channel messages | `/facebook/channels/{channel_id}/messages/preview` | Get channel messages |
| WhatsApp channel updates | `/whatsapp/channels/{channel_id}/updates/preview` | Get channel updates |
| Facebook donations | `/facebook/fundraisers/{fundraiser_id}/donations/preview` | Get a fundraiser's donations |

```
✓ Correct   GET instagram/posts/{post_id}/comments/preview   params: limit
✗ Wrong     GET instagram/comments/preview                  params: post_ids   (path does not exist)
```

### The general shape: ID-based retrieval

Both patterns above are instances of one rule — an MCL ID can be put **in the
path**, on its own or followed by a nested resource:

```
{entity_type}/{mcl_id}/preview                      # one entity by ID
{entity_type}/{mcl_id}/{nested_resource}/preview    # its children
```

Documented as supported for Facebook pages, groups, events, profiles, posts,
comments, Marketplace listings, fundraisers, donations, channels and channel
messages; Instagram accounts, posts, comments, fundraisers, channels and channel
messages; WhatsApp channels and channel updates; and nonprofits. These are sync
reads, so the 1,000-result page cap applies — go async when you need more.

Code: `languages/r/query_params.md` § "Nested endpoints" · `languages/python/query_params.md` § "Nested endpoints"

## Finding Surface IDs (MCL IDs ≠ Facebook/Instagram URL IDs)

**Critical:** The numeric IDs in Facebook/Instagram URLs are **NOT** valid Meta Content Library IDs. MCL assigns its own library-specific IDs (privacy by design). Passing a raw URL ID as `surface_ids` / `account_ids` fails with `error_subcode 3790088` ("Invalid Meta Content Library ID").

You must look the entity up by name and read the `id` MCL returns. Lookup
endpoints by entity (search with `q`, read `id` from `data`):

| Entity | Endpoint | ID used in queries |
|--------|----------|--------------------|
| Facebook group    | `facebook/groups/preview`    | `surface_ids` |
| Facebook page     | `facebook/pages/preview`     | `surface_ids` |
| Facebook profile  | `facebook/profiles/preview`  | `surface_ids` |
| Instagram account | `instagram/accounts/preview` | `account_ids` |

**ID params are arrays.** `surface_ids` / `account_ids` / `post_ids` must be
passed as arrays — a scalar is rejected with `"Invalid parameter"`, and that
includes a single ID. Each language file says how to guarantee an array at
every length. `post_ids` accepts at most **250 IDs per call**; chunk longer
lists, and keep `surface_ids` batches at ≤ 250 too — see
`references/query_params.md` § "ID Parameter Batch Limits".

Notes:
- Group search only covers **public** groups indexed in the Content Library; a private or non-indexed group won't appear and isn't queryable.
- Always hard-code and pass IDs as **quoted strings** — see [ID Handling](#id-handling-ids-are-strings).
- Disambiguate similar names using `member_count` (and `description` if present).
- The client expects `params` to be a mapping; do not pass an empty, unnamed
  container. Omit `params` when there are none.

Code: `languages/r/query_params.md` § "Looking up a surface ID" · `languages/python/query_params.md` § "Looking up a surface ID"

## Safe Response Handling

API responses may return nothing, an empty `data`, or a non-tabular object.
Always validate before counting rows. Each layer has a `safe_get_data()` funnel
that parses with the ID-safe helper and returns either the rows or nothing.

Code: `languages/r/jobs.md` § "Safe response handling" · `languages/python/jobs.md` § "Safe response handling"

## Waiting for a Job

**[verified 2026-08-21]** `get_status()` returns **`COMPLETE`** — uppercase.
Observed on four separate jobs against v6.0; the 2025-11-10 REST-ful pass did
**not** lowercase job status. A bare
`while (status != "COMPLETE")` would not, in fact, have spun.

Keep using a helper anyway. One session on one API version is not a contract,
the failure mode if that changes is silent, and the helper costs nothing:

- `while (status != "COMPLETE")` against `"complete"` — **spins forever**, no error
- `while (status == "IN_PROGRESS")` against `"in_progress"` — **exits immediately**
  and reads a half-written result as if it were final

The helper upper-cases and trims the status, returns on `COMPLETE`, raises on
`FAILED`, times out, and treats any other status as "keep waiting". Every wait
in this skill goes through it. If you compare a status yourself, compare the
normalized value, never the raw return.

Casing is settled and **not uniform across parameters** — see the table in
`references/query_params.md` § "Post Filters".

Code: `languages/r/jobs.md` § "Waiting for a job" · `languages/python/jobs.md` § "Waiting for a job"

## Async Query Template

Four steps, in this order:

1. **Estimate** — `GET {platform}/{resource}/estimate` with the same parameters;
   read `estimated_results` and `expected_complete` before spending budget.
2. **Submit** — `POST {platform}/{resource}/job` with `mode = "SNAPSHOT"`, a
   `name` and a `description`. The response carries `id` (the job) and
   `query_id` (the reusable query).
3. **Wait** — `get_async_job(job_id=…)`, then the wait helper.
4. **Save, then load with IDs as strings** — `write_data_to_file(directory=,
   filename=)`, then parse the saved file with the ID-safe helper.

Code: `languages/r/jobs.md` § "Async query template" · `languages/python/jobs.md` § "Async query template"

## Rate Limits & Budget

| Resource | Limit |
|----------|-------|
| Sync queries | 60/minute |
| Async queries | 1/minute |
| Query budget | 500,000 records/7-day rolling (default — per-account, raisable) |
| Comment budget | 500,000 comments/7-day rolling (default, separate pool) |
| Max async results | ~100,000 per query |
| Snapshots | 100 concurrent per user (subcode 3790172; LIVE jobs are exempt) |
| Comment estimate | Reports "1 million or more" above 1,000,000 |
| Multimedia queries | 1,000 per rolling week — **third-party cleanroom environments only**, not the SRE |

The 7-day window is rolling *"to the second"*, not to the day: each query's usage
expires exactly seven days after it was submitted.

**The two 500,000 figures are defaults, not API constants.** The ceiling is a
per-account setting that Meta support will raise on request, so **never hard-code
it** — read `max_usage_limit` from `budgets` and compute headroom from
that. Any code or threshold that assumes 500,000 is wrong on a raised account,
and wrong again when the increase lapses.

Increases are granted as a **doubling, for three months at a time**, applied to
the Content Library UI and the API together, and they **expire** — the limit
reverts with no notification. `references/utilities.md` § "Quota increases".
[documented — from Meta support, 2026-08-31; not measured]

`budgets` reports four numbers per pool, not two:
`current_usage`, `preallocated_rows_for_running_queries`, `total_usage` and
`max_usage_limit`. **`preallocated_rows_for_running_queries` is the reason a
deleted job does not refund budget** — rows are reserved when the job is
submitted, not when it finishes. `references/utilities.md` § "Check Quota Status"
reads all four.

Code: `languages/r/utilities.md` § "Budget headroom" · `languages/python/utilities.md` § "Budget headroom"

## SNAPSHOT vs LIVE Mode

Use **SNAPSHOT** for anything you need to reproduce or share: it is refreshed
every 30 days, the job can be shared, and Meta documents retention as up to a
year. **Do not plan on that year — see the box below.** **LIVE** data
is deleted after 30 days and cannot be shared — but LIVE jobs do **not** count
against the 100-snapshot cap, so run exploration LIVE and save results to disk.
**Deleting a job does NOT refund its budget charge** — confirmed by the researcher
2026-08-23 after a duplicate submission. Budget is consumed at submission; deletion only frees
the snapshot slot. So the cost of an accidental double-submission is the full second charge,
permanently. **Guard every submission cell** so a re-run is a no-op — check for
the file the first run wrote before submitting again.

> ⚠ **Measured 2026-09-02: no job survives the monthly wipe, SNAPSHOT included.**
>
> `async/jobs`, read the morning after a wipe on an account that had been
> submitting steadily, returned **24 jobs — every one `EXPIRED`, every one
> `SNAPSHOT`**, created between 2026-08-21 and 2026-08-30. The newest was
> **three days old**. Jobs from earlier were absent from the listing entirely,
> and fetching one by id returned `error_subcode 3790112`, *"ID is unavailable
> in MCL system or you don't have access."*
>
> The wipe deletes **"All S3 bucket files"** (`references/utilities.md`
> § "The monthly wipe") and job outputs live in S3, which is the likely
> mechanism. Either way **the documented one-year retention does not survive a
> month boundary**, and no design may rely on it.
>
> **Consequence — download every job's results to disk in the same calendar
> month you submit it.** A job id is not a durable handle; only the downloaded
> data is. Echoing job ids into a markdown cell so they outlive the wipe is
> necessary and **not sufficient**: the id survives, the job behind it does not.

A LIVE job can be promoted later with `POST async/jobs/{job_id}/snapshot`.

Full comparison, the 100-snapshot cap (subcode 3790172), and how to free slots:
`references/collections.md` § "The 100-Snapshot Cap".

Code: `languages/r/jobs.md` § "Guarding a submission cell" · `languages/python/jobs.md` § "Guarding a submission cell"

## The 100,000 Result Limit

The cap is **per query**. It surfaces two ways: silently, as
`expected_complete = FALSE` on the estimate with truncated results, or as a hard
failure with `error_subcode 3790057` ("Estimated response size too large"). Check
`estimated_results` before submitting.

**Solutions:**
1. Split by **date** into smaller windows (months/quarters/weeks)
2. Add more filters, or query fewer `surface_ids` per call
3. See `references/chunking.md` for automated chunking

To collect only the latest N results, iterate date windows **newest-first** and
stop once N is reached — see `references/chunking.md` § "Collecting Only the
Latest N Results".

## Rerun a Query

`POST async/queries/{query_id}/job` with a body of `mode` creates a new job for
an existing query; the response's `id` is the new job.

Code: `languages/r/jobs.md` § "Rerunning a query" · `languages/python/jobs.md` § "Rerunning a query"

## API Search IDs — run a UI search from code

**[added 2026-08-25 from Meta's docs]** A search built in the Content Library UI
can be handed to the API as an **API search ID** (`alias_id`) — an alias for the
query *and all its filters*. It stores the search, never the results.

The format is the same date-slug shape as job and producer-list IDs:
`2024-10-12-iehs`, `2024-10-12-iut-opq`. Like those, it is already a string —
none of the [ID Handling](#id-handling-ids-are-strings) hazards apply.

**Create it in the UI**: run the search → *Create API search ID* in the top menu
bar (or, from a saved search: *Saved searches* → **…** → *Create API search ID*).

**Use it from code** — the ID goes in the **path**, not in `params`:
`GET facebook/posts/preview/{alias_id}` runs it synchronously,
`POST facebook/posts/job/{alias_id}` with `mode`, `name` and `description` runs
it as a job, and `GET lists/shared-searches/{alias_id}` inspects it without
running it.

`lists/shared-searches/{alias_id}` returns `id`, `creation_time`, `platform`
(facebook or instagram), **`filters_sync_search`** and **`filters_async_search`**
(the same filters formatted for each call style), and `version` — the API version
current when the alias was made. Read it before running an alias you did not
create: an alias is opaque, and this is the only way to see what it will query.

**Override individual filters** by appending parameters to the call; the rest of
the stored search is preserved. This is the clean way to re-run someone else's
search over your own date window.

Two things to know before relying on it:

- **Available for Facebook and Instagram post searches**, and shareable only with
  users who have **the same account type** as you.
- **A UI search that returns more than 100,000 results will fail as an async
  job.** The UI shows you the result count; check it there before replaying the
  search here. The same applies to the *Get API code* button (`</>` in the UI
  menu bar), which generates a ready-made R or Python snippet for the current
  search — convenient, and under no obligation to fit inside the API's caps.

Producer lists have the same UI-to-API bridge, with its own snapshot semantics:
`references/producer_lists.md` § "Share producer lists between the UI and the
API".

Code: `languages/r/query_params.md` § "Running an API search ID" · `languages/python/query_params.md` § "Running an API search ID"

## Citing the Data

Meta assigns a **DOI per version**, and the API and the Library are cited
separately. For v6.0:

| Product | Citation |
|---|---|
| Content Library **API** | Meta Platforms, Inc., (Month Accessed, Year Accessed). Meta Content Library API version v6.0 <https://doi.org/10.48680/meta.metacontentlibraryapi.6.0> |
| Content **Library** (the UI) | Meta Platforms, Inc., (Month Accessed, Year Accessed). Meta Content Library version v6.0 <https://doi.org/10.48680/meta.metacontentlibrary.6.0> |

Cite the version you actually queried, not the current one — the DOI is
version-specific precisely because the data scope changes between versions (the
follower threshold alone moved 25,000 → 1,000 → 100 across v4.0, v5.0 and v6.0).
`LATEST_VERSION` in the [Setup](#setup) block means a notebook re-run after a
version bump is querying a different corpus than the paper described; pin the
version explicitly with `set_default_version()` if that matters.

Current list, including older versions:
<https://developers.facebook.com/docs/content-library-and-api/citations>.

## Common Errors

These are the errors that change how you write a query in the first place. For
the diagnostic long tail — type mismatches, silent join misses, empty responses,
wrong response fields — see `references/common_errors.md`. Errors that exist
only because of how a language talks to the client are in
`languages/r/common_errors.md` and `languages/python/common_errors.md`.

| Error | Cause | Fix |
|-------|-------|-----|
| Method not allowed | GET on /job endpoint | Use POST |
| Results limited to 1000 | Using sync /preview | Switch to async /job |
| Type mismatch | An integer parameter arrived as a float | Send integers as integers — R needs the `L` suffix |
| Invalid parameter | Wrong ID param for platform | Facebook: `surface_ids`, Instagram: `account_ids` |
| Invalid parameter with the right param name | ID param sent as a scalar (a comma-joined string, or a single ID not wrapped in an array) | Pass an array at every length — see the language file |
| Invalid Keyword Search (subcode 3790184) | Query used a double-quoted phrase | Remove double quotes. There is no phrase search to reach — matching is word by word |
| **No error — silently narrower results** | `q` used the *words* `AND` / `OR` / `NOT`. Meta documents only the symbols `&` (or a space), `\|` and `-` | Use `climate \| policy`, `climate policy`, `vaccine -covid` — see `references/query_params.md` § "Query Syntax" |
| **No error — only top-level comments** | A comments job without `fetch_all` | `fetch_all = TRUE` returns every reply level |
| 404 on `{platform}/comments/preview` | That path does not exist | Sync comments hang off the parent post/comment; bulk comments go through `{platform}/comments/job` |
| Invalid Meta Content Library ID (subcode 3790088) | Used a raw Facebook/Instagram URL ID as `surface_ids`/`account_ids` | Search the entity by name (e.g. `facebook/groups/preview` with `q`) and use the returned `id` |
| Invalid Meta Content Library ID (subcode 3790088) with a *correct* ID | ID held as a float, so it was sent as `9.6378e+14` | Parse with the ID-safe helper; pass IDs as quoted strings — see [ID Handling](#id-handling-ids-are-strings) |
| Estimated response size too large (subcode 3790057) | Query would return more than ~100,000 results | Split by date window, and/or query fewer `surface_ids` |
| Exceeded async snapshots limit (subcode 3790172) | More than 100 concurrent SNAPSHOT jobs | Use `mode = "LIVE"` when reproducibility isn't needed; delete finished snapshots |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset |
| Producer-list post query estimates ~0 results | List is mostly ordinary profiles, whose posts aren't in the queryable dataset | Verified or 100+ follower profiles only — see `references/field_reference.md` § "Data Scope" |

## Staying Current

This skill is a transcription of documentation that changes without warning, and
**a stale field name fails silently** — `fields` drops unknown names without
erroring, and column selection by name drops them again. That failure mode is
why this section exists: nothing will tell you the skill is out of date.

### Baseline — what the last check found

> **Documentation checked: 2026-08-25.** Two changelogs are watched, and at that
> date the newest **dated** entry on each was:
>
> | Tree | Newest entry |
> |---|---|
> | [Content Library and API](https://developers.facebook.com/docs/content-library-and-api/changelog) | **2026-04-30** — WhatsApp channels data, which this skill covers |
> | [Secure Research Environment](https://developers.facebook.com/docs/researcher-platform/changelog) | **2025-08-18** — the Researcher Platform → Secure Research Environment rename |
>
> Everything below v6.0 in Meta's version list was already reconciled.

State the baseline as a *finding*, not just a date: the next checker compares one
entry against another rather than doing arithmetic on when someone last looked.

### When to check

**Do not fetch on every invocation.** Two rules, both cheap to evaluate:

1. **If today is more than ~30 days past the baseline date**, say so in one line
   and offer to check. Do not block the researcher's actual question on it. A
   natural hook: the SRE is unavailable on the first of each month anyway
   (`references/utilities.md` § "The monthly wipe"), so that day is already lost
   to querying and is a good one to spend on this.
2. **If stale *and* you are about to assert something this skill marks as
   documentation-sourced rather than `[verified DATE]`, check first.** The
   provenance markers exist precisely so this rule is decidable — a table headed
   "Documented, not tested" or a row without a `[verified]` stamp is exactly the
   kind of claim that a docs change invalidates. A `[verified]` observation is
   safer, because it was true of a real response.

**The changelogs are the tripwire** — fetch only the two pages named above,
compare each one's topmost dated entry against the baseline, and stop if
nothing is newer. How to read those pages, what a clean run does and does not
prove, how to record the result, what to say when you cannot fetch, and how the
source repository automates the check: `references/staying_current.md`.

### Where a changed page lands in this skill

Derived 2026-08-25 by reconciling every page against every file. Use it to go
straight from a changelog entry to the file that owns the fact — and to be sure
a change is recorded once rather than in three places. A page owns a *fact*
here; the code that exercises it lives in `languages/<lang>/<same basename>.md`.
Change the fact once, then check both mirrors.

| Meta page | Owner in this skill |
|---|---|
| `guides/search-guide`, `guides/advanced-search` | `references/query_params.md` § "Query Syntax (`q`)" |
| `guides/rate-limiting` | SKILL.md § "Rate Limits & Budget"; `references/utilities.md` § "Check Quota Status" |
| `guides/data-deletion` | `references/utilities.md` § "The monthly wipe" |
| `guides/fb-posts`, `guides/ig-posts` | `references/field_reference.md` (post tables); `query_params.md` (post filters) |
| `guides/fb-comments`, `guides/ig-comments`, `guides/bulk-comments` | `field_reference.md` (comment tables); `query_params.md` § "Comments Queries" |
| `guides/fb-pages`, `fb-groups`, `fb-events`, `fb-profiles`, `ig-accounts` | `field_reference.md` (producer tables); `query_params.md` (ID params, sort defaults) |
| `guides/fb-channel*`, `ig-channel*`, `wa-channel*`, `fb-marketplace`, `fb-fundraisers`, `ig-fundraisers`, `fb-donations` | `references/surfaces.md` — owns both parameters and fields for these |
| `guides/id-based-retrieval` | SKILL.md § "Nested Endpoints" |
| `appendix/data` (the data dictionary) | `field_reference.md` and `surfaces.md` — field names for every surface |
| `appendix/field-expansion` | `query_params.md` § "Field expansion" |
| `appendix/search-quality` | `query_params.md` § "How good is the search?" |
| `appendix/share-producer-list` | `references/producer_lists.md` |
| `appendix/api-search-id` | SKILL.md § "API Search IDs"; code `languages/*/query_params.md` |
| `appendix/get-api-code` (emits R or Python) | SKILL.md § "API Search IDs" |
| `content-library-api/overview` | `field_reference.md` § "Data Scope" — geography, audience limits, the download prohibition |
| `content-library-api/quick-start` (R and Python tabs), `get-access` | SKILL.md § "Environment" and § "Setup"; code `languages/r/setup.md`, `languages/python/setup.md` |
| `citations` | SKILL.md § "Citing the Data" |
| `support` | `docs/SUPPORT_TICKET_ML_MODELS.md` |
| `researcher-platform/features/install-r` | `languages/r/utilities.md` |
| `researcher-platform/pip` | `languages/python/utilities.md` |
| `researcher-platform/features/ml-models` | `references/utilities.md` (paths, proxy, errors, org prefix); code `languages/*/utilities.md`; the list `references/ml_models_approved.md` |
| `researcher-platform/features/*`, `secure-research-environment/*` | `references/utilities.md` — export, packages, GPU, the monthly wipe. **Anything about *driving* the SRE is a client's concern, not this skill's** |

## Contributing Back

"Staying Current" is the loop that brings Meta's documentation *into* this
skill. This section is the loop in the other direction: what a session *taught*,
carried back to the source. The skill is largely transcribed from documentation,
and only execution catches the errors that matter — the v1.18.0 entry in
`CHANGELOG.md`, where a "preserved up to a year" claim turned out not to survive
a month boundary, is what one live observation is worth. The same principle as
above applies: **a session that writes its findings nowhere did not happen.**

The Python layer is where this matters most right now: every section there is
`[documented]`, and one successful call from a Python kernel promotes it.

### When — two rules, both cheap

1. **On the spot.** The moment a live response disagrees with something this
   skill states, or confirms a claim it marks as `[documented]` or "Documented,
   not tested", say so to the researcher in one line and keep it as a **field
   note** (shape below). Write the note when the finding is fresh, not at the
   end — a note deferred to the end is a note that is usually never written.
2. **At a natural close.** When the researcher's question is answered, they say
   they are done, or the topic changes: if there is at least one field note,
   offer **once** —

   > "This session taught N things this skill did not know. Want me to write
   > them up as a field report?"

   Never block the researcher's question on it. Never repeat the offer. No
   notes, no offer. *A client that runs unattended may replace the offer with
   its own end-of-run step; the notes and the report shape are unchanged.*

### The field note

One line, six parts, written the moment the finding appears:

```
kind · language · file § section · what the skill says · what was observed · date
```

For example, the note that became the `3790079` row in `references/common_errors.md`:

```
addition · R · common_errors.md § Scope and Quota Errors · no row for 3790079 · "Invalid time range" (3790079) with until = today: "the until time must come before current_epoch_time" · 2026-08-29
```

### What counts

Four kinds, keyed to the provenance tags this skill already uses:

| Kind | You saw | It becomes |
|---|---|---|
| **correction** | a stated fact was wrong live — an endpoint 404s, a parameter is rejected, an enum's casing differs, a cap is not where stated | the fix, stamped `[verified DATE]`, and a changelog entry that says what the documentation said, what was observed, and which one won |
| **promotion** | a claim marked `[documented]` or "Documented, not tested" behaved as documented | the same sentence with a `[verified DATE]` stamp. **The cheapest and most under-filed contribution there is**; it takes one successful call |
| **addition** | an error subcode, field, limit or behaviour this skill does not mention | a new row or paragraph at the file that owns the topic — use the owner map in "Staying Current" |
| **open** | one observation that could be transient or account-specific | `docs/OPEN_QUESTION_<topic>.md`, in the shape of the ones already there |

**What does not count.** The triage question is always the same: *would this
sentence still be true for a different research question on a different
corpus?* If not, it belongs to the study, not here. Also not this skill's:
anything about driving the SRE's notebook or browser surface (that is a
client's concern), and the SRE's operational state on a given day. And **never
any data** — no post text, no user names, no result rows. Error messages,
subcodes, endpoint paths, parameter values, field names and counts are fine;
MCL content is not, and it does not leave the SRE for any reason.

### Where and how

`references/field_report.md` owns the template, a filled example, the three
routes a report can travel (a pull request from a clone, the *Field report*
issue form, or markdown handed to the researcher), and what happens to a report
once it arrives. Four things make a report actionable, and a report missing any
of them is not: the **skill version** (from the frontmatter of this file), the
**language** the call was made from, the **date observed**, and the **verbatim
API response** — message and `error_subcode`, or the response's field names.

## References

Facts live in `references/`; the call that exercises them lives under the same
basename in each language directory.

| Topic | Facts | R (verified) | Python (documented) |
|---|---|---|---|
| Setup, client, version pinning | SKILL.md § "Setup" | `languages/r/setup.md` | `languages/python/setup.md` |
| IDs as strings | SKILL.md § "ID Handling (IDs Are Strings)" | `languages/r/ids.md` | `languages/python/ids.md` |
| Async jobs: wait, template, guard, rerun | SKILL.md § "Waiting for a Job" and following | `languages/r/jobs.md` | `languages/python/jobs.md` |
| Search parameters, filters, `q` syntax, batch limits | `references/query_params.md` | `languages/r/query_params.md` | `languages/python/query_params.md` |
| Large dataset chunking | `references/chunking.md` | `languages/r/chunking.md` | `languages/python/chunking.md` |
| Collections, the 100-snapshot cap | `references/collections.md` | `languages/r/collections.md` | `languages/python/collections.md` |
| Producer lists: endpoint, sharing, batching, matching | `references/producer_lists.md` | `languages/r/producer_lists.md` | `languages/python/producer_lists.md` |
| Quota, packages, ML models, the wipe, export, job retrieval | `references/utilities.md` | `languages/r/utilities.md` | `languages/python/utilities.md` |
| Error catalog and debugging | `references/common_errors.md` | `languages/r/common_errors.md` | `languages/python/common_errors.md` |
| Fields by entity, reshare resolution, data scope | `references/field_reference.md` | `languages/r/field_reference.md` | `languages/python/field_reference.md` |
| Analysis patterns on collected results | `references/common_patterns.md` | `languages/r/common_patterns.md` | `languages/python/common_patterns.md` |
| Channels, Marketplace, fundraisers, donations | `references/surfaces.md` | `languages/r/surfaces.md` | `languages/python/surfaces.md` |
| Approved ML models, canonical repo ids | `references/ml_models_approved.md` | — | — |
| The documentation check in full | `references/staying_current.md` | — | — |
| Field report template and routes | `references/field_report.md` | — | — |

Version history: [CHANGELOG.md](CHANGELOG.md)

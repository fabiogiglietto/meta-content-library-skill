---
name: mcl-api
description: "Meta Content Library (MCL) API v6.0 in R. Use when querying Facebook, Instagram or WhatsApp content via reticulate in the SRE or SOMAR VDE: async queries, producer lists, SNAPSHOT mode, IDs, quotas."
version: 1.19.0
updated: 2026-09-04
---

# Meta Content Library API v6.0 — R and Python

> **Skill Version:** 1.19.0 | **Updated:** 2026-09-04 | [Changelog](CHANGELOG.md)

## Environment

- **Platform**: Amazon WorkSpaces Secure Browser with JupyterLab — there are
  **two portals, United States and Ireland**; pick the one your access was
  granted for
- **Language**: R with Python client via reticulate
- **Export**: notebook only, and **its outputs are stripped** — code, markdown and
  **images** survive; cell outputs, stdout, stderr and HTML do not. Numbers do not
  leave as numbers. See `references/utilities.md` § "Getting Results Out"
- **No internet access** *(inside the SRE — not for you; see below)*: R packages
  come from a custom CRAN mirror and pre-trained ML models from an approved
  Hugging Face list — see `references/utilities.md`
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
- **Anything else, when this skill is more than a month stale** — see
  [Staying Current](#staying-current) at the end of this file. It is one page
  fetch, and it tells you whether the rest of the file can be trusted.

## Critical Requirements

1. **Always use async queries** (POST to `/job` endpoints) for research
2. **Integer literals**: Use `L` suffix (e.g., `limit = 100L`)
3. **Always document**: Include `name`, `description`, `mode = "SNAPSHOT"` in every query
4. **Use `flush.console()`** after `cat()` in Jupyter for real-time output
5. **Safe response handling**: Always validate API responses before calling `nrow()` — see [Safe Response Handling](#safe-response-handling)
6. **IDs are character, always**: Never let `fromJSON()` parse an ID into a `numeric`. Parse every MCL response with `mcl_fromJSON()` — see [ID Handling](#id-handling-always-load-ids-as-character)

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

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
async_utils <- import("metacontentlibraryapi")$MetaContentLibraryAPIAsyncUtils
client$set_default_version(client$LATEST_VERSION)
```

Also define `mcl_fromJSON()` from [ID Handling](#id-handling-always-load-ids-as-character) — every example in this skill parses responses with it instead of `fromJSON()`.

## ID Handling (Always Load IDs as Character)

MCL IDs are 15–19 digit numbers. Some endpoints return them **unquoted** in JSON, and `jsonlite::fromJSON()` then parses them as `numeric`. Two things break:

- **Silent precision loss** above 2^53 (~9.0e15): `17841400000000123` comes back as `17841400000000124`. Unrecoverable after parsing — no post-hoc coercion can restore the digits.
- **Scientific notation** below 2^53: the value is exact but prints/pastes as `9.6378e+14`, so `paste0("instagram/posts/", post_id, "/comments/preview")` builds a garbage URL and the API answers *"Invalid Meta Content Library ID"* (subcode 3790088) — the same error you get from a raw URL ID.

There's also a typing hazard: `bigint_as_char = TRUE` alone converts a column **only when some value in that batch exceeds 2^53**, so the same column is `chr` in one chunk and `num` in the next, and `bind_rows()` fails with *"Can't combine `id` <character> and `id` <double>"*.

**Scope note — [verified 2026-08-21].** This applies to **post, producer and
surface** ids, which are 16-digit numerics. It does **not** apply to **async job
ids** or **producer-list ids**, which in v6.0 are date-slugs of the form
`2026-08-21-nqw-ytm` and `2026-08-17-cwqm`. Those are already strings and carry
no scientific-notation hazard.

**Fix both at once — parse with `bigint_as_char = TRUE`, then coerce every ID field unconditionally:**

```r
# Matches id, post_id, surface_ids, parent_id, and flattened author.id / producer.id
MCL_ID_PATTERN <- "(^|[._])ids?$"

mcl_fix_ids <- function(x, name = "") {
  if (is.data.frame(x)) {
    x[] <- Map(mcl_fix_ids, x, names(x))
    return(x)
  }
  if (is.list(x)) {                      # nested lists and list-columns of IDs
    nms <- names(x)
    if (is.null(nms)) nms <- rep(name, length(x))
    x[] <- Map(mcl_fix_ids, x, nms)
    return(x)
  }
  if (grepl(MCL_ID_PATTERN, name) && is.numeric(x)) {   # numeric only: is_invalid_id stays logical
    out <- rep(NA_character_, length(x))  # keeps JSON null as NA, not the string "NA"
    ok <- !is.na(x)
    out[ok] <- sprintf("%.0f", x[ok])     # full digits, never scientific notation
    return(out)
  }
  x
}

# Use this for EVERY MCL response — response text or a job's saved .json file
mcl_fromJSON <- function(txt) {
  mcl_fix_ids(fromJSON(txt, flatten = TRUE, bigint_as_char = TRUE))
}
```

Rules that follow from this:

| Do | Don't |
|----|-------|
| `mcl_fromJSON(resp$text)` | `fromJSON(resp$text, flatten = TRUE)` |
| `mcl_fromJSON(file.path("results", "job.json"))` | `fromJSON(filepath, flatten = TRUE)` |
| `sprintf("%.0f", x)` to fix a stray numeric ID | `as.character(x)` — returns `"1.784e+16"` for big IDs |
| `read_csv(f, col_types = cols(.default = col_character()))` | `read_csv(f)` — re-parses ID columns as double |
| Keep IDs as character in `distinct()`, joins, and `as.list(ids)` params | Comparing/merging on numeric IDs |

`options(scipen = 999)` only changes **display** — the value is still a double and still rounds above 2^53. It is not a fix.

If an ID reaches R as a number from somewhere else (a CSV, a Python object via reticulate, a spreadsheet), convert it with `sprintf("%.0f", x)` immediately — and treat anything at or above 2^53 as already corrupted, since re-fetching it from MCL is the only way back.

## OpenAPI Spec

Retrieve the complete API spec programmatically (v6.0+) — use it to discover
endpoints, parameters, and response schemas, and to settle any question this
skill does not answer:

```r
spec <- client$openapi_spec()
paths <- names(spec$paths)

# Find Instagram endpoints
instagram_paths <- paths[grepl("instagram", paths, ignore.case = TRUE)]
print(instagram_paths)

# Inspect one endpoint's parameters
str(spec$paths[["/instagram/posts/preview"]]$get$parameters)

# Save full spec for reference
write(toJSON(spec, pretty = TRUE), "openapi_spec.json")
```

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
`paging$cursors$after` (an opaque ~100-char string). Pass it back as the `after`
parameter for the next page; it is absent or empty on the last one.

```r
acc <- list(); after <- NULL
repeat {
  p <- c(base_params, if (!is.null(after)) list(after = after))
  pg <- mcl_fromJSON(client$get(path = "facebook/posts/preview", params = p)$text)
  acc <- c(acc, list(pg$data))
  after <- pg$paging$cursors$after
  if (is.null(after) || !nzchar(after)) break
}
```

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

```r
# ✓ Correct - post_id in URL path
client$get(
  path = paste0("instagram/posts/", post_id, "/comments/preview"),
  params = list("limit" = 10L)
)

# ✗ Wrong - post_id as parameter
client$get(
  path = "instagram/comments/preview",
  params = list("post_ids" = post_id)
)
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

## Finding Surface IDs (MCL IDs ≠ Facebook/Instagram URL IDs)

**Critical:** The numeric IDs in Facebook/Instagram URLs are **NOT** valid Meta Content Library IDs. MCL assigns its own library-specific IDs (privacy by design). Passing a raw URL ID as `surface_ids` / `account_ids` fails with `error_subcode 3790088` ("Invalid Meta Content Library ID").

You must look the entity up by name and read the `id` MCL returns:

```r
# GROUP -> get its MCL surface id (do NOT use the number from the group URL)
resp <- client$get(
  path   = "facebook/groups/preview",
  params = list("q" = "GROUP NAME", "limit" = 50L)
)
groups <- mcl_fromJSON(resp$text)$data
print(groups[, c("id", "name", "member_count")])   # use this `id`, not the URL number

GROUP_ID <- "PASTE_MCL_ID_FROM_SEARCH"   # quoted! e.g. "963780196442228", NOT the URL's 910620404641635
```

Lookup endpoints by entity (search with `q`, read `id` from `$data`):

| Entity | Endpoint | ID used in queries |
|--------|----------|--------------------|
| Facebook group    | `facebook/groups/preview`    | `surface_ids` |
| Facebook page     | `facebook/pages/preview`     | `surface_ids` |
| Facebook profile  | `facebook/profiles/preview`  | `surface_ids` |
| Instagram account | `instagram/accounts/preview` | `account_ids` |

**ID params are arrays.** `surface_ids` / `account_ids` / `post_ids` must be
passed as arrays — a scalar is rejected with `"Invalid parameter"`, and that
includes a single ID (reticulate converts a length-1 R vector into a Python
string). Use `as.list()` unconditionally:

```r
params[["surface_ids"]] <- as.list(ids)   # ✓ array at every length
params[["surface_ids"]] <- ids[1]         # ✗ sent as a scalar string
```

`post_ids` accepts at most **250 IDs per call**; chunk longer lists, and keep
`surface_ids` batches at ≤ 250 too — see `references/query_params.md` § "ID
Parameter Batch Limits".

Notes:
- Group search only covers **public** groups indexed in the Content Library; a private or non-indexed group won't appear and isn't queryable.
- Always hard-code and pass IDs as **quoted strings**. An unquoted 15+ digit literal in R is a double and will be sent in scientific notation → subcode 3790088.
- Disambiguate similar names using `member_count` (and `description` if present).
- Don't pass `params = list()` (empty list). reticulate converts it to a Python list `[]` and the client calls `.items()` on it → `'list' object has no attribute 'items'`. Omit `params` when there are none, or pass a named list.

## Safe Response Handling

API responses may return NULL, empty lists, or non-data.frame objects. Always validate before calling `nrow()`. This is the single funnel for MCL data — it parses with `mcl_fromJSON()`, so IDs come out as character:

```r
# ✓ Correct - safe pattern
safe_get_data <- function(response_text) {
  parsed <- mcl_fromJSON(response_text)   # IDs as character, see ID Handling
  if (!is.null(parsed$data) && is.data.frame(parsed$data) && nrow(parsed$data) > 0) {
    return(parsed$data)
  }
  return(NULL)
}

# Usage
resp <- client$get(path = "instagram/accounts/preview", params = list("q" = "test", "limit" = 10L))
results <- safe_get_data(resp$text)
if (!is.null(results)) {
  cat("Found", nrow(results), "results\n")
}

# ✗ Wrong - will error on NULL/empty responses, and mangles IDs into doubles
results <- fromJSON(resp$text, flatten = TRUE)$data
if (nrow(results) > 0) { ... }  # Error: missing value where TRUE/FALSE needed
```

## Waiting for a Job

**[verified 2026-08-21]** `get_status()` returns **`COMPLETE`** — uppercase.
Observed on four separate jobs against v6.0; the 2025-11-10 REST-ful pass did
**not** lowercase job status. A bare
`while (status != "COMPLETE")` would not, in fact, have spun.

Keep using the helper anyway. One session on one API version is not a contract,
the failure mode if that changes is silent, and the helper costs nothing:

- `while (status != "COMPLETE")` against `"complete"` — **spins forever**, no error
- `while (status == "IN_PROGRESS")` against `"in_progress"` — **exits immediately**
  and reads a half-written result as if it were final

It is correct under either casing, it cannot spin forever, and it treats an
unrecognized status as "keep waiting" rather than as success:

```r
mcl_job_status <- function(job) toupper(trimws(job$get_status()))

mcl_wait_for_job <- function(job, poll = 5, timeout = 3600) {
  deadline <- Sys.time() + timeout
  repeat {
    st <- mcl_job_status(job)
    if (st == "COMPLETE") return(st)
    if (st == "FAILED")   stop("Job failed (status: ", st, ")")
    if (Sys.time() > deadline)
      stop("Job did not finish within ", timeout, "s (last status: ", st, ")")
    cat("Status:", st, "\n"); flush.console()
    Sys.sleep(poll)
  }
}
```

Every wait in this skill goes through `mcl_wait_for_job()`. If you compare a
status yourself, compare `mcl_job_status(job)`, never the raw return value.

Casing is settled and **not uniform across parameters** — see the table in
`references/query_params.md` § "Post Filters".

## Async Query Template

```r
# 1. Check estimate
estimate_response <- client$get(
    path = "facebook/posts/estimate",
    params = list("q" = "climate change", "since" = "2024-01-01", "until" = "2024-12-31")
)
estimate <- mcl_fromJSON(estimate_response$text)
cat("Estimated:", estimate$estimated_results, "| Complete:", estimate$expected_complete, "\n")

# 2. Submit job (creates query + first job)
response <- client$post(
    path = "facebook/posts/job",
    params = list(
        "q" = "climate change",
        "since" = "2024-01-01",
        "until" = "2024-12-31",
        "limit" = 100L,  # Integer with L!
        "mode" = "SNAPSHOT",
        "name" = "Climate Change - 2024 Full Year",
        "description" = "Baseline dataset. PI: Dr. Smith, IRB #2024-001"
    )
)
job_data <- mcl_fromJSON(response$text)
job_id <- job_data$id          # character
query_id <- job_data$query_id  # character

# 3. Monitor status (see "Waiting for a Job" for mcl_wait_for_job)
job <- client$get_async_job(job_id = job_id)
mcl_wait_for_job(job)

# 4. Save results, then load with IDs as character
job$write_data_to_file(directory = "results", filename = "climate_2024.json")
posts <- mcl_fromJSON(file.path("results", "climate_2024.json"))
```

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
it** — read `max_usage_limit` from `budgets` (below) and compute headroom from
that. Any code or threshold that assumes 500,000 is wrong on a raised account,
and wrong again when the increase lapses.

Increases are granted as a **doubling, for three months at a time**, applied to
the Content Library UI and the API together, and they **expire** — the limit
reverts with no notification. `references/utilities.md` § "Quota increases".
[documented — from Meta support, 2026-08-31; not measured]

**Check budget:**
```r
budget <- mcl_fromJSON(client$get(path = "budgets")$text)
cat("Available:", budget$queries$max_usage_limit - budget$queries$total_usage, "\n")
```

`budgets` reports four numbers per pool, not two:
`current_usage`, `preallocated_rows_for_running_queries`, `total_usage` and
`max_usage_limit`. **`preallocated_rows_for_running_queries` is the reason a
deleted job does not refund budget** — rows are reserved when the job is
submitted, not when it finishes. `references/utilities.md` § "Check Quota Status"
reads all four.

## SNAPSHOT vs LIVE Mode

Use **SNAPSHOT** for anything you need to reproduce or share: it is refreshed
every 30 days, the job can be shared, and Meta documents retention as up to a
year. **Do not plan on that year — see the box below.** **LIVE** data
is deleted after 30 days and cannot be shared — but LIVE jobs do **not** count
against the 100-snapshot cap, so run exploration LIVE and save results to disk.
**Deleting a job does NOT refund its budget charge** — confirmed by the researcher
2026-08-23 after a duplicate submission. Budget is consumed at submission; deletion only frees
the snapshot slot. So the cost of an accidental double-submission is the full second charge,
permanently. **Guard every submission cell** so a re-run is a no-op:

```r
if (file.exists("jobs.rds")) stop("already submitted - delete jobs.rds to resubmit")
```

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

A LIVE job can be promoted later:

```r
client$post(path = paste0("async/jobs/", job_id, "/snapshot"))
```

Full comparison, the 100-snapshot cap (subcode 3790172), and how to free slots:
`references/collections.md` § "The 100-Snapshot Cap".

## The 100,000 Result Limit

The cap is **per query**. It surfaces two ways: silently, as
`estimate$expected_complete = FALSE` with truncated results, or as a hard failure
with `error_subcode 3790057` ("Estimated response size too large"). Check
`estimate$estimated_results` before submitting.

**Solutions:**
1. Split by **date** into smaller windows (months/quarters/weeks)
2. Add more filters, or query fewer `surface_ids` per call
3. See `references/chunking.md` for automated chunking

To collect only the latest N results, iterate date windows **newest-first** and
stop once N is reached — see `references/chunking.md` § "Collecting Only the
Latest N Results".

## Rerun a Query

```r
# Creates new job for existing query
rerun_response <- client$post(
    path = paste0("async/queries/", query_id, "/job"),
    body = list(mode = "SNAPSHOT")
)
new_job_id <- mcl_fromJSON(rerun_response$text)$id
```

## API Search IDs — run a UI search from R

**[added 2026-08-25 from Meta's docs]** A search built in the Content Library UI
can be handed to the API as an **API search ID** (`alias_id`) — an alias for the
query *and all its filters*. It stores the search, never the results.

The format is the same date-slug shape as job and producer-list IDs:
`2024-10-12-iehs`, `2024-10-12-iut-opq`. Like those, it is already a string —
none of the [ID Handling](#id-handling-always-load-ids-as-character) hazards
apply.

**Create it in the UI**: run the search → *Create API search ID* in the top menu
bar (or, from a saved search: *Saved searches* → **…** → *Create API search ID*).

**Use it from R** — the ID goes in the **path**, not in `params`:

```r
# Run the stored search synchronously
resp <- client$get(path = "facebook/posts/preview/2026-08-25-abcd")

# ... or as an async job
job <- client$post(path = "facebook/posts/job/2026-08-25-abcd",
                   params = list("mode" = "SNAPSHOT",
                                 "name" = "UI search, replayed",
                                 "description" = "PI: …, IRB #…"))

# Inspect the filters an alias carries, without running it
filters <- mcl_fromJSON(client$get(path = "lists/shared-searches/2026-08-25-abcd")$text)
```

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
`client$LATEST_VERSION` in the [Setup](#setup) block means a notebook re-run
after a version bump is querying a different corpus than the paper described; pin
the version explicitly with `client$set_default_version()` if that matters.

Current list, including older versions:
<https://developers.facebook.com/docs/content-library-and-api/citations>.

## Common Errors

These are the errors that change how you write a query in the first place. For
the diagnostic long tail — type mismatches, silent join misses, NULL responses,
wrong response fields — see `references/common_errors.md`.

| Error | Cause | Fix |
|-------|-------|-----|
| Method not allowed | GET on /job endpoint | Use POST |
| Results limited to 1000 | Using sync /preview | Switch to async /job |
| Type mismatch | Missing `L` suffix | Add `L` to integers |
| Invalid parameter | Wrong ID param for platform | Facebook: `surface_ids`, Instagram: `account_ids` |
| Invalid parameter with the right param name | ID param sent as a scalar (comma-joined string, or a length-1 vector reticulate turned into a string) | Pass an array: `as.list(ids)` |
| `'list' object has no attribute 'items'` | Passed `params = list()` (empty list) | Omit `params`, or pass a named list |
| Invalid Keyword Search (subcode 3790184) | Query used a double-quoted phrase | Remove double quotes. There is no phrase search to reach — matching is word by word |
| **No error — silently narrower results** | `q` used the *words* `AND` / `OR` / `NOT`. Meta documents only the symbols `&` (or a space), `\|` and `-` | Use `climate \| policy`, `climate policy`, `vaccine -covid` — see `references/query_params.md` § "Query Syntax" |
| **No error — only top-level comments** | A comments job without `fetch_all` | `fetch_all = TRUE` returns every reply level |
| 404 on `{platform}/comments/preview` | That path does not exist | Sync comments hang off the parent post/comment; bulk comments go through `{platform}/comments/job` |
| Invalid Meta Content Library ID (subcode 3790088) | Used a raw Facebook/Instagram URL ID as `surface_ids`/`account_ids` | Search the entity by name (e.g. `facebook/groups/preview` with `q`) and use the returned `id` |
| Invalid Meta Content Library ID (subcode 3790088) with a *correct* ID | ID held as `numeric`, so it was sent as `9.6378e+14` | Parse with `mcl_fromJSON()`; pass IDs as quoted character — see [ID Handling](#id-handling-always-load-ids-as-character) |
| Estimated response size too large (subcode 3790057) | Query would return more than ~100,000 results | Split by date window, and/or query fewer `surface_ids` |
| Exceeded async snapshots limit (subcode 3790172) | More than 100 concurrent SNAPSHOT jobs | Use `mode = "LIVE"` when reproducibility isn't needed; delete finished snapshots |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset |
| Producer-list post query estimates ~0 results | List is mostly ordinary profiles, whose posts aren't in the queryable dataset | Verified or 100+ follower profiles only — see `references/field_reference.md` § "Data Scope" |

## Staying Current

This skill is a transcription of documentation that changes without warning, and
**a stale field name fails silently** — `fields` drops unknown names without
erroring, and `intersect()`-style column selection drops them again. That failure
mode is why this section exists: nothing will tell you the skill is out of date.

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

### The check: two pages, then stop

**The changelogs are the tripwire.** Fetch only these:

| Page | Covers |
|---|---|
| <https://developers.facebook.com/docs/content-library-and-api/changelog> | the API — endpoints, fields, parameters, caps |
| <https://developers.facebook.com/docs/researcher-platform/changelog> | the environment — access, portals, storage, export |

Compare each one's topmost **dated** entry against the baseline above. The second
page is quiet — it had five entries in twenty months — but the environment is
half of what this skill asserts, and until 2026-08-25 nothing watched it at all.

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
  map below. A full reconciliation of all 25 guides is a day's work and is not
  what a monthly check is for.

Two things about the **Content Library** page that will otherwise waste a fetch: it interleaves
**dated** entries (no version number — the 2026 and 2025 changes) with
**versioned** ones (v5.0, v4.0…), and **v6.0 itself shipped as the undated
2025-11-10 "REST-ful API updates" entry**. So "is there a new version?" is the
wrong question; "is there a dated entry newer than the baseline?" is the right
one.

### Where a changed page lands in this skill

Derived 2026-08-25 by reconciling every page against every file. Use it to go
straight from a changelog entry to the file that owns the fact — and to be sure
a change is recorded once rather than in three places.

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
| `appendix/api-search-id`, `appendix/get-api-code` | SKILL.md § "API Search IDs" |
| `content-library-api/overview` | `field_reference.md` § "Data Scope" — geography, audience limits, the download prohibition |
| `content-library-api/quick-start`, `get-access` | SKILL.md § "Environment" and § "Setup" |
| `citations` | SKILL.md § "Citing the Data" |
| `support` | `docs/SUPPORT_TICKET_ML_MODELS.md` |
| `researcher-platform/features/*`, `secure-research-environment/*` | `references/utilities.md` — export, packages, GPU, the monthly wipe. **Anything about *driving* the SRE is the client's, not this skill's** |

### Record the result — including "nothing changed"

**A check that writes nothing down did not happen.** Next month's reader cannot
tell "checked, clean" from "never checked", and will pay for the fetch again.

- **Nothing new:** update the baseline date above and add one line to
  `CHANGELOG.md` — *"docs check 2026-09-25: newest dated entry still 2026-04-30,
  no action."* No version bump.
- **Something changed:** update the affected file, bump the baseline to the new
  entry, and follow the release checklist at the end of `CHANGELOG.md`.

### When you cannot fetch

Some surfaces this skill runs on have no web access. **Say so rather than
assuming the file is current**: "this skill's documentation baseline is
2026-08-25 and I can't check Meta's changelog from here — treat field names and
limits as of that date." Silence reads as currency, and that is the failure this
section exists to prevent.

### Who actually runs it

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

## Contributing Back

"Staying Current" is the loop that brings Meta's documentation *into* this
skill. This section is the loop in the other direction: what a session *taught*,
carried back to the source. The skill is largely transcribed from documentation,
and only execution catches the errors that matter — the v1.18.0 entry in
`CHANGELOG.md`, where a "preserved up to a year" claim turned out not to survive
a month boundary, is what one live observation is worth. The same principle as
above applies: **a session that writes its findings nowhere did not happen.**

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

One line, five parts, written the moment the finding appears:

```
kind · file § section · what the skill says · what was observed · date
```

For example, the note that became the `3790079` row in `references/common_errors.md`:

```
addition · common_errors.md § Query / Job Errors · no row for 3790079 · "Invalid time range" (3790079) with until = today: "the until time must come before current_epoch_time" · 2026-08-29
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

### Where

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

### Format

`references/field_report.md` owns the template and shows a filled example.
Three things make a report actionable, and a report missing any of them is
not: the **skill version** (from the frontmatter of this file), the **date
observed**, and the **verbatim API response** — message and `error_subcode`,
or the response's field names.

## References

- `references/query_params.md` - Search parameters, filters, and `q` syntax
- `references/chunking.md` - Large dataset handling
- `references/collections.md` - Organizing queries
- `references/producer_lists.md` - Working with producer lists (endpoint paths, response structure, cross-platform matching)
- `references/utilities.md` - Quota check, package install, ML model download, job retrieval
- `references/common_errors.md` - Troubleshooting and error solutions
- `references/field_reference.md` - Available fields by entity type, reshare resolution, data scope
- `references/common_patterns.md` - Reusable code patterns
- `references/surfaces.md` - Channels (FB/IG/WhatsApp), Marketplace, fundraisers, donations
- `references/field_report.md` - The field report template: how a session's findings travel back to this repository

Version history: [CHANGELOG.md](CHANGELOG.md)

---
name: mcl-api-r
description: Meta Content Library (MCL) API v6.0 in R. Use when querying Facebook, Instagram or WhatsApp content via reticulate in the SRE or SOMAR VDE: async queries, producer lists, SNAPSHOT mode, IDs, quotas.
version: 1.11.5
updated: 2026-08-24
---

# Meta Content Library API v6.0 for R

> **Skill Version:** 1.11.5 | **Updated:** 2026-08-24 | [Changelog](CHANGELOG.md)

## Environment

- **Platform**: Amazon WorkSpaces Secure Browser with JupyterLab
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

**Answering questions about available ML models?** Re-fetch
[Meta's list](https://developers.facebook.com/docs/researcher-platform/features/ml-models)
first and compare it against `references/ml_models_approved.md` — it grows, and
the skill's copy is a dated transcription. The no-internet constraint above binds
the code you write for the SRE, **not you**: you run on the researcher's machine.
Procedure and fallback: `references/utilities.md` § "Download Machine Learning
Models".

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
Facebook:  /facebook/{posts|pages|groups|events|profiles|comments}/{preview|job|estimate}
           /facebook/{channels|fundraisers|marketplace-listings}/preview
Instagram: /instagram/{posts|accounts|comments}/{preview|job|estimate}
           /instagram/{channels|fundraisers}/preview
WhatsApp:  /whatsapp/channels/preview
Utility:   /budgets, /async/jobs, /async/queries, /async/collections
Producer:  /lists/producers, /lists/producers/{list_id}
```

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

## Nested Endpoints

Some resources require parent IDs in the URL path, not as query parameters:

| Resource | Pattern | Example |
|----------|---------|---------|
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
| Query budget | 500,000 records/7-day rolling |
| Comment budget | 500,000 comments/7-day rolling (separate) |
| Max async results | ~100,000 per query |
| Snapshots | 100 concurrent per user (subcode 3790172; LIVE jobs are exempt) |

**Check budget:**
```r
budget <- mcl_fromJSON(client$get(path = "budgets")$text)
cat("Available:", budget$queries$max_usage_limit - budget$queries$total_usage, "\n")
```

## SNAPSHOT vs LIVE Mode

Use **SNAPSHOT** for anything you need to reproduce or share: data is preserved
up to a year, refreshed every 30 days, and the job can be shared. **LIVE** data
is deleted after 30 days and cannot be shared — but LIVE jobs do **not** count
against the 100-snapshot cap, so run exploration LIVE and save results to disk.
**Deleting a job does NOT refund its budget charge** — confirmed by the researcher
2026-08-23 after a duplicate submission. Budget is consumed at submission; deletion only frees
the snapshot slot. So the cost of an accidental double-submission is the full second charge,
permanently. **Guard every submission cell** so a re-run is a no-op:

```r
if (file.exists("jobs.rds")) stop("already submitted - delete jobs.rds to resubmit")
```

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
| Invalid Keyword Search (subcode 3790184) | Query used a double-quoted phrase | Remove double quotes; use single-word tokens joined with `OR` (quoted phrases work in the UI, not the API) |
| Invalid Meta Content Library ID (subcode 3790088) | Used a raw Facebook/Instagram URL ID as `surface_ids`/`account_ids` | Search the entity by name (e.g. `facebook/groups/preview` with `q`) and use the returned `id` |
| Invalid Meta Content Library ID (subcode 3790088) with a *correct* ID | ID held as `numeric`, so it was sent as `9.6378e+14` | Parse with `mcl_fromJSON()`; pass IDs as quoted character — see [ID Handling](#id-handling-always-load-ids-as-character) |
| Estimated response size too large (subcode 3790057) | Query would return more than ~100,000 results | Split by date window, and/or query fewer `surface_ids` |
| Exceeded async snapshots limit (subcode 3790172) | More than 100 concurrent SNAPSHOT jobs | Use `mode = "LIVE"` when reproducibility isn't needed; delete finished snapshots |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset |
| Producer-list post query estimates ~0 results | List is mostly ordinary profiles, whose posts aren't in the queryable dataset | Verified or 100+ follower profiles only — see `references/field_reference.md` § "Data Scope" |

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

Version history: [CHANGELOG.md](CHANGELOG.md)

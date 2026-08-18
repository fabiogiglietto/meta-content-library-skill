---
name: mcl-api-r
description: Meta Content Library (MCL) API v6.0 helper for R users on Meta Research Platforms. Use when researchers need to query Facebook, Instagram, or Threads public content using R via reticulate in the Meta Secure Research Environment (SRE) or SOMAR Virtual Data Enclave (VDE). Covers async queries, collections, jobs, pagination, rate limits, SNAPSHOT mode, loading IDs as character, and proper integer handling.
version: 1.7.0
updated: 2026-08-18
---

# Meta Content Library API v6.0 for R

> **Skill Version:** 1.7.0 | **Updated:** 2026-08-18 | [Changelog](#changelog)

## Environment

- **Platform**: Amazon WorkSpaces Secure Browser with JupyterLab
- **Language**: R with Python client via reticulate
- **Export**: Entire notebook only (no copy/paste)

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
- **Job**: Single execution of a query. Has `id`, status (IN_PROGRESS/COMPLETE/FAILED), mode (LIVE/SNAPSHOT).
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

## OpenAPI Specification

Retrieve the complete API spec programmatically (v6.0+):

```r
spec <- client$openapi_spec()
```

Use this to discover all endpoints, parameters, and response schemas.

## OpenAPI Spec Discovery

When unsure about endpoint parameters, query the OpenAPI spec:

```r
spec <- client$openapi_spec()
paths <- names(spec$paths)

# Find Instagram endpoints
instagram_paths <- paths[grepl("instagram", paths, ignore.case = TRUE)]
print(instagram_paths)

# Save full spec for reference
write(toJSON(spec, pretty = TRUE), "openapi_spec.json")
```

## Key Endpoints (v6.0)

```
Facebook:  /facebook/{posts|pages|groups|events|profiles|comments}/{preview|job|estimate}
Instagram: /instagram/{posts|accounts|channels|comments}/{preview|job|estimate}
Utility:   /budgets, /async/jobs, /async/queries, /async/collections
Producer:  /lists/producers, /lists/producers/{list_id}
```

Producer lists are **created in the Content Library UI**, not via the API: import
a CSV with a single `Producer URL` column of `https://www.facebook.com/<username>`
URLs, max 1,000 producers. Import is by URL, not by MCL id — see
`references/producer_lists.md`. Reading a list uses `lists/producers/{list_id}`
(not `producer-lists/{id}`) and returns a `$producers` data.frame (id, name, type)
plus `$platform`.

- **preview** (GET): Sync, max 1000 results - exploration only
- **job** (POST): Async, unlimited results - use for research
- **estimate** (GET): Check result count before querying

## Nested Endpoints

Some resources require parent IDs in the URL path, not as query parameters:

| Resource | Pattern | Example |
|----------|---------|---------|
| Instagram post comments | `/instagram/posts/{post_id}/comments/preview` | Get comments on a post |
| Instagram comment replies | `/instagram/comments/{comment_id}/replies/preview` | Get replies to a comment |
| Instagram channel messages | `/instagram/channels/{channel_id}/messages/preview` | Get channel messages |
| Instagram channel comments | `/instagram/channels/{channel_id}/comments/preview` | Get channel comments |

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
`surface_ids` batches at ≤ 250 too.

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

# 3. Monitor status
job <- client$get_async_job(job_id = job_id)
while(job$get_status() != "COMPLETE") {
    Sys.sleep(5)
    cat("Status:", job$get_status(), "\n"); flush.console()
}

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

| SNAPSHOT (recommended) | LIVE |
|------------------------|------|
| Data preserved up to 1 year | Deleted after 30 days |
| Can be shared for reproducibility | Cannot be shared |
| Refreshed every 30 days | N/A |
| Use for research | Use for exploration only |
| Counts against the 100-snapshot cap | Does **not** count against it |

When reproducibility isn't needed, run LIVE and save results to disk — LIVE jobs
don't consume a snapshot slot, and a LIVE job can be promoted later with
`client$post(path = paste0("async/jobs/", job_id, "/snapshot"))`. Free slots by
deleting finished snapshots; see `references/collections.md` § "The 100-Snapshot
Cap".

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

| Error | Cause | Fix |
|-------|-------|-----|
| Method not allowed | GET on /job endpoint | Use POST |
| Results limited to 1000 | Using sync /preview | Switch to async /job |
| Type mismatch | Missing `L` suffix | Add `L` to integers |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset |
| Invalid parameter | Wrong ID param for platform | Facebook: `surface_ids`, Instagram: `account_ids` |
| Invalid parameter with the right param name | ID param sent as a scalar (comma-joined string, or a length-1 vector reticulate turned into a string) | Pass an array: `as.list(ids)` |
| 404 on producer-lists/ | Wrong endpoint path | Use `lists/producers/` not `producer-lists/` |
| "first argument must be a vector" | Accessing field that doesn't exist | Inspect the parsed response with `str(mcl_fromJSON(resp$text))` |
| "missing value where TRUE/FALSE needed" | `nrow()` on NULL | Use safe response handling pattern |
| Invalid Meta Content Library ID (subcode 3790088) | Used a raw Facebook/Instagram URL ID as `surface_ids`/`account_ids` | Search the entity by name (e.g. `facebook/groups/preview` with `q`) and use the returned `id` |
| Invalid Meta Content Library ID (subcode 3790088) with a *correct* ID | ID held as `numeric`, so it was sent as `9.6378e+14` | Parse with `mcl_fromJSON()`; pass IDs as quoted character — see [ID Handling](#id-handling-always-load-ids-as-character) |
| "Can't combine `id` <character> and `id` <double>" | `bigint_as_char` typed the column per batch | Coerce all ID fields unconditionally via `mcl_fromJSON()` |
| Join/`distinct()` misses obvious matches, IDs end in 0 | ID parsed as double, digits rounded above 2^53 | Re-parse the source with `mcl_fromJSON()` — rounded IDs cannot be repaired |
| `'list' object has no attribute 'items'` | Passed `params = list()` (empty list) | Omit `params`, or pass a named list |
| Invalid Keyword Search (subcode 3790184) | Query used a double-quoted phrase | Remove double quotes; use single-word tokens joined with `OR` (quoted phrases work in the UI, not the API) |
| Invalid Meta Content Library ID (subcode 3790088) when resolving a reshare | The reshared original is out of scope, and one bad ID rejects the whole `post_ids` call | Bisect the batch and skip the offending IDs — see `references/field_reference.md` § "Reshares" |
| Estimated response size too large (subcode 3790057) | Query would return more than ~100,000 results | Split by date window, and/or query fewer `surface_ids` |
| Exceeded async snapshots limit (subcode 3790172) | More than 100 concurrent SNAPSHOT jobs | Use `mode = "LIVE"` when reproducibility isn't needed; delete finished snapshots |
| Producer-list post query estimates ~0 results | List is mostly ordinary profiles, whose posts aren't in the queryable dataset | Verified or 25,000+ follower profiles only — see `references/field_reference.md` § "Data Scope" |

## References

- `references/query_params.md` - Search parameters, filters, and `q` syntax
- `references/chunking.md` - Large dataset handling
- `references/collections.md` - Organizing queries
- `references/producer_lists.md` - Working with producer lists (endpoint paths, response structure, cross-platform matching)
- `references/utilities.md` - Quota check, package install, job retrieval
- `references/common_errors.md` - Troubleshooting and error solutions
- `references/field_reference.md` - Available fields by entity type, reshare resolution, data scope
- `references/common_patterns.md` - Reusable code patterns

---

## Changelog

### v1.7.0 (2026-08-18)
- Consolidated verified API behaviors: MCL IDs != URL IDs (3790088); ID params
  must be arrays; empty-params reticulate pitfall; no double-quoted phrases
  (3790184); 100k single-query cap (3790057) -> date windows; SNAPSHOT cap
  (3790172) vs LIVE + LIVE->SNAPSHOT conversion; profile post-inclusion thresholds
  (verified/25k+ followers); comment (owner.*) vs post (post_owner.*) schemas;
  replies require a second parent_ids pull; reshares carry shared_post_id resolved
  via post_ids; producer-list CSV import format (Producer URL, max 1000).

### v1.6.0 (2026-08-17)
- Documented that the API rejects double-quoted phrase searches (subcode
  3790184) even though the UI supports them; use single-word OR tokens.

### v1.5.0 (2026-08-17)
- Documented creating producer lists via the GUI CSV import: single `Producer URL`
  column of `https://www.facebook.com/<username>` URLs, max 1,000 producers, import
  is by URL not by MCL id. Added a recipe for building a list from active public
  commenters.
- Clarified that `surface_ids` / `account_ids` / `post_ids` must be passed as
  **arrays** (`as.list(ids)`); a scalar is rejected with "Invalid parameter",
  including a length-1 vector reticulate converts to a string. Updated every
  affected example.

### v1.4.0 (2026-08-16)
- **IMPORTANT**: All IDs (surface, post, comment, account, job, query) must be loaded as **character**. Added an "ID Handling" section with `mcl_fromJSON()` / `mcl_fix_ids()`, which combine `bigint_as_char = TRUE` (exactness above 2^53) with unconditional `sprintf("%.0f", ...)` coercion of every ID field (no scientific notation, no per-batch type drift).
- Folded ID coercion into `safe_get_data()` and switched every example in SKILL.md and the reference files from `fromJSON()` to `mcl_fromJSON()`.
- Added error rows for scientific-notation 3790088, `bind_rows()` type mismatch, and silent precision loss in joins/dedup.

### v1.3.0 (2026-08-13)
- **IMPORTANT**: Documented that MCL IDs are library-specific and differ from Facebook/Instagram URL IDs. Added a "Finding Surface IDs" section with per-entity lookup endpoints and error rows for subcode 3790088 and the empty-`params` reticulate pitfall.

### v1.2.0 (2026-03-29)
- **BREAKING**: Fixed producer list endpoint: `lists/producers/{id}` not `producer-lists/{id}`
- **BREAKING**: Producer list response uses `$producers` data.frame (cols: id, name, type), not `$ids` vector
- Added safe response handling pattern for API responses (prevents `nrow()` on NULL)
- Added Instagram accounts response field documentation (id, name, username, biography, account_type, is_verified, follower_count, following_count, creation_date, website)
- Added cross-platform account matching workflow to producer_lists.md
- Added producer endpoint to Key Endpoints section
- Updated common_errors.md with 404 producer list, NULL response, and nrow() errors

### v1.1.0 (2025-01-04)
- Fixed Instagram parameter documentation (`post_ids` not `surface_ids`)
- Added nested endpoints documentation for Instagram comments/replies
- Added OpenAPI spec discovery pattern for debugging
- Added common_errors.md reference file
- Clarified platform-specific ID parameter differences

### v1.0.0 (2025-01-04)
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

<!-- 
UPDATE CHECKLIST:
When updating this skill, remember to:
1. Increment version in frontmatter and header
2. Update the "updated" date
3. Add changelog entry
4. Update all reference files if needed
5. Re-upload to Claude Projects
-->

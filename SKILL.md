---
name: mcl-api-r
description: Meta Content Library (MCL) API v6.0 helper for R users on Meta Research Platforms. Use when researchers need to query Facebook, Instagram, or Threads public content using R via reticulate in the Meta Secure Research Environment (SRE) or SOMAR Virtual Data Enclave (VDE). Covers async queries, collections, jobs, pagination, rate limits, SNAPSHOT mode, and proper integer handling.
version: 1.2.0
updated: 2026-01
---

# Meta Content Library API v6.0 for R

> **Skill Version:** 1.2.0 | **Updated:** 2026-01 | [Changelog](#changelog)

## Environment

- **Platform**: Amazon WorkSpaces Secure Browser with JupyterLab
- **Language**: R with Python client via reticulate
- **Export**: Entire notebook only (no copy/paste)

## Critical Requirements

1. **Always use async queries** (POST to `/job` endpoints) for research
2. **Integer literals**: Use `L` suffix (e.g., `limit = 100L`)
3. **Always document**: Include `name`, `description`, `mode = "SNAPSHOT"` in every query
4. **Use `flush.console()`** after `cat()` in Jupyter for real-time output

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
library(dplyr)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
async_utils <- import("metacontentlibraryapi")$MetaContentLibraryAPIAsyncUtils
client$set_default_version(client$LATEST_VERSION)
```

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
Utility:   /budgets, /async/jobs, /async/queries, /async/collections, /lists/producers
```

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

## Async Query Template

```r
# 1. Check estimate
estimate_response <- client$get(
    path = "facebook/posts/estimate",
    params = list("q" = "climate change", "since" = "2024-01-01", "until" = "2024-12-31")
)
estimate <- fromJSON(estimate_response$text, flatten = TRUE)
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
job_data <- fromJSON(response$text, flatten = TRUE)
job_id <- job_data$id
query_id <- job_data$query_id

# 3. Monitor status
job <- client$get_async_job(job_id = job_id)
while(job$get_status() != "COMPLETE") {
    Sys.sleep(5)
    cat("Status:", job$get_status(), "\n"); flush.console()
}

# 4. Save results
job$write_data_to_file(directory = "results", filename = "climate_2024.json")
```

## Rate Limits & Budget

| Resource | Limit |
|----------|-------|
| Sync queries | 60/minute |
| Async queries | 1/minute |
| Query budget | 500,000 records/7-day rolling |
| Comment budget | 500,000 comments/7-day rolling (separate) |
| Max async results | ~100,000 per query |
| Snapshots | 100 per user |
| `account_ids` per request | 250 |
| `surface_ids` per request | 250 |

**Check budget:**
```r
budget <- fromJSON(client$get(path = "budgets")$text, flatten = TRUE)
cat("Available:", budget$queries$max_usage_limit - budget$queries$total_usage, "\n")
```

## SNAPSHOT vs LIVE Mode

| SNAPSHOT (recommended) | LIVE |
|------------------------|------|
| Data preserved up to 1 year | Deleted after 30 days |
| Can be shared for reproducibility | Cannot be shared |
| Refreshed every 30 days | N/A |
| Use for research | Use for exploration only |

## The 100,000 Result Limit

If `estimate$expected_complete = FALSE`, your query exceeds ~100,000 results and will be truncated.

**Solutions:**
1. Narrow date range (split into months/quarters)
2. Add more filters (country, language, surface_ids)
3. See `references/chunking.md` for automated chunking

## Rerun a Query

```r
# Creates new job for existing query
rerun_response <- client$post(
    path = paste0("async/queries/", query_id, "/job"),
    body = list(mode = "SNAPSHOT")
)
new_job_id <- fromJSON(rerun_response$text, flatten = TRUE)$id
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| Method not allowed | GET on /job endpoint | Use POST |
| Results limited to 1000 | Using sync /preview | Switch to async /job |
| Type mismatch | Missing `L` suffix | Add `L` to integers |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset |
| Invalid parameter | Wrong ID param for platform | Facebook: `surface_ids`, Instagram: `account_ids` |

## References

- `references/query_params.md` - Search parameters and filters
- `references/chunking.md` - Large dataset handling
- `references/collections.md` - Organizing queries
- `references/producer_lists.md` - Working with producer lists (surface_ids vs account_ids)
- `references/utilities.md` - Quota check, package install, job retrieval
- `references/common_errors.md` - Troubleshooting and error solutions

---

## Changelog

### v1.2.0 (2026-01)
- **BREAKING**: Fixed producer lists endpoint (`/lists/producers` not `/producer-lists`)
- **BREAKING**: Fixed producer ID extraction (`list_data$producers$id` not `list_data$ids`)
- Added `account_ids` and `surface_ids` limit of 250 per request
- Added batching pattern for large producer lists
- Added `dplyr::bind_rows()` recommendation for combining results
- Added new common errors and solutions
- Added complete working example for posts + comments retrieval

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

---
name: mcl-api-r
description: Meta Content Library (MCL) API v6.0 helper for R users on Meta Research Platforms. Use when researchers need to query Facebook, Instagram, or Threads public content using R via reticulate in the Meta Secure Research Environment (SRE) or SOMAR Virtual Data Enclave (VDE). Covers async queries, collections, jobs, pagination, rate limits, SNAPSHOT mode, and proper integer handling.
---

# Meta Content Library API v6.0 for R

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

## Key Endpoints (v6.0)

```
Facebook:  /facebook/{posts|pages|groups|events|profiles|comments}/{preview|job|estimate}
Instagram: /instagram/{posts|accounts|channels|comments}/{preview|job|estimate}
Utility:   /budgets, /async/jobs, /async/queries, /async/collections
```

- **preview** (GET): Sync, max 1000 results - exploration only
- **job** (POST): Async, unlimited results - use for research
- **estimate** (GET): Check result count before querying

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

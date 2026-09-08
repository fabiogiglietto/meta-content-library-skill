# Collections and query management — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

Every snippet parses with `mcl_fromJSON()` (`languages/r/ids.md` §
"mcl_fromJSON"), so IDs come out as character.

## Managing collections

Facts: `references/collections.md` § "Collections (Folders)"

```r
# Create collection
response <- client$post(
    path = "async/collections",
    body = list(
        name = "Climate Research 2024",
        description = "PI: Dr. Smith, IRB #2024-001, NSF Grant #12345"
    )
)
collection_id <- mcl_fromJSON(response$text)$id

# Set as default (new queries auto-added here)
client$post(
    path = paste0("async/collections/", collection_id),
    body = list(default = TRUE)
)

# List all collections
collections <- mcl_fromJSON(client$get(path = "async/collections")$text)

# Delete collection (queries remain)
client$delete(path = paste0("async/collections/", collection_id))
```

## Managing queries

Facts: `references/collections.md` § "Query Management"

```r
# List all queries
queries <- mcl_fromJSON(client$get(path = "async/queries")$text)

# Get specific query with all its jobs
query_details <- mcl_fromJSON(
    client$get(path = paste0("async/queries/", query_id))$text
)

# Update query metadata
client$post(
    path = paste0("async/queries/", query_id),
    body = list(
        name = "Updated Name - PUBLISHED",
        description = "Updated with DOI: 10.1234/paper.2025"
    )
)

# Move query to collection
client$post(
    path = paste0("async/queries/", query_id),
    body = list(collection_id = collection_id)
)

# Make query public (for sharing)
client$post(
    path = paste0("async/queries/", query_id),
    body = list(visibility = "PUBLIC")
)

# Delete query (deletes all jobs too!)
client$delete(path = paste0("async/queries/", query_id))
```

## Listing jobs — [verified 2026-08-24]

Facts: `references/collections.md` § "Job Management"

The listing sits under `$jobs`, not `$data`; the `stopifnot()` is there because
reading the wrong key fails silently (next section).

```r
# List all jobs -- the payload is under $jobs, NOT $data. See the warning below.
jl   <- mcl_fromJSON(client$get(path = "async/jobs")$text)
jobs <- jl$jobs                      # data.frame: id, creation_time, update_time,
                                     #             status, mode, query_id
stopifnot(is.data.frame(jobs))       # assert; the wrong key fails silently

# Get job metadata
job_meta <- mcl_fromJSON(
    client$get(path = paste0("async/jobs/", job_id))$text
)
# Returns: id, status, mode, query_id, creation_time
```

## The `data` fallback idiom is wrong for async/jobs — [verified 2026-08-24]

Facts: `references/collections.md` § "⚠ The `async/jobs` envelope key is `jobs`, not `data`"

The common defensive idiom for list-shaped responses:

```r
d <- if (!is.null(x$data)) x$data else x     # WRONG for async/jobs
```

Against `async/jobs` it falls through silently: `$data` is NULL, so `d` becomes
the whole envelope and `d$mode` is NULL. Read `$jobs` explicitly instead:

```r
# Counting SNAPSHOT slots against the 100-concurrent cap, correctly:
jobs <- mcl_fromJSON(client$get(path = "async/jobs")$text)$jobs
sum(jobs$mode == "SNAPSHOT" & jobs$status != "FAILED", na.rm = TRUE)

# Convert LIVE to SNAPSHOT (preserve data)
client$post(path = paste0("async/jobs/", job_id, "/snapshot"))

# Delete job
client$delete(path = paste0("async/jobs/", job_id))
```

## Staying under the 100-snapshot cap

Facts: `references/collections.md` § "The 100-Snapshot Cap"

Run a pull LIVE when reproducibility isn't needed for it:

```r
params[["mode"]] <- "LIVE"      # does not consume a snapshot slot
```

Promote a LIVE job later if it turns out to be worth preserving (the same call
as `languages/r/jobs.md` § "Promoting a LIVE job to a snapshot"):

```r
client$post(path = paste0("async/jobs/", job_id, "/snapshot"))
```

Free slots by deleting finished snapshots — job by job, or a whole query:

```r
client$delete(path = paste0("async/jobs/", job_id))       # one job
client$delete(path = paste0("async/queries/", query_id))  # query + all its jobs
```

## Copying a public query or collection

Facts: `references/collections.md` § "Reproducibility: Sharing & Copying"

```r
# Copy another researcher's public query
response <- client$post(
    path = paste0("async/queries/", other_query_id, "/copy")
)
# Copies query + COMPLETE SNAPSHOT jobs
# Jobs are rerun (counts toward YOUR budget)

# Copy entire public collection
response <- client$post(
    path = paste0("async/collections/", other_collection_id, "/copy")
)
```

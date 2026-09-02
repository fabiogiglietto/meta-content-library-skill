# Collections and Query Management

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

## Collections (Folders)

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

## Query Management

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

## Job Management

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

### ⚠ The `async/jobs` envelope key is `jobs`, not `data` — **[verified 2026-08-24]**

Most list-shaped responses in this API wrap their payload in `data`, so the common
defensive idiom is:

```r
d <- if (!is.null(x$data)) x$data else x     # WRONG for async/jobs
```

Against `async/jobs` that idiom **falls through silently**: `$data` is NULL, so `d`
becomes the whole envelope, `d$mode` is NULL, and any summary computed from it is
wrong *without erroring*. On 2026-08-24 this reported `0 of 100 snapshot slots used`
on an account with 434 jobs; the true figure was 5. A wrong number that looks
plausible is worse than a failure, and the only thing that caught it was probing the
response shape rather than trusting the idiom.

```
class(jl):  list          names(jl):  jobs
jl$jobs:    'data.frame': 434 obs. of 6 variables
```

Two further properties of the listing:

- **`creation_time` and `update_time` are integer epoch seconds here**, not the ISO-8601
  strings `creation_time` carries on a *post* record. Same field name, different type,
  different endpoint.
- **There is no `name` column.** The `name` supplied at submission is not readable back
  from the job listing, so **jobs cannot be identified by name from this endpoint** —
  which matters if you are trying to detect an already-submitted duplicate. That lives
  on the query (`async/queries`), which was returning **502** on the same date; see
  `../docs/OPEN_QUESTION_ASYNC_QUERIES_502.md`.

```r
# Counting SNAPSHOT slots against the 100-concurrent cap, correctly:
jobs <- mcl_fromJSON(client$get(path = "async/jobs")$text)$jobs
sum(jobs$mode == "SNAPSHOT" & jobs$status != "FAILED", na.rm = TRUE)

# Convert LIVE to SNAPSHOT (preserve data)
client$post(path = paste0("async/jobs/", job_id, "/snapshot"))

# Delete job
client$delete(path = paste0("async/jobs/", job_id))
```

### Nothing inside the SRE reliably survives the month — the job least of all

⚠ **This section previously said the opposite.** It advised recovering after a
wipe by re-reading the job, on the strength of Meta's documented one-year
SNAPSHOT retention. **Measured 2026-09-02: every job was `EXPIRED` after a wipe,
SNAPSHOT included**, and ids from a week earlier resolved to `error_subcode
3790112`. SKILL.md § "SNAPSHOT vs LIVE Mode" owns that finding.

So the recovery path this section used to recommend **does not exist**:

| | documented | measured 2026-09-02 |
|---|---|---|
| Server-side job data | held up to a year, re-readable | **all jobs `EXPIRED`** |
| Your files in the SRE | deleted monthly | **survived** on the account tested |

The file survival is *probably* the documented exception for approved EU
systemic-risk programmes, and it is **one observation on one account** — do not
plan on it either. `references/utilities.md` § "The monthly wipe" owns the wipe.

**The only durable artefact is one that has left the enclave, or lives in a
notebook input/markdown cell.** Download a job's results the same calendar month
you submit it, and export what the study needs before the boundary. Budget is
charged at submission and never refunded, so a re-run after losing both the job
and the file costs the full amount again.

### The 100-Snapshot Cap

SNAPSHOT-mode jobs are capped at **100 concurrent per user**; exceeding it fails
with `error_subcode 3790172` ("Exceeded async snapshots limit"). **LIVE jobs do
not count against the cap.**

When reproducibility isn't needed for a given pull, run it LIVE and save the
results to disk:

```r
params[["mode"]] <- "LIVE"      # does not consume a snapshot slot
```

A LIVE job can be promoted later if it turns out to be worth preserving:

```r
client$post(path = paste0("async/jobs/", job_id, "/snapshot"))
```

Free slots by deleting finished snapshots — either job by job, or a whole query
(which deletes its jobs with it):

```r
client$delete(path = paste0("async/jobs/", job_id))       # one job
client$delete(path = paste0("async/queries/", query_id))  # query + all its jobs
```

Retention differs: LIVE data is kept ~30 days, SNAPSHOT up to 1 year.

## Reproducibility: Sharing & Copying

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

## Naming Best Practices

**Collections**: Project-level names
```r
"Climate Change Research 2024-2025"
"Election Misinformation Study"
```

**Queries**: Specific + Time period
```r
"Climate Posts - 2024 Q1 - US Only"
"Vaccine Discourse - Instagram - Jan 2024"
```

**Descriptions**: Include everything
```r
description = "
  WHAT: Facebook posts mentioning 'climate change'
  WHEN: Q1 2024 (Jan 1 - Mar 31)
  WHY: Baseline for discourse analysis
  WHO: Dr. Smith (PI), IRB #2024-001
  RELATED: See 'Climate Posts Q2' for continuation
"
```

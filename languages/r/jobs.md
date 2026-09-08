# Async jobs — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Waiting for a job — [verified 2026-08-21]

Facts: `SKILL.md` § "Waiting for a Job"

`get_status()` returns `COMPLETE`, uppercase, and the helper is correct under
either casing: it cannot spin forever, and it treats an unrecognized status as
"keep waiting" rather than as success.

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

## Safe response handling

Facts: `SKILL.md` § "Safe Response Handling"

This is the single funnel for MCL data — it parses with `mcl_fromJSON()`
(`languages/r/ids.md` § "mcl_fromJSON"), so IDs come out as character, and it
validates before anything calls `nrow()`:

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

## Async query template

Facts: `SKILL.md` § "Async Query Template"

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

# 3. Monitor status (see "Waiting for a job" for mcl_wait_for_job)
job <- client$get_async_job(job_id = job_id)
mcl_wait_for_job(job)

# 4. Save results, then load with IDs as character
job$write_data_to_file(directory = "results", filename = "climate_2024.json")
posts <- mcl_fromJSON(file.path("results", "climate_2024.json"))
```

`limit` carries the `L` suffix because an R `100` is a double
(`languages/r/query_params.md` § "Integer parameters").

## Guarding a submission cell

Facts: `SKILL.md` § "SNAPSHOT vs LIVE Mode"

Budget is consumed at submission and a deleted job does not refund it, so a
re-run of the submission cell must be a no-op:

```r
if (file.exists("jobs.rds")) stop("already submitted - delete jobs.rds to resubmit")
```

## Promoting a LIVE job to a snapshot

Facts: `SKILL.md` § "SNAPSHOT vs LIVE Mode"

```r
client$post(path = paste0("async/jobs/", job_id, "/snapshot"))
```

## Rerunning a query

Facts: `SKILL.md` § "Rerun a Query"

```r
# Creates new job for existing query
rerun_response <- client$post(
    path = paste0("async/queries/", query_id, "/job"),
    body = list(mode = "SNAPSHOT")
)
new_job_id <- mcl_fromJSON(rerun_response$text)$id
```

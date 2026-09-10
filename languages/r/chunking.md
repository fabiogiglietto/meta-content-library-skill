# Chunking — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Automatic date chunking

Facts: `references/chunking.md` § "Automatic Date Chunking"

```r
query_with_chunking <- function(query_text, start_date, end_date, platform = "facebook", 
                                 content_type = "posts", chunk_size = 90) {
  library(dplyr)
  
  start <- as.Date(start_date)
  end <- as.Date(end_date)
  
  # Generate date chunks
  chunks <- list()
  current <- start
  i <- 1
  while (current <= end) {
    chunk_end <- min(current + chunk_size - 1, end)
    chunks[[i]] <- list(
      since = format(current, "%Y-%m-%d"),
      until = format(chunk_end, "%Y-%m-%d")
    )
    current <- chunk_end + 1
    i <- i + 1
  }
  
  cat("Split into", length(chunks), "chunks\n"); flush.console()
  
  all_job_ids <- list()
  
  for (i in seq_along(chunks)) {
    chunk <- chunks[[i]]
    cat("Chunk", i, ":", chunk$since, "to", chunk$until, "\n"); flush.console()
    
    # Check estimate first
    est <- mcl_fromJSON(client$get(
      path = paste0(platform, "/", content_type, "/estimate"),
      params = list("q" = query_text, "since" = chunk$since, "until" = chunk$until)
    )$text)
    
    if (!isTRUE(est$expected_complete)) {
      cat("  Warning: Chunk exceeds 100k, consider smaller chunks\n")
    }
    
    # Submit job
    response <- client$post(
      path = paste0(platform, "/", content_type, "/job"),
      params = list(
        "q" = query_text,
        "since" = chunk$since,
        "until" = chunk$until,
        "mode" = "SNAPSHOT",
        "name" = paste0(query_text, " - ", chunk$since, " to ", chunk$until),
        "description" = paste0("Chunk ", i, " of ", length(chunks), " for large query")
      )
    )
    
    job_data <- mcl_fromJSON(response$text)
    all_job_ids[[i]] <- job_data$id   # character
    
    cat("  Job ID:", job_data$id, "\n"); flush.console()
    
    # Rate limit: 1 async per minute
    if (i < length(chunks)) {
      cat("  Waiting 60s for rate limit...\n"); flush.console()
      Sys.sleep(60)
    }
  }
  
  return(all_job_ids)
}

# Usage
job_ids <- query_with_chunking(
  query_text = "climate change",
  start_date = "2024-01-01",
  end_date = "2024-12-31",
  chunk_size = 30  # 30-day chunks
)
```

## Combining chunked results

Facts: `references/chunking.md` § "Combining Chunked Results"

Every chunk is parsed with `mcl_fromJSON()`, so the `id` column is character in
all of them and `bind_rows()` cannot fail with *"Can't combine `id` <character>
and `id` <double>"*. The `stopifnot()` guard makes that assumption explicit
before `distinct()` runs.

```r
combine_chunk_results <- function(job_ids, output_dir = "results") {
  library(dplyr)
  
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
  
  all_data <- list()
  
  for (i in seq_along(job_ids)) {
    job_id <- job_ids[[i]]
    cat("Processing job", i, ":", job_id, "\n"); flush.console()
    
    job <- client$get_async_job(job_id = job_id)
    
    # Wait for completion — mcl_wait_for_job() is defined in languages/r/jobs.md
    # § "Waiting for a job". A bare != "COMPLETE" loop spins forever if the
    # status comes back lowercase.
    mcl_wait_for_job(job, poll = 10)
    
    # Save to file
    filename <- paste0("chunk_", i, "_", job_id, ".json")
    job$write_data_to_file(directory = output_dir, filename = filename)
    
    # Load data (IDs as character, so chunk column types always match)
    data <- mcl_fromJSON(file.path(output_dir, filename))
    if (nrow(data) > 0) {
      data$source_chunk <- i
      data$source_job_id <- job_id
      all_data[[i]] <- data
    }
    
    cat("  Retrieved", nrow(data), "records\n"); flush.console()
  }
  
  # Combine and deduplicate
  combined <- bind_rows(all_data)
  
  if ("id" %in% colnames(combined)) {
    stopifnot(is.character(combined$id))   # guard: never dedup on numeric IDs
    before <- nrow(combined)
    combined <- distinct(combined, id, .keep_all = TRUE)
    cat("\nDeduplicated:", before, "->", nrow(combined), "records\n")
  }
  
  # Save combined
  saveRDS(combined, file.path(output_dir, "combined_deduplicated.rds"))
  
  return(combined)
}

# Usage
all_data <- combine_chunk_results(job_ids)
```

## Collecting only the latest N results

Facts: `references/chunking.md` § "Collecting Only the Latest N Results"

`run_job()` stands for your submit-wait-load sequence (`languages/r/jobs.md`
§ "Async query template").

```r
collect_latest <- function(params_base, until, n_target, window_days = 7L,
                           max_windows = 52L) {
  collected <- list()
  n_have <- 0L
  end <- as.Date(until)

  for (i in seq_len(max_windows)) {
    start <- end - window_days
    params <- c(params_base, list(
      "since" = as.character(start),
      "until" = as.character(end),
      "limit" = 100L,
      "mode"  = "LIVE",
      "name"  = sprintf("Latest N - window %d", i),
      "description" = "Newest-first collection, stops at target"
    ))

    # ... submit the job, wait, read results into `chunk` ...
    chunk <- run_job(params)

    if (!is.null(chunk) && nrow(chunk) > 0) {
      collected[[length(collected) + 1L]] <- chunk
      n_have <- n_have + nrow(chunk)
      cat(sprintf("Window %s..%s: +%d (total %d/%d)\n",
                  start, end, nrow(chunk), n_have, n_target)); flush.console()
    }

    if (n_have >= n_target) break
    end <- start
  }

  bind_rows(collected) %>%
    arrange(desc(creation_time)) %>%
    head(n_target)
}
```

# Handling Large Datasets (Chunking)

When `expected_complete = FALSE`, split queries to avoid truncation.

> **The ~100,000-result cap is per query.** A single async query returns at most
> ~100,000 results. Depending on the endpoint this shows up either as silent
> truncation (`estimate$expected_complete = FALSE`) or as a hard failure with
> `error_subcode 3790057` ("Estimated response size too large"). When
> `estimate$estimated_results` exceeds ~100k, split by **date** into smaller
> windows — and/or query fewer `surface_ids` per call — so each query stays under
> the cap.

> **Parse every chunk with `mcl_fromJSON()`** (defined in SKILL.md § "ID Handling
> (Always Load IDs as Character)"). Chunking is where plain `fromJSON()` bites
> hardest: a chunk containing an ID above 2^53 types `id` as character while
> another chunk types it as double, and `bind_rows()` then fails with
> *"Can't combine `id` <character> and `id` <double>"*. Deduplicating on doubles
> is also unsafe — rounded IDs collide.

## Automatic Date Chunking

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
  while (current < end) {
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

## Combining Chunked Results

```r
combine_chunk_results <- function(job_ids, output_dir = "results") {
  library(dplyr)
  
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
  
  all_data <- list()
  
  for (i in seq_along(job_ids)) {
    job_id <- job_ids[[i]]
    cat("Processing job", i, ":", job_id, "\n"); flush.console()
    
    job <- client$get_async_job(job_id = job_id)
    
    # Wait for completion
    while (job$get_status() != "COMPLETE") {
      cat("  Status:", job$get_status(), "- waiting...\n"); flush.console()
      Sys.sleep(10)
    }
    
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

## Chunk Size Guidelines

| Estimated Results | Recommended Chunk |
|-------------------|-------------------|
| < 100,000 | No chunking needed |
| 100k - 500k | Quarterly (90 days) |
| 500k - 1M | Monthly (30 days) |
| > 1M | Weekly (7 days) or add filters |

ID batch size is a separate limit: `post_ids` takes at most **250 IDs per call**,
and `surface_ids` is best kept at ≤ 250 too. A query can therefore need chunking
on both axes — date windows for the result cap, ID batches for the parameter cap.

## Collecting Only the Latest N Results

When you want the most recent N posts rather than the full history, iterate date
windows **newest-first** and stop once N is reached — this avoids paying for
older windows you'd discard, and keeps every query under the cap:

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

# Handling Large Datasets (Chunking)

When `expected_complete = FALSE`, split queries to avoid truncation.

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
    est <- fromJSON(client$get(
      path = paste0(platform, "/", content_type, "/estimate"),
      params = list("q" = query_text, "since" = chunk$since, "until" = chunk$until)
    )$text, flatten = TRUE)
    
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
    
    job_data <- fromJSON(response$text, flatten = TRUE)
    all_job_ids[[i]] <- job_data$id
    
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
    
    # Load data
    data <- fromJSON(file.path(output_dir, filename), flatten = TRUE)
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

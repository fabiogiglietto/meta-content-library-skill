# MCL API Utilities

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

Verified working code for common utility tasks.

## Check Quota Status

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "budgets")
budgets <- mcl_fromJSON(response$text)

# Extract query budget (posts, pages, groups, events, accounts)
queries <- budgets$queries
queries_used <- as.numeric(queries$total_usage)
queries_limit <- as.numeric(queries$max_usage_limit)
queries_avail <- queries_limit - queries_used

cat("Query Budget:\n")
cat(sprintf("  Used:      %s / %s\n", format(queries_used, big.mark=","), format(queries_limit, big.mark=",")))
cat(sprintf("  Available: %s records\n", format(queries_avail, big.mark=",")))

# In-progress queries (preallocated)
if (queries$preallocated_rows_for_running_queries > 0) {
  cat(sprintf("  In Progress: %s records\n", format(queries$preallocated_rows_for_running_queries, big.mark=",")))
}

# Separate comments budget
comments <- budgets$comments
comments_avail <- as.numeric(comments$max_usage_limit) - as.numeric(comments$total_usage)
cat(sprintf("\nComments Budget: %s available\n", format(comments_avail, big.mark=",")))
```

### Quota Thresholds

| Available Records | Status | Recommendation |
|-------------------|--------|----------------|
| >= 200,000 | Excellent | Full analysis |
| >= 100,000 | Good | Moderate analysis |
| >= 50,000 | Fair | Reduced parameters |
| >= 10,000 | Low | Minimal analysis |
| < 10,000 | Critical | Wait for reset |
| <= 0 | Over quota | Cannot run queries |

### Quota Reset
- **Rolling window**: 7 days
- Each query's usage expires exactly 7 days after submission
- Check daily to see quota freeing up

## Install R Packages

The Meta SRE uses a custom CRAN mirror. Use `fbrir` to install packages:

```r
library(fbrir)

# Initialize CRAN instance
cran <- CRAN$new()

# Install single package
cran$InstallPackages("flextable", dependencies = TRUE)

# Install multiple packages
cran$InstallPackages(c("ggplot2", "dplyr", "tidyr"), dependencies = TRUE)
```

**Note**: Standard `install.packages()` does not work in the SRE.

## Retrieve Completed Job Data

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

job_id <- "2025-11-30-xxx-xxx"  # Your job ID

# Get job object
job <- client$get_async_job(job_id = job_id)

# Check status. mcl_job_status() upper-cases and trims; comparing the raw
# return value is unsafe — see SKILL.md § "Waiting for a Job".
status <- mcl_job_status(job)
cat("Status:", status, "\n")

if (status == "COMPLETE") {
  # Save to file
  output_dir <- "retrieved_jobs"
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
  
  filename <- paste0("job_", job_id, ".json")
  job$write_data_to_file(directory = output_dir, filename = filename)
  
  # Load into R
  filepath <- file.path(output_dir, filename)
  job_data <- mcl_fromJSON(filepath)
  
  cat("Retrieved", nrow(job_data), "records\n")
}
```

### Get Job Metadata

```r
# Full job details
job_response <- client$get(path = paste0("async/jobs/", job_id))
job_metadata <- mcl_fromJSON(job_response$text)

cat("Mode:", job_metadata$mode, "\n")
cat("Query ID:", job_metadata$query_id, "\n")
cat("Created:", as.POSIXct(job_metadata$creation_time, origin = "1970-01-01"), "\n")
```

### Get Query Information

```r
query_response <- client$get(path = paste0("async/queries/", job_metadata$query_id))
query_info <- mcl_fromJSON(query_response$text)

cat("Query Name:", query_info$name, "\n")
cat("Platform:", query_info$platform, "\n")
cat("Entity Type:", query_info$entity_type, "\n")
cat("Parameters:", query_info$params, "\n")
```

## List All Jobs

```r
jobs_response <- client$get(path = "async/jobs")
jobs_data <- mcl_fromJSON(jobs_response$text)

# View summary
print(jobs_data$jobs[, c("id", "status", "mode", "query_id")])
```

## Verify IDs Loaded as Character

Run this on any data.frame before joining, deduplicating, or exporting — it fails
loudly if an ID slipped through as a double:

```r
check_ids <- function(df) {
  id_cols <- grep(MCL_ID_PATTERN, names(df), value = TRUE)   # "(^|[._])ids?$"
  bad <- id_cols[vapply(df[id_cols], is.numeric, logical(1))]   # logical is_invalid_id is fine

  if (length(bad)) {
    stop("Numeric ID column(s): ", paste(bad, collapse = ", "),
         " — re-parse the source with mcl_fromJSON()")
  }
  # Digits above 2^53 are already rounded and cannot be repaired
  risky <- vapply(df[id_cols], function(x) {
    if (!is.character(x)) return(FALSE)
    any(nchar(x) >= 16, na.rm = TRUE)
  }, logical(1))

  cat(sprintf("%d ID column(s) OK (%d with 16+ digit values)\n",
              length(id_cols), sum(risky)))
  invisible(TRUE)
}

check_ids(posts)
```

## SNAPSHOT vs LIVE Data Retention

SNAPSHOT data is kept up to a year and is shareable; LIVE data is kept ~30 days
and is not. SNAPSHOT jobs refresh every 30 days with updated data, including
`updated_fields` and `is_invalid_id` flags for redacted content.

Full comparison and the 100-snapshot cap: `references/collections.md` § "The
100-Snapshot Cap".

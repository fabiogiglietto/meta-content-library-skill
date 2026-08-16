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
# List all jobs
jobs <- mcl_fromJSON(client$get(path = "async/jobs")$text)

# Get job metadata
job_meta <- mcl_fromJSON(
    client$get(path = paste0("async/jobs/", job_id))$text
)
# Returns: id, status, mode, query_id, creation_time

# Convert LIVE to SNAPSHOT (preserve data)
client$post(path = paste0("async/jobs/", job_id, "/snapshot"))

# Delete job
client$delete(path = paste0("async/jobs/", job_id))
```

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

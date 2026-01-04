# Producer Lists

Producer lists are pre-defined sets of account IDs for Facebook Pages or Instagram Accounts.

## Critical Platform Differences

| Platform | ID Parameter | Entity Types |
|----------|--------------|--------------|
| Facebook | `surface_ids` | pages, groups, profiles |
| Instagram | `account_ids` | accounts |

**This is the #1 source of errors when working with producer lists.**

## List All Producer Lists

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "producer-lists")
lists <- fromJSON(response$text, flatten = TRUE)

# View available lists with platform
print(lists$producer_lists[, c("id", "name", "platform", "entity_type")])
```

## Get IDs from Producer List

```r
list_id <- "2025-12-11-xxxx"

response <- client$get(path = paste0("producer-lists/", list_id))
list_data <- fromJSON(response$text, flatten = TRUE)

# Platform is in metadata
platform <- tolower(list_data$platform)  # "facebook" or "instagram"
entity_type <- list_data$entity_type

# Extract IDs
ids <- list_data$ids
cat("Platform:", platform, "\n")
cat("Entity type:", entity_type, "\n")
cat("Total IDs:", length(ids), "\n")
```

## Query Posts from Producer List

### Auto-Detect Platform Pattern

```r
# Get list metadata first
response <- client$get(path = paste0("producer-lists/", list_id))
list_data <- fromJSON(response$text, flatten = TRUE)
platform <- tolower(list_data$platform)
ids <- list_data$ids

# Build correct parameter name
id_param <- if (platform == "instagram") "account_ids" else "surface_ids"

# Build parameters
params <- list(
  "since" = "2024-01-01",
  "until" = "2024-12-31",
  "limit" = 100L,
  "mode" = "SNAPSHOT",
  "name" = "Posts from Producer List",
  "description" = "Researcher: X, IRB: Y"
)
params[[id_param]] <- paste(ids, collapse = ",")

# Submit job
response <- client$post(
  path = paste0(platform, "/posts/job"),
  params = params
)
job_data <- fromJSON(response$text, flatten = TRUE)
job_id <- job_data$id
```

### Platform and Endpoint ID Parameters

```r
get_id_param_name <- function(platform, endpoint_type = "posts") {
  platform <- tolower(platform)

  if (platform == "instagram") {
    if (endpoint_type == "posts") return("post_ids")
    if (endpoint_type == "accounts") return("account_ids")
  } else if (platform == "facebook") {
    return("surface_ids")
  }

  stop("Unknown platform/endpoint combination")
}
```

## Batching Large Producer Lists

When a producer list has many IDs, batch them to stay under the ~100,000 result limit:

```r
batch_ids <- function(ids, batch_size = 50) {
  n <- length(ids)
  batches <- split(ids, ceiling(seq_along(ids) / batch_size))
  return(batches)
}

# Process each batch
batches <- batch_ids(ids, batch_size = 50L)
all_job_ids <- c()

for (i in seq_along(batches)) {
  batch <- batches[[i]]
  cat("Batch", i, "of", length(batches), "-", length(batch), "IDs\n"); flush.console()
  
  params <- list(
    "since" = "2024-01-01",
    "until" = "2024-12-31",
    "limit" = 100L,
    "mode" = "SNAPSHOT",
    "name" = sprintf("Batch %d of %d", i, length(batches)),
    "description" = "Batched producer list query"
  )
  params[[id_param]] <- paste(batch, collapse = ",")
  
  response <- client$post(
    path = paste0(platform, "/posts/job"),
    params = params
  )
  job_data <- fromJSON(response$text, flatten = TRUE)
  all_job_ids <- c(all_job_ids, job_data$id)
  
  # Rate limit: 1 async query per minute
  if (i < length(batches)) {
    cat("Waiting 60s for rate limit...\n"); flush.console()
    Sys.sleep(60)
  }
}
```

## Query Account/Page Information

To get profile metadata (not posts) for IDs in a producer list:

### Instagram Accounts

```r
# Batch IDs (max ~50 per query for reliability)
id_batches <- batch_ids(ids, batch_size = 50L)

for (batch in id_batches) {
  params <- list(
    "account_ids" = paste(batch, collapse = ","),
    "limit" = 100L
  )
  
  response <- client$get(
    path = "instagram/accounts/preview",
    params = params
  )
  # Process results...
}
```

### Facebook Pages

```r
for (batch in id_batches) {
  params <- list(
    "surface_ids" = paste(batch, collapse = ","),
    "limit" = 100L
  )
  
  response <- client$get(
    path = "facebook/pages/preview",
    params = params
  )
  # Process results...
}
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Invalid parameter" | Wrong ID param name | Use `surface_ids` for Facebook, `account_ids` for Instagram |
| Empty results | IDs from wrong platform | Verify producer list platform matches endpoint |
| Results truncated | Too many IDs | Batch into smaller groups |

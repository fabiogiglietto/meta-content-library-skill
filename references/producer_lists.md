# Producer Lists

Producer lists are pre-defined sets of account IDs for Facebook Pages or Instagram Accounts.

## Critical Platform Differences

| Platform | ID Parameter | Entity Types |
|----------|--------------|--------------|
| Facebook | `surface_ids` | pages, groups, profiles |
| Instagram | `account_ids` | accounts |

**This is the #1 source of errors when working with producer lists.**

## Correct Endpoints

| Action | Endpoint | Method |
|--------|----------|--------|
| List all producer lists | `/lists/producers` | GET |
| Get specific producer list | `/lists/producers/{alias_id}` | GET |

**Note:** The old `/producer-lists` endpoint is incorrect and will return 404.

## List All Producer Lists

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "lists/producers")
lists <- fromJSON(response$text, flatten = TRUE)

# View available lists with platform
print(lists$producer_lists[, c("id", "name", "platform", "entity_type")])
```

## Get Producer IDs from List

### Response Structure (CRITICAL)

The API returns a `producers` array of objects, **NOT** a simple `ids` array:

```json
{
  "id": "2026-01-04-ozau",
  "name": "List Name",
  "platform": "instagram",
  "producers": [
    {"id": "24590850730565550", "name": "Account Name", "type": "personal"},
    {"id": "8835619496490162", "name": "Another Account", "type": "creator"}
  ]
}
```

### Correct ID Extraction

```r
list_id <- "2026-01-04-xxxx"

# Get list data
response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- fromJSON(response$text, flatten = TRUE)

# Platform is in metadata
platform <- tolower(list_data$platform)  # "facebook" or "instagram"

# ✓ CORRECT - Extract from producers array
producers_df <- list_data$producers
producer_ids <- producers_df$id

# ✗ WRONG - This field doesn't exist
# producer_ids <- list_data$ids  # ERROR!

cat("Platform:", platform, "\n")
cat("Total IDs:", length(producer_ids), "\n")
```

## Rate Limit: 250 IDs Per Request

**NEW LIMIT:** You can only pass up to **250** `account_ids` or `surface_ids` in a single request.

For producer lists with more than 250 IDs, you **must** batch them.

## Batching Large Producer Lists

```r
# Batch producer IDs (max 250 per request)
batch_size <- 250L
batches <- split(producer_ids, ceiling(seq_along(producer_ids) / batch_size))

cat("Total producers:", length(producer_ids), "\n")
cat("Number of batches:", length(batches), "\n\n")

# Submit separate jobs per batch
all_job_ids <- c()

for (b in seq_along(batches)) {
  batch_ids <- batches[[b]]
  cat("Batch", b, "of", length(batches), "-", length(batch_ids), "IDs\n")
  flush.console()

  # Build parameters
  params <- list(
    "since" = "2026-01-01",
    "until" = "2026-01-31",
    "limit" = 100L,
    "mode" = "SNAPSHOT",
    "name" = sprintf("Query - Batch %d of %d", b, length(batches)),
    "description" = "Batched query for large producer list"
  )

  # Platform-specific ID parameter
  if (platform == "instagram") {
    params[["account_ids"]] <- paste(batch_ids, collapse = ",")
    endpoint <- "instagram/posts/job"
  } else {
    params[["surface_ids"]] <- paste(batch_ids, collapse = ",")
    endpoint <- "facebook/posts/job"
  }

  # Submit job
  response <- client$post(path = endpoint, params = params)
  job_data <- fromJSON(response$text, flatten = TRUE)
  all_job_ids <- c(all_job_ids, job_data$id)

  # Rate limit: 1 async job per minute
  if (b < length(batches)) {
    cat("Waiting 60s for rate limit...\n\n")
    flush.console()
    Sys.sleep(60)
  }
}

cat("Submitted", length(all_job_ids), "jobs\n")
```

## Combining Results with Mismatched Columns

**CRITICAL:** API responses from different batches may have different columns. Using `rbind()` will fail.

```r
library(dplyr)

# Collect job results
all_results <- list()

for (job_id in all_job_ids) {
  job <- client$get_async_job(job_id = job_id)

  # Wait for completion
  while (job$get_status() == "IN_PROGRESS") {
    Sys.sleep(10)
  }

  # Save and load
  job$write_data_to_file(directory = "results", filename = paste0(job_id, ".json"))
  result <- fromJSON(file.path("results", paste0(job_id, ".json")), flatten = TRUE)
  all_results[[length(all_results) + 1]] <- result
}

# ✗ WRONG - Fails with mismatched columns
# combined <- do.call(rbind, all_results)  # ERROR!

# ✓ CORRECT - Handles different columns
combined <- bind_rows(all_results)
```

## Auto-Detect Platform Pattern

```r
# Get list metadata first
response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- fromJSON(response$text, flatten = TRUE)

platform <- tolower(list_data$platform)
producer_ids <- list_data$producers$id

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
params[[id_param]] <- paste(producer_ids, collapse = ",")

# Submit job
response <- client$post(
  path = paste0(platform, "/posts/job"),
  params = params
)
job_data <- fromJSON(response$text, flatten = TRUE)
job_id <- job_data$id
```

## Query Account/Page Information

To get profile metadata (not posts) for IDs in a producer list:

### Instagram Accounts

```r
# Batch IDs (max 250 per query)
batch_size <- 250L
id_batches <- split(producer_ids, ceiling(seq_along(producer_ids) / batch_size))

all_accounts <- list()

for (batch in id_batches) {
  params <- list(
    "account_ids" = paste(batch, collapse = ","),
    "limit" = 1000L
  )

  response <- client$get(
    path = "instagram/accounts/preview",
    params = params
  )
  result <- fromJSON(response$text, flatten = TRUE)

  if (!is.null(result$data) && length(result$data) > 0) {
    all_accounts[[length(all_accounts) + 1]] <- result$data
  }
}

accounts_data <- bind_rows(all_accounts)
```

### Facebook Pages

```r
for (batch in id_batches) {
  params <- list(
    "surface_ids" = paste(batch, collapse = ","),
    "limit" = 1000L
  )

  response <- client$get(
    path = "facebook/pages/preview",
    params = params
  )
  # Process results...
}
```

---

# =============================================================================
# Complete Example: Posts and Comments from Producer List
# =============================================================================

```r
library(reticulate)
library(jsonlite)
library(dplyr)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

# --- 1. Get Producer List ---
list_id <- "your-list-id"
list_response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- fromJSON(list_response$text, flatten = TRUE)

platform <- tolower(list_data$platform)
producer_ids <- list_data$producers$id  # CORRECT extraction

cat("Platform:", platform, "| Producers:", length(producer_ids), "\n")

# --- 2. Batch if > 250 IDs ---
batch_size <- 250L
batches <- split(producer_ids, ceiling(seq_along(producer_ids) / batch_size))

# --- 3. Submit Jobs per Batch ---
job_ids <- c()

for (b in seq_along(batches)) {
  params <- list(
    "since" = "2026-01-01",
    "until" = "2026-01-31",
    "limit" = 100L,
    "mode" = "SNAPSHOT",
    "name" = paste0("Posts - Batch ", b),
    "description" = "Batched producer list query"
  )

  # Platform-specific ID parameter
  if (platform == "instagram") {
    params[["account_ids"]] <- paste(batches[[b]], collapse = ",")
    endpoint <- "instagram/posts/job"
  } else {
    params[["surface_ids"]] <- paste(batches[[b]], collapse = ",")
    endpoint <- "facebook/posts/job"
  }

  response <- client$post(path = endpoint, params = params)
  job_ids <- c(job_ids, fromJSON(response$text)$id)

  if (b < length(batches)) Sys.sleep(60)  # Rate limit
}

# --- 4. Wait and Collect Results ---
all_posts <- list()

for (job_id in job_ids) {
  job <- client$get_async_job(job_id = job_id)
  while (job$get_status() == "IN_PROGRESS") Sys.sleep(10)

  job$write_data_to_file(directory = "results", filename = paste0(job_id, ".json"))
  posts <- fromJSON(file.path("results", paste0(job_id, ".json")), flatten = TRUE)
  all_posts[[length(all_posts) + 1]] <- posts
}

# IMPORTANT: Use bind_rows for mismatched columns
posts_data <- bind_rows(all_posts)

# --- 5. Get Comments (Instagram nested endpoint) ---
if (platform == "instagram") {
  all_comments <- list()

  for (post_id in posts_data$id) {
    response <- client$get(
      path = paste0("instagram/posts/", post_id, "/comments/preview"),
      params = list("limit" = 100L)
    )
    result <- fromJSON(response$text, flatten = TRUE)

    if (!is.null(result$data) && length(result$data) > 0) {
      comments_df <- as.data.frame(result$data)
      comments_df$source_post_id <- post_id
      all_comments[[length(all_comments) + 1]] <- comments_df
    }

    Sys.sleep(1)  # Rate limit: 60/min
  }

  comments_data <- bind_rows(all_comments)
}
```

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| "Invalid parameter" | Wrong ID param name | Use `surface_ids` for Facebook, `account_ids` for Instagram |
| "Path '/producer-lists' was not found" (404) | Wrong endpoint | Use `/lists/producers` instead |
| "Invalid vector size" / "account_ids must have at most 250 elements" | Too many IDs | Batch into groups of 250 |
| `rbind` "numbers of columns do not match" | Combining dataframes with different columns | Use `dplyr::bind_rows()` |
| Producer list returns 0 IDs | Parsing wrong field | Extract from `list_data$producers$id` not `list_data$ids` |
| Empty results | IDs from wrong platform | Verify producer list platform matches endpoint |

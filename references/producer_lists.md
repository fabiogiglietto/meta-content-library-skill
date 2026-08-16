# Producer Lists

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

Producer lists are pre-defined sets of accounts for Facebook Pages/Profiles or Instagram Accounts, created in the Content Library UI.

## Critical: Endpoint Path

```
✓ Correct:  lists/producers/{list_id}
✗ Wrong:    producer-lists/{list_id}     ← Returns 404
```

The MCL UI shows the correct path when you click the API ID button on a producer list.

## Critical: Platform Differences

| Platform | Post ID Parameter | Account ID Parameter | Entity Types |
|----------|-------------------|---------------------|--------------|
| Facebook | `surface_ids` | `surface_ids` | pages, groups, profiles |
| Instagram | `post_ids` | `account_ids` | accounts |

**This is the #1 source of errors when working with producer lists.**

## List All Producer Lists

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "lists/producers")
lists <- mcl_fromJSON(response$text)

# View available lists
print(lists)
```

## Get Producer List Details

The response contains a `producers` **data.frame** with columns `id`, `name`, `type` — not a simple vector of IDs.

```r
list_id <- "2026-03-29-bqtm"

response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- mcl_fromJSON(response$text)

# Response structure:
# list_data$id        - character: list ID
# list_data$name      - character: list name
# list_data$platform  - character: "facebook" or "instagram"
# list_data$producers - data.frame: columns (id, name, type)

cat("List name:", list_data$name, "\n")
cat("Platform:", list_data$platform, "\n")
cat("Producer count:", nrow(list_data$producers), "\n")

# Extract the producers data.frame
producers <- list_data$producers
head(producers)
#          id                    name   type
# 1 252084...  DICO NO All'unione...   page
# 2 250547...     Emanuele Tesauro     page
# 3 249073...        Mauro Fagiolo  profile

# Extract just the IDs as a vector (character, thanks to mcl_fromJSON)
ids <- producers$id
stopifnot(is.character(ids))   # a numeric vector here means fromJSON() was used
```

## Query Posts from Producer List

### Auto-Detect Platform Pattern

```r
# Get list metadata first
response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- mcl_fromJSON(response$text)
platform <- tolower(list_data$platform)
ids <- list_data$producers$id  # Note: $producers$id, not $ids

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
job_data <- mcl_fromJSON(response$text)
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
  job_data <- mcl_fromJSON(response$text)
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

## Cross-Platform Account Matching

Find Instagram accounts that match Facebook pages in a producer list using name similarity:

```r
library(stringdist)  # Install via: cran$InstallPackages("stringdist", dependencies = TRUE)

# 1. Get FB producers (names already included in response)
response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- mcl_fromJSON(response$text)
fb_producers <- list_data$producers

# 2. Search IG accounts for each FB name
ig_candidates <- list()
for (i in seq_len(nrow(fb_producers))) {
  term <- gsub("[^[:alnum:][:space:]]", " ", fb_producers$name[i])
  term <- trimws(gsub("\\s+", " ", term))
  if (nchar(term) < 3) next

  cat(sprintf("[%d/%d] Searching IG for: '%s'\n", i, nrow(fb_producers), term)); flush.console()

  results <- tryCatch({
    resp <- client$get(
      path = "instagram/accounts/preview",
      params = list("q" = term, "limit" = 10L)
    )
    parsed <- mcl_fromJSON(resp$text)
    if (!is.null(parsed$data) && is.data.frame(parsed$data) && nrow(parsed$data) > 0) {
      parsed$data
    } else NULL
  }, error = function(e) { cat("  Error:", e$message, "\n"); NULL })

  if (!is.null(results)) {
    results$fb_source_id <- fb_producers$id[i]
    results$fb_source_name <- fb_producers$name[i]
    ig_candidates[[i]] <- results
  }

  Sys.sleep(1.5)  # Sync rate limit
}

# 3. Score by name similarity (Jaro-Winkler)
ig_all <- bind_rows(ig_candidates)
scored <- ig_all %>%
  rowwise() %>%
  mutate(
    name_sim = 1 - stringdist(tolower(name), tolower(fb_source_name), method = "jw"),
    user_sim = 1 - stringdist(tolower(username), tolower(gsub("[^[:alnum:]]", "", fb_source_name)), method = "jw"),
    best_sim = max(name_sim, user_sim, na.rm = TRUE)
  ) %>%
  ungroup() %>%
  distinct(id, .keep_all = TRUE) %>%
  mutate(
    tier = case_when(
      best_sim >= 0.90 ~ "HIGH",
      best_sim >= 0.75 ~ "MEDIUM",
      best_sim >= 0.60 ~ "LOW",
      TRUE             ~ "REVIEW"
    )
  ) %>%
  arrange(desc(best_sim))
```

### Instagram Account Fields (from /preview)

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique account ID |
| `name` | string | Display name |
| `username` | string | Instagram handle |
| `biography` | string | Profile bio text |
| `account_type` | string | "business" or "creator" |
| `is_verified` | boolean | Verified badge |
| `follower_count` | integer | Followers |
| `following_count` | integer | Following |
| `creation_date` | string | Account creation (e.g., "March 2016") |
| `website` | string | Profile website URL(s) |

## Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| 404 "Path not found" | Using `producer-lists/` path | Use `lists/producers/` |
| "first argument must be a vector" | Accessing `$ids` instead of `$producers$id` | Use `list_data$producers$id` |
| "Invalid parameter" | Wrong ID param name | Use `surface_ids` for Facebook, `account_ids` for Instagram |
| "missing value where TRUE/FALSE needed" | `nrow()` on NULL from empty search | Use safe response handling (check `is.null` and `is.data.frame` before `nrow`) |
| "Invalid Meta Content Library ID" (3790088) with IDs straight from a list | IDs parsed as numeric → `paste(ids, collapse = ",")` produces `"9.6378e+14,..."` | Parse the list with `mcl_fromJSON()`; check `is.character(ids)` before batching |
| Empty results | IDs from wrong platform | Verify producer list platform matches endpoint |
| Results truncated | Too many IDs | Batch into smaller groups |

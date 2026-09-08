# Producer lists — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

Every snippet parses with `mcl_fromJSON()` (`languages/r/ids.md` §
"mcl_fromJSON") so that producer ids arrive as character; `safe_get_data()` is
in `languages/r/jobs.md` § "Safe response handling".

## ID parameters are arrays

Facts: `references/producer_lists.md` § "Critical: ID Parameters Must Be Arrays"

```r
# ✓ Correct - array (Python list), even for one ID
params[[id_param]] <- as.list(ids)

# ✗ Wrong - a length-1 R vector: reticulate converts it to a Python *string*
params[[id_param]] <- ids[1]
```

reticulate converts an R character vector of length > 1 into a Python list, but
a length-1 vector into a Python string. `as.list()` stays a list at every
length, so use it unconditionally — the full mechanism is in
`languages/r/query_params.md` § "ID parameters are arrays".

## Recipe: producer list from active commenters

Facts: `references/producer_lists.md` § "Recipe: producer list from active commenters"

`top_commenters` is one row per account, aggregated from comment records parsed
with `mcl_fromJSON()` (so the handle is `owner.username` and the display name is
`owner.name`).

```r
library(dplyr)
library(readr)

# Weights for the activity blend — tune these, don't bury them in the formula
W <- c(comments = 0.4, posts = 0.3, reactions = 0.2, days = 0.1)

producers <- top_commenters %>%
  # 1. Keep only public accounts: both a display name and a username.
  #    No username -> no URL -> cannot be imported.
  filter(!is.na(owner.username), nzchar(owner.username),
         !is.na(owner.name),     nzchar(owner.name)) %>%
  # 2. Safety net in case the upstream table isn't already one row per account —
  #    duplicates would silently burn slots against the 1,000 cap
  mutate(username = tolower(trimws(owner.username))) %>%
  distinct(username, .keep_all = TRUE) %>%
  # 3. Score activity as a weighted blend of percentile ranks, so no single
  #    heavy-tailed metric dominates
  mutate(
    activity_score =
      W[["comments"]]  * percent_rank(n_comments)      +
      W[["posts"]]     * percent_rank(n_distinct_posts) +
      W[["reactions"]] * percent_rank(n_reactions)      +
      W[["days"]]      * percent_rank(n_active_days)
  ) %>%
  # 4. Keep the top quartile, then cap at the 1,000-producer import limit
  filter(activity_score >= quantile(activity_score, 0.75, na.rm = TRUE)) %>%
  arrange(desc(activity_score))

if (nrow(producers) > 1000L) {
  cat("Top quartile has", nrow(producers), "accounts - dropping",
      nrow(producers) - 1000L, "below the 1,000 import cap\n"); flush.console()
}
producers <- slice_head(producers, n = 1000L)

# 5. Write the one-column import file (literal header, space and capitals)
producers %>%
  transmute(`Producer URL` = paste0("https://www.facebook.com/", owner.username)) %>%
  write_csv("producer_import.csv")   # write_csv, not write.csv (no row-name column)
```

`write_csv()` rather than `write.csv()`: the base function adds a row-name
column, which would make the file two-column and break the import.

## List all producer lists

Facts: `references/producer_lists.md` § "List All Producer Lists"

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

## Resolving a list by name — [verified 2026-08-21]

Facts: `references/producer_lists.md` § "Resolving a list by name — names are NOT unique"

```r
ll  <- mcl_fromJSON(client$get(path = "lists/producers")$text)
d   <- if (!is.null(ll$data)) ll$data else ll
hit <- d[trimws(tolower(d$name)) == tolower(TARGET_NAME), ]
stopifnot(NROW(hit) == 1)          # 2 matches is a real, observed case
list_id <- hit$id[1]
```

`stopifnot(NROW(hit) == 1)` is the guard the neutral file calls "necessary but
not sufficient": when it stops on two or three ids, follow the tie-break
procedure there (fetch each candidate, compare producer-id sets).

## Get producer list details

Facts: `references/producer_lists.md` § "Get Producer List Details"

The `producers` payload arrives as a **data.frame** with columns `id`, `name`,
`type` — not a simple vector of IDs.

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

`nrow(list_data$producers)` is the count to size batching arithmetic from, not
the UI's figure.

## Auto-detect platform pattern

Facts: `references/producer_lists.md` § "Auto-Detect Platform Pattern"

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
params[[id_param]] <- as.list(ids)   # array, not a comma-joined string

# Submit job
response <- client$post(
  path = paste0(platform, "/posts/job"),
  params = params
)
job_data <- mcl_fromJSON(response$text)
job_id <- job_data$id
```

## Batching large producer lists

Facts: `references/producer_lists.md` § "Batching Large Producer Lists"

`batch_ids()` is defined here and reused by the metadata sections below.

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
  params[[id_param]] <- as.list(batch)   # array, even if the batch has 1 ID
  
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

`as.list(batch)` even on the last batch: `split()` can leave a single ID there,
and a length-1 vector would be sent as a scalar (§ "ID parameters are arrays").

## Instagram account metadata

Facts: `references/producer_lists.md` § "Instagram Accounts"

```r
# Batch IDs (max ~50 per query for reliability)
id_batches <- batch_ids(ids, batch_size = 50L)

for (batch in id_batches) {
  params <- list(
    "account_ids" = as.list(batch),
    "limit" = 100L
  )
  
  response <- client$get(
    path = "instagram/accounts/preview",
    params = params
  )
  # Process results...
}
```

## Facebook page metadata

Facts: `references/producer_lists.md` § "Facebook Pages"

```r
for (batch in id_batches) {
  params <- list(
    "surface_ids" = as.list(batch),
    "limit" = 100L
  )
  
  response <- client$get(
    path = "facebook/pages/preview",
    params = params
  )
  # Process results...
}
```

## Cross-platform account matching

Facts: `references/producer_lists.md` § "Cross-Platform Account Matching"

Needs `stringdist` for Jaro–Winkler; install it in the SRE with
`cran$InstallPackages()` as the first line shows.

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

`bind_rows()` on `ig_candidates` works because every element was parsed with
`mcl_fromJSON()`, so `id` is character in every batch.

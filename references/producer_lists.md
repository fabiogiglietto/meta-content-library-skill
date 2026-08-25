# Producer Lists

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

Producer lists are pre-defined sets of accounts for Facebook Pages/Profiles or Instagram Accounts, created in the Content Library UI.

**A list created in the UI is invisible to the API until you generate an API ID
for it** — a manual, per-list step. See § "Share producer lists between the UI
and the API".

## Critical: Endpoint Path

```
✓ Correct:  lists/producers/{list_id}
✗ Wrong:    producer-lists/{list_id}     ← Returns 404
```

The `{list_id}` here is the **API producer list ID** — a date-slug such as
`2026-08-17-cwqm`, *not* the numeric id in the UI's URL. It must be generated
per list; see § "Share producer lists between the UI and the API".

## Critical: Platform Differences

| Platform | Post ID Parameter | Account ID Parameter | Entity Types |
|----------|-------------------|---------------------|--------------|
| Facebook | `surface_ids` | `surface_ids` | pages, groups, profiles |
| Instagram | `post_ids` | `account_ids` | accounts |

**This is the #1 source of errors when working with producer lists.**

## Critical: ID Parameters Must Be Arrays

`surface_ids` / `account_ids` / `post_ids` are **array** parameters. A scalar is
rejected with `"Invalid parameter"` — including the case of a single ID:

```r
# ✓ Correct - array (Python list), even for one ID
params[[id_param]] <- as.list(ids)

# ✗ Wrong - a length-1 R vector: reticulate converts it to a Python *string*
params[[id_param]] <- ids[1]
```

reticulate converts an R character vector of length > 1 into a Python list, but
a length-1 vector into a Python string. `as.list()` stays a list at every
length, so use it unconditionally — batching loops otherwise fail only on the
final batch when it happens to hold a single ID.

## Creating a Producer List (CSV Import in the UI)

Producer lists are **created in the Content Library UI**, not via the API. The
import file is a CSV with a **single column named `Producer URL`**, one public
Facebook URL per row, **max 1,000 producers per list**:

```csv
Producer URL
https://www.facebook.com/giorgiameloni
https://www.facebook.com/matteosalviniofficial
```

Notes:

- Import is by **URL**, not by MCL id. MCL ids are internal and differ from the
  public Facebook URL — you cannot turn an MCL id into a producer URL. Use the
  account's username (`owner.username` on comment/post records).
- Accounts that expose only a display name and no username can't be represented
  as a URL and can't be imported this way.
- Producers are public Pages, groups, events, or profiles; profiles must be
  public and either verified — including paid Meta Verified — or have 100+
  followers under v6.0. Lists built against the old 25,000 threshold are not
  wrong, just narrower than they need to be.
- **After creating a list in the UI you must generate an API ID before the API
  can see it at all** — see § "Share producer lists between the UI and the API".
  This is not optional and not automatic.

### Recipe: producer list from active commenters

Build a list of the accounts that comment most actively on a corpus. Input is a
top-commenters table with one row per account, as produced by aggregating
comment records parsed with `mcl_fromJSON()` (so the handle is `owner.username`
and the display name is `owner.name`).

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

Then import `producer_import.csv` in the Content Library UI and generate an API
ID for the resulting list.

## Share producer lists between the UI and the API

**A producer list created in the UI is not reachable from the API until you
generate an API ID for it.** The id is **generated on demand and does not
pre-exist**. Until it is generated the list is absent from `lists/producers`
*and* unreachable at `lists/producers/{id}` — it is invisible, not merely
mis-addressed.

Source: [Share a producer list](https://developers.facebook.com/docs/content-library-and-api/appendix/share-producer-list).
Requires **v4.0 or later**. **[documented 2026-08-22]**

### The UI steps — walked end to end, **[verified 2026-08-22]**

1. **Producers lists** in the left navigation bar
2. **View** on the list's card (or open `/producer-lists/{ui_id}/` directly)
3. the **`▼` caret immediately to the RIGHT of the `Share` button**
4. **Create API list ID**
5. a dialog shows the id and the exact call to make

The top bar reads, left to right: `···` · `Share` · **`▼`** · `Save changes`.

**Three traps, each of which cost a live session real time:**

- **The caret is to the RIGHT of `Share`, not the left.** Meta's page says only
  "adjacent to the Share button". The control on the *left* is the `···` menu.
- **The caret's accessible label is `Copy`, not anything containing "dropdown" or
  "API".** Searching the DOM for a control labelled "Open Dropdown" finds the
  `···` menu and misses this one entirely. Identify it by
  `aria-haspopup="menu"` positioned to the right of the `Share` button, not by
  its label.
- **The `···` menu and the `Share` dialog are both dead ends.** `···` offers
  *Make a copy / Rename / Delete / Version history*; `Share` opens people-access
  (email invite, viewer/owner, copy link). Before the caret menu is opened, the
  string "API" does not appear anywhere in the page text.

The caret menu contains exactly: **`Copy link`** and **`Create API list ID`**.

**Driving it programmatically:** a bare `element.click()` does **not** open this
menu — the app ignores it. A full pointer sequence does:
`pointerover, pointerenter, pointerdown, mousedown, pointerup, mouseup, click`,
each with `clientX`/`clientY` at the element centre. Same for the menu item.

### The id format tells you when the snapshot was taken

The dialog's own wording:

> *"The ID consists of the today's date in YYYY-MM-DD format, followed by a
> randomly generated string of characters."*

So `2026-08-22-lxdb` was generated on 2026-08-22. **The date in a producer-list
id is the date the ID was generated — i.e. the date of the snapshot — not the
date the list was created.** That makes the id self-documenting about snapshot
age, which is exactly the provenance a reproducible analysis needs: an id whose
date is months before your collection window is a warning sign on its face.

### The id is a SNAPSHOT — this has research consequences

Meta's wording: the API ID *"represents a **snapshot** of a producer list."*

The id is therefore bound to the list **as it was when the id was generated**,
not to the list as it evolves. Edits made afterwards — adding or removing
producers, possibly renaming — are not guaranteed to be visible through an id
generated earlier.

- **Finish curating the list, then generate the id.** Not the other way round.
- **If you edit a list after generating its id, regenerate the id**, and record
  which id a given analysis actually used.
- **Record the id together with the date it was generated.** Two analyses citing
  "the same list" under different ids may not be using the same producers — a
  reproducibility hazard that is invisible in the results.
- A producer count from `lists/producers/{id}` that disagrees with the UI's count
  is the **expected symptom of a stale id**, not a bug.

### Symptom → cause

| Symptom | Cause |
|---|---|
| A list plainly visible in the UI is absent from `lists/producers` | No API ID has been generated for it |
| `lists/producers/{numeric id from the UI URL}` errors | The UI URL id is not the API id — see § "Critical: Endpoint Path" |
| The API's producer count differs from the UI's | The id is a snapshot predating the list's last edit |

### Sharing with other researchers

*"You can only share producer lists with users who have the same account type as
yours."* **[documented]**

### Creation is UI-only — VERIFIED against the spec

`client$openapi_spec()`, read live on 2026-08-22, declares exactly two methods on
the producer-list paths, **both `get`**:

```
/lists/producers            -> get
/lists/producers/{alias_id} -> get
```

**There is no `POST`. Producer lists cannot be created or modified through the
API** — the CSV import in the UI is the only route, and the API-ID step above is
the only way to make a list readable. **[verified 2026-08-22]**

This matters because it is a natural thing to assume otherwise: every other
collection-shaped resource in this API (`async/jobs`, `async/queries`,
marketplace-listings jobs) *does* accept a POST. Producer lists are the exception.

### The path parameter is `{alias_id}`, not `{list_id}`

The spec names it **`alias_id`**. That wording is consistent with the API ID
being a *snapshot alias* rather than a pointer to the live list — see the
snapshot section above. This file uses `{list_id}` throughout for readability;
they are the same thing.

### Related, from the same spec read: `/lists/shared-searches/{alias_id}`

A sibling endpoint exists — **`get`** only — for **shared searches**, the
saved-search analogue of a shared producer list. This skill does not otherwise
document it. **[verified 2026-08-22 — endpoint exists; parameters and response
shape unread]**

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

### Resolving a list by name — names are NOT unique

**[verified 2026-08-21]** A single `lists/producers` response carried **two**
lists with byte-identical names — same platform, same producer count, same
composition, one evidently made with the UI's "Make a copy". A resolve-by-name
helper will silently pick one of them, and which one it picks is not stable.

Because the list id is a date-slug generated per snapshot (§ "Share producer
lists between the UI and the API"), resolving by name is the natural reflex.
Assert uniqueness every time:

```r
ll  <- mcl_fromJSON(client$get(path = "lists/producers")$text)
d   <- if (!is.null(ll$data)) ll$data else ll
hit <- d[trimws(tolower(d$name)) == tolower(TARGET_NAME), ]
stopifnot(NROW(hit) == 1)          # 2 matches is a real, observed case
list_id <- hit$id[1]
```

Prefer pinning the id itself in analysis code, with the date it was generated.

#### The guard is necessary but not sufficient — you also need a tie-break

**[verified 2026-08-24]** The two-identical-lists case above is the easy one. A later
account held **three** ids per name, and they were *not* all the same list:

| id | name | producers | types |
|---|---|---|---|
| `2026-08-24-kasv` | Extremists 2 (clean) | 96 | page 84, profile 12 |
| `2026-08-24-iicm` | Extremists 2 (clean) | 96 | page 84, profile 12 |
| `2026-03-29-bqtm` | Extremists 2 (clean) | **95** | page 83, profile 12 |

Comparing the producer-id **sets**, not just the counts:

```
kasv vs iicm   identical: TRUE    shared 96      <- same-day pair, redundant
kasv vs bqtm   identical: FALSE   shared 95      <- different population
```

So `stopifnot(NROW(hit) == 1)` correctly refuses to guess, but on its own it leaves you
stuck. The resolution procedure that works:

1. **Fetch each candidate's detail** — the `lists/producers` listing carries only
   `id`, `name`, `platform`, **no producer count**, so the counts that let you tell them
   apart require one GET per candidate.
2. **Compare the producer-id sets**, not the counts. Equal counts do not imply equal sets.
3. **Same-date duplicates are typically redundant** (byte-identical here, on both names) —
   pick either and record which.
4. **Cross-date ids are different populations**, because the date in the id is the date
   the snapshot was taken (§ "The id format tells you when the snapshot was taken"). The
   five-month-old ids each held one producer fewer.
5. **The researcher chooses.** Which snapshot is correct is a research decision — a fresh
   population or a reproduction of an older one — not something the resolver can infer.

The reason this cannot be shortcut: a wrong pick here yields a complete, plausible answer
to a slightly different question, with nothing downstream to flag it.

#### Lists sharing producers is normal — dedupe before passing ids

Where a query spans several lists, expect heavy overlap. `Extremists 1` (144) and
`Extremists 2` (96) shared **89** producers, so the deduped union was **151**, not 240.
Passing the concatenation would have sent 89 ids twice. Union, `unique()`, then chunk.

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

### The UI and the API can disagree on producer count

**[verified 2026-08-21]** For one list the UI header read *"50 of 832
producers"* while `lists/producers/{id}` returned **830**. The cause is
**[open]** — plausibly accounts that no longer resolve.

**Treat `nrow(list_data$producers)` as authoritative for batching arithmetic**,
and do not check it against the UI figure to decide whether a pull is complete.
A batching loop sized from the UI number will look like it is two producers
short of a full pass every time.

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
params[[id_param]] <- as.list(ids)   # array, not a comma-joined string

# Submit job
response <- client$post(
  path = paste0(platform, "/posts/job"),
  params = params
)
job_data <- mcl_fromJSON(response$text)
job_id <- job_data$id
```

### `account_ids` vs `post_ids` (Instagram)

These are not alternatives for the same job:

| Parameter | Platform | Selects |
|-----------|----------|---------|
| `surface_ids` | Facebook | Posts made to these pages / groups / profiles |
| `account_ids` | Instagram | Posts **by** these accounts — the producer-list case above |
| `post_ids` | either | These **specific posts**, by ID (e.g. resolving reshare originals) |

So a producer-list query uses `surface_ids` on Facebook and `account_ids` on
Instagram. `post_ids` is for when you already hold the post IDs you want.

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

## Query Account/Page Information

To get profile metadata (not posts) for IDs in a producer list:

### Instagram Accounts

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

### Facebook Pages

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
| "Invalid parameter" with the right param name | ID param passed as a scalar — e.g. a length-1 vector that reticulate turned into a Python string | Pass an array: `params[[id_param]] <- as.list(ids)` |
| "missing value where TRUE/FALSE needed" | `nrow()` on NULL from empty search | Use safe response handling (check `is.null` and `is.data.frame` before `nrow`) |
| "Invalid Meta Content Library ID" (3790088) with IDs straight from a list | IDs parsed as numeric → `paste(ids, collapse = ",")` produces `"9.6378e+14,..."` | Parse the list with `mcl_fromJSON()`; check `is.character(ids)` before batching |
| Empty results | IDs from wrong platform | Verify producer list platform matches endpoint |
| Results truncated | Too many IDs | Batch into smaller groups |

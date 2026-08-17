# Query Parameters Reference

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

## Common Parameters (All Endpoints)

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (keywords, phrases, boolean) |
| `since` | string | Start date (YYYY-MM-DD) |
| `until` | string | End date (YYYY-MM-DD) |
| `limit` | integer | Results per page (use `L` suffix: `100L`) |
| `lang` | string | Language filter (ISO 639-1: "en", "es") |
| `country` | string | Country filter (ISO 3166-1: "US", "GB") |
| `surface_ids` | list | Filter to specific Page/Account IDs — **character strings only** |

## Async-Only Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `mode` | string | `"SNAPSHOT"` (recommended) or `"LIVE"` |
| `name` | string | Query name for identification |
| `description` | string | Purpose, methodology, IRB info |

## Boolean Query Syntax

```r
# AND (both required)
"q" = "climate AND policy"

# OR (either term)
"q" = "climate OR environment"

# NOT (exclude)
"q" = "vaccine NOT covid"

# ✗ Exact phrase - NOT supported by the API (subcode 3790184), UI only
"q" = '"climate change"'

# ✓ Use a distinctive single token, or tokens joined with OR
# (OR broadens — it matches either word, not the phrase)
"q" = "climate OR warming"

# Complex
"q" = '(climate OR environment) AND (policy OR legislation)'
```

## Producer Lists

Query posts from specific accounts using a producer list:

```r
# Get producer list (note: lists/producers/ not producer-lists/)
response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- mcl_fromJSON(response$text)

# Response: $producers is a data.frame with cols: id, name, type
ids <- list_data$producers$id
platform <- tolower(list_data$platform)

# Use correct ID parameter for platform
id_param <- if (platform == "instagram") "account_ids" else "surface_ids"

params <- list(
    "since" = "2024-01-01",
    "mode" = "SNAPSHOT",
    "name" = "Producer List Query",
    "description" = "Posts from tracked accounts"
)
params[[id_param]] <- as.list(ids)   # array, not a comma-joined string

response <- client$post(
    path = paste0(platform, "/posts/job"),
    params = params
)
```

## Comments Queries

Comments require `parent_ids` (post IDs):

```r
response <- client$post(
    path = "facebook/comments/job",
    params = list(
        "parent_ids" = c("post_id_1", "post_id_2"),
        "mode" = "SNAPSHOT",
        "name" = "Comments on Target Posts",
        "description" = "Comments for sentiment analysis"
    )
)
```

## Estimate Response

```r
estimate <- mcl_fromJSON(client$get(
    path = "facebook/posts/estimate",
    params = list("q" = "election", "since" = "2024-01-01", "until" = "2024-12-31")
)$text)

# Key fields:
# estimate$estimated_results - Approximate count
# estimate$expected_complete - TRUE if <100k (will get all results)
```

## Integer Parameters (Critical!)

Always use `L` suffix for integers:

```r
# ✓ Correct
params = list("limit" = 100L, "offset" = 0L)

# ✗ Wrong - will cause type errors
params = list("limit" = 100, "offset" = 0)
```

## ID Parameters Are Always Character (Critical!)

`L` applies to counts and limits — **never to IDs**. IDs are 15–19 digits, far
beyond `.Machine$integer.max`, and a bare numeric literal becomes a double that
is sent in scientific notation → "Invalid Meta Content Library ID" (subcode
3790088).

```r
# ✓ Correct - array of quoted strings
params = list("surface_ids" = list("963780196442228", "252084123456789"), "limit" = 100L)
params[[id_param]] <- as.list(ids)   # ids came from mcl_fromJSON() → character

# ✗ Wrong - numeric IDs
params = list("surface_ids" = 963780196442228)          # sent as 9.6378e+14
params = list("surface_ids" = as.list(as.numeric(ids))) # each sent as 9.6378e+14

# ✗ Wrong - scalar instead of array → "Invalid parameter"
params = list("surface_ids" = ids[1])   # length-1 vector → Python string

# Rescue an ID that arrived as numeric from elsewhere (CSV, spreadsheet, reticulate)
ids <- sprintf("%.0f", ids)     # NOT as.character(), which yields "1.784e+16"
```

## Platform-Specific ID Parameters

| Platform | Endpoint | ID Parameter | Notes |
|----------|----------|--------------|-------|
| Facebook | `/facebook/posts/preview` | `surface_ids` | Pages, groups, profiles |
| Facebook | `/facebook/comments/preview` | `parent_ids` | Post IDs as parameter |
| Instagram | `/instagram/posts/preview` | `post_ids` | NOT `surface_ids` |
| Instagram | `/instagram/accounts/preview` | `account_ids` | Account lookup |
| Instagram | Post comments | N/A | Use nested URL: `/instagram/posts/{id}/comments/preview` |

**Common Error:** Using `surface_ids` for Instagram returns "Missing required parameters". Use `post_ids` instead.

## Producer List Endpoint

```
✓ Correct: lists/producers/{list_id}
✗ Wrong:   producer-lists/{list_id}     ← Returns 404
```

The producer list response contains a `$producers` data.frame (columns: id, name, type), not a `$ids` vector.

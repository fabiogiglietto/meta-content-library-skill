# Query Parameters Reference

## Common Parameters (All Endpoints)

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query (keywords, phrases, boolean) |
| `since` | string | Start date (YYYY-MM-DD) |
| `until` | string | End date (YYYY-MM-DD) |
| `limit` | integer | Results per page (use `L` suffix: `100L`) |
| `lang` | string | Language filter (ISO 639-1: "en", "es") |
| `country` | string | Country filter (ISO 3166-1: "US", "GB") |
| `surface_ids` | list | Filter to specific Page/Account IDs |

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

# Exact phrase
"q" = '"climate change"'

# Complex
"q" = '(climate OR environment) AND (policy OR legislation)'
```

## Producer Lists

Query posts from specific accounts:

```r
# Get producer list IDs
producers <- fromJSON(client$get(path = "lists/producers")$text)

# Query with surface_ids
response <- client$post(
    path = "facebook/posts/job",
    params = list(
        "surface_ids" = list("page_id_1", "page_id_2"),
        "since" = "2024-01-01",
        "mode" = "SNAPSHOT",
        "name" = "Producer List Query",
        "description" = "Posts from tracked accounts"
    )
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
estimate <- fromJSON(client$get(
    path = "facebook/posts/estimate",
    params = list("q" = "election", "since" = "2024-01-01", "until" = "2024-12-31")
)$text, flatten = TRUE)

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

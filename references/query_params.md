# Query Parameters Reference

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

## Common Parameters (All Endpoints)

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query — keywords and boolean operators. **No double-quoted phrases** (subcode 3790184) |
| `since` | string | Start date (YYYY-MM-DD) |
| `until` | string | End date (YYYY-MM-DD) |
| `limit` | integer | Results per page (use `L` suffix: `100L`) |
| `lang` | string | Language filter (ISO 639-1: "en", "es") |
| `country` | string | Country filter (ISO 3166-1: "US", "GB") |
| `surface_ids` | list | Facebook only: filter to specific page / group / profile IDs — **character strings only**, always `as.list()` |
| `account_ids` | list | Instagram only: filter to specific account IDs — same rules |

## Async-Only Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `mode` | string | `"SNAPSHOT"` (recommended) or `"LIVE"` |
| `name` | string | Query name for identification |
| `description` | string | Purpose, methodology, IRB info |

## Query Syntax (`q`)

### Boolean Operators

Combine terms with `AND`, `OR`, `NOT`, and parentheses:

```r
# AND - both terms required
params = list("q" = "climate AND policy")

# OR - either term
params = list("q" = "climate OR environment")

# NOT - exclude term
params = list("q" = "vaccine NOT covid")

# Complex combinations with parentheses
params = list("q" = "(climate OR environment) AND (policy OR legislation)")
```

### No Double-Quoted Phrases (subcode 3790184)

Unlike the Content Library UI, the API **rejects** double-quoted phrase searches:

```json
{"title":"Invalid Keyword Search",
 "detail":"Searching with phrases using double quotes is not supported. Please search without double quotes.",
 "error_subcode":3790184,"status":400}
```

```r
# ✗ Rejected by the API (works only in the UI)
params = list("q" = '"climate change"')

# ✓ Distinctive single token
params = list("q" = "climate")

# ✓ Tokens joined with OR
params = list("q" = "climate OR warming")

# ✓ Narrow with AND instead of a phrase
params = list("q" = "climate AND policy")
```

`OR` does not reproduce a phrase — it matches posts containing *either* word, so
it broadens the corpus rather than matching the bigram. Prefer a distinctive
single token where one exists (`Meloni` rather than `"Giorgia Meloni"`, `M5S`
rather than `"Movimento 5 Stelle"`), and use `AND` when both words must appear.

Note that `q = "climate change"` — an R string holding two space-separated words
— is fine: no double-quote character reaches the API. What 3790184 rejects is a
query **value** containing `"` characters, i.e. `q = '"climate change"'`.

## Producer Lists

Read a list with `lists/producers/{list_id}`, then pass its IDs as the
platform's ID parameter — `surface_ids` for Facebook, `account_ids` for
Instagram:

```r
list_data <- mcl_fromJSON(client$get(path = paste0("lists/producers/", list_id))$text)
ids       <- list_data$producers$id            # character, via mcl_fromJSON()
platform  <- tolower(list_data$platform)
id_param  <- if (platform == "instagram") "account_ids" else "surface_ids"

params <- list("since" = "2024-01-01", "mode" = "SNAPSHOT",
               "name" = "Producer List Query",
               "description" = "Posts from tracked accounts")
params[[id_param]] <- as.list(ids)   # array, not a comma-joined string

response <- client$post(path = paste0(platform, "/posts/job"), params = params)
```

`references/producer_lists.md` owns this topic: list creation, response shape,
batching, cross-platform matching, and the `account_ids` vs `post_ids`
distinction.

## Comments Queries

Comments require `parent_ids` (post IDs):

```r
response <- client$post(
    path = "facebook/comments/job",
    params = list(
        "parent_ids" = as.list(post_ids),   # array, even for one ID
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

## Finding MCL IDs (Never Use URL IDs)

The numeric ID in a Facebook/Instagram **URL** is not a valid Content Library ID
— MCL assigns its own (privacy by design). Passing a URL ID is rejected with
`error_subcode 3790088` ("Invalid Meta Content Library ID"). Look the entity up
by name via the matching preview endpoint and use the `id` it returns.

**See SKILL.md § "Finding Surface IDs"** for the per-entity lookup table and the
full pattern.

## ID Parameter Batch Limits

`post_ids` accepts at most **250 IDs per call**. Chunk longer lists — and chunk
`surface_ids` at ≤ 250 as well, to stay on the safe side:

```r
chunks <- split(ids, ceiling(seq_along(ids) / 250L))
for (chunk in chunks) {
  params <- list("limit" = 100L)
  params[["post_ids"]] <- as.list(chunk)
  # ...
}
```

`references/producer_lists.md` batches at 50 for producer-list queries, which is
well inside this limit.

## Never Pass an Empty `params`

```r
# ✗ Wrong - reticulate converts list() to a Python list [], and the client
#   calls .items() on it → 'list' object has no attribute 'items'
client$get(path = "budgets", params = list())

# ✓ Correct - omit params entirely, or pass a named list
client$get(path = "budgets")
```

## Platform-Specific ID Parameters

| Platform | Endpoint | ID Parameter | Notes |
|----------|----------|--------------|-------|
| Facebook | `/facebook/posts/preview` | `surface_ids` | Pages, groups, profiles |
| Facebook | `/facebook/comments/preview` | `parent_ids` | Post IDs as parameter |
| Instagram | `/instagram/posts/preview` | `account_ids` | Posts **by** these accounts |
| Instagram | `/instagram/posts/preview` | `post_ids` | These **specific posts**, by ID |
| Instagram | `/instagram/accounts/preview` | `account_ids` | Account lookup |
| Instagram | Post comments | N/A | Use nested URL: `/instagram/posts/{id}/comments/preview` |

**Common Error:** Using `surface_ids` for Instagram returns "Missing required
parameters. Input at least one parameter [q, post_ids, account_ids]".
`surface_ids` is Facebook-only. See `references/producer_lists.md` §
"`account_ids` vs `post_ids` (Instagram)" for which of the two you want.

## Producer List Endpoint

Use `lists/producers/{list_id}` — `producer-lists/{list_id}` returns 404, and
the response carries a `$producers` data.frame (id, name, type), not a `$ids`
vector. Details: `references/producer_lists.md`.

# Query parameters and endpoints — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Reading the OpenAPI spec

Facts: `SKILL.md` § "OpenAPI Spec"

```r
spec <- client$openapi_spec()
paths <- names(spec$paths)

# Find Instagram endpoints
instagram_paths <- paths[grepl("instagram", paths, ignore.case = TRUE)]
print(instagram_paths)

# Inspect one endpoint's parameters
str(spec$paths[["/instagram/posts/preview"]]$get$parameters)

# Save full spec for reference
write(toJSON(spec, pretty = TRUE), "openapi_spec.json")
```

## Paging a preview — [verified 2026-08-29]

Facts: `SKILL.md` § "Key Endpoints (v6.0)"

The response carries `paging$cursors$after`; pass it back as `after` until it is
absent or empty:

```r
acc <- list(); after <- NULL
repeat {
  p <- c(base_params, if (!is.null(after)) list(after = after))
  pg <- mcl_fromJSON(client$get(path = "facebook/posts/preview", params = p)$text)
  acc <- c(acc, list(pg$data))
  after <- pg$paging$cursors$after
  if (is.null(after) || !nzchar(after)) break
}
```

## Nested endpoints

Facts: `SKILL.md` § "Nested Endpoints"

The parent ID goes in the **path**, not in `params`:

```r
# ✓ Correct - post_id in URL path
client$get(
  path = paste0("instagram/posts/", post_id, "/comments/preview"),
  params = list("limit" = 10L)
)

# ✗ Wrong - post_id as parameter
client$get(
  path = "instagram/comments/preview",
  params = list("post_ids" = post_id)
)
```

## Looking up a surface ID

Facts: `SKILL.md` § "Finding Surface IDs (MCL IDs ≠ Facebook/Instagram URL IDs)"

Search the entity by name and read the `id` MCL returns; never use the number
from the Facebook or Instagram URL:

```r
# GROUP -> get its MCL surface id (do NOT use the number from the group URL)
resp <- client$get(
  path   = "facebook/groups/preview",
  params = list("q" = "GROUP NAME", "limit" = 50L)
)
groups <- mcl_fromJSON(resp$text)$data
print(groups[, c("id", "name", "member_count")])   # use this `id`, not the URL number

GROUP_ID <- "PASTE_MCL_ID_FROM_SEARCH"   # quoted! e.g. "963780196442228", NOT the URL's 910620404641635
```

## Integer parameters

Facts: `references/query_params.md` § "Integer Parameters"

An R `100` is a double and reaches the Python client as `100.0`. Every integer
parameter takes the `L` suffix:

```r
# ✓ Correct
params = list("limit" = 100L, "offset" = 0L)

# ✗ Wrong - will cause type errors
params = list("limit" = 100, "offset" = 0)
```

`L` applies to counts and limits — **never to IDs** (next section).

## ID parameters are arrays

Facts: `references/query_params.md` § "ID Parameters Are Arrays of Strings"

`surface_ids` / `account_ids` / `post_ids` must be sent as arrays, and that
includes a single ID: reticulate converts a length-1 R vector into a Python
scalar, which the API rejects with `"Invalid parameter"`. Use `as.list()`
unconditionally:

```r
params[["surface_ids"]] <- as.list(ids)   # ✓ array at every length
params[["surface_ids"]] <- ids[1]         # ✗ sent as a scalar string
```

And the elements must be character. IDs are 15–19 digits, far beyond
`.Machine$integer.max`, so a bare numeric literal becomes a double that is
sent in scientific notation → "Invalid Meta Content Library ID" (subcode
3790088). IDs that came through `mcl_fromJSON()` are already character; rescue
one that arrived as numeric from elsewhere with `sprintf("%.0f", x)`, never
`as.character()`:

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

## Never pass an empty params

Facts: `references/query_params.md` § "Never Pass an Empty `params`"

`params = list()` (an empty, unnamed list) becomes a Python list `[]`, and the
client calls `.items()` on it → `'list' object has no attribute 'items'`. Omit
`params` when there are none, or pass a named list.

```r
# ✗ Wrong - reticulate converts list() to a Python list [], and the client
#   calls .items() on it → 'list' object has no attribute 'items'
client$get(path = "budgets", params = list())

# ✓ Correct - omit params entirely, or pass a named list
client$get(path = "budgets")
```

## Running an API search ID

Facts: `SKILL.md` § "API Search IDs — run a UI search from code"

The alias goes in the **path**, not in `params`:

```r
# Run the stored search synchronously
resp <- client$get(path = "facebook/posts/preview/2026-08-25-abcd")

# ... or as an async job
job <- client$post(path = "facebook/posts/job/2026-08-25-abcd",
                   params = list("mode" = "SNAPSHOT",
                                 "name" = "UI search, replayed",
                                 "description" = "PI: …, IRB #…"))

# Inspect the filters an alias carries, without running it
filters <- mcl_fromJSON(client$get(path = "lists/shared-searches/2026-08-25-abcd")$text)
```

## Link search without `q` — [verified 2026-08-29]

Facts: `references/query_params.md` § "The `link` parameter"

```r
# right
client$get(path = "facebook/posts/preview",
           params = list(link = URL, since = S, until = U, limit = 100L, fields = F))
```

## Filtering `creation_time` client-side — [verified 2026-08-21]

Facts: `references/query_params.md` § "The `since` / `until` window is not a clean UTC day"

Request one day wider than you need, then keep only the rows whose
`creation_time` falls on the target UTC date:

```r
# want: posts created on 2026-08-20 UTC
res <- ...   # query with since = "2026-08-20", until = "2026-08-21"
ct   <- as.POSIXct(gsub("T", " ", sub("(\\+|Z).*$", "", res$creation_time)), tz = "UTC")
res  <- res[which(as.Date(ct) == as.Date("2026-08-20")), , drop = FALSE]
```

## Pinning `until` with an epoch second — [not yet run]

Facts: `references/query_params.md` § "The experiment that would close this"

`as.integer()` matters: `as.POSIXct()` yields a double, and `until` is
integer-typed when given as a timestamp.

```r
# 2026-08-24 00:00:00 UTC, exactly
until_epoch <- as.integer(as.POSIXct("2026-08-24 00:00:00", tz = "UTC"))
params <- list("since" = "2026-08-17", "until" = until_epoch, ...)
```

## Query operators

Facts: `references/query_params.md` § "The word forms `AND` / `OR` / `NOT` are not documented operators"

```r
# ✓ union — either word
params = list("q" = "climate | environment")

# ✓ intersection — both words (a blank space IS the AND operator)
params = list("q" = "climate policy")
params = list("q" = "climate&policy")     # identical

# ✓ exclusion
params = list("q" = "vaccine -covid")

# ✓ grouping
params = list("q" = "(climate | environment) (policy | legislation)")
```

## No double-quoted phrases

Facts: `references/query_params.md` § "No Double-Quoted Phrases (subcode 3790184)"

What 3790184 rejects is a `"` character inside the query **value** — the
single-quoted R literal `'"climate change"'` below. The double-quoted R string
`"climate change"` is fine: no quote character reaches the API, and the space
is the AND operator.

```r
# ✗ Rejected by the API (works only in the UI)
params = list("q" = '"climate change"')

# ✓ Distinctive single token
params = list("q" = "climate")

# ✓ Tokens joined with OR
params = list("q" = "climate | warming")

# ✓ Narrow with AND instead of a phrase
params = list("q" = "climate policy")
```

## Querying a producer list

Facts: `references/query_params.md` § "Producer Lists"

`ids` is character because it came through `mcl_fromJSON()`; `as.list()` sends
it as an array rather than a comma-joined string.

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

## Submitting a comments job

Facts: `references/query_params.md` § "Comments Queries"

```r
response <- client$post(
    path = "facebook/comments/job",
    params = list(
        "parent_ids" = as.list(post_ids),   # array, even for one ID; max 250
        "fetch_all" = TRUE,                 # all reply levels, not just top-level
        "mode" = "SNAPSHOT",
        "name" = "Comments on Target Posts",
        "description" = "Comments for sentiment analysis"
    )
)
```

## Reading an estimate

Facts: `references/query_params.md` § "Estimate Response"

```r
estimate <- mcl_fromJSON(client$get(
    path = "facebook/posts/estimate",
    params = list("q" = "election", "since" = "2024-01-01", "until" = "2024-12-31")
)$text)

# Key fields:
# estimate$estimated_results - Approximate count
# estimate$expected_complete - TRUE if <100k (will get all results)
```

Use `nrow()` of the result, not `estimated_results`, as the denominator of any
reported rate.

## Requesting nested fields — [verified 2026-08-22]

Facts: `references/query_params.md` § "Field expansion: the `fields` parameter uses BRACE syntax, not dots"

```r
# CORRECT — returns id, statistics.like_count, statistics.haha_count
client$get(path = "facebook/posts/preview",
           params = list("q" = "cybercrime",
                         "fields" = "id,statistics{like_count,haha_count}"))
```

## Previewing a `fields` string before the job — [verified 2026-08-25]

Facts: `references/query_params.md` § "`fields` works on the ASYNC JOB endpoint too"

`id_params` is the named list holding the producer IDs (`surface_ids` or
`account_ids`, built with `as.list()` as in "Querying a producer list" above);
`c()` splices it into the parameter list.

```r
FIELDS <- paste0("id,creation_time,text,lang,surface{id,name,type},",
                 "statistics{views,reaction_count,comment_count,share_count,like_count}")

# 1. FREE positive control -- confirm the projection before spending anything
pv <- mcl_fromJSON(client$get(path = "facebook/posts/preview",
                              params = c(list("limit" = 5L, "fields" = FIELDS), id_params))$text)
stopifnot("text" %in% names(pv$data))          # the field that is NOT default

# 2. the same string on the job
job <- client$post(path = "facebook/posts/job",
                   params = c(list("fields" = FIELDS, "mode" = "LIVE"), id_params))
```

## Chunking an ID list

Facts: `references/query_params.md` § "ID Parameter Batch Limits"

```r
chunks <- split(ids, ceiling(seq_along(ids) / 250L))
for (chunk in chunks) {
  params <- list("limit" = 100L)
  params[["post_ids"]] <- as.list(chunk)
  # ...
}
```

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
params = list("limit" = 100L)   # ✓
params = list("limit" = 100)    # ✗ type mismatch
```

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

## Never pass an empty params

Facts: `references/query_params.md` § "Never Pass an Empty `params`"

`params = list()` (an empty, unnamed list) becomes a Python list `[]`, and the
client calls `.items()` on it → `'list' object has no attribute 'items'`. Omit
`params` when there are none, or pass a named list.

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

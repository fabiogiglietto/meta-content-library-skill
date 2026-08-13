# Common Errors and Solutions

## Producer List Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 404 "Path '/meta-content-library/producer-lists/{id}' was not found" | Wrong endpoint path | Use `lists/producers/{id}` not `producer-lists/{id}`. The MCL UI shows the correct path when you click the API ID button. |
| "first argument must be a vector" on `split()` | Accessing `$ids` (doesn't exist) instead of `$producers$id` | Producer list response has `$producers` data.frame with columns (id, name, type). Use `list_data$producers$id` to get the ID vector. |

## Response Handling Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "missing value where TRUE/FALSE needed" on `nrow()` | API returned NULL or empty list instead of data.frame | Always validate before `nrow()`: `if (!is.null(x) && is.data.frame(x) && nrow(x) > 0)` |
| "$ operator is invalid for atomic vectors" | Accessing nested field on empty/atomic response | Parse with `fromJSON(resp$text, flatten = TRUE)` and check structure before accessing fields |

### Safe Response Pattern

```r
# Wrap all API data extraction in this pattern
safe_get_data <- function(response_text) {
  parsed <- fromJSON(response_text, flatten = TRUE)
  if (!is.null(parsed$data) && is.data.frame(parsed$data) && nrow(parsed$data) > 0) {
    return(parsed$data)
  }
  return(NULL)
}

# Usage in loops
results <- tryCatch({
  resp <- client$get(path = "instagram/accounts/preview", params = list("q" = term, "limit" = 10L))
  safe_get_data(resp$text)
}, error = function(e) {
  cat("Error:", e$message, "\n"); flush.console()
  return(NULL)
})

if (!is.null(results)) {
  cat("Found", nrow(results), "results\n")
}
```

## Instagram Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing required parameters. Input at least one parameter [q, post_ids, account_ids]" | Used `surface_ids` for Instagram | Use `post_ids` for posts, `account_ids` for accounts |
| "Invalid Meta Content Library ID" (subcode 3790088) | Used a raw Instagram URL ID, or the post/account is not in MCL | MCL IDs are library-specific and differ from the numeric IDs in Instagram URLs. Look the account up with `instagram/accounts/preview` (search with `q`) and use the returned `id`. If a search-returned ID still fails, the post may be private, deleted, or from an account with <1K followers. |
| "Invalid Meta Content Library ID" on comments endpoint | Wrong endpoint pattern | Use nested URL `/instagram/posts/{id}/comments/preview` instead of parameter-based query |

## Facebook Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing required parameters" | Wrong ID parameter | Use `surface_ids` for Facebook entities |
| "Invalid Meta Content Library ID" (subcode 3790088) | Used the numeric ID from a Facebook group/page URL as `surface_ids` | URL IDs are never valid MCL IDs. Search by name (e.g. `facebook/groups/preview` with `q`) and use the returned `id`. Private or non-indexed groups don't appear in search and aren't queryable. |

## General Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Type mismatch | Missing `L` suffix on integers | Add `L`: `limit = 100L` |
| Method not allowed | GET on /job endpoint | Use POST for async job endpoints |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset, check with `/budgets` |

## Debugging with OpenAPI Spec

When encountering parameter or endpoint errors, check the OpenAPI spec:

```r
spec <- client$openapi_spec()
paths <- names(spec$paths)

# Find relevant endpoints
relevant <- paths[grepl("your_keyword", paths, ignore.case = TRUE)]
print(relevant)

# Check specific endpoint parameters
endpoint_spec <- spec$paths[["/instagram/posts/preview"]]
print(names(endpoint_spec$get$parameters))
```

## Debugging Response Structure

When an API response causes unexpected errors, inspect the raw structure:

```r
response <- client$get(path = "some/endpoint", params = list(...))

# 1. Raw JSON
cat(substr(response$text, 1, 2000), "\n")

# 2. Parsed structure
parsed <- fromJSON(response$text, flatten = TRUE)
cat("Top-level fields:", paste(names(parsed), collapse = ", "), "\n")

# 3. Inspect each field
for (fn in names(parsed)) {
  val <- parsed[[fn]]
  cat(sprintf("  %s: class=%s, length=%s\n", fn, paste(class(val), collapse="/"), length(val)))
  if (is.data.frame(val)) {
    cat("    rows:", nrow(val), "cols:", paste(names(val), collapse = ", "), "\n")
  }
}
```

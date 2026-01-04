# Common Errors and Solutions

## Instagram Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing required parameters. Input at least one parameter [q, post_ids, account_ids]" | Used `surface_ids` for Instagram | Use `post_ids` for posts, `account_ids` for accounts |
| "Invalid Meta Content Library ID" | Post/account not in MCL | Post may be private, deleted, or from account with <1K followers. Use IDs returned from MCL searches. |
| "Invalid Meta Content Library ID" on comments endpoint | Wrong endpoint pattern | Use nested URL `/instagram/posts/{id}/comments/preview` instead of parameter-based query |

## Facebook Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing required parameters" | Wrong ID parameter | Use `surface_ids` for Facebook entities |

## General Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Type mismatch | Missing `L` suffix on integers | Add `L`: `limit = 100L` |
| Method not allowed | GET on /job endpoint | Use POST for async job endpoints |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset, check with `/budgets` |

## Debugging with OpenAPI Spec

When encountering parameter errors, check the OpenAPI spec:

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

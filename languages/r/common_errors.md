# Common errors — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Errors that only exist through reticulate

Facts: `SKILL.md` § "Common Errors"

These do not come from the API; they come from how R values cross into the
Python client. None of them exists in the Python layer.

| Error | Cause | Fix |
|-------|-------|-----|
| Type mismatch | Missing `L` suffix | Add `L` to integers — `languages/r/query_params.md` § "Integer parameters" |
| Invalid parameter with the right param name | A length-1 vector reticulate turned into a scalar string | `as.list(ids)` — `languages/r/query_params.md` § "ID parameters are arrays" |
| `'list' object has no attribute 'items'` | Passed `params = list()` (empty list) | Omit `params`, or pass a named list |
| Invalid Meta Content Library ID (subcode 3790088) with a *correct* ID | ID held as `numeric`, so it was sent as `9.6378e+14` | Parse with `mcl_fromJSON()`; pass IDs as quoted character — `languages/r/ids.md` |

## Errors that only exist in R

Facts: `references/common_errors.md` § "ID / Numeric Precision Errors"

These come from jsonlite, dplyr and base R, not from the API.

| Error / symptom | Cause | Solution |
|-----------------|-------|----------|
| "Can't combine `id` <character> and `id` <double>" on `bind_rows()` | `bigint_as_char = TRUE` only converts a column when a value in *that batch* exceeds 2^53, so chunk types differ | Coerce every ID field unconditionally — `mcl_fromJSON()` does this |
| A `parent_id` column full of the literal string `"NA"` | Blanket `sprintf("%.0f", x)` over a column containing JSON `null` | Use `mcl_fix_ids()`, which maps `NA` → `NA_character_` |
| IDs read back from a CSV are doubles again | `read_csv()`/`read.csv()` type-guess numeric ID columns | `read_csv(f, col_types = cols(.default = col_character()))` |
| "first argument must be a vector" on `split()` | Accessing `$ids` (doesn't exist) instead of `$producers$id` | Producer list response has `$producers` data.frame with columns (id, name, type). Use `list_data$producers$id` to get the ID vector. |
| "missing value where TRUE/FALSE needed" on `nrow()` | API returned NULL or empty list instead of data.frame | Always validate before `nrow()`: `if (!is.null(x) && is.data.frame(x) && nrow(x) > 0)` — `safe_get_data()` in `languages/r/jobs.md` |
| "$ operator is invalid for atomic vectors" | Accessing nested field on empty/atomic response | Parse with `mcl_fromJSON(resp$text)` and check structure before accessing fields |
| "first argument must be a vector" | Accessing a field the response doesn't have | Inspect the parsed response first: `str(mcl_fromJSON(resp$text))` |

Notes:
- `as.character()` is **not** a safe converter: `as.character(1.784e16)` returns `"1.784e+16"`. Use `sprintf("%.0f", x)`.
- `options(scipen = 999)` changes display only. The value is still a double and still rounds above 2^53.

Wrapping a call in a loop so one failure is logged rather than fatal:

```r
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

## Debugging with the OpenAPI spec

Facts: `references/common_errors.md` § "Debugging with OpenAPI Spec"

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

## Debugging response structure

Facts: `references/common_errors.md` § "Debugging Response Structure"

```r
response <- client$get(path = "some/endpoint", params = list(...))

# 1. Raw JSON
cat(substr(response$text, 1, 2000), "\n")

# 2. Parsed structure
parsed <- mcl_fromJSON(response$text)
cat("Top-level fields:", paste(names(parsed), collapse = ", "), "\n")

# 3. Inspect each field
for (fn in names(parsed)) {
  val <- parsed[[fn]]
  cat(sprintf("  %s: class=%s, length=%s\n", fn, paste(class(val), collapse="/"), length(val)))
  if (is.data.frame(val)) {
    cat("    rows:", nrow(val), "cols:", paste(names(val), collapse = ", "), "\n")
  }
}

# 4. Confirm every ID field came out as character
if (is.data.frame(parsed$data)) {
  id_cols <- grep(MCL_ID_PATTERN, names(parsed$data), value = TRUE)
  str(parsed$data[id_cols])   # all should be chr, none showing e+15 / e+16
}
```

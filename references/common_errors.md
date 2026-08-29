# Common Errors and Solutions

> All examples here parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". Never call `fromJSON()` directly
> on an MCL response — IDs come back as doubles.

> This file is the **full** error catalog. `SKILL.md` § "Common Errors" carries
> only the subset that changes how you write a first query.

## ID / Numeric Precision Errors

| Error / symptom | Cause | Solution |
|-----------------|-------|----------|
| "Invalid Meta Content Library ID" (subcode 3790088) with an ID you copied from a search result | The ID is a `numeric`, so `paste0()` rendered it as `9.6378e+14` in the URL or parameter | Parse with `mcl_fromJSON()`; hard-code IDs as quoted strings (`"963780196442228"`, never bare digits) |
| "Can't combine `id` <character> and `id` <double>" on `bind_rows()` | `bigint_as_char = TRUE` only converts a column when a value in *that batch* exceeds 2^53, so chunk types differ | Coerce every ID field unconditionally — `mcl_fromJSON()` does this |
| Joins/`distinct()` silently miss matches; IDs end in unexpected digits | IDs above 2^53 (~9.0e15) lost precision when parsed as double (`...123` → `...124`) | Re-parse from the raw response/file with `mcl_fromJSON()`. Rounded IDs are unrecoverable |
| A `parent_id` column full of the literal string `"NA"` | Blanket `sprintf("%.0f", x)` over a column containing JSON `null` | Use `mcl_fix_ids()`, which maps `NA` → `NA_character_` |
| IDs read back from a CSV are doubles again | `read_csv()`/`read.csv()` type-guess numeric ID columns | `read_csv(f, col_types = cols(.default = col_character()))` |
| Nested `author.id` / `producer.id` still numeric | ID regex didn't account for `flatten = TRUE` dot names | Match with `"(^|[._])ids?$"` (what `mcl_fix_ids()` uses) |

Notes:
- `as.character()` is **not** a safe converter: `as.character(1.784e16)` returns `"1.784e+16"`. Use `sprintf("%.0f", x)`.
- `options(scipen = 999)` changes display only. The value is still a double and still rounds above 2^53.

## Producer List Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 404 "Path '/meta-content-library/producer-lists/{id}' was not found" | Wrong endpoint path | Use `lists/producers/{id}` not `producer-lists/{id}`. |
| A producer list visible in the UI is **absent from `lists/producers`** and also errors at `lists/producers/{id}` | **No API ID has been generated for that list.** The id is created on demand, not automatically | In the UI: *Producers lists* → *View* → the **down-arrow next to `Share`** → **Create API list ID**. The `···` menu does *not* offer this. See `producer_lists.md` § "Share producer lists between the UI and the API" |
| Producer count from the API disagrees with the count shown in the UI | The API ID is a **snapshot**; the list was edited after the id was generated | Regenerate the API ID and record which id the analysis used |
| "first argument must be a vector" on `split()` | Accessing `$ids` (doesn't exist) instead of `$producers$id` | Producer list response has `$producers` data.frame with columns (id, name, type). Use `list_data$producers$id` to get the ID vector. |

## Response Handling Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "missing value where TRUE/FALSE needed" on `nrow()` | API returned NULL or empty list instead of data.frame | Always validate before `nrow()`: `if (!is.null(x) && is.data.frame(x) && nrow(x) > 0)` |
| "$ operator is invalid for atomic vectors" | Accessing nested field on empty/atomic response | Parse with `mcl_fromJSON(resp$text)` and check structure before accessing fields |
| "first argument must be a vector" | Accessing a field the response doesn't have | Inspect the parsed response first: `str(mcl_fromJSON(resp$text))` |

### Safe Response Pattern

```r
# Wrap all API data extraction in this pattern
safe_get_data <- function(response_text) {
  parsed <- mcl_fromJSON(response_text)   # IDs as character (SKILL.md § ID Handling)
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
| "Invalid Meta Content Library ID" (subcode 3790088) with a valid MCL ID | ID held as `numeric` → `paste0("instagram/posts/", post_id, "/comments/preview")` builds `.../1.784e+16/comments/preview` | Parse with `mcl_fromJSON()` so `post_id` is character before it reaches the URL |
| "Invalid Meta Content Library ID" on comments endpoint | Wrong endpoint pattern | Use nested URL `/instagram/posts/{id}/comments/preview` instead of parameter-based query |

## Facebook Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing required parameters" | Wrong ID parameter | Use `surface_ids` for Facebook entities |
| "Invalid Meta Content Library ID" (subcode 3790088) | Used the numeric ID from a Facebook group/page URL as `surface_ids` | URL IDs are never valid MCL IDs. Search by name (e.g. `facebook/groups/preview` with `q`) and use the returned `id`. Private or non-indexed groups don't appear in search and aren't queryable. |
| "Invalid Meta Content Library ID" (subcode 3790088) with a valid MCL ID | `surface_ids` built from numeric IDs → each value is sent as `9.6378e+14` | Keep IDs character end-to-end (`mcl_fromJSON()`), or convert with `sprintf("%.0f", ids)` before building the array |
| "Invalid parameter" with a correct `surface_ids` / `account_ids` / `post_ids` name | ID param sent as a scalar — e.g. a length-1 R vector that reticulate turned into a Python string | Pass an array: `params[[id_param]] <- as.list(ids)` |

| "Invalid Meta Content Library ID" (3790088) when resolving a reshare | The reshared original is out of scope for the Content Library, and one bad ID rejects the **whole** `post_ids` call | Bisect the batch and skip the offenders — see `references/field_reference.md` § "Reshares" |

## Scope and Quota Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Estimated response size too large" (subcode 3790057) | A single query would return more than ~100,000 results | Split by date window and/or query fewer `surface_ids` — see `references/chunking.md` |
| "Exceeded async snapshots limit" (subcode 3790172) | More than 100 concurrent SNAPSHOT jobs | Run `mode = "LIVE"` where reproducibility isn't needed, and delete finished snapshots — see `references/collections.md` § "The 100-Snapshot Cap" |
| A producer-list post query estimates ~0 results | The list is mostly ordinary profiles, whose posts aren't in the queryable dataset | Only public profiles that are verified or have 100+ followers qualify (v6.0; it was 1,000 in v5.0 and 25,000 before that) — see `references/field_reference.md` § "Data Scope" |
| "Invalid Keyword Search" (subcode 3790184) | The query used a double-quoted phrase | Drop the double quotes; use single-word tokens joined with `OR` — see `references/query_params.md` § "Query Syntax (`q`)" |
| "Invalid time range" (subcode **3790079**) | `until` is in the future, or `since` is not before `until` | **[verified 2026-08-29]** `until` must be strictly **before the current epoch time**. Verbatim: *"The since time must come before the until time, and the until time must come before current_epoch_time."* A window ending "today or later" fails outright |

## Failures that return HTTP 200 — **[verified 2026-08-29]**

The worst class: the call succeeds, the rows look plausible, and the filter never
ran. A row count is not evidence a parameter was honoured. **Score every filter
against a control that must return nothing** — e.g. a URL nobody could have
shared — and treat "same rows as without the filter" as *ignored*, not *working*.

| Symptom | Cause | Solution |
|---|---|---|
| `q` + `link` returns a full page of posts unrelated to the URL | The `link` matched nothing, so it was **dropped from the query** and you got the `q`-only result set (Jaccard 1.0 against `q` alone) | Drop `q`. `link` alone works and returns 0 correctly for an unmatched URL — see `references/query_params.md` § "The `link` parameter" |
| `estimate` reports millions for a link query | The same bug reaches `estimate`, so a mistyped URL is sized as if unfiltered | Size link queries with `link` alone, no `q` — magnitudes in `query_params.md` § "The `link` parameter" |
| An Instagram query with `link` returns unfiltered results | `instagram/posts` has no link filter and **silently ignores** the parameter | There is no link search on Instagram. Filter client-side on `link_attachment` — see `references/query_params.md` § Instagram |
| `link` returns 0 for a URL you know was shared | The exact string is not a key Meta has seen — **not** proof nobody shared it | Try the publisher's canonical form; see the false-zero rates in `query_params.md` § "The `link` parameter" |
| A `fields` name returns no column | Unknown names are dropped silently | Send a positive control (`statistics{like_count}`) in the same request — see `references/query_params.md` |

## General Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Type mismatch | Missing `L` suffix on integers | Add `L`: `limit = 100L` |
| Method not allowed | GET on /job endpoint | Use POST for async job endpoints |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset, check with `/budgets` |
| `'list' object has no attribute 'items'` | Passed `params = list()` (empty list) | reticulate converts an empty R list to a Python list `[]`, and the client calls `.items()` on it. Omit `params` when there are none, or pass a named list. |

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

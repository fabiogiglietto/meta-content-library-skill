# Field reference — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Fetching reshared originals

Facts: `references/field_reference.md` § "Reshares"

```r
resp <- client$get(
  path   = "facebook/posts/preview",
  params = list("post_ids" = as.list(shared_ids), "limit" = 100L)   # array, max 250
)
originals <- safe_get_data(resp$text)
originals[, c("id", "post_owner.id", "post_owner.username")]
```

## Resolving originals defensively

Facts: `references/field_reference.md` § "Reshares"

```r
resolve_originals <- function(ids) {
  if (length(ids) == 0L) return(NULL)
  out <- tryCatch(
    safe_get_data(client$get(
      path   = "facebook/posts/preview",
      params = list("post_ids" = as.list(ids), "limit" = 100L)
    )$text),
    error = function(e) NULL
  )
  if (!is.null(out)) return(out)
  if (length(ids) == 1L) return(NULL)          # this one ID is out of scope - skip it
  mid <- length(ids) %/% 2L
  bind_rows(resolve_originals(ids[seq_len(mid)]),
            resolve_originals(ids[(mid + 1L):length(ids)]))
}
```

## Replies as a second pull

Facts: `references/field_reference.md` § "Replies: one job with `fetch_all`, or a second pull"

```r
# 1. Top-level comments for the posts
top <- safe_get_data(client$post(
  path   = "facebook/comments/job",
  params = list("parent_ids" = as.list(post_ids), "mode" = "SNAPSHOT",
                "name" = "Top-level comments", "description" = "…")
)$text)

# 2. Replies: pass the COMMENT ids that have replies
with_replies <- top$id[top$statistics.top_level_reply_count > 0]
replies <- safe_get_data(client$post(
  path   = "facebook/comments/job",
  params = list("parent_ids" = as.list(with_replies), "mode" = "SNAPSHOT",
                "name" = "Replies", "description" = "…")
)$text)
# reply records carry parent_id = the comment they answer
```

## Requesting match_type — [verified 2026-08-22]

Facts: `references/field_reference.md` § "`image_text` is a match_type VALUE, not a field — but it IS usable"

```r
client$get(path = "facebook/posts/preview",
           params = list("q" = "governo",
                         "search_scope" = "post_text_and_image_text",
                         "fields" = "id,match_type"))
# -> match_type tally over 25 rows:  image_text 5 | post_text 24
```

## Reading field names from the spec

Facts: `references/field_reference.md` § "THE RULE: get field names from the SPEC, not the data dictionary"

```r
sp <- client$openapi_spec()
fb <- sp$components$schemas$FacebookPost$properties
names(fb)                                  # the definitive field list for THIS deployment
sp$components$schemas$LinkAttachment$properties   # and its nested schemas
```

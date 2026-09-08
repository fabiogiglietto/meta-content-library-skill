# ID handling — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Why R needs a helper

Facts: `SKILL.md` § "ID Handling (IDs Are Strings)"

MCL IDs are 15–19 digit numbers, and some endpoints return them **unquoted** in
JSON. `jsonlite::fromJSON()` then parses them as `numeric`, which breaks two ways:
silent precision loss above 2^53, and scientific notation (`9.6378e+14`) below
it, which turns a path like `paste0("instagram/posts/", post_id, "/comments/preview")`
into a garbage URL and earns subcode 3790088.

There is also a typing hazard specific to jsonlite: `bigint_as_char = TRUE`
alone converts a column **only when some value in that batch exceeds 2^53**, so
the same column is `chr` in one chunk and `num` in the next, and `bind_rows()`
fails with *"Can't combine `id` <character> and `id` <double>"*.

## mcl_fromJSON

Facts: `SKILL.md` § "ID Handling (IDs Are Strings)"

Fix both at once — parse with `bigint_as_char = TRUE`, then coerce every ID
field unconditionally:

```r
# Matches id, post_id, surface_ids, parent_id, and flattened author.id / producer.id
MCL_ID_PATTERN <- "(^|[._])ids?$"

mcl_fix_ids <- function(x, name = "") {
  if (is.data.frame(x)) {
    x[] <- Map(mcl_fix_ids, x, names(x))
    return(x)
  }
  if (is.list(x)) {                      # nested lists and list-columns of IDs
    nms <- names(x)
    if (is.null(nms)) nms <- rep(name, length(x))
    x[] <- Map(mcl_fix_ids, x, nms)
    return(x)
  }
  if (grepl(MCL_ID_PATTERN, name) && is.numeric(x)) {   # numeric only: is_invalid_id stays logical
    out <- rep(NA_character_, length(x))  # keeps JSON null as NA, not the string "NA"
    ok <- !is.na(x)
    out[ok] <- sprintf("%.0f", x[ok])     # full digits, never scientific notation
    return(out)
  }
  x
}

# Use this for EVERY MCL response — response text or a job's saved .json file
mcl_fromJSON <- function(txt) {
  mcl_fix_ids(fromJSON(txt, flatten = TRUE, bigint_as_char = TRUE))
}
```

Every example in this skill parses responses with `mcl_fromJSON()` instead of
`fromJSON()`. It accepts response text (`resp$text`) and a file path (a job's
saved `.json`) alike, because `fromJSON()` does.

## Rules that follow

Facts: `SKILL.md` § "ID Handling (IDs Are Strings)"

| Do | Don't |
|----|-------|
| `mcl_fromJSON(resp$text)` | `fromJSON(resp$text, flatten = TRUE)` |
| `mcl_fromJSON(file.path("results", "job.json"))` | `fromJSON(filepath, flatten = TRUE)` |
| `sprintf("%.0f", x)` to fix a stray numeric ID | `as.character(x)` — returns `"1.784e+16"` for big IDs |
| `read_csv(f, col_types = cols(.default = col_character()))` | `read_csv(f)` — re-parses ID columns as double |
| Keep IDs as character in `distinct()`, joins, and `as.list(ids)` params | Comparing/merging on numeric IDs |
| Hard-code IDs as quoted strings: `"963780196442228"` | An unquoted 15+ digit literal — it is a double, and is sent in scientific notation |

`options(scipen = 999)` only changes **display** — the value is still a double
and still rounds above 2^53. It is not a fix.

If an ID reaches R as a number from somewhere else (a CSV, a Python object via
reticulate, a spreadsheet), convert it with `sprintf("%.0f", x)` immediately —
and treat anything at or above 2^53 as already corrupted, since re-fetching it
from MCL is the only way back.

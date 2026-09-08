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

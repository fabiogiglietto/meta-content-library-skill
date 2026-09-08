# Utilities — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Budget headroom

Facts: `SKILL.md` § "Rate Limits & Budget"

Read `max_usage_limit` from `budgets` rather than hard-coding 500,000 — the
ceiling is a per-account setting:

```r
budget <- mcl_fromJSON(client$get(path = "budgets")$text)
cat("Available:", budget$queries$max_usage_limit - budget$queries$total_usage, "\n")
```

# Open question: `async/queries` returns 502 Bad Gateway

**Status:** open. One observation, 2026-08-24.

## The question

Is `GET async/queries` broken, or was this transient?

## What was seen

```r
ql <- mcl_fromJSON(client$get(path = "async/queries")$text)
```

```
<html>
<head><title>502 Bad Gateway</title></head>
<body>
<center><h1>502 Bad Gateway</h1></center>
</body>
</html>
```

The endpoint returns an **HTML error page**, so `mcl_fromJSON()` raises rather than
returning anything parseable, and the error surfaces as a `requests.exceptions.HTTPError`
through reticulate. Observed once; the call was then wrapped in `tryCatch` and the run
continued without it.

Same session, minutes either side: `budgets`, `async/jobs`, `lists/producers`,
`lists/producers/{id}`, `facebook/posts/estimate`, `facebook/posts/preview`,
`facebook/posts/job` and `client$openapi_spec()` all responded normally. So it was not a
general outage of the API or of that account's access.

## Why it matters

`async/jobs` carries **no `name` column** (`references/collections.md` § "The `async/jobs`
envelope key"). The name supplied at submission lives on the *query*, so `async/queries`
is the only route to **"has a job for this window already been submitted?"** — the check
that prevents a duplicate spend when more than one person, or more than one agent session,
is working the same question. On 2026-08-24 that check was wanted and unavailable, and a
concurrent session working the same corpus was already known to exist.

`references/collections.md` documents four operations against this endpoint (list, get,
update metadata, move to collection, delete). If the 502 is persistent, **all of them are
unreachable**, including `visibility = "PUBLIC"` — the documented sharing path.

## What would settle it

One zero-budget call on any later session:

```r
r <- client$get(path = "async/queries")
cat(substr(r$text, 1, 120), "\n")
```

| Outcome | Action |
|---|---|
| Valid JSON | Transient. Record the date, delete this file, and note in `collections.md` that a 502 was seen once. |
| 502 again | Persistent. Promote to a documented limitation in `collections.md`, mark the query-management block **[broken]**, and file a support ticket (`docs/SUPPORT_TICKET_ML_MODELS.md` shows the format of a filed one). |
| A different error | New information; reopen with both observations. |

## Correct regardless of the answer

**Wrap `async/queries` in `tryCatch` and carry on.** Nothing in a collection run should
depend on it:

```r
ql <- tryCatch(mcl_fromJSON(client$get(path = "async/queries")$text),
               error = function(e) NULL)
if (is.null(ql)) cat("queries-endpoint: unavailable\n")
```

This is already the form used on 2026-08-24 and it is correct whether the endpoint is
broken or merely flaky.

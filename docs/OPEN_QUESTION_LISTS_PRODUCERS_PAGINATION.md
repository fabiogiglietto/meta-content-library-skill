# Open question: is `lists/producers` paginated?

**Status:** open. Never tested; noticed 2026-08-24.

## The question

`GET lists/producers` returned **80 lists** in a single call. Is that everything the
account can see, or the first page of more?

## What is known

- The response envelope is `{"data": [...]}`, and `data` is a data.frame with exactly
  three columns: `id`, `name`, `platform`. **[verified 2026-08-24]**
- **No `paging`, `next`, `cursor`, `after` or `limit` field appeared anywhere in the
  response**, and none is documented in `references/producer_lists.md` § "List All
  Producer Lists".
- By contrast, `facebook/posts/preview` on the same day returned an envelope of
  `data, paging` — so **this API does use a `paging` key where pagination exists**, and its
  absence here is weak evidence that the listing is complete. Weak, not conclusive: 80 is
  a suspiciously round number, and an endpoint can page without advertising it on page one.

### Checked against Meta's documentation, 2026-08-25 — still nothing

The appendix page that documents the feature
([Share producer lists](https://developers.facebook.com/docs/content-library-and-api/appendix/share-producer-list))
describes the UI steps, the snapshot semantics, the `/lists/producers/<api_producer_list_id>`
path and the same-account-type sharing rule. **It says nothing about pagination,
about a `limit` parameter, or about any cap on the number of lists returned.**

That is a third weak signal in the same direction as the missing `paging` key —
and it is worth exactly as much: the guides omit an `estimate` endpoint that the
OpenAPI spec declares (see `references/surfaces.md`), so an absence in the guides
is not evidence of an absence in the API. **The spec, not the guides, is where
this could still be answered without a live call**: read
`client$openapi_spec()$paths[["/lists/producers"]]$get$parameters` and see whether
a `limit` or `after` is declared. That is free and has not been done.

## Why it matters

Resolve-by-name is the documented and recommended way to reach a list, because the API id
is a per-snapshot date-slug and the UI URL id is not it (§ "Critical: Endpoint Path"). If
the listing silently pages, then a name that resolves to **zero** matches may be a list
that simply is not on page one — and the caller's reasonable conclusion, "the list has no
API ID generated yet", would be wrong. That sends someone into the UI to regenerate an ID
that already exists, and § "The id is a SNAPSHOT" warns that regenerating changes which
producers an analysis actually used.

So the failure is not "missing data"; it is **a plausible wrong diagnosis of a
resolution failure**, on the exact path this file tells people to use.

## What would settle it

Zero budget, on any account with a known list count:

```r
ll <- mcl_fromJSON(client$get(path = "lists/producers")$text)
d  <- ll$data
cat("returned:", NROW(d), "| envelope keys:", paste(names(ll), collapse = ","), "\n")

# Does it accept a limit at all? If pagination exists, this should change the count.
l2 <- mcl_fromJSON(client$get(path = "lists/producers", params = list("limit" = 5L))$text)
cat("with limit=5L:", NROW(if (!is.null(l2$data)) l2$data else l2), "\n")
```

| Outcome | Reading |
|---|---|
| `limit` ignored, same count, no `paging` key | Listing is complete. Document it and delete this file. |
| `limit` respected, or a `paging` key appears | Paginated. Document the cursor and fix the resolve-by-name recipe to page. |
| Count equals the account's true list count | Complete for that account, but says nothing about larger accounts — leave open. |

Best tested on an account holding **more than 80** lists; 80 is exactly the kind of number
a default page size takes.

## Correct regardless of the answer

**Print the listing size next to any resolve-by-name result**, so a suspicious round
number is visible at the point of use:

```r
cat("lists-visible:", NROW(d), "| matches:", NROW(hit), "\n")
```

And when a name resolves to zero, **report pagination as one of the candidate causes**
alongside spelling, platform, the wrong account, and an ungenerated API ID — rather than
concluding the list is invisible to the API.

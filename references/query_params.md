# Query Parameters Reference

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

## Common Parameters (All Endpoints)

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query — keywords and boolean operators. **No double-quoted phrases** (subcode 3790184) |
| `since` | string | Start date (YYYY-MM-DD). **Not a clean UTC-midnight boundary — see below** |
| `until` | string | End date (YYYY-MM-DD). **Inclusive of at least part of the named date — see below** |
| `limit` | integer | Results per page (use `L` suffix: `100L`) |
| `lang` | string | Language filter (ISO 639-1: "en", "es") |
| `country` | string | Country filter (ISO 3166-1: "US", "GB") |
| `surface_ids` | list | Facebook only: filter to specific page / group / profile IDs — **character strings only**, always `as.list()` |
| `account_ids` | list | Instagram only: filter to specific account IDs — same rules |

## Post Filters (Facebook Posts)

> Documented, not tested — transcribed from the Facebook posts guide
> (fetched 2026-08-21). Confirm anything surprising with `client$openapi_spec()`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `search_scope` | enum | `post_text_only` (default) or `post_text_and_image_text` — the text-in-images search added in v5.0. OCR covers roughly the last 180 days |
| `content_types` | list | `albums`, `photos`, `videos` (includes reels), `links`, `stories`, `reshare`, `status`. **Replaces `media_types`**, deprecated in v5.0 |
| `sort` | enum | `most_to_least_views` (the v5.0 default), `newest_to_oldest`, `oldest_to_newest`. Versions before 5.0 defaulted to newest-first — a query that used to return recent posts now returns the most-viewed ones |
| `is_surface_verified` | boolean | Restrict to posts whose Page or profile is verified |
| `is_branded_content` | boolean | Include or exclude branded-content posts |
| `link` | string | Filter on a URL in the post. Only usable **together with** `q` |
| `surface_types` | list | `page`, `profile`, `group`, `event` |
| `surface_countries` | list | ISO 3166-1 alpha-2, uppercase |
| `views_bucket_start` / `views_bucket_end` | integer | View-count bounds |
| `post_ids` | list | Specific posts, max 250 |
| `fields` | list | Field selection |

`profile_ids`, `page_ids`, `group_ids` and `event_ids` were deprecated in v4.0
in favour of `surface_ids`; `admin_countries` and `owner_types` became
`surface_countries` and `surface_types`. Code written against the older names
predates two deprecations and will not run.

### The Four Spellings of "verified"

Same concept, a different parameter name on every surface. Getting it wrong
returns "Invalid parameter", not a silently ignored filter:

| Endpoint | Filter parameter |
|----------|------------------|
| `facebook/posts` | `is_surface_verified` |
| `facebook/profiles`, `instagram/accounts` | `is_verified` |
| `facebook/channels`, `instagram/channels` | `is_admin_verified` |
| `whatsapp/channels` | `is_channel_verified` |

Since 2025-11-10, "verified" includes **paid Meta Verified subscriptions**, not
just legacy badges — so these filters now admit accounts that a pre-2025 study
design would have treated as unverified.

Note also that `media_type` (singular) is a *response field* on Instagram posts;
`media_types` (plural) was the deprecated *filter*. They are not the same thing,
and only the filter was replaced.

**Enum casing in v6.0 is not uniform. Do not generalise from one parameter to
another** — all three of these were verified separately on 2026-08-21:

| Where | Casing | How verified |
|---|---|---|
| `sort` | **lowercase** — `most_to_least_views` | the 2025-11-10 REST-ful pass lowercased them |
| `mode` | **UPPERCASE** — `"SNAPSHOT"` / `"LIVE"` | `enum` declaration in `client$openapi_spec()`, 5 occurrences |
| `status` (returned) | **UPPERCASE** — `COMPLETE` | `get_status()` on four live jobs |

Note the trap that makes guessing unsafe: `mode`'s own `description` in the spec
reads "live mode or snapshot mode" in lowercase while its `enum` says
`["LIVE", "SNAPSHOT"]`. **Prose casing in this spec does not predict enum
casing.** `status` has no `enum` in the spec at all — only prose reading "in
progress, completed, failed, etc." — so its uppercase value could only ever have
been established by running a job, which is what settled it.

## The `since` / `until` window is not a clean UTC day

**[verified 2026-08-21]** Requesting `since = "2026-08-20", until = "2026-08-21"`
against a producer list returned posts with `creation_time` from
**2026-08-20 00:14:45 UTC through 2026-08-21 00:59:52 UTC** — 18 of 2,872 rows
fell on the 21st.

So `until` is **not** exclusive at UTC midnight; it includes at least part of the
named date. What the boundary actually is remains **[open]**: only the first hour
of the 21st appeared, not the whole day, while the window opened before 01:00 on
the 20th. That is consistent with an offset of about an hour from UTC, but a
single observation cannot distinguish that from other explanations and this file
does not assert one.

`creation_time` itself is documented UTC (`field_reference.md`).

**What to do about it.** Do not rely on the boundary. Request one day wider than
you need and filter client-side on `creation_time`:

```r
# want: posts created on 2026-08-20 UTC
res <- ...   # query with since = "2026-08-20", until = "2026-08-21"
ct   <- as.POSIXct(gsub("T", " ", sub("(\\+|Z).*$", "", res$creation_time)), tz = "UTC")
res  <- res[which(as.Date(ct) == as.Date("2026-08-20")), , drop = FALSE]
```

This is correct under any boundary semantics, and comparing the returned range
against the requested one is how the anomaly above was found in the first place.

## Async-Only Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `mode` | string | `"SNAPSHOT"` (recommended) or `"LIVE"` |
| `name` | string | Query name for identification |
| `description` | string | Purpose, methodology, IRB info |

## Query Syntax (`q`)

### Boolean Operators

Combine terms with `AND`, `OR`, `NOT`, and parentheses:

```r
# AND - both terms required
params = list("q" = "climate AND policy")

# OR - either term
params = list("q" = "climate OR environment")

# NOT - exclude term
params = list("q" = "vaccine NOT covid")

# Complex combinations with parentheses
params = list("q" = "(climate OR environment) AND (policy OR legislation)")
```

### No Double-Quoted Phrases (subcode 3790184)

Unlike the Content Library UI, the API **rejects** double-quoted phrase searches:

```json
{"title":"Invalid Keyword Search",
 "detail":"Searching with phrases using double quotes is not supported. Please search without double quotes.",
 "error_subcode":3790184,"status":400}
```

```r
# ✗ Rejected by the API (works only in the UI)
params = list("q" = '"climate change"')

# ✓ Distinctive single token
params = list("q" = "climate")

# ✓ Tokens joined with OR
params = list("q" = "climate OR warming")

# ✓ Narrow with AND instead of a phrase
params = list("q" = "climate AND policy")
```

`OR` does not reproduce a phrase — it matches posts containing *either* word, so
it broadens the corpus rather than matching the bigram. Prefer a distinctive
single token where one exists (`Meloni` rather than `"Giorgia Meloni"`, `M5S`
rather than `"Movimento 5 Stelle"`), and use `AND` when both words must appear.

Note that `q = "climate change"` — an R string holding two space-separated words
— is fine: no double-quote character reaches the API. What 3790184 rejects is a
query **value** containing `"` characters, i.e. `q = '"climate change"'`.

## Producer Lists

Read a list with `lists/producers/{list_id}`, then pass its IDs as the
platform's ID parameter — `surface_ids` for Facebook, `account_ids` for
Instagram:

```r
list_data <- mcl_fromJSON(client$get(path = paste0("lists/producers/", list_id))$text)
ids       <- list_data$producers$id            # character, via mcl_fromJSON()
platform  <- tolower(list_data$platform)
id_param  <- if (platform == "instagram") "account_ids" else "surface_ids"

params <- list("since" = "2024-01-01", "mode" = "SNAPSHOT",
               "name" = "Producer List Query",
               "description" = "Posts from tracked accounts")
params[[id_param]] <- as.list(ids)   # array, not a comma-joined string

response <- client$post(path = paste0(platform, "/posts/job"), params = params)
```

`references/producer_lists.md` owns this topic: list creation, response shape,
batching, cross-platform matching, and the `account_ids` vs `post_ids`
distinction.

## Other Surfaces

Channels (Facebook, Instagram, WhatsApp), Marketplace listings, fundraisers and
donations take a different parameter set — member/follower thresholds, category
filters, price bounds. See `references/surfaces.md`.

## Comments Queries

Comments require `parent_ids` (post IDs):

```r
response <- client$post(
    path = "facebook/comments/job",
    params = list(
        "parent_ids" = as.list(post_ids),   # array, even for one ID
        "mode" = "SNAPSHOT",
        "name" = "Comments on Target Posts",
        "description" = "Comments for sentiment analysis"
    )
)
```

## Estimate Response

```r
estimate <- mcl_fromJSON(client$get(
    path = "facebook/posts/estimate",
    params = list("q" = "election", "since" = "2024-01-01", "until" = "2024-12-31")
)$text)

# Key fields:
# estimate$estimated_results - Approximate count
# estimate$expected_complete - TRUE if <100k (will get all results)
```

## Field expansion: the `fields` parameter uses BRACE syntax, not dots

**[verified 2026-08-22]** Source:
[Field expansion](https://developers.facebook.com/docs/content-library-and-api/appendix/field-expansion).

Nested sub-fields are requested with **curly braces**:

```r
# CORRECT — returns id, statistics.like_count, statistics.haha_count
client$get(path = "facebook/posts/preview",
           params = list("q" = "cybercrime",
                         "fields" = "id,statistics{like_count,haha_count}"))
```

**The dots in the data dictionary are naming, not request syntax.** The dictionary writes
`statistics.like_count`; the *request* is `statistics{like_count}`; the *response* comes back
flattened to `statistics.like_count` again. Requesting `"statistics.like_count"` does not work.

Defaults: naming a parent without braces returns that entity's default expanded fields; omitting
`fields` entirely returns default expanded fields on default parent fields.

### `fields` drops unknown names SILENTLY — always use a positive control

An unrecognised field name is not an error. The call succeeds and the column is simply absent,
which is **indistinguishable from the field existing but being empty**. This has produced wrong
conclusions twice.

**So when testing whether a field exists, include a field you know works in the same request**
— `statistics{like_count}` is a good control. If the control comes back and the field under test
does not, the field genuinely is not served. Without a control you cannot separate "not
available" from "I typed it wrong" or "wrong syntax".

Worked example of the discipline, run on Facebook posts (group and page surfaces):

| Requested | Returned |
|---|---|
| `id,statistics{like_count,haha_count}` | `id, statistics.like_count, statistics.haha_count` — **control passes** |
| `id,multimedia{type,url,duration,user_tags}` | `id, multimedia` — parent only; `url`/`user_tags` absent |
| `id,link_attachment_fields{link,name,caption,description}` | `id` — **field not served** |
| `id,match_type` | `id` — **field not served** |

Conclusion, on sound evidence: `link_attachment_fields` and `match_type` are **not available**
in the Content Library API; they belong to the Third-Party Cleanroom schema (see
`field_reference.md` § "The data dictionary is segmented by product").

## Integer Parameters (Critical!)

Always use `L` suffix for integers:

```r
# ✓ Correct
params = list("limit" = 100L, "offset" = 0L)

# ✗ Wrong - will cause type errors
params = list("limit" = 100, "offset" = 0)
```

## ID Parameters Are Always Character (Critical!)

`L` applies to counts and limits — **never to IDs**. IDs are 15–19 digits, far
beyond `.Machine$integer.max`, and a bare numeric literal becomes a double that
is sent in scientific notation → "Invalid Meta Content Library ID" (subcode
3790088).

```r
# ✓ Correct - array of quoted strings
params = list("surface_ids" = list("963780196442228", "252084123456789"), "limit" = 100L)
params[[id_param]] <- as.list(ids)   # ids came from mcl_fromJSON() → character

# ✗ Wrong - numeric IDs
params = list("surface_ids" = 963780196442228)          # sent as 9.6378e+14
params = list("surface_ids" = as.list(as.numeric(ids))) # each sent as 9.6378e+14

# ✗ Wrong - scalar instead of array → "Invalid parameter"
params = list("surface_ids" = ids[1])   # length-1 vector → Python string

# Rescue an ID that arrived as numeric from elsewhere (CSV, spreadsheet, reticulate)
ids <- sprintf("%.0f", ids)     # NOT as.character(), which yields "1.784e+16"
```

## Finding MCL IDs (Never Use URL IDs)

The numeric ID in a Facebook/Instagram **URL** is not a valid Content Library ID
— MCL assigns its own (privacy by design). Passing a URL ID is rejected with
`error_subcode 3790088` ("Invalid Meta Content Library ID"). Look the entity up
by name via the matching preview endpoint and use the `id` it returns.

**See SKILL.md § "Finding Surface IDs"** for the per-entity lookup table and the
full pattern.

## ID Parameter Batch Limits

`post_ids` accepts at most **250 IDs per call**. Chunk longer lists — and chunk
`surface_ids` at ≤ 250 as well, to stay on the safe side:

```r
chunks <- split(ids, ceiling(seq_along(ids) / 250L))
for (chunk in chunks) {
  params <- list("limit" = 100L)
  params[["post_ids"]] <- as.list(chunk)
  # ...
}
```

`references/producer_lists.md` batches at 50 for producer-list queries, which is
well inside this limit.

## Never Pass an Empty `params`

```r
# ✗ Wrong - reticulate converts list() to a Python list [], and the client
#   calls .items() on it → 'list' object has no attribute 'items'
client$get(path = "budgets", params = list())

# ✓ Correct - omit params entirely, or pass a named list
client$get(path = "budgets")
```

## Platform-Specific ID Parameters

| Platform | Endpoint | ID Parameter | Notes |
|----------|----------|--------------|-------|
| Facebook | `/facebook/posts/preview` | `surface_ids` | Pages, groups, profiles |
| Facebook | `/facebook/comments/preview` | `parent_ids` | Post IDs as parameter |
| Instagram | `/instagram/posts/preview` | `account_ids` | Posts **by** these accounts |
| Instagram | `/instagram/posts/preview` | `post_ids` | These **specific posts**, by ID |
| Instagram | `/instagram/accounts/preview` | `account_ids` | Account lookup |
| Instagram | Post comments | N/A | Use nested URL: `/instagram/posts/{id}/comments/preview` |

**Common Error:** Using `surface_ids` for Instagram returns "Missing required
parameters. Input at least one parameter [q, post_ids, account_ids]".
`surface_ids` is Facebook-only. See `references/producer_lists.md` §
"`account_ids` vs `post_ids` (Instagram)" for which of the two you want.

## Producer List Endpoint

Use `lists/producers/{list_id}` — `producer-lists/{list_id}` returns 404, and
the response carries a `$producers` data.frame (id, name, type), not a `$ids`
vector. Details: `references/producer_lists.md`.

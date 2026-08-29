# Query Parameters Reference

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

## Common Parameters (All Endpoints)

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Search query — keywords and boolean operators. **No double-quoted phrases** (subcode 3790184) |
| `since` | string **or integer** | Start date `YYYY-MM-DD` **or a UNIX timestamp**. **Not a clean UTC-midnight boundary — see below** |
| `until` | string **or integer** | End date `YYYY-MM-DD` **or a UNIX timestamp**. **Inclusive of at least part of the named date — see below** |
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
| `link` | string | Filter on a URL in the post. **Do NOT pair with `q`** — see § The `link` parameter below |
| `surface_types` | list | `page`, `profile`, `group`, `event` |
| `surface_countries` | list | ISO 3166-1 alpha-2, uppercase |
| `views_bucket_start` / `views_bucket_end` | integer | View-count bounds |
| `post_ids` | list | Specific posts, max 250 |
| `fields` | list | Field selection |

### The `link` parameter — **[verified 2026-08-29]**

Meta's guide is wrong in both directions here. Measured on
`facebook/posts/preview`, US and Italian publishers, 33 URLs.

**Use it without `q`.** The guide says `link` "cannot be used without the q
parameter". It can, and it must: `link` alone returned **90** posts where
`q="trump"` + the same `link` returned **16** (a verified subset). `q` only
narrows.

```r
# right
client$get(path = "facebook/posts/preview",
           params = list(link = URL, since = S, until = U, limit = 100L, fields = F))
```

**⚠ With `q` present, an unmatched `link` is silently ignored.** `q` + a URL
nobody shared returned the *identical* 100 rows as `q` alone (Jaccard 1.0), HTTP
200, no warning — while that URL **alone** correctly returned 0. `estimate`
reproduces it: **3,000,000** for the mistyped link versus **20** for the real
one. A typo'd URL therefore reports millions of rows instead of zero. Dropping
`q` removes the failure mode entirely.

**It matches a content entity, not a string.** Querying one URL returns every
form Meta has seen for the same content — including **shortener → destination**
(`nyti.ms/3TP0f5I` returned 100 posts, only 5 still in shortener form, 49 in the
`nytimes.com/...` form) and **reshares** (62 of 90 baseline hits were
`content_type = reshare` with no `link_attachment` at all).

**But it is an index lookup, not parameter stripping.** A *fabricated* parameter
form matches nothing — 0 posts in **33 of 33** tests — while a really-posted one
matches everything. Meta indexes URL strings it has seen and groups them by
content; only host case, `www.`, and percent-encoding are canonicalised
syntactically.

| query form | matches? |
|---|---|
| `www.` added or removed | ✅ |
| host upper-cased | ✅ |
| path char percent-encoded | ✅ |
| a different **really-posted** parameter form | ✅ |
| `http://` for `https://` | ❌ scheme is significant |
| no scheme at all | ❌ |
| trailing slash added | ❌ |
| `#fragment` appended | ❌ |
| `m.` subdomain | ❌ |
| path segment truncated | ❌ no prefix matching |
| **a fabricated `?utm_…&fbclid=…`** | ❌ |
| bare domain | matches the **homepage only** — a different set |

**So query the parameter-free base URL — but only strip *tracking* parameters.**
It is normally a key Meta has seen, and one query then gathers every variant.

> **⚠ Never strip an *identity* parameter.** `utm_*`, `fbclid`, `smid` and `ref`
> are tracking. `?p=`, `?id=`, `?page_id=` and `?story_fbid=` are **identity**.
> `voxnews.org` (NewsGuard 7.5) publishes articles as
> `https://voxnews.org/?p=482077` — the path is `/` and the article *is* the
> query string. Stripping it turns every article into the **homepage**, a
> different content entity. Same trap, milder, on `abcnews.com/…/story?id=…`,
> where dropping `?id=` returned 0 while keeping it returned 90.
> **Rule of thumb: if the path carries no article slug, the query string is the
> URL — keep it whole.** Il Fatto Quotidiano publishes through
Echobox, stamping a **per-share unique** `utm_id`: one article was shared **43
times under 30 distinct URL strings**, the bare canonical form appearing among
them **not once**. The base-URL query found all 43.

**⚠ `n = 0` is ambiguous** — "this exact string is not a known key", not "nobody
shared it". False-zero rate on URLs derived by *stripping* parameters off an
observed URL: **1 of 9** mainstream, **1 of 18** problematic (NewsGuard < 60),
**0 of 5** on publisher-canonical URLs. Prefer canonical URLs from the
publisher; never report a bare 0 as a count.

**There is no domain-wide link search.** Bare-domain `link` returns homepage
posts only, and `q` cannot reach URLs at all (see § "`q` does not search URLs").

**Recall within attachments is complete — [verified 2026-08-29].** Measured
against the `mcl-links-comments` Stage 2 census (43,285 posts, 16,786 distinct
URLs): 12 URLs sampled, **51 of 51** known census posts recovered, every URL at
recall **1.00**, shorteners included. `link` returned *more* than the census
each time (up to 116 vs 3) because the census saw only its frame's producers
while `link` searches all queryable surfaces. Caveat: this is a consistency
check between two API query paths, not absolute truth — a post the index never
held is invisible to both. Sample was low-frequency URLs (3–8 posts each).

**But the carrier ceiling stands: `link` matches the attachment only.** A URL appearing solely
in post *text* is invisible to it — 4 of 4 such posts were excluded even though
the index demonstrably held the URL (38/15/14/6 other posts carrying it were
returned). `link_attachment` is **never** populated on a non-link
`content_type` (0 of 300 `status`/`photos`/`videos` posts), so text carriers are
a real and separate class. On the `mcl-links-comments` frame they are **15.8%**
of link-bearing posts. Pair `link` with a text-URL regex pass for any count that
claims completeness.

### `q` does not search URLs — **[verified 2026-08-29]**

The Facebook-posts guide recommends, for domain-level search, "use the q
parameter where q=url … posts from cnn.com/entertainment would be included in a
search for cnn.com". **This does not work.**

| probe | result |
|---|---|
| `q = "abcnews.com/Politics"` (the guide's own shape) | **0** |
| `q = "abcnews.co"` (partial token) | **0** — no substring matching |
| `q = "nyti.ms"` | 100 posts, of which **0** link to `nyti.ms` |

`q` searches post text. Of 100 rows for `q="abcnews.com"`, **none** carried the
domain in the attachment URL without also carrying it in the text. Treat the
guide's `q=url` recipe as incorrect.

### The v4.0 deprecations are scoped to `facebook/posts` — **[corrected 2026-08-25]**

On **`facebook/posts`**, `profile_ids` / `page_ids` / `group_ids` / `event_ids`
were replaced by `surface_ids` in v4.0, and `admin_countries` / `owner_types`
became `surface_countries` / `surface_types`. Post code written against the older
names predates two deprecations and will not run.

**Those same names are alive and current on the producer-search endpoints.** An
earlier version of this file stated the deprecation without qualification, which
reads as "never use `page_ids`" — wrong, and it leaves you with no way to
restrict a Page search to known Pages:

| Endpoint | ID parameter | Max |
|---|---|---|
| `facebook/pages/preview` | `page_ids` | 250 |
| `facebook/groups/preview` | `group_ids` | 250 |
| `facebook/profiles/preview` | `profile_ids` | 250 |
| `facebook/events/preview` | `event_ids` | 250 |
| `instagram/accounts/preview` | `account_ids` | 250 |
| `facebook/posts/preview` | `surface_ids` (**not** the four above) | 250 |
| `instagram/posts/preview` | `account_ids` / `post_ids` | 250 |

`admin_countries` likewise survives on `facebook/pages` and `facebook/profiles`
(it filters on the admin's country); it is only on `facebook/posts` that the
name is `surface_countries`. `website` is a further filter on both of those two
endpoints, matching the URL in the About section.

### The Five Spellings of "verified"

Same concept, a different parameter name on every surface. Getting it wrong
returns "Invalid parameter", not a silently ignored filter. **Two rows were added
2026-08-25 from Meta's guides** — the Instagram *posts* spelling in particular is
not the one the Instagram *accounts* endpoint uses:

| Endpoint | Filter parameter |
|----------|------------------|
| `facebook/posts` | `is_surface_verified` |
| `instagram/posts` | `is_account_verified` |
| `facebook/pages`, `facebook/profiles`, `instagram/accounts` | `is_verified` |
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

### Reproduced on a 7-day window — **[verified 2026-08-24]**

A second run, over seven days rather than one, reproduces the same shape and shows what
the narrow window would have cost:

```
requested:   since = 2026-08-17, until = 2026-08-24
returned:    2026-08-17 00:01:02  ->  2026-08-24 00:25:33  UTC

2026-08-17 2026-08-18 2026-08-19 2026-08-20 2026-08-21 2026-08-22 2026-08-23  2026-08-24
      1431        830       1194       1158       1137       1100       1085          19
```

- **The until-day contributes a sliver, not a day.** 19 rows, ending **00:25:33**. The
  2026-08-21 observation saw the sliver end at 00:59:52. Both are consistent with a
  boundary shortly after UTC midnight on the until-day; **neither pins it**, and the size
  of the sliver just reflects how many posts happen to exist in those first minutes. The
  exact boundary stays **[open]**.
- **The since-day opens at or before 00:01:02**, consistent with 00:14:45 on 2026-08-20.
  Nothing yet shows the window opening meaningfully *after* midnight, so widening `since`
  is optional; widening `until` is not.
- **What the narrow window would have cost:** requesting `until = 2026-08-23` would have
  returned that day's first ~25 minutes only — losing essentially all **1,085** posts of
  the last target day, one seventh of the corpus, silently. This is the concrete reason
  the mitigation above is mandatory rather than defensive.

### The experiment that would close this — **[not yet run]**

`since` and `until` are documented as accepting **either `YYYY-MM-DD` or a UNIX
timestamp**, on every endpoint that has them. That is a lever the two runs above
did not have: a timestamp names an exact second, so one query pins the boundary
that two date-granular observations could not.

```r
# 2026-08-24 00:00:00 UTC, exactly
until_epoch <- as.integer(as.POSIXct("2026-08-24 00:00:00", tz = "UTC"))
params <- list("since" = "2026-08-17", "until" = until_epoch, ...)
```

If the returned maximum `creation_time` still runs past the requested instant,
the offset is server-side and the date form is not the cause. Procedure:
`docs/TESTING_PROCEDURE.md` § "Pin the `until` boundary with an epoch second".

Until that is run, **the widen-and-filter mitigation above stays the operative
advice** — it is correct under every boundary semantics, and a timestamp that
turns out to behave like a date would silently reintroduce the loss.

## Sort Defaults Differ by Endpoint — and the Default Is Rarely Chronological

> Transcribed from the endpoint guides, 2026-08-25. Casing is lowercase
> throughout (see the enum-casing table above).

| Endpoint | `sort` values | Default |
|---|---|---|
| `facebook/posts`, `instagram/posts` | `most_to_least_views`, `newest_to_oldest`, `oldest_to_newest` | `most_to_least_views` |
| `facebook/pages` | `most_to_least_follower_count`, `newest_to_oldest` | `most_to_least_follower_count` |
| `facebook/groups` | `most_to_least_member_count`, `newest_to_oldest` | `most_to_least_member_count` |
| `facebook/profiles` | `most_to_least_followers_count`, `newest_to_oldest` | `most_to_least_followers_count` |
| `facebook/events` | `most_to_least_people_going_count`, `newest_to_oldest` | `most_to_least_people_going_count` |
| `facebook/comments`, `instagram/comments` | `newest_to_oldest`, `oldest_to_newest`, `none` | `newest_to_oldest` |
| `facebook/channels`, `instagram/channels` | `most_to_least_member_count`, `newest_to_oldest`, `oldest_to_newest` | `most_to_least_member_count` |
| `whatsapp/channels` | `most_to_least_follower_count`, `most_to_least_channel_updates`, `newest_to_oldest`, `oldest_to_newest` | `most_to_least_follower_count` |

Two traps:

- **The docs spell the Pages value `most_to_least_follower_count` and the
  Profiles value `most_to_least_followers_count`** — singular on one endpoint,
  plural on the other. One of the two may be a documentation typo; treat the
  pair as unverified and read the enum from `client$openapi_spec()` before
  relying on either. An unrecognised `sort` is an "Invalid parameter" error, so
  this fails loudly rather than silently.
- **`sort` is documented as synchronous-only on `instagram/accounts`,
  `facebook/events` and the comments endpoints.** The bulk-comments guide states
  outright that *"no sorting is applied in the response"* of an async comments
  job — so an async pull is unordered and must be sorted client-side.

Because a truncated result set is the *top* of the sort order, the default
matters: a `facebook/posts` query cut off at 100,000 keeps the most-viewed
posts, not the most recent ones.

## Instagram Post Filters

> Transcribed from the Instagram posts guide, 2026-08-25.

Mostly parallel to the Facebook post filters, with three differences that break
copy-pasted code:

| Parameter | Type | Description |
|-----------|------|-------------|
| `account_ids` | list | Instagram account IDs, max 250 — **not** `surface_ids` |
| `account_types` | list | `creator`, `business`, `personal` — the Instagram analogue of `surface_types` |
| `is_account_verified` | boolean | **not** `is_surface_verified` |
| `search_scope` | enum | `post_text_only` (default), `post_text_and_image_text` |
| `content_types` | list | `albums`, `photos`, `stories`, `videos` |
| `sort` | enum | `most_to_least_views` (default), `newest_to_oldest`, `oldest_to_newest` |
| `is_branded_content` | boolean | Include or exclude branded content |
| `views_bucket_start` / `views_bucket_end` | integer | View-count bounds |
| `post_ids` | list | Specific posts, max 250 |
| `lang`, `since`, `until`, `fields` | | as for Facebook posts |

There is no `link` filter and no `surface_countries` equivalent on Instagram.

> **⚠ Instagram accepts `link` and silently ignores it — [verified 2026-08-29].**
> `instagram/posts/preview` with `q` alone and with `q` + `link` returned
> **identical** 100-row sets. No error, no warning. An Instagram "link search"
> is an unfiltered keyword search that looks like it worked.

## Facebook Events Has Four Date Parameters

`facebook/events/preview` distinguishes when the event *record* falls from when
the event itself *runs*:

| Parameter | Filters on |
|---|---|
| `since` / `until` | events **scheduled** on or after / before the date |
| `event_since` / `event_until` | events that **started** on or after / before the date |

All four accept `YYYY-MM-DD` or a UNIX timestamp. Using only `since`/`until` out
of habit answers a different question from the one most event studies ask.

## Async-Only Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `mode` | string | `"SNAPSHOT"` (recommended) or `"LIVE"` |
| `name` | string | Query name for identification |
| `description` | string | Purpose, methodology, IRB info |

## Query Syntax (`q`)

### Operators are SYMBOLS, not words — **[corrected 2026-08-25 from Meta's docs]**

Source: [Advanced search guidelines](https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/advanced-search).

| Operator | Written as | Examples, verbatim from the docs |
|---|---|---|
| AND | `&` **or a blank space** | `cat&dog&allergy` · `cat dog allergy` · `cat&dog allergy` |
| OR | `\|` | `cat \| dog` · `cat\|dog` · `cat \|dog` |
| NOT | `-` | `dog -puppy` · `dog-puppy` · `dog - puppy` |

Whitespace around an operator is optional and does not change the meaning.

**Precedence: NOT first, then AND, then OR** — left to right among clauses of
equal precedence. Parentheses regroup:

| Query | Means |
|---|---|
| `lemon lime \| grapefruit` | (lemon AND lime) OR grapefruit |
| `fuyu \| persimmon - astringent` | fuyu OR (persimmon NOT astringent) |
| `(fuyu \| persimmon) - astringent` | (fuyu OR persimmon) NOT astringent |
| `((action movie) \| (newman \| redford)) - outlaw` | nesting is allowed |

Constraints, all documented:

- **Single-word keywords only.** Phrases are not supported (see below), and
  **wildcards are not supported**.
- **The operator characters cannot themselves be keywords** — ampersand, pipe,
  hyphen, blank space and parentheses.
- **Right-to-left languages** are parsed right to left, keeping the same
  NOT → AND → OR precedence, and **grouping with parentheses is not supported**
  for them.

### The word forms `AND` / `OR` / `NOT` are not documented operators

Earlier versions of this file taught `"climate AND policy"`, `"climate OR
environment"` and `"vaccine NOT covid"`. **Meta's documentation lists only the
symbols.** No live test has yet been run, so this file does not assert that the
word forms fail — but it can say which way the error runs, and that is enough to
stop using them:

- If `OR` is treated as an **ordinary keyword**, `climate OR environment`
  tokenises to `climate & or & environment` — every match must contain all
  three words. That is dramatically **narrower** than the union it looks like.
- If `OR` is dropped as a **stopword**, the query becomes `climate &
  environment` — the intersection. Also **narrower**.

Under either reading the result is narrower than the OR that was intended, and
nothing errors. Anyone who copied `"climate OR environment"` out of an earlier
version of this file has been running a different query than they thought.

**Use the symbols.** They are what the documentation specifies:

```r
# ✓ union — either word
params = list("q" = "climate | environment")

# ✓ intersection — both words (a blank space IS the AND operator)
params = list("q" = "climate policy")
params = list("q" = "climate&policy")     # identical

# ✓ exclusion
params = list("q" = "vaccine -covid")

# ✓ grouping
params = list("q" = "(climate | environment) (policy | legislation)")
```

To settle the word forms for good, compare three `estimate` calls — `estimate`
is free and sync searches run 60/minute, so this costs nothing but a minute:
see `docs/TESTING_PROCEDURE.md` § "Which `q` operators does the API honour?".

### No Double-Quoted Phrases (subcode 3790184)

Unlike the Content Library UI, the API **rejects** double-quoted phrase searches:

```json
{"title":"Invalid Keyword Search",
 "detail":"Searching with phrases using double quotes is not supported. Please search without double quotes.",
 "error_subcode":3790184,"status":400}
```

Meta's search guide gives the underlying reason: matching is performed
independently word by word, *"meaning that searching by phrase is not supported
(queries 'All for one' and 'One for all' are equivalent)"*. So the rejection is
not a parser quirk to work around — **there is no phrase search to reach**.

```r
# ✗ Rejected by the API (works only in the UI)
params = list("q" = '"climate change"')

# ✓ Distinctive single token
params = list("q" = "climate")

# ✓ Tokens joined with OR
params = list("q" = "climate | warming")

# ✓ Narrow with AND instead of a phrase
params = list("q" = "climate policy")
```

`|` does not reproduce a phrase — it matches posts containing *either* word, so
it broadens the corpus rather than matching the bigram. Prefer a distinctive
single token where one exists (`Meloni` rather than `"Giorgia Meloni"`, `M5S`
rather than `"Movimento 5 Stelle"`), and use a space (AND) when both words must
appear — remembering that word order and adjacency are not tested either way.

Note that `q = "climate change"` — an R string holding two space-separated words
— is fine: no double-quote character reaches the API, and the space is simply
the AND operator. What 3790184 rejects is a query **value** containing `"`
characters, i.e. `q = '"climate change"'`.

### Tokenization — exact, with no stemming

From Meta's [Search guide](https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/search-guide):

- Tokens are words separated by spaces or punctuation
  ( `?@$%^*()+=~[{}];:"<>|.` ), with some URL normalisation and locale-specific
  handling for non-English languages.
- **Tokenization is exact — it introduces no word variants.** *"'cats' will not
  be tokenized to 'cat'"*. There is no stemming, lemmatisation or fuzzy
  matching, so plurals and inflections must be enumerated:
  `elezione | elezioni | elettorale`.
- **Direct @mentions are excluded from the index** and are scrubbed from results
  when the mentioned user does not meet eligibility criteria. You cannot find
  posts by searching for the handle they mention.

### What `q` actually searches, per endpoint

`q` is not a free-text search over the whole record — each endpoint declares
which fields it covers:

| Endpoint | `q` searches |
|---|---|
| `facebook/posts`, `instagram/posts` | the post `text` field |
| `facebook/pages` | `name` and `description` |
| `facebook/groups` | `name` and `description` |
| `facebook/events` | `name` and `description` |
| `facebook/profiles` | `name` and `intro` |
| `instagram/accounts` | `name` and `biography` |
| `facebook/channels`, `instagram/channels` | `name` only |
| `whatsapp/channels` | `name` and `description` |
| `facebook/marketplace-listings` | listing title and description |
| `facebook/fundraisers`, `instagram/fundraisers` | `title` and `description` |

With `search_scope = "post_text_and_image_text"` on posts, text recognised in
images joins the searchable surface — see `field_reference.md` § "`image_text`
is a match_type VALUE".

### How good is the search? — measured by Meta, not by us

Meta publishes a [search quality approach](https://developers.facebook.com/docs/content-library-api/search-quality)
with figures from tests run **2024-12-01 to 2024-12-05** over ~50 test terms:

| Measure | Result |
|---|---|
| Median recall | 99 % across Pages, groups, events, profiles, Instagram accounts and posts |
| Recall, 20th percentile | 97 % (Facebook posts), 96 % (Instagram posts) |
| Median precision | 98–99 % across endpoints |
| Ranked recall (top 1,000 by creation time or views) | 96–99 % median |

Quality was also tested in Arabic, German and Hindi with results comparable to
English, with two named limitations: **German queries cannot process "ß"**, and
**Arabic requires a separate search per diacritical variant**.

Meta's own caveats matter more than the headline numbers: the validation set may
contain ineligible content (which *understates* true recall), indexing is
occasionally imperfect or delayed, and content visible on-platform can be
excluded from the API as privacy rules evolve. A missing post is not
automatically a bug in your query.

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

Comments split by access mode, and the split is not the usual preview/job pair —
**there is no `{platform}/comments/preview`**. Sync reads hang off the parent
post or comment; bulk reads go through `{platform}/comments/job` with
`parent_ids`, with `{platform}/comments/estimate` to size it first. **SKILL.md
§ "Nested Endpoints" owns the path table**; this section owns the parameters.

```r
response <- client$post(
    path = "facebook/comments/job",
    params = list(
        "parent_ids" = as.list(post_ids),   # array, even for one ID; max 250
        "fetch_all" = TRUE,                 # all reply levels, not just top-level
        "mode" = "SNAPSHOT",
        "name" = "Comments on Target Posts",
        "description" = "Comments for sentiment analysis"
    )
)
```

### Bulk-comment parameters

> Transcribed from the [Bulk comments guide](https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/bulk-comments)
> and the Facebook comments guide, 2026-08-25.

| Parameter | Type | Description |
|---|---|---|
| `parent_ids` | list | Post **or comment** IDs, in any mix. **Max 250 per query** |
| `fetch_all` | boolean | `TRUE` returns **every reply level**; `FALSE` (the default) returns **top-level replies only** |
| `fields` | list | Field selection; defaults apply if omitted |
| `sort` | enum | `newest_to_oldest` (default), `oldest_to_newest`, `none` — **synchronous endpoints only** |
| `since` / `until` | string or integer | `YYYY-MM-DD` or UNIX timestamp. Documented as **UTC** for comments |

**`fetch_all = TRUE` collapses the two-pull workaround.** `field_reference.md` §
"Replies Require a Second Pull" documents fetching top-level comments and then
re-querying with the comment IDs that report replies. That still works and is
still the way to fetch replies *selectively* — but a whole thread now comes back
from one job. The default is `FALSE`, so **a comments job written without
`fetch_all` returns top-level comments only**, and nothing says so.

Three further limits:

- Async comment responses are **unordered** — *"no sorting is applied in the
  response"*. Sort client-side.
- The comments **estimate caps at 1,000,000**: a larger corpus reports "1 million
  or more" rather than a number.
- Comments draw on their **own 500,000-record 7-day budget**, separate from the
  query budget (SKILL.md § "Rate Limits & Budget").

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

**"Approximate" is worth a magnitude — [observed 2026-08-25].** A producer-list query
over a 7-day window estimated **700** and the completed job returned **583**: the
estimate ran **~20 % high**. One observation, on one query, so it is not a bound — but
it is enough to say that `estimated_results` is a **sizing** figure, not a count.

Two consequences: do not use it as the denominator of any reported rate (use
`nrow()` of the result), and when an estimate sits just under a cap, treat it as
*near* the cap rather than under it. `expected_complete` is the reliable half — it
was `TRUE` and the job did return everything.

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

### `fields` works on the ASYNC JOB endpoint too — **[verified 2026-08-25]**

Everything above was established against `preview`. It holds unchanged on
**`facebook/posts/job`**, which is the case that costs money to get wrong: a job
submitted without `fields` returns the 24-column default projection, and **`text` is
not in it** (`field_reference.md` § "The default projection"). Discovering that after
the job has completed means paying for a second job at full budget, with no refund.

Verified end to end on a 211-producer list over a 7-day window — the same `fields`
string previewed first, then submitted:

```r
FIELDS <- paste0("id,creation_time,text,lang,surface{id,name,type},",
                 "statistics{views,reaction_count,comment_count,share_count,like_count}")

# 1. FREE positive control -- confirm the projection before spending anything
pv <- mcl_fromJSON(client$get(path = "facebook/posts/preview",
                              params = c(list("limit" = 5L, "fields" = FIELDS), id_params))$text)
stopifnot("text" %in% names(pv$data))          # the field that is NOT default

# 2. the same string on the job
job <- client$post(path = "facebook/posts/job",
                   params = c(list("fields" = FIELDS, "mode" = "LIVE"), id_params))
```

All nine requested fields came back on both calls, and the 583-row job result carried
`text`, `lang`, `surface.{id,name,type}` and the four `statistics.*` columns — brace
expansion, flattening and all.

> **The discipline this implies is cheap and worth making a habit:** `preview` costs no
> budget, so **preview the exact `fields` string before submitting the job that uses it.**
> Because unknown names are dropped *silently* (next section), a typo is otherwise
> invisible until the job is paid for and finished.

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

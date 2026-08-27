# Field Reference by Endpoint

> **Every field typed `string` below that holds an ID** (`id`, `post_owner.id`,
> `owner.id`, `surface.id`, `producer_id`, `post_id`, `parent_comment_id`,
> `shared_post_id`, `host_id`, …) must end up
> as a **character** vector in R. Some endpoints send these as unquoted JSON
> numbers, so `fromJSON()` types them `numeric` — losing digits above 2^53 and
> printing as `9.6378e+14`. Parse with `mcl_fromJSON()` (SKILL.md § "ID Handling").
> Only counts and timestamps are genuinely numeric.

> **Provenance.** Confirmed against live responses: the Instagram account fields
> (v1.2.0), comment `owner.*` and post `post_owner.*` / `surface.*` (v1.7.0), and
> `shared_post_id` on reshares (v1.7.0). The remaining tables are compiled from
> documentation and **not** confirmed against a live response — treat an
> unexpected `NULL` column as the table being wrong, not your query.

## Table of Contents
1. [Facebook Posts](#facebook-posts)
2. [Facebook Pages](#facebook-pages)
3. [Facebook Groups](#facebook-groups)
4. [Facebook Events](#facebook-events)
5. [Facebook Profiles](#facebook-profiles)
6. [Facebook Comments](#facebook-comments)
7. [Instagram Posts](#instagram-posts)
8. [Instagram Accounts](#instagram-accounts)
9. [Instagram Comments](#instagram-comments)
10. [Threads — documented in the Library, absent from the API](#threads--documented-in-the-library-absent-from-the-api)
11. [Data Scope: Whose Posts Are Queryable](#data-scope-whose-posts-are-queryable)
12. [Where the docs and this file disagree](#where-the-docs-and-this-file-disagree)

Channels (Facebook, Instagram, WhatsApp), Marketplace listings, fundraisers and
donations are newer surfaces and live in `references/surfaces.md`, which owns
both their parameters and their fields.

## Facebook Posts

### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique post identifier |
| `creation_time` | datetime | When post was created (UTC) |
| `text` | string | Post body text |
| `lang` | string | Detected language (ISO 639-1) |

### The default projection — what you get without asking

**[verified 2026-08-24]** A `facebook/posts/preview` with no `fields` parameter returns
**exactly these 24 columns**:

```
id, creation_time, modified_time, multimedia, is_branded_content, content_type,
statistics.like_count, statistics.love_count, statistics.wow_count,
statistics.haha_count, statistics.sad_count, statistics.angry_count,
statistics.care_count, statistics.comment_count, statistics.reaction_count,
statistics.views, statistics.views_date_last_refreshed, statistics.share_count,
post_owner.type, post_owner.id, post_owner.name,
surface.type, surface.id, surface.name
```

Two things follow that are easy to get wrong:

- **`text` is NOT in the default projection.** Post bodies must be requested explicitly
  via `fields`. Code that assumes `text` is present will find it missing and can easily
  misread that as an API fault rather than the default. (The incidental upside: post text
  does not leave the API unless something asks for it.)
- **`lang`, `media_type`, `has_media`, `image_text`, `link_url`, `is_reshare`,
  `shared_post_id` and `location.country` are likewise absent by default**, though all are
  documented below as retrievable. This table describes what the API *can* return, not
  what it returns unasked.

### There is no post permalink field — **[verified absent 2026-08-24]**

Nothing in the response carries a link back to the post, and this is now checked rather
than merely unstated: the 24-column projection above has no URL field, and a grep of
`client$openapi_spec()` for `permalink|post_url|content_url|share_url` returned **zero**
matches. `link_url` is the URL *shared in* a post, not a link *to* it.

To point a reader at a post, construct a **Content Library GUI** URL:

```
https://www.facebook.com/transparency-tools/content-library/dataset/{DATASET_ID}/facebook/entity/{POST_ID}
```

**[verified 2026-08-24]**, with two controls, because "the page rendered" proves nothing
against an SPA that returns its own chrome for any route:

- A **bogus id** is rejected — a not-found signal appears, and the rendered text collapses
  (7,828 → 386 characters). So the route validates the id.
- **Two different posts by the same producer render differently** (fingerprints `c7e8fcb2`
  at 508 chars vs `ab2f8b79` at 570). So `entity` resolves the **post**, not its owner —
  which was the live risk, since a `/post/{id}/` URL redirects to `/entity/{id}` and
  appends `time_preset=ALL_TIME&sort=most-recent`, parameters that read like a *listing*
  view of a producer.

**The `DATASET_ID` is account-scoped** (`1119037145491882` for the account tested) and is
visible in the GUI's own navigation links. Whether such a link resolves for a reader with
different dataset permissions is **[untested]** — do not present these as public URLs.

### Producer Fields

These are the **flattened** names returned by `mcl_fromJSON()` (which parses with
`flatten = TRUE`). The posting account is under `post_owner.*`; the surface the
post was made to is under `surface.*` — for a post to a Page they usually agree,
but for a post to a group they differ.

| Field | Type | Description |
|-------|------|-------------|
| `post_owner.id` | string | ID of the posting account |
| `post_owner.username` | string | Handle (use this to build a producer URL) |
| `post_owner.name` | string | Display name |
| `post_owner.type` | string | page, group, event, profile |
| `surface.id` | string | ID of the surface the post was made to |
| `surface.name` | string | Surface display name |
| `surface.type` | string | page, group, event, profile |

### Reshares

| Field | Type | Description |
|-------|------|-------------|
| `shared_post_id` | string | ID of the **original** post, on a reshare |

A reshare carries no field for the original *account* — only `shared_post_id`.
To attribute it, fetch the original post by `post_ids` and read its
`post_owner.*`:

```r
resp <- client$get(
  path   = "facebook/posts/preview",
  params = list("post_ids" = as.list(shared_ids), "limit" = 100L)   # array, max 250
)
originals <- safe_get_data(resp$text)
originals[, c("id", "post_owner.id", "post_owner.username")]
```

Resolve **defensively**: some reshared originals are out of scope for the
Content Library, their IDs are invalid, and a single bad ID rejects the *whole*
`post_ids` call with subcode 3790088. Bisect the batch (or drop to one ID at a
time) and skip the offenders rather than losing the batch:

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

### Engagement Statistics

**[verified 2026-08-24 against a live `facebook/posts/preview` projection]** — the names
are `*_count`. Earlier versions of this table listed bare plurals
(`statistics.reactions`, `.comments`, `.shares`); **those names are not returned by the
API** and code written against them silently produces nothing, because the usual way to
select columns is `intersect()`, which drops what it cannot match without complaint.

| Field | Type | Description |
|-------|------|-------------|
| `statistics.reaction_count` | integer | Total reactions |
| `statistics.comment_count` | integer | Comment count |
| `statistics.share_count` | integer | Share count |
| `statistics.views` | integer | View count (where available — see below) |
| `statistics.views_date_last_refreshed` | — | When the view count was last refreshed |

Reactions are also broken out per emoji, which the bare `reactions` name obscured
entirely:

| Field | Field | Field |
|---|---|---|
| `statistics.like_count` | `statistics.love_count` | `statistics.wow_count` |
| `statistics.haha_count` | `statistics.sad_count` | `statistics.angry_count` |
| `statistics.care_count` | | |

**`statistics.views_date_last_refreshed` matters for any views-based ranking**: it dates
the number you are sorting on, so two posts' view counts are not necessarily current as
of the same moment. Its exact type and semantics are **[untested]** — it was observed in
the projection, not exercised.

#### How much of a corpus carries `views` is not a property of the API

"Where available" means video/reel. What fraction of a corpus that is depends entirely on
the corpus, and two runs bracket a range wide enough to change what a ranking means:
**5.5 %** on 2,854 posts from 830 ordinary profiles (2026-08-21), **88.8 %** on 7,935
posts from 130 pages + 21 profiles (2026-08-24). Measure it per query rather than
carrying either figure forward.

**Distinguish absent from zero.** Both runs returned hundreds of `NA` and **exactly zero**
real zeros (2,697/0 and 890/0). The field is *absent* on non-video posts, not
measured-as-zero, so coercing `NA` to `0` before ranking invents a result.

### Media Fields
| Field | Type | Description |
|-------|------|-------------|
| `media_type` | string | photo, video, link, text |
| `has_media` | boolean | Contains media attachment |
| `image_text` | string | OCR text from images (last 180 days) |

### Link Fields
| Field | Type | Description |
|-------|------|-------------|
| `link_url` | string | Shared link URL |
| `link_title` | string | Link preview title |
| `link_description` | string | Link preview description |

### Context Fields
| Field | Type | Description |
|-------|------|-------------|
| `is_reshare` | boolean | Is this a shared post |
| `location.country` | string | Country code if geotagged |

### `activities` — what the spec's mystery array holds

**[added 2026-08-25 from Meta's data dictionary]** The `FacebookPost` schema
lists an `activities` array (see § "The complete Facebook Post schema") but the
spec says nothing about its contents. The dictionary does:

| Field | Description |
|-------|-------------|
| `activities.type` | Type of activity in the post. Documented types: **`streaming`**, **`playing`** |
| `activities.name` | Name of the activity — e.g. the title of what is being streamed or played |

This is the gaming-video metadata added in v5.0. It is the only route to "what
game / what stream" on a Facebook post, and it is absent from the default
projection — request it explicitly.

Also documented and easy to miss: **`is_verified` on a post** (whether the post
came from a verified Facebook surface) and **`branded_content_page_id`** (the
Page associated with a branded-content post). Neither is in the 24-column
default projection.

## Facebook Pages

**[corrected 2026-08-25 from Meta's data dictionary]** Two of the names this
table used to carry are not the ones the API uses: the verification field is
**`verification_status`**, not a boolean `verified`, and categories arrive as
**`page_categories`**, a list of up to three, not a scalar `category`. `about`
and `description` are *different* fields — the short and the long paragraph of
the About section respectively — not synonyms.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique Page ID |
| `name` | string | Page name |
| `username` | string | Page username, if available |
| `about` | string | The **short** paragraph from the About section |
| `description` | string | The **long** paragraph from the About section |
| `website` | string | External URL from the About section |
| `verification_status` | string | Verification status of the Page |
| `page_categories` | list | Up to **three** categories, chosen by the Page manager |
| `follower_count` | integer | Number of followers |
| `creation_date` | date | When the Page was created |

`like_count`, `location.city` and `location.country` appeared in earlier versions
of this table and are **not** in Meta's Page dictionary. They may still be served
— read `client$openapi_spec()` rather than assuming either way.

## Facebook Groups

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique Group ID |
| `name` | string | Group name |
| `description` | string | Group description |
| `member_count` | integer | Number of members |
| `creation_date` | date | When the Group was created |

`privacy` and `admin_count` were listed here previously and do **not** appear in
Meta's group dictionary — treat them as unconfirmed. Only public groups indexed
in the Content Library are returned at all, so a `privacy` column would have a
single value even if it exists.

## Facebook Events

**[corrected 2026-08-25]** The start and end times are **`event_start_time`** and
**`event_end_time`** — this table previously said `start_time` / `end_time`.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique Event ID |
| `name` | string | Event name |
| `description` | string | Event description |
| `event_start_time` | datetime | Event start time |
| `event_end_time` | datetime | Event end time |
| `going_count` | integer | Number of Going responses |
| `interested_count` | integer | Number of Interested responses |

`location.*` and `host_id` were listed here previously and are not in Meta's
event dictionary — unconfirmed.

## Facebook Profiles

New in this file as of 2026-08-25 — profiles had a lookup endpoint in SKILL.md
but no field table.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique profile ID |
| `name` | string | Profile name, if the user meets eligibility criteria |
| `username` | string | Profile username, if available and eligible |
| `follower_count` | integer | Number of followers |
| `verification_status` | string | **`not_verified`** or **`blue_verified`** |
| `creation_date` | date | When the profile was created |

`verification_status` is an enum, not a boolean — `if (profile$verification_status)`
is a type error waiting to happen, and the string `"not_verified"` is truthy in
most careless coercions. Compare explicitly:
`profile$verification_status == "blue_verified"`.

Note the asymmetry with the *filter*: you search with `is_verified` (a boolean)
and you get back `verification_status` (a string). See `query_params.md` § "The
Five Spellings of 'verified'".

## Facebook Comments

Comment records name the commenter under `owner.*` — **not** `author_id`, which
may be present but empty. Flattened names as returned by `mcl_fromJSON()`:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique comment ID |
| `post_id` | string | Parent post ID |
| `parent_comment_id` | string | Parent **comment** ID. **Present only when `fetch_all = TRUE`; absent entirely on a top-level-only pull** — [verified 2026-08-27] |
| `text` | string | Comment text |
| `creation_time` | datetime | When comment was posted |
| `owner.id` | string | Commenter ID |
| `owner.username` | string | Commenter handle (use this to build a producer URL) |
| `owner.name` | string | Commenter display name |
| `owner.type` | string | page, profile, … |
| `author_id` | string | Present in some responses but **empty** — use `owner.id` |
| `lang` | string | Comment language (ISO 639-1, 2-letter lowercase) |
| `link_attachment.link` | string | **URL of a link attached to the comment — the field is `link`, exactly as on posts** [verified 2026-08-27] |
| `link_attachment.name` | string | Name of the link attachment |
| `link_attachment.caption` | string | Caption of the link attachment |

> **⚠ Corrected 2026-08-27 — `link_attachment.url` does not exist on comments.**
> This table previously said `url` for comments and `link` for posts, and the
> distinction was load-bearing in downstream study code. Live check on
> `facebook/posts/{id}/comments/preview`: the **default projection** returns
> `link_attachment.link`, `.name`, `.caption` — no `url`. Requesting
> `link_attachment{url,link,name,caption,description}` returned only `link`,
> `name`, `caption`; `url` and `description` were silently dropped while the
> positive control `statistics{like_count}` survived, which is the
> discriminating evidence. **Comment attachments have no `description`
> either.** Code selecting `link_attachment.url` gets no column, silently.

`owner.type` on a comment takes a value the post surfaces do not: **`private`**,
alongside `page` and `profile`. A private commenter is a real row with a real
comment and an unusable identity — count it, don't try to resolve it.

### Comment statistics — a fuller set than this file used to list

**[added 2026-08-25 from Meta's data dictionary]** Comments carry the same
per-emoji reaction breakdown as posts, plus **two different reply counts**:

| Field | Type | Description |
|-------|------|-------------|
| `statistics.reaction_count` | integer | Total reactions on the comment |
| `statistics.like_count` … `statistics.care_count` | integer | Per-emoji breakdown: `like`, `love`, `wow`, `haha`, `sad`, `angry`, `care` |
| `statistics.comment_count` | integer | **All** replies to this comment, including replies to replies |
| `statistics.top_level_reply_count` | integer | **Top-level** replies only |

**`comment_count` and `top_level_reply_count` are not interchangeable.** The
first counts a whole subtree, the second one level. Reporting "replies" from
whichever happens to be present changes the number without changing the label.

Instagram comments carry a narrower set — `statistics.like_count`,
`statistics.comment_count` and `statistics.top_level_reply_count` only, with no
per-emoji breakdown and only `link_attachment.link` for attachments.

### ✅ `parent_id` or `parent_comment_id`? — **[settled 2026-08-27]**

**The field is `parent_comment_id`. `parent_id` does not exist.** Meta's data
dictionary was right and this file was wrong.

Verified live against `facebook/posts/{id}/comments/preview` on an Italian
page post with 25,616 comments:

| Request | `parent_id` | `parent_comment_id` |
|---|---|---|
| default projection, `fetch_all` unset (top-level only) | absent | **absent** |
| named explicitly in `fields` | absent | absent (silently dropped) |
| `fetch_all = TRUE` | absent | **present** |

Both halves of the old question are answered:

- **The name** is `parent_comment_id`, for Facebook comments as the data
  dictionary said.
- **Absent, not empty.** On a top-level-only pull the column is not in the
  data frame at all, so `df$parent_comment_id == ""` tests a `NULL` and
  `"parent_comment_id" %in% names(df)` is the correct guard. The column
  materialises only when replies can be in the result set — i.e. under
  `fetch_all = TRUE`.

Consequence for the two-pull route: replies fetched through
`/facebook/comments/{id}/replies/preview` come back with **no parent field**,
so the caller must carry the linkage (it knows which comment it asked for).

### Replies: one job with `fetch_all`, or a second pull

**[added 2026-08-25]** A comments job accepts **`fetch_all = TRUE`**, which
returns every reply level in one pass. The parameter is documented in
`references/query_params.md` § "Bulk-comment parameters", which owns it; what
belongs here is **which of the two routes to take**:

| | One job, `fetch_all = TRUE` | Two pulls |
|---|---|---|
| Gets | Every reply level, everywhere | Only the replies you ask for |
| Budget | Whole threads, including subtrees nobody will read | Top-level comments, then replies for the comments that report having any |
| Use when | The thread structure *is* the object of study | The corpus is large, or replies matter only for a subset |

The comment budget is its own 500,000-record pool, so on a large corpus the
second route is materially cheaper. The default is `fetch_all = FALSE`, which
means the behaviour described below is what you get unasked:

A comments query with `parent_ids` = **post** IDs and no `fetch_all` returns
**top-level comments only**. Replies are then a separate fetch, keyed on the
comment IDs that report replies:

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

## Instagram Posts

**[corrected 2026-08-25 from Meta's data dictionary]** Earlier versions of this
file listed `caption`, `producer_id` / `producer_username` / `producer_name` /
`producer_type` / `producer_verified`, `statistics.likes`,
`statistics.comments`, `statistics.plays`, `media_count` and `image_text`.
**None of those names appear in Meta's Instagram post dictionary.** They were a
guess at symmetry with a Facebook table that itself turned out to be wrong (see
§ "Engagement Statistics" above, corrected against a live response on
2026-08-24). The documented shape is the *same* shape Facebook was verified to
return: `*_count` statistics and a `post_owner.*` block.

The correction runs the same way the Facebook one did: `intersect()`-style column
selection drops unmatched names in silence, so code written against
`producer_username` or `statistics.likes` yields a results table with the author
and the engagement columns quietly missing.

### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique post identifier |
| `text` | string | Post text — **`text`, not `caption`**. Tags excluded. Not applicable to stories |
| `creation_time` | datetime | When posted |
| `modified_time` | datetime | Most recent modification |
| `lang` | string | Detected language (ISO 639-1) |
| `hashtags` | list | Hashtags in the post — a real field, with no Facebook equivalent |
| `match_type` | list | Match types for text searches in text, images and stories |
| `is_verified` | boolean | Whether the post was made from a verified account |
| `is_branded_content` | boolean | Branded content or not |
| `media_type` | string | albums, photos, videos, reels |
| `content_type` | string | Media type included in the post |

### Producer Fields — `post_owner.*`, not `producer_*`
| Field | Type | Description |
|-------|------|-------------|
| `post_owner.id` | string | Account ID of the post owner |
| `post_owner.username` | string | Username of the post owner |
| `post_owner.name` | string | Display name of the post owner |
| `post_owner.type` | string | Account type — creator, business, personal |

**Meta's dictionary lists no `surface.*` fields for Instagram posts** — which
would mean the `post_owner` / `surface` split that matters so much on Facebook
(see § "`post_owner` vs `surface`") has no Instagram analogue, and that a
producer-list pull with `account_ids` returns what those accounts published with
no reshare-amplification to filter out.

**Do not build a study design on that.** It is an inference from an omission, in
the same dictionary that was wrong about Facebook's engagement names, wrong about
`post_owner.data.*` and wrong about where the view-refresh date lands. Run
`names()` on a real response and look for a `surface.*` column before concluding
you do not need an owner filter — Test 12.3 checks exactly this.

### Engagement Statistics
| Field | Type | Description |
|-------|------|-------------|
| `statistics.like_count` | integer | Like reactions. Not applicable to stories |
| `statistics.comment_count` | integer | Comments. Not applicable to stories |
| `statistics.views` | integer | Times on screen, excluding the owner's own screen |
| `view_date_last_refreshed` | — | When the view count was last refreshed — **see the note below on where this actually lands** |

Meta's dictionary lists **no per-emoji breakdown for Instagram** (Facebook's
`love/wow/haha/sad/angry/care_count` have no counterpart there), and **no
`statistics.plays` or `statistics.share_count`** — again an absence in a source
with a track record of omissions, so treat it as "not documented", not as
"confirmed absent". `statistics.views` carries the
same "absent, not zero" hazard documented for Facebook — do not coerce `NA` to
`0` before ranking.

> **Unverified against a live response.** This table is transcribed from the
> documentation, and the documentation was wrong about Facebook until a live
> projection corrected it. Confirm the Instagram shape the same way — run a
> `instagram/posts/preview` with no `fields` and read `names()` off the result —
> before building on it. `docs/TESTING_PROCEDURE.md` § "Instagram post default
> projection" has the procedure.

## Instagram Accounts

Confirmed from a live `/instagram/accounts/preview` response (v1.2.0). The field
table lives in `references/producer_lists.md` § "Instagram Account Fields (from
/preview)" — `id`, `name`, `username`, `biography`, `account_type`,
`is_verified`, `follower_count`, `following_count`, `creation_date`, `website`.

Note the spellings: `biography` (not `bio`) and `is_verified` (not `verified`).

## Instagram Comments

> **Note:** Comments are accessed via nested endpoints. Use `/instagram/posts/{post_id}/comments/preview` not `/instagram/comments/preview` with a `post_ids` parameter.

Not confirmed against a live response. Facebook comments name the commenter under
`owner.*`, with `author_id` present but empty (verified, v1.7.0); assume the same
shape here and check with `str()` before relying on it.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique comment ID |
| `post_id` | string | Parent post ID |
| `parent_id` | string | Parent **comment** ID; empty on top-level comments |
| `text` | string | Comment text |
| `creation_time` | datetime | When posted |
| `owner.id` | string | Commenter account ID |
| `owner.username` | string | Commenter handle |
| `owner.name` | string | Commenter display name |

Engagement fields on Instagram comments (like and reply counts) are unconfirmed
— Facebook comments report `statistics.reaction_count` and
`statistics.top_level_reply_count`. Check the actual shape with
`str(mcl_fromJSON(resp$text)$data)`, or read the endpoint's entry from
`client$openapi_spec()`.

## Threads — documented in the Library, absent from the API

**[corrected 2026-08-25]** Earlier versions of this file carried a speculative
Threads field table (`statistics.likes`, `statistics.replies`,
`statistics.reposts`, `statistics.quotes`, `is_reply`, `parent_id`). **Delete
any code written against it.** Those names were invented by analogy; Meta's data
dictionary does not list them.

What the documentation actually shows:

- The data dictionary **does** have Threads sections — Threads post, Threads
  profile, Threads reply — describing the concepts (likes, replies, reposts,
  views, post owner, content type, view-count refresh date, and so on).
- **Their "API field" column reads `N/A` for every row but one.** The single
  exception is `is_account_verified` on a Threads post. So the dictionary
  documents Threads as *Content Library* data, and declines to name API
  properties for it.
- **None of the 25 API guide pages covers Threads.** There are guides for
  Facebook, Instagram and WhatsApp surfaces; there is no `th-posts`.
- Threads *is* named in the API's own policy text: *"Downloading of Facebook,
  Instagram, Threads and WhatsApp data from the Content Library API by any means
  is not permitted."* So it is not that Threads is outside the product.

**Operationally:** no Threads endpoint is documented and no Threads API field
name is published. If you need Threads, read the paths out of
`client$openapi_spec()` first — that is the authority for what this deployment
actually serves — and treat anything you find there as a discovery worth
recording here. Threads data is subject to the same verified-or-100-followers
rule as Facebook and Instagram profiles.

## The data dictionary is segmented by product — check the anchor

**[verified 2026-08-22]** Meta's post data dictionary documents several product surfaces on one
page, distinguished only by URL anchor. The section at **`#dd-fb-post-3pcleanroom`** describes
the **Third-Party Cleanroom** schema, **not** the Content Library API served in the SRE.

Fields documented there that the Content Library API **does not return**, tested on both a
group and a page surface, in both parent and dotted form:

| Documented under `3pcleanroom` | Content Library API |
|---|---|
| `link_attachment_fields.{link,name,caption,description}` | **not returned** — silently dropped from `fields` |
| `multimedia.url` (flagged "third-party cleanroom feature") | **not returned** |
| `multimedia.user_tags` | **not returned** |
| `match_type` | **not returned** |

**Rule: a field documented under a `3pcleanroom` anchor is not evidence that the Content Library
API serves it.** The `fields` parameter drops unknown names **silently**, so a request that
"succeeds" with fewer columns is the signature of asking for fields this deployment does not
have. **`client$openapi_spec()` is the authority for what is actually served** — free and
in-session.

### `multimedia` sub-fields vary by item type

**[verified 2026-08-22]** `multimedia` is a list column whose sub-fields depend on what the item
is:

```
group surface, ~80% photos   -> multimedia sub-fields: type
page surface,  ~88% video    -> multimedia sub-fields: type, duration
```

`multimedia.duration` is real and available — but only on video items, so a corpus of photos
will never show it. Do not conclude a sub-field is absent from one sample.

### `image_text` is a match_type VALUE, not a field — but it IS usable

**[verified 2026-08-22]** There is **no OCR text column** on any Content Library API post
surface. `image_text` is a *value* of `match_type`, and it works.

**`match_type` has three documented values, not two** — `post_text`, `image_text`
and **`multimedia_text`** (added here 2026-08-25 from Meta's dictionary). The run
below observed only the first two, which is what a corpus of photos and text
posts would produce; `multimedia_text` presumably reports a match inside video or
other multimedia and has **not** been observed. Do not write a two-way `switch`
on this field.

```r
client$get(path = "facebook/posts/preview",
           params = list("q" = "governo",
                         "search_scope" = "post_text_and_image_text",
                         "fields" = "id,match_type"))
# -> match_type tally over 25 rows:  image_text 5 | post_text 24
```

**`match_type` requires a `q` search.** Requesting it alongside `surface_ids` with no query
returns nothing — there is no "match" to report. That is not the field being unavailable, and it
is an easy false negative to record.

**What this buys.** In-image text can be **interrogated by keyword** and the matching posts
**identified**, even though the OCR text itself is never returned. So a hypothesis about image
content is testable at zero budget (`estimate` is free), and the matched post ids can be carried
into further analysis. What is *not* possible is embedding or modelling in-image text, because
you never receive it.

### `multimedia{url}` DOES work — but the URLs are ephemeral, not identifiers

**[verified 2026-08-22]** Request the sub-field explicitly and media URLs are returned:

```r
fields = "id,multimedia{type,url,duration,user_tags}"
# multimedia sub-fields present: type, duration, url   (user_tags never appeared)
```

Measured over 25 items: **25 URLs, 25 unique, 0 missing**, all on
`prod-fortapis-api-async-uploads.s3.amazonaws.com`, **median length 1,803 characters**.

That shape — a Meta research S3 bucket, `async-uploads`, a ~1.8 kB URL — is a **presigned,
time-limited download link generated per request**, not a stable content address.

**Two consequences, and they pull in opposite directions:**

- **Media files are retrievable in principle.** This is the download path the docs attribute to
  the cleanroom; it is exposed here too, on explicit request.
- **URLs cannot be used as artifact identity.** The same image in two posts will get two
  different presigned URLs. Any de-duplication or diffusion analysis keyed on media URL is
  invalid. Use `shared_post_id` for reshare identity; there is no image-identity field.

Retrieving the bytes additionally depends on outbound network from an SRE cell — untested, and
gated on Meta's Import & Export Policy — and analysing them needs a **vision model, which the
approved-model list does not contain** (`ml_models_approved.md`). So today: retrievable in
principle, not analysable.

### THE RULE: get field names from the SPEC, not the data dictionary

**[verified 2026-08-22]** The data dictionary shows **human-readable display labels**. The API
uses **property names**. They are not the same string, and transliterating a label into a field
name silently returns nothing.

This cost four consecutive false negatives in one session. The label *"Link attachment fields
description"* was read as `link_attachment_fields.description`. **The actual property is
`link_attachment`.**

**Always start here:**

```r
sp <- client$openapi_spec()
fb <- sp$components$schemas$FacebookPost$properties
names(fb)                                  # the definitive field list for THIS deployment
sp$components$schemas$LinkAttachment$properties   # and its nested schemas
```

Free, in-session, complete, and specific to the deployment you are querying. There is no reason
to discover a field list by trial and error.

### The complete Facebook Post schema, from the spec

**[verified 2026-08-22]** `FacebookPost` has **16 properties**:

| Property | Type |
|---|---|
| `id`, `text`, `creation_time`, `modified_time`, `lang` | string |
| `content_type`, `shared_post_id`, `branded_content_page_id` | string |
| `is_branded_content` | boolean |
| `match_type` | array |
| `activities` | array of `FacebookActivity` |
| `multimedia` | array of `Multimedia` |
| `statistics` | `FacebookStatistics` |
| `post_owner`, `surface` | `FacebookEntityOwner` |
| **`link_attachment`** | **`FacebookLinkAttachment`** |

Nested schemas:

```
LinkAttachment -> description, link, name          (response also carries .caption)
Multimedia     -> id, type, duration, tags, url
```

### `link_attachment` WORKS — link URLs are obtainable

**[verified 2026-08-22]** Requested by its real name, on link posts:

```r
fields = "id,content_type,link_attachment,shared_post_id"
# -> id, content_type,
#    link_attachment.description, link_attachment.link,
#    link_attachment.name, link_attachment.caption      (25 rows)
```

**A shared link's URL, title, caption and description are all retrievable.** Co-sharing
analysis, domain-level media-diet measurement and URL-based diffusion **are buildable on this
API**. Any earlier claim to the contrary in this skill was a naming error, now corrected.

### `multimedia` — `id` and `tags` exist too

**[verified 2026-08-22]** The schema is `id, type, duration, tags, url`. Earlier notes here
listed only `type`/`duration`/`url` because that is what a default projection happened to
return; **`id` and `tags` require explicit request**. `multimedia.id` is a candidate stable
media identifier — unlike `multimedia.url`, which is an ephemeral presigned link (below) — but
whether the same image in two posts shares an id is **untested**.

### `fields` is not in the spec's parameter list, but it works

**[verified 2026-08-22]** `/facebook/posts/preview` declares:
`lang, q, since, until, is_branded_content, is_surface_verified, content_types,
views_bucket_start, views_bucket_end, post_ids, surface_ids, surface_ids_to_exclude,
surface_types, surface_countries, search_scope, limit, sort, after, X-API-Version`.

**`fields` is absent from that list yet is honoured by the server.** So the spec is authoritative
for *schemas* but not exhaustive for *parameters* — do not conclude a parameter is unsupported
because the spec omits it.

Three parameters worth noting that this skill does not otherwise document:
**`surface_ids_to_exclude`** (server-side exclusion — useful for building a "rest of the group"
corpus without post-hoc filtering), **`surface_countries`**, and
**`views_bucket_start` / `views_bucket_end`**.

### `post_owner` vs `surface` — the pair the tier logic rests on

**[verified 2026-08-23]** Meta's data dictionary, verbatim:

- **Post owner** — *"Unique ID linked to the owner associated with the Facebook post"* — is
  **who created the post**.
- **Post surface** — *"The type of surface of the Facebook post. Post surface types include:
  Pages, profiles, groups and events"* — is **where the post appears**.

**They differ whenever content is reshared.** When a Page reshares another account's post, the
**owner stays the original creator** and the **surface is the Page distributing it**;
`shared_post_id` carries *"Unique ID linked to the reshared post included in the Facebook
post."* Meta's own framing: this separation lets researchers *"distinguish between original
content producers and the accounts amplifying that content through reshares."*

**Consequence for producer-list queries, and it is easy to get wrong:** `surface_ids` selects by
**surface**, so a producer-list pull returns *everything that appeared on those surfaces*,
including reshares **authored by accounts outside the list**. Observed on live data: a 14-page
producer list returned 10,731 posts with **72 distinct `post_owner.id`s**, and a 2-page list
returned 389 posts with **50 owners**.

So decide explicitly which question is being asked:

| Question | Filter |
|---|---|
| What did these accounts **publish** (incl. amplification)? | none — `surface_ids` already answers it |
| What did these accounts **author**? | keep rows where `post_owner.id %in% <list ids>` |
| What did they **amplify**? | rows where `post_owner.id` is *not* in the list, or `!is.na(shared_post_id)` |

Reporting an owner-based count as if it were a surface-based one (or vice versa) silently
changes the population.

*(An earlier draft of this file claimed Meta's docs omit groups from the surface-type
enumeration. That was wrong — a bad reading of a partial fetch. The docs list "Pages, profiles,
groups and events".)*

## Data Scope: Whose Posts Are Queryable

**Post availability depends on producer type.** For Facebook **profiles**, posts
enter the queryable dataset only if the profile is public and either verified or
above a follower threshold. **In v6.0 that threshold is 100 followers.** An
ordinary private or tiny profile returns ~0 posts even though it can be added to
a producer list and appears in `facebook/profiles/preview`.

| Producer type | Posts queryable? |
|---------------|------------------|
| Page | Yes |
| Group (public, indexed) | Yes |
| Profile — public and verified, or 100+ followers | Yes |
| Profile — private, or under the threshold | No (returns ~0 posts) |

The threshold has moved twice and older write-ups are stale: it was 25,000
before v5.0, 1,000 in v5.0 (2024-11-11), and 100 from v6.0 (2025-11-10). The
same 100-follower rule governs which Instagram **personal** accounts are
included; creator and business accounts have no follower requirement. "Verified"
now also covers **paid Meta Verified subscriptions**, not just legacy badges, so
a small account can qualify by subscription alone.

Separately, the *downloadable* dataset offered through ICPSR / CASD still
documents a 25,000-follower floor. That is a different product from the API —
don't apply its number when reasoning about why an API query came back empty.

Symptom: a producer-list post query estimates ~0 results despite the list having
many members — the members are mostly ordinary profiles. Check the mix before
concluding the query is wrong.

For profiles, only posts made to their **own** profile are returned; their
comments and posts on other surfaces are not part of that producer's posts.

### Geography and audience restrictions — **[added 2026-08-25]**

Producer type is not the only thing that removes content from the dataset. From
the API overview:

- **Four countries are excluded outright.** *"Public data/content will be
  excluded from these countries: China, North Korea, South Korea, Togo."* A
  comparative study that includes any of them will find them empty, and that is
  the product, not the query.
- **Age-restricted content is excluded**, on the grounds that it is not
  publicly accessible.
- **Location-restricted content** is excluded on **Instagram and WhatsApp**. On
  **Facebook** it depends on the location the query is run from — so two
  researchers running the identical query from different countries can get
  different Facebook corpora. Record where a corpus was collected; it is part of
  the method.

### Downloading is not permitted — **[added 2026-08-25]**

*(This file owns this fact; `surfaces.md` points here.)*

Verbatim from the overview: *"Downloading of Facebook, Instagram, Threads and
WhatsApp data from the Content Library API by any means is not permitted."*

This is the policy behind several practical facts documented elsewhere in this
skill: the scrubbed notebook export, the enclave-owned S3 bucket that is not an
exit (`utilities.md` § "Getting Results Out"), and the presigned `multimedia{url}`
links that are retrievable *in principle* (§ "`multimedia{url}` DOES work"). Read
that section with this sentence next to it — the constraint on taking media out
is a rule, not merely a missing capability.

## Field Availability Notes

**ID fields**: Documented as `string`, but not always quoted in the JSON payload. Always load them as character (`mcl_fromJSON()`); never compare, join, or deduplicate on a numeric ID.

1. **View counts**: Not available for all posts; depends on privacy settings
2. **Image text (OCR)**: Only available for content from last ~180 days
3. **Location data**: Excluded for some countries due to legal requirements
4. **Historical data**: Some fields added in API updates may not be backfilled
5. **Threads data**: Available since Feb 2025; subject to the same verified-or-100-followers rule as of v6.0

## Requesting Fields

Field selection **is** verified and documented — it lives in
`references/query_params.md` § "Field expansion: the `fields` parameter uses
BRACE syntax, not dots" (verified 2026-08-22). Two things to carry into any
reading of the tables above:

- The request syntax is `statistics{like_count}`; the dots in this file and in
  Meta's dictionary are *naming*, and the flattened response, not request syntax.
- **`fields` drops unknown names silently.** Always send a known-good field as a
  positive control alongside anything you are testing, or you cannot tell "not
  served" from "misspelled".

*(This section previously said field selection had not been verified. That was
stale as of v1.11.)*

## Where the docs and this file disagree

**[recorded 2026-08-25]** Reconciling this skill against Meta's documentation
turned up four places where the published field name differs from what a live
response actually returned. **The live observation is operative in every case**
— this table exists so that a reader who finds the documented name is not left
wondering which to trust.

| Concept | Meta's data dictionary | Observed live | Status |
|---|---|---|---|
| Facebook post owner | `post_owner.data.id`, `.data.type`, `.data.name`, `.data.username` | `post_owner.id`, `.type`, `.name` | **[verified 2026-08-24]** — use the observed form |
| View-count refresh date | `view_date_last_refreshed` (top level, FB **and** IG) | `statistics.views_date_last_refreshed` | **[verified 2026-08-24]** — use the observed form |
| Facebook post link attachment | `link_attachment_fields.{link,name,caption,description}` | `link_attachment` (`LinkAttachment` in the spec) | **[verified 2026-08-22]** — the documented name returns nothing |
| Producer list payload | `producers.data[].{id,type,name}` | `$producers` data.frame (id, name, type) | **[verified]** — see `producer_lists.md` |

**A hypothesis that ties three of them together:** the dictionary appears to
describe the *unflattened graph envelope*, in which an expanded sub-entity sits
under a `data` key — `post_owner.data.id`, `producers.data[].id`. `mcl_fromJSON()`
parses with `flatten = TRUE`, and the client appears to unwrap that envelope, so
the `data` level never reaches R. That would make the dictionary and the
observations descriptions of the same payload at different stages rather than a
contradiction. It is **a hypothesis, not a finding** — nothing has been tested —
but it predicts that any `X.data.y` in the dictionary reaches R as `X.y`, which
is a cheap thing to check next time one appears.

It does **not** explain `view_date_last_refreshed` (which moves *into*
`statistics`, not out of a `data` wrapper) or `link_attachment_fields` (which
`field_reference.md` § "THE RULE" already attributes to the dictionary printing
human-readable display labels rather than property names).

**The rule this leaves you with is unchanged: `client$openapi_spec()` is the
authority for what this deployment serves.** It is free, in-session, and specific
to your version. The dictionary tells you what a field *means*; the spec tells
you what it is *called*.

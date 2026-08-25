# Field Reference by Endpoint

> **Every field typed `string` below that holds an ID** (`id`, `post_owner.id`,
> `owner.id`, `surface.id`, `producer_id`, `post_id`, `parent_id`,
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
5. [Facebook Comments](#facebook-comments)
6. [Instagram Posts](#instagram-posts)
7. [Instagram Accounts](#instagram-accounts)
8. [Instagram Comments](#instagram-comments)
9. [Threads Posts](#threads-posts)
10. [Data Scope: Whose Posts Are Queryable](#data-scope-whose-posts-are-queryable)

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

## Facebook Pages

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique Page ID |
| `name` | string | Page name |
| `category` | string | Page category |
| `description` | string | Page description |
| `verified` | boolean | Has verified badge |
| `follower_count` | integer | Number of followers |
| `like_count` | integer | Number of likes |
| `creation_date` | date | When Page was created |
| `location.city` | string | City if listed |
| `location.country` | string | Country if listed |
| `website` | string | Listed website URL |

## Facebook Groups

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique Group ID |
| `name` | string | Group name |
| `description` | string | Group description |
| `privacy` | string | public (only public groups returned) |
| `member_count` | integer | Number of members |
| `creation_date` | date | When Group was created |
| `admin_count` | integer | Number of admins |

## Facebook Events

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique Event ID |
| `name` | string | Event title |
| `description` | string | Event description |
| `start_time` | datetime | Event start time |
| `end_time` | datetime | Event end time |
| `location.name` | string | Venue name |
| `location.city` | string | City |
| `location.country` | string | Country |
| `interested_count` | integer | Users marked interested |
| `going_count` | integer | Users marked going |
| `host_id` | string | Hosting Page/profile ID |

## Facebook Comments

Comment records name the commenter under `owner.*` — **not** `author_id`, which
may be present but empty. Flattened names as returned by `mcl_fromJSON()`:

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique comment ID |
| `post_id` | string | Parent post ID |
| `parent_id` | string | Parent **comment** ID; empty on top-level comments |
| `text` | string | Comment text |
| `creation_time` | datetime | When comment was posted |
| `owner.id` | string | Commenter ID |
| `owner.username` | string | Commenter handle (use this to build a producer URL) |
| `owner.name` | string | Commenter display name |
| `owner.type` | string | page, profile, … |
| `author_id` | string | Present in some responses but **empty** — use `owner.id` |
| `statistics.reaction_count` | integer | Total reactions on the comment |
| `statistics.top_level_reply_count` | integer | Number of replies to this comment |

### Replies Require a Second Pull

A comments query with `parent_ids` = **post** IDs returns **top-level comments
only** (their `parent_id` is empty). Replies are a separate fetch, keyed on the
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

### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique post identifier |
| `creation_time` | datetime | When posted (UTC) |
| `caption` | string | Post caption |
| `lang` | string | Detected language |

### Producer Fields
| Field | Type | Description |
|-------|------|-------------|
| `producer_id` | string | Account ID |
| `producer_username` | string | Instagram handle |
| `producer_name` | string | Display name |
| `producer_type` | string | business, creator |
| `producer_verified` | boolean | Has verified badge |

### Engagement Statistics
| Field | Type | Description |
|-------|------|-------------|
| `statistics.likes` | integer | Like count |
| `statistics.comments` | integer | Comment count |
| `statistics.views` | integer | View count (video/reel) |
| `statistics.plays` | integer | Play count (reels) |

### Media Fields
| Field | Type | Description |
|-------|------|-------------|
| `media_type` | string | image, video, carousel, reel |
| `media_count` | integer | Items in carousel |
| `image_text` | string | OCR text from images |

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

## Threads Posts

> **Unverified.** No Threads endpoint path has been confirmed for this API
> version, and this table has not been checked against a live Threads query.
> Discover the available paths with `client$openapi_spec()` before relying on it.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique post ID |
| `creation_time` | datetime | When posted (UTC) |
| `text` | string | Post text |
| `producer_id` | string | Author account ID |
| `producer_username` | string | Threads handle |
| `producer_verified` | boolean | Has verified badge |
| `statistics.likes` | integer | Like count |
| `statistics.replies` | integer | Reply count |
| `statistics.reposts` | integer | Repost count |
| `statistics.quotes` | integer | Quote count |
| `media_type` | string | text, image, video |
| `is_reply` | boolean | Is this a reply |
| `parent_id` | string | Parent post if reply |

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
surface. `image_text` is a *value* of `match_type`, and it works:

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

## Field Availability Notes

**ID fields**: Documented as `string`, but not always quoted in the JSON payload. Always load them as character (`mcl_fromJSON()`); never compare, join, or deduplicate on a numeric ID.

1. **View counts**: Not available for all posts; depends on privacy settings
2. **Image text (OCR)**: Only available for content from last ~180 days
3. **Location data**: Excluded for some countries due to legal requirements
4. **Historical data**: Some fields added in API updates may not be backfilled
5. **Threads data**: Available since Feb 2025; subject to the same verified-or-100-followers rule as of v6.0

## Requesting Fields

Field selection is not documented here because it has not been verified against
a live response. To check whether an endpoint accepts a field-selection
parameter, read its entry in the OpenAPI spec — see SKILL.md § "OpenAPI Spec".

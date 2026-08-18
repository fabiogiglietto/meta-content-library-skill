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

## Facebook Posts

### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique post identifier |
| `creation_time` | datetime | When post was created (UTC) |
| `text` | string | Post body text |
| `lang` | string | Detected language (ISO 639-1) |

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
| Field | Type | Description |
|-------|------|-------------|
| `statistics.reactions` | integer | Total reactions count |
| `statistics.comments` | integer | Comment count |
| `statistics.shares` | integer | Share count |
| `statistics.views` | integer | View count (where available) |

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

## Data Scope: Whose Posts Are Queryable

**Post availability depends on producer type.** For Facebook **profiles**, posts
enter the queryable dataset only if the profile is verified or has enough
followers — 25,000+ for the downloadable/API subset, 100+ for view-only. An
ordinary profile returns ~0 posts even though it can be added to a producer list
and appears in `facebook/profiles/preview`.

| Producer type | Posts queryable? |
|---------------|------------------|
| Page | Yes |
| Group (public, indexed) | Yes |
| Profile — verified, or 25,000+ followers | Yes |
| Profile — ordinary | No (returns ~0 posts) |

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
5. **Threads data**: Available since Feb 2025, only for 1K+ follower accounts

## Requesting Fields

Field selection is not documented here because it has not been verified against
a live response. To check whether an endpoint accepts a field-selection
parameter, read its entry in the OpenAPI spec — see SKILL.md § "OpenAPI Spec".

# Field Reference by Endpoint

> **Every field typed `string` below that holds an ID** (`id`, `producer_id`,
> `post_id`, `parent_id`, `author_id`, `host_id`, `shared_from_id`, …) must end up
> as a **character** vector in R. Some endpoints send these as unquoted JSON
> numbers, so `fromJSON()` types them `numeric` — losing digits above 2^53 and
> printing as `9.6378e+14`. Parse with `mcl_fromJSON()` (SKILL.md § "ID Handling").
> Only counts and timestamps are genuinely numeric.

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

## Facebook Posts

### Core Fields
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique post identifier |
| `creation_time` | datetime | When post was created (UTC) |
| `text` | string | Post body text |
| `lang` | string | Detected language (ISO 639-1) |

### Producer Fields
| Field | Type | Description |
|-------|------|-------------|
| `producer_id` | string | ID of posting account |
| `producer_name` | string | Display name |
| `producer_type` | string | page, group, event, profile |
| `producer_verified` | boolean | Has verified badge |

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
| `shared_from_id` | string | Original post ID if reshare |
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

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique comment ID |
| `post_id` | string | Parent post ID |
| `parent_id` | string | Parent comment ID (for replies) |
| `text` | string | Comment text |
| `creation_time` | datetime | When comment was posted |
| `author_id` | string | Commenter ID |
| `reactions` | integer | Reaction count |
| `reply_count` | integer | Number of replies |

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

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique account ID |
| `username` | string | Instagram handle |
| `name` | string | Display name |
| `bio` | string | Profile biography |
| `account_type` | string | business, creator |
| `category` | string | Business category |
| `verified` | boolean | Has verified badge |
| `follower_count` | integer | Number of followers |
| `following_count` | integer | Number following |
| `post_count` | integer | Total posts |
| `website` | string | Profile website |

## Instagram Comments

> **Note:** Comments are accessed via nested endpoints. Use `/instagram/posts/{post_id}/comments/preview` not `/instagram/comments/preview` with a `post_ids` parameter.

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique comment ID |
| `post_id` | string | Parent post ID |
| `text` | string | Comment text |
| `creation_time` | datetime | When posted |
| `author_id` | string | Commenter account ID |
| `likes` | integer | Like count |
| `reply_count` | integer | Number of replies |

## Threads Posts

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

## Field Availability Notes

**ID fields**: Documented as `string`, but not always quoted in the JSON payload. Always load them as character (`mcl_fromJSON()`); never compare, join, or deduplicate on a numeric ID.

1. **View counts**: Not available for all posts; depends on privacy settings
2. **Image text (OCR)**: Only available for content from last ~180 days
3. **Location data**: Excluded for some countries due to legal requirements
4. **Historical data**: Some fields added in API updates may not be backfilled
5. **Threads data**: Available since Feb 2025, only for 1K+ follower accounts

## Requesting Fields

Specify fields explicitly to reduce response size:

```r
client$search_fb_posts(
  q = "climate",
  fields = c(
    "id",
    "creation_time",
    "producer_name",
    "statistics"
  )
)
```

Default fields vary by endpoint. Check current documentation for defaults.

# Surfaces Added in v6.0 (Channels, Marketplace, Fundraisers, Donations)

> **Documented, not tested.** Everything in this file is transcribed from the
> Meta Content Library API guides and Data dictionary (fetched 2026-08-21;
> re-checked against the same pages 2026-08-25, which confirmed the channel,
> Marketplace, fundraiser and donation parameters unchanged and added the
> WhatsApp update fields below).
> None of it has been run against a live SRE session, unlike the tables in
> `field_reference.md` marked as confirmed. Treat an unexpected `NULL` column or
> a rejected parameter as this file being wrong, not your query — and settle it
> with `client$openapi_spec()` (SKILL.md § "OpenAPI Spec").

These surfaces reached the API after the skill's earlier endpoint list was
written:

| Surface | Added |
|---------|-------|
| Facebook Marketplace listings | 2025-03-14 |
| Facebook / Instagram fundraisers, Facebook donations | 2025-06-30 |
| Instagram channels and channel messages | 2025-06-30 |
| Facebook channels and channel messages | 2026-03-12 |
| WhatsApp channels and channel updates | 2026-04-30 |

## Table of Contents

1. [Sync vs Async Path Shapes](#sync-vs-async-path-shapes)
2. [Facebook Channels](#facebook-channels)
3. [Instagram Channels](#instagram-channels)
4. [WhatsApp Channels](#whatsapp-channels)
5. [Channel Messages and Updates](#channel-messages-and-updates)
6. [Facebook Marketplace Listings](#facebook-marketplace-listings)
7. [Fundraisers and Donations](#fundraisers-and-donations)

## Sync vs Async Path Shapes

The `/{resource}/{preview|job}` pattern does **not** hold for the message and
update surfaces. Sync reads hang off the parent channel node; async jobs use a
**hyphenated** resource name at the platform root:

| Read | Path |
|------|------|
| Messages of many Facebook channels (async) | `facebook/channel-messages/job` |
| Messages of many Instagram channels (async) | `instagram/channel-messages/job` |
| Updates of many WhatsApp channels (async) | `whatsapp/channel-updates/job` |
| Marketplace listings (sync) | `facebook/marketplace-listings/preview` |

The corresponding **sync** reads hang off the parent node and live in SKILL.md §
"Nested Endpoints", which owns that table.

Guessing `facebook/channels/job` or `facebook/marketplace/preview` from the
older pattern gets you a 404.

**Correction, 2026-08-22 — Marketplace *does* have an `estimate` endpoint.** This
file previously said "No `estimate` endpoint is documented for any of these
surfaces — none of the guides mention one." The guides may not, but the **OpenAPI
spec does**. Read live via `client$openapi_spec()`:

```
/facebook/marketplace-listings/preview             -> get
/facebook/marketplace-listings/estimate            -> get
/facebook/marketplace-listings/estimate/{alias_id} -> get
/facebook/marketplace-listings/job                 -> post
/facebook/marketplace-listings/job/{alias_id}      -> post
/facebook/marketplace-listings/{mcl_id}            -> get
```

So Marketplace has the full **preview / estimate / job** trio, plus per-alias
variants and a by-id fetch. **[verified 2026-08-22]** The absence of an `estimate`
in the *guides* is a documentation gap, not an API one — **the spec is the
authority, and it is free to read.** The claim about channels, fundraisers and
donations is untouched: those were not in this spec read and remain unverified.

> **Sort values and defaults for these surfaces are repeated in the per-surface
> tables below for convenience; `references/query_params.md` § "Sort Defaults
> Differ by Endpoint" owns the cross-endpoint comparison and the warning that a
> truncated result set is the *top* of the sort order.**

## Facebook Channels

Search: `facebook/channels/preview`. Either `q` or `admin_ids` is required.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Keywords. Searches the channel `name` field only |
| `admin_ids` | list | MCL Facebook Page or profile IDs that admin the channel |
| `sort` | enum | `most_to_least_member_count` (default), `newest_to_oldest`, `oldest_to_newest` |
| `member_count_min` | integer | Minimum members |
| `member_count_max` | integer | Maximum members |
| `is_admin_verified` | boolean | Filter on the admin's verified badge |
| `since` / `until` | string | `YYYY-MM-DD` or UNIX timestamp |

```r
resp <- client$get(
  path   = "facebook/channels/preview",
  params = list("q" = "meta", "member_count_min" = 1000L)
)
channels <- safe_get_data(resp$text)   # IDs stay character
```

Fields: `id`, `name`, `description`, `creation_time`, `is_admin_verified`,
`member_count`, `admin.id`, `admin.type` (Page or profile), `admin.username`,
`admin.name`.

## Instagram Channels

Search: `instagram/channels/preview`. Either `q` or `admin_ids` is required.
Same filter set as Facebook channels — `member_count_min` / `member_count_max`
are the "member count filter" added 2025-11-10.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Keywords. Searches the channel `name` field only |
| `admin_ids` | list | MCL Instagram account IDs |
| `sort` | enum | `most_to_least_member_count`, `newest_to_oldest`, `oldest_to_newest` |
| `member_count_min` / `member_count_max` | integer | Member thresholds |
| `is_admin_verified` | boolean | Filter on the admin's verified badge |
| `since` / `until` | string | `YYYY-MM-DD` or UNIX timestamp |

Fields: `id`, `name`, `creation_time`, `is_admin_verified`, `member_count`,
`admin.id`, `admin.type` (creator / business / personal), `collaborators[].id`,
`collaborators[].type`, `moderators[].id`, `moderators[].type`.

The array fields arrive as list-columns after `flatten = TRUE`; `mcl_fromJSON()`
walks into them, so the nested IDs are character too.

## WhatsApp Channels

Search: `whatsapp/channels/preview`. WhatsApp channels are keyed on
**followers**, not members, and carry their own verification flag.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Keywords. Searches the channel `name` and `description` fields |
| `channel_ids` | list | MCL WhatsApp channel IDs |
| `categories` | list | Category names to filter on |
| `sort` | enum | `most_to_least_follower_count` (default), `most_to_least_channel_updates`, `newest_to_oldest`, `oldest_to_newest` |
| `follower_count_min` / `follower_count_max` | integer | Follower thresholds |
| `is_channel_verified` | boolean | Filter on the channel's verified badge |
| `limit` | integer | Page size, 10–50 |
| `since` / `until` | string | `YYYY-MM-DD` or UNIX timestamp |

```r
resp <- client$get(
  path   = "whatsapp/channels/preview",
  params = list("q" = "news", "follower_count_min" = 10000L, "limit" = 50L)
)
```

Fields: `id`, `name`, `description`, `creation_time`, `categories[]`,
`is_verified`, `follower_count`.

Note the inconsistency across the three platforms — the *filter* is
`is_channel_verified`, the *field* it filters is `is_verified`, and the
Facebook/Instagram equivalents are `is_admin_verified` on both sides.

## Channel Messages and Updates

### Sync: one channel at a time

```r
# Facebook
client$get(path = paste0("facebook/channels/", channel_id, "/messages/preview"),
           params = list("limit" = 50L))
# Instagram
client$get(path = paste0("instagram/channels/", channel_id, "/messages/preview"),
           params = list("limit" = 50L))
# WhatsApp
client$get(path = paste0("whatsapp/channels/", channel_id, "/updates/preview"),
           params = list("limit" = 50L))
```

`limit` here is **0–50, default 10** — not the 100 that applies to other sync
searches. Sync reads reach only the **last 1000 messages/updates** on the
channel, and WhatsApp updates go back **30 days** at most.

### Async: many channels at once

```r
resp <- client$post(
  path   = "facebook/channel-messages/job",
  params = list(
    "channel_ids"  = as.list(channel_ids),   # array, max 250 IDs
    "text_filter"  = "election",
    "mode"         = "SNAPSHOT",
    "name"         = "Channel messages - election",
    "description"  = "PI: …, IRB #…"
  )
)
```

`text_filter` is applied **after** the messages are loaded, so an estimate taken
before filtering can be far higher than the row count you actually get back.
Budget on the unfiltered estimate.

Message and update fields:

| Field | Facebook | Instagram | WhatsApp |
|-------|----------|-----------|----------|
| `id`, `text`, `creation_time` | yes | yes | yes |
| `channel.id`, `channel.name` | yes | yes | yes |
| `content_type` | text, photo, video, album, audio, link, poll, prompt, unknown | text, photo, video, album, audio, link, poll, daily_prompt, unknown | text, photo, video, gif, sticker, audio, link, poll, quiz, question, question_reply, forwarded_poll, forwarded_quiz, unknown |
| `owner.id` / `owner.type` | page, profile | creator, business, personal, private | — (`admin_profile.name` instead) |
| `statistics.reactions_count`, `statistics.top_reactions[]` | yes | yes | yes |
| `statistics.replies_count` | — | yes | — |
| `statistics.forward_count` | — | — | yes |
| `link_attachment.name` / `.url` ⚠ | yes | — | `link_attachment.url` ⚠ |
| `poll_attachment.question`, `poll_attachment.options[].text` / `.vote_count` | yes | — | yes |
| `quiz_attachment.question`, `quiz_attachment.options[].is_correct_answer` | — | — | yes |

> **⚠ `link_attachment.url` is suspect here — [flagged 2026-08-29].** On both
> **posts** and **comments** the property is `link_attachment.link`; `.url` does
> not exist and is dropped silently (`CHANGELOG.md` v1.15.0,
> `field_reference.md` § Link Fields). The rows above are transcribed from Meta's
> docs and **have not been run** against a channel-message response, so they are
> left as documented rather than corrected. Verify with `client$openapi_spec()`
> before relying on `.url` — one call settles it.
| `shared_instagram_post_id`, `message_replied_to_id` | — | yes | — |

`multimedia` on Facebook channel messages carries type, MCL ID, duration and
user tags. Media **URLs** resolve only in an approved third-party cleanroom; in
the SRE you must request `multimedia{url}` explicitly and it may come back empty.
Meta's dictionary is explicit for WhatsApp: `multimedia.url` is *"URL within a
storage location to which the multimedia content has been downloaded by the
third-party cleanroom"* — and taking media out is prohibited outright, not merely
unimplemented (`field_reference.md` § "Downloading is not permitted"). Treat
media URLs as metadata, not as a download path.

### WhatsApp channel updates carry more than the table above — **[added 2026-08-25]**

The cross-platform table lists what the three platforms have in common. WhatsApp
updates have four further groups of fields, all from Meta's data dictionary, and
they are the reason WhatsApp is worth querying separately rather than folding
into a generic "channel message" schema:

| Field | Description |
|---|---|
| `forwarded_update_info.id` / `.name` | The channel an update was **forwarded from**. With `statistics.forward_count`, this is a directed diffusion edge between channels — the closest thing this API offers to a sharing graph |
| `question_reply_attachment.quoted_question_text` | The original question a `question_reply` update answers |
| `question_reply_attachment.user_response_text` | The response text |
| `admin_profile.name` | The channel admin who posted the update (WhatsApp has no `owner.*` block) |
| `multimedia.type` / `.id` / `.url` / `.duration` | photo, video or audio; `duration` on video |
| `statistics.top_reactions[].reaction` / `.count` | The **top five** reaction types and their counts — an emoji, e.g. ♥️, plus a number |
| `statistics.reactions_count` | Total reactions of all types |
| `link_attachment.name` / `.description` / `.url` | Link attachments |

Poll and quiz attachments are structured, not free text:

```
poll_attachment.question
poll_attachment.options[].text
poll_attachment.options[].vote_count

quiz_attachment.question
quiz_attachment.options[].text
quiz_attachment.options[].vote_count
quiz_attachment.options[].is_correct_answer
```

Two notes for analysis. **`statistics.top_reactions` is truncated at five** —
it is not a complete reaction distribution, and summing it will not equal
`statistics.reactions_count`. And every `options[]` field is an **array inside a
list-column** after `flatten = TRUE`; `mcl_fromJSON()` walks into them so any IDs
stay character, but you still need `tidyr::unnest()` (or a `purrr::map_int()`)
to get vote counts into a data.frame.

## Facebook Marketplace Listings

Search: `facebook/marketplace-listings/preview`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Keywords across listing title and description |
| `categories` | list | Marketplace category names |
| `content_types` | list | `photos`, `videos` |
| `listing_countries` | list | ISO 3166-1 alpha-2, uppercase |
| `sort` | enum | `most_to_least_views`, `newest_to_oldest`, `oldest_to_newest`, `highest_to_lowest_price`, `lowest_to_highest_price` |
| `price_min` / `price_max` | integer | Price bounds — only valid when filtering to a **single** country |
| `views_bucket_start` / `views_bucket_end` | integer | View-count bounds |
| `fields` | list | Field selection |
| `since` / `until` | string | `YYYY-MM-DD` or UNIX timestamp |

Fields: `id`, `description`, `creation_time`, `modified_time`, `content_type`,
`listing_details.title`, `.location`, `.category`, `.availability`,
`.condition`, `.price.amount`, `.price.currency` (ISO 4217),
`.vehicle_info.make`, `.vehicle_info.mileage.value`,
`.property_info.bedrooms_number`, `.property_info.bathrooms_number`.

Prices are cross-currency unless you pin `listing_countries` to one country —
that is the reason `price_min` / `price_max` are refused otherwise, and the
reason `amount` is meaningless without `currency` in any aggregation.

## Fundraisers and Donations

Search: `facebook/fundraisers/preview` and `instagram/fundraisers/preview`.

| Parameter | Type | Description |
|-----------|------|-------------|
| `q` | string | Keywords across fundraiser `title` and `description` |
| `sort` | enum | Facebook: `most_to_least_donors` (default), `newest_to_oldest`, `oldest_to_newest`. Instagram: `most_to_least_donations`, `newest_to_oldest`, `oldest_to_newest` |
| `nonprofit_ids` | list | MCL nonprofit IDs, max 250 |
| `nonprofit_categories` | list | Facebook only |
| `nonprofit_countries` | list | ISO 3166-1 alpha-2, uppercase |
| `owner_ids` | list | MCL owner IDs as **strings**, max 250 |
| `since` / `until` | string | `YYYY-MM-DD` or UNIX timestamp |

Fundraiser fields: `id`, `title`, `description`, `creation_time`,
`has_fundraiser_ended`, `fundraiser_type` (`nonprofit_fundraiser`,
`personal_fundraiser`, `fundraiser_post`), `goal_amount`, `amount_raised`,
`currency`, `owner.id`, `owner.type` (profile / Page / private), `nonprofit.id`,
`statistics.donor_count`, `statistics.share_count`.

Donations hang off a fundraiser and are Facebook-only:

```r
resp <- client$get(
  path   = paste0("facebook/fundraisers/", fundraiser_id, "/donations/preview"),
  params = list("since" = "2026-01-01")
)
```

Donation fields: `owner.id`, `owner.type` (profile / Page / private),
`donation_time`, `statistics.reaction_count`, `statistics.reply_count`.

Only donations whose privacy is set to *everyone* are included, and the donor is
`owner.type = "private"` when they gave anonymously — so `statistics.donor_count`
on the fundraiser is **not** the row count you get here. Don't reconcile the two.

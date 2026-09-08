# Surfaces added in v6.0 — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

Nothing in this file has been run against a live SRE session — the snippets
are transcribed from Meta's guides, like the tables they accompany. Every one
parses with `mcl_fromJSON()` (`languages/r/ids.md` § "mcl_fromJSON") or
`safe_get_data()` (`languages/r/jobs.md` § "Safe response handling"), so IDs
come out as character.

## Searching Facebook channels

Facts: `references/surfaces.md` § "Facebook Channels"

```r
resp <- client$get(
  path   = "facebook/channels/preview",
  params = list("q" = "meta", "member_count_min" = 1000L)
)
channels <- safe_get_data(resp$text)   # IDs stay character
```

`member_count_min` carries the `L` suffix because it is integer-typed
(`languages/r/query_params.md` § "Integer parameters").

## Nested array fields on Instagram channels

Facts: `references/surfaces.md` § "Instagram Channels"

`collaborators[]` and `moderators[]` arrive as list-columns after
`flatten = TRUE`; `mcl_fromJSON()` walks into them, so the nested IDs are
character too.

## Searching WhatsApp channels

Facts: `references/surfaces.md` § "WhatsApp Channels"

```r
resp <- client$get(
  path   = "whatsapp/channels/preview",
  params = list("q" = "news", "follower_count_min" = 10000L, "limit" = 50L)
)
```

## Channel messages, one channel at a time

Facts: `references/surfaces.md` § "Sync: one channel at a time"

The channel ID goes in the path; `limit` is capped at 50 on these endpoints.

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

## Channel messages, many channels at once

Facts: `references/surfaces.md` § "Async: many channels at once"

`channel_ids` goes through `as.list()` so a single ID is still sent as an array
(`languages/r/query_params.md` § "ID parameters are arrays").

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

## Unnesting poll and quiz options

Facts: `references/surfaces.md` § "WhatsApp channel updates carry more than the table above"

Every `options[]` field is an array inside a list-column after `flatten = TRUE`;
`mcl_fromJSON()` walks into them so any IDs stay character, but you still need
`tidyr::unnest()` (or a `purrr::map_int()`) to get vote counts into a
data.frame.

## Donations of a fundraiser

Facts: `references/surfaces.md` § "Fundraisers and Donations"

The fundraiser ID goes in the path:

```r
resp <- client$get(
  path   = paste0("facebook/fundraisers/", fundraiser_id, "/donations/preview"),
  params = list("since" = "2026-01-01")
)
```

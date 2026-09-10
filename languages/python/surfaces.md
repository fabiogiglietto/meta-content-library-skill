# Surfaces added in v6.0 — Python

> **Language layer: Python — [documented] unless a section is stamped `[verified DATE]`.** First run from a Python kernel in the SRE on 2026-09-10 (Step 0, Step 0b, Tests 1.1 and 10.1; no job submitted). Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

Nothing in this file has been run against a live SRE session in either
language — the snippets are transcribed from Meta's guides, like the tables
they accompany. Every one parses with `mcl_from_json()`
(`languages/python/ids.md` § "mcl_from_json") or `safe_get_data()`
(`languages/python/jobs.md` § "Safe response handling"), so IDs come out as
`str`.

## Searching Facebook channels — [documented]

Facts: `references/surfaces.md` § "Facebook Channels"

```python
resp = client.get(
    path="facebook/channels/preview",
    params={"q": "meta", "member_count_min": 1000},
)
channels = safe_get_data(resp.text)   # IDs stay str
```

`member_count_min` is integer-typed; a Python `int` needs nothing further
(`languages/python/query_params.md` § "Integer parameters").

## Nested array fields on Instagram channels — [documented]

Facts: `references/surfaces.md` § "Instagram Channels"

`collaborators[]` and `moderators[]` arrive as lists of dicts inside each
record. `mcl_fix_ids()` recurses into them, so the nested IDs are `str` too;
`pd.json_normalize(data, record_path="collaborators", meta=["id"])` turns one
of them into a long table keyed by the channel `id`.

## Searching WhatsApp channels — [documented]

Facts: `references/surfaces.md` § "WhatsApp Channels"

```python
resp = client.get(
    path="whatsapp/channels/preview",
    params={"q": "news", "follower_count_min": 10000, "limit": 50},
)
```

## Channel messages, one channel at a time — [documented]

Facts: `references/surfaces.md` § "Sync: one channel at a time"

The channel ID goes in the path; `limit` is capped at 50 on these endpoints.

```python
# Facebook
client.get(path=f"facebook/channels/{channel_id}/messages/preview",
           params={"limit": 50})
# Instagram
client.get(path=f"instagram/channels/{channel_id}/messages/preview",
           params={"limit": 50})
# WhatsApp
client.get(path=f"whatsapp/channels/{channel_id}/updates/preview",
           params={"limit": 50})
```

## Channel messages, many channels at once — [documented]

Facts: `references/surfaces.md` § "Async: many channels at once"

`channel_ids` is a `list` so a single ID is still sent as an array
(`languages/python/query_params.md` § "ID parameters are arrays").

```python
resp = client.post(
    path="facebook/channel-messages/job",
    params={
        "channel_ids": list(channel_ids),   # a list, max 250 IDs
        "text_filter": "election",
        "mode": "SNAPSHOT",
        "name": "Channel messages - election",
        "description": "PI: …, IRB #…",
    },
)
```

## Unnesting poll and quiz options — [documented]

Facts: `references/surfaces.md` § "WhatsApp channel updates carry more than the table above"

Every `options[]` field is a list of dicts inside each record. `mcl_fix_ids()`
recurses into them so any IDs stay `str`; use `df.explode("options")` followed
by `pd.json_normalize(df["options"])`, or `pd.json_normalize(data,
record_path="options", meta=["id"])`, to get vote counts into a table.

## Donations of a fundraiser — [documented]

Facts: `references/surfaces.md` § "Fundraisers and Donations"

The fundraiser ID goes in the path:

```python
resp = client.get(
    path=f"facebook/fundraisers/{fundraiser_id}/donations/preview",
    params={"since": "2026-01-01"},
)
```

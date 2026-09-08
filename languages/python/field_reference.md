# Field reference — Python

> **Language layer: Python — [documented], not yet run.** Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Fetching reshared originals — [documented; mirrors languages/r/field_reference.md]

Facts: `references/field_reference.md` § "Reshares"

```python
resp = client.get(
    path="facebook/posts/preview",
    params={"post_ids": list(shared_ids), "limit": 100},   # a list, max 250
)
originals = safe_get_data(resp.text)
originals[["id", "post_owner.id", "post_owner.username"]]
```

## Resolving originals defensively — [documented; mirrors languages/r/field_reference.md]

Facts: `references/field_reference.md` § "Reshares"

The exception class the client raises is **open**; this catches `Exception`.

```python
import pandas as pd


def resolve_originals(ids):
    ids = list(ids)
    if not ids:
        return None
    try:
        out = safe_get_data(client.get(
            path="facebook/posts/preview",
            params={"post_ids": ids, "limit": 100},
        ).text)
    except Exception:          # narrow this once the client's exception class is known
        out = None
    if out is not None:
        return out
    if len(ids) == 1:
        return None            # this one ID is out of scope - skip it
    mid = len(ids) // 2
    parts = [p for p in (resolve_originals(ids[:mid]), resolve_originals(ids[mid:])) if p is not None]
    return pd.concat(parts, ignore_index=True) if parts else None
```

## Replies as a second pull — [documented; mirrors languages/r/field_reference.md]

Facts: `references/field_reference.md` § "Replies: one job with `fetch_all`, or a second pull"

```python
# 1. Top-level comments for the posts
top = safe_get_data(client.post(
    path="facebook/comments/job",
    params={"parent_ids": list(post_ids), "mode": "SNAPSHOT",
            "name": "Top-level comments", "description": "…"},
).text)

# 2. Replies: pass the COMMENT ids that have replies
with_replies = top.loc[top["statistics.top_level_reply_count"] > 0, "id"].tolist()
replies = safe_get_data(client.post(
    path="facebook/comments/job",
    params={"parent_ids": with_replies, "mode": "SNAPSHOT",
            "name": "Replies", "description": "…"},
).text)
# reply records carry parent_id = the comment they answer
```

## Requesting match_type — [documented; mirrors languages/r/field_reference.md, verified 2026-08-22 from R]

Facts: `references/field_reference.md` § "`image_text` is a match_type VALUE, not a field — but it IS usable"

```python
resp = client.get(path="facebook/posts/preview",
                  params={"q": "governo",
                          "search_scope": "post_text_and_image_text",
                          "fields": "id,match_type"})
safe_get_data(resp.text)["match_type"].value_counts()
# -> match_type tally over 25 rows:  image_text 5 | post_text 24
```

## Reading field names from the spec — [documented; mirrors languages/r/field_reference.md]

Facts: `references/field_reference.md` § "THE RULE: get field names from the SPEC, not the data dictionary"

```python
sp = client.openapi_spec()
fb = sp["components"]["schemas"]["FacebookPost"]["properties"]
list(fb)                                                   # the definitive field list for THIS deployment
sp["components"]["schemas"]["LinkAttachment"]["properties"]   # and its nested schemas
```

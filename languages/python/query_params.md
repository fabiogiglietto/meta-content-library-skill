# Query parameters and endpoints — Python

> **Language layer: Python — [documented] unless a section is stamped `[verified DATE]`.** First run from a Python kernel in the SRE on 2026-09-10 (Step 0, Step 0b, Tests 1.1 and 10.1; no job submitted). Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Reading the OpenAPI spec — [verified 2026-09-10]

Facts: `SKILL.md` § "OpenAPI Spec"

```python
import json

spec = client.openapi_spec()
paths = list(spec["paths"])

# Find Instagram endpoints
instagram_paths = [p for p in paths if "instagram" in p.lower()]
print(instagram_paths)

# Inspect one endpoint's parameters
print(spec["paths"]["/instagram/posts/preview"]["get"]["parameters"])

# Save full spec for reference
with open("openapi_spec.json", "w", encoding="utf-8") as f:
    json.dump(spec, f, indent=2)
```

`openapi_spec()` returns a `dict` [verified 2026-09-10] with the keys `openapi,
info, servers, paths, components, security, tags`.

## Paging a preview — [verified 2026-09-10]

Facts: `SKILL.md` § "Key Endpoints (v6.0)"

The response carries `paging.cursors.after`; pass it back as `after` until it is
absent or empty:

```python
acc, after = [], None
while True:
    p = dict(base_params, **({"after": after} if after else {}))
    pg = mcl_from_json(client.get(path="facebook/posts/preview", params=p).text)
    acc.extend(pg.get("data") or [])
    after = ((pg.get("paging") or {}).get("cursors") or {}).get("after")
    if not after:
        break
```

The client also pages by itself [verified 2026-09-10] — `has_next_page(response)`
reads the same cursor (`True` on a page with `paging.cursors.after`, `False`
on an empty result) and `query_next_page(response)` re-issues the request
with `&after=…` appended, returning the next `requests.models.Response`.
Neither exists in R, so this loop is the language-neutral shape and the pair
below is the Python shortcut:

```python
resp = client.get(path="facebook/posts/preview", params=base_params)
acc = list(mcl_from_json(resp.text).get("data") or [])
while client.has_next_page(resp):
    resp = client.query_next_page(resp)
    acc.extend(mcl_from_json(resp.text).get("data") or [])
```

On a response with no `paging`, `query_next_page()` did not raise — it
returned 200 with `data` again — so the `while` guard is what stops it.

## Nested endpoints — [documented; mirrors languages/r/query_params.md]

Facts: `SKILL.md` § "Nested Endpoints"

The parent ID goes in the **path**, not in `params` — and `post_id` is a `str`,
so the f-string renders every digit:

```python
# ✓ Correct - post_id in URL path
client.get(
    path=f"instagram/posts/{post_id}/comments/preview",
    params={"limit": 10},
)

# ✗ Wrong - post_id as parameter (the path does not exist)
client.get(
    path="instagram/comments/preview",
    params={"post_ids": [post_id]},
)
```

## Looking up a surface ID — [documented; mirrors languages/r/query_params.md]

Facts: `SKILL.md` § "Finding Surface IDs (MCL IDs ≠ Facebook/Instagram URL IDs)"

Search the entity by name and read the `id` MCL returns; never use the number
from the Facebook or Instagram URL:

```python
import pandas as pd

# GROUP -> get its MCL surface id (do NOT use the number from the group URL)
resp = client.get(
    path="facebook/groups/preview",
    params={"q": "GROUP NAME", "limit": 50},
)
groups = pd.json_normalize(mcl_from_json(resp.text)["data"])
print(groups[["id", "name", "member_count"]])   # use this `id`, not the URL number

GROUP_ID = "PASTE_MCL_ID_FROM_SEARCH"   # quoted! e.g. "963780196442228", NOT the URL's 910620404641635
```

## Integer parameters — [verified 2026-09-10]

Facts: `references/query_params.md` § "Integer Parameters"

A Python `100` is already an integer; there is no suffix and nothing to convert.
An **integral float is honoured** from Python [verified 2026-09-10]: `limit=5.0`
returned 5 rows and `limit=3.0` returned 3, on `facebook/posts/preview`. The
client's echoed request line omits the float (`?q="climate"` alone) while the
integer form shows `&limit=3`, so do not read that line as proof a parameter
was dropped. This does not match the R layer's "type mismatch" on an R double
— whether the rejection there is reticulate's marshalling, a different
parameter, or an API change is **open**; pass `int` and the question never
arises:

```python
params = {"limit": 100}     # ✓
params = {"limit": 100.0}   # accepted on 2026-09-10; still pass an int
```

## ID parameters are arrays — [documented]

Facts: `references/query_params.md` § "ID Parameters Are Arrays of Strings"

`surface_ids` / `account_ids` / `post_ids` must be sent as arrays, and that
includes a single ID. A bare `str` is a scalar and the API rejects it with
`"Invalid parameter"`; a comma-joined string is a scalar too. Always a `list`
of `str`:

```python
params["surface_ids"] = list(ids)   # ✓ a list at every length, even one
params["surface_ids"] = ids[0]      # ✗ a bare str — sent as a scalar
params["surface_ids"] = ",".join(ids)  # ✗ one string, not an array
```

The reticulate hazard the R layer describes — a length-1 vector collapsing to a
scalar — does not exist in Python: `["963780196442228"]` stays a list.

## Never pass an empty params — [verified 2026-09-10]

Facts: `references/query_params.md` § "Never Pass an Empty `params`"

The client calls `.items()` on `params`, which is how the R layer's empty
`list()` (a Python `[]`) produced `'list' object has no attribute 'items'`.
From Python, `params={}`, `params=None` and omitting `params` all succeeded
on `budgets` [verified 2026-09-10] — the rule's name is the R layer's; here it
reduces to *never pass a `list` or `tuple` as `params`*. Omit it when there
are none, for readability.

## Running an API search ID — [documented; mirrors languages/r/query_params.md]

Facts: `SKILL.md` § "API Search IDs — run a UI search from code"

The alias goes in the **path**, not in `params`:

```python
# Run the stored search synchronously
resp = client.get(path="facebook/posts/preview/2026-08-25-abcd")

# ... or as an async job
job = client.post(
    path="facebook/posts/job/2026-08-25-abcd",
    params={"mode": "SNAPSHOT",
            "name": "UI search, replayed",
            "description": "PI: …, IRB #…"},
)

# Inspect the filters an alias carries, without running it
filters = mcl_from_json(client.get(path="lists/shared-searches/2026-08-25-abcd").text)
```

## Link search without `q` — [documented; mirrors languages/r/query_params.md, verified 2026-08-29 from R]

Facts: `references/query_params.md` § "The `link` parameter"

```python
# right
client.get(path="facebook/posts/preview",
           params={"link": URL, "since": S, "until": U, "limit": 100, "fields": F})
```

## Filtering `creation_time` client-side — [documented; mirrors languages/r/query_params.md, verified 2026-08-21 from R]

Facts: `references/query_params.md` § "The `since` / `until` window is not a clean UTC day"

Request one day wider than you need, then keep only the rows whose
`creation_time` falls on the target UTC date:

```python
import pandas as pd

# want: posts created on 2026-08-20 UTC
res = ...   # query with since = "2026-08-20", until = "2026-08-21"
ct = pd.to_datetime(res["creation_time"], utc=True)
res = res[ct.dt.date == pd.Timestamp("2026-08-20").date()]
```

## Pinning `until` with an epoch second — [documented; not yet run in either language]

Facts: `references/query_params.md` § "The experiment that would close this"

`until` is integer-typed when given as a timestamp; `int()` keeps it one.

```python
from datetime import datetime, timezone

# 2026-08-24 00:00:00 UTC, exactly
until_epoch = int(datetime(2026, 8, 24, tzinfo=timezone.utc).timestamp())
params = {"since": "2026-08-17", "until": until_epoch}   # plus the rest of the query
```

## Query operators — [documented; mirrors languages/r/query_params.md]

Facts: `references/query_params.md` § "The word forms `AND` / `OR` / `NOT` are not documented operators"

```python
# ✓ union — either word
params = {"q": "climate | environment"}

# ✓ intersection — both words (a blank space IS the AND operator)
params = {"q": "climate policy"}
params = {"q": "climate&policy"}     # identical

# ✓ exclusion
params = {"q": "vaccine -covid"}

# ✓ grouping
params = {"q": "(climate | environment) (policy | legislation)"}
```

## No double-quoted phrases — [documented; mirrors languages/r/query_params.md]

Facts: `references/query_params.md` § "No Double-Quoted Phrases (subcode 3790184)"

What 3790184 rejects is a `"` character inside the query **value** — the
single-quoted Python literal `'"climate change"'` below. The double-quoted
Python string `"climate change"` is fine: no quote character reaches the API,
and the space is the AND operator.

```python
# ✗ Rejected by the API (works only in the UI)
params = {"q": '"climate change"'}

# ✓ Distinctive single token
params = {"q": "climate"}

# ✓ Tokens joined with OR
params = {"q": "climate | warming"}

# ✓ Narrow with AND instead of a phrase
params = {"q": "climate policy"}
```

## Querying a producer list — [documented; mirrors languages/r/query_params.md]

Facts: `references/query_params.md` § "Producer Lists"

`ids` is a list of `str` because it came through `mcl_from_json()`; it is sent
as an array rather than a comma-joined string.

```python
list_data = mcl_from_json(client.get(path=f"lists/producers/{list_id}").text)
ids = [p["id"] for p in list_data["producers"]]   # str, via mcl_from_json()
platform = list_data["platform"].lower()
id_param = "account_ids" if platform == "instagram" else "surface_ids"

params = {"since": "2024-01-01", "mode": "SNAPSHOT",
          "name": "Producer List Query",
          "description": "Posts from tracked accounts"}
params[id_param] = ids   # a list, not a comma-joined string

response = client.post(path=f"{platform}/posts/job", params=params)
```

## Submitting a comments job — [documented; mirrors languages/r/query_params.md]

Facts: `references/query_params.md` § "Comments Queries"

```python
response = client.post(
    path="facebook/comments/job",
    params={
        "parent_ids": list(post_ids),   # a list, even for one ID; max 250
        "fetch_all": True,              # all reply levels, not just top-level
        "mode": "SNAPSHOT",
        "name": "Comments on Target Posts",
        "description": "Comments for sentiment analysis",
    },
)
```

## Reading an estimate — [documented; mirrors languages/r/query_params.md]

Facts: `references/query_params.md` § "Estimate Response"

```python
estimate = mcl_from_json(client.get(
    path="facebook/posts/estimate",
    params={"q": "election", "since": "2024-01-01", "until": "2024-12-31"},
).text)

# Key fields:
# estimate["estimated_results"] - Approximate count
# estimate["expected_complete"] - True if <100k (will get all results)
```

Use `len()` of the result, not `estimated_results`, as the denominator of any
reported rate.

## Requesting nested fields — [documented; mirrors languages/r/query_params.md, verified 2026-08-22 from R]

Facts: `references/query_params.md` § "Field expansion: the `fields` parameter uses BRACE syntax, not dots"

```python
# CORRECT — returns id, statistics.like_count, statistics.haha_count
client.get(path="facebook/posts/preview",
           params={"q": "cybercrime",
                   "fields": "id,statistics{like_count,haha_count}"})
```

## Previewing a `fields` string before the job — [documented; mirrors languages/r/query_params.md, verified 2026-08-25 from R]

Facts: `references/query_params.md` § "`fields` works on the ASYNC JOB endpoint too"

`id_params` is the dict holding the producer IDs (`surface_ids` or
`account_ids`, as a list, as in "Querying a producer list" above); `**` splices
it into the parameter dict.

```python
FIELDS = ("id,creation_time,text,lang,surface{id,name,type},"
          "statistics{views,reaction_count,comment_count,share_count,like_count}")

# 1. FREE positive control -- confirm the projection before spending anything
pv = mcl_from_json(client.get(path="facebook/posts/preview",
                              params={"limit": 5, "fields": FIELDS, **id_params}).text)
assert "text" in pd.json_normalize(pv["data"]).columns   # the field that is NOT default

# 2. the same string on the job
job = client.post(path="facebook/posts/job",
                  params={"fields": FIELDS, "mode": "LIVE", **id_params})
```

## Chunking an ID list — [documented; mirrors languages/r/query_params.md]

Facts: `references/query_params.md` § "ID Parameter Batch Limits"

```python
chunks = [ids[i:i + 250] for i in range(0, len(ids), 250)]
for chunk in chunks:
    params = {"limit": 100}
    params["post_ids"] = list(chunk)
    # ...
```

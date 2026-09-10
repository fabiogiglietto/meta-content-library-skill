# Common errors — Python

> **Language layer: Python — [documented] unless a section is stamped `[verified DATE]`.** First run from a Python kernel in the SRE on 2026-09-10 (Step 0, Step 0b, Tests 1.1 and 10.1; no job submitted). Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Errors that only exist in Python — [verified 2026-09-10 where stamped]

Facts: `SKILL.md` § "Common Errors"

The R layer's table (`languages/r/common_errors.md` § "Errors that only exist
through reticulate") lists failures that come from R values crossing into the
Python client: the `L` suffix, the length-1 vector, the empty `list()`. None of
those exists here. These are their Python-side relatives — failures that come
from the standard library or pandas, not from the API.

| Error | Cause | Fix |
|-------|-------|-----|
| `requests.exceptions.HTTPError` | Any 4xx from the API — the message is the error JSON verbatim (`title`, `detail`, `error_subcode`, `status`) and `e.response` is the `Response` [verified 2026-09-10] | `e.response.json()["error_subcode"]` names the row in `references/common_errors.md` |
| `'list' object has no attribute 'items'` | `params` passed as a `list` or `tuple` — the client calls `.items()` on it **[inferred from the R observation]**; `{}` and `None` are accepted [verified 2026-09-10] | Pass a `dict`, or omit `params` — `languages/python/query_params.md` § "Never pass an empty params" |
| Type mismatch on an integer parameter | **Not reproduced from Python** [verified 2026-09-10]: an integral `float` `limit` was honoured | Pass `int` anyway — `languages/python/query_params.md` § "Integer parameters" |
| Invalid Meta Content Library ID (subcode 3790088) with a *correct* ID | ID held as a `float` (a pandas column that met a null), so the f-string rendered `9.6378e+14` | Parse with `mcl_from_json()`; keep IDs as `str` — `languages/python/ids.md` |
| **No error — wrong rows joined or de-duplicated** | An ID column became `float64` in `pd.concat()` (int64 + float64 → float64) and rounded above 2^53; or `astype(str)` produced `"nan"` strings that then matched each other | IDs as `str` before any concat; never `astype(str)` a float column |
| `KeyError: 'data'` | An *error* response (`title`/`detail`/`error_subcode`, no `data`) read as if it were data — an empty result does carry `"data": []` [verified 2026-09-10] | Read through `safe_get_data()` — `languages/python/jobs.md` § "Safe response handling" |
| `TypeError: 'NoneType' object is not subscriptable` | Indexing `["paging"]["cursors"]["after"]` on the last page, where `paging` is absent | The paging loop in `languages/python/query_params.md` § "Paging a preview" uses `.get()` at every level |

Wrapping a call in a loop so one failure is logged rather than fatal. The
client raises `requests.exceptions.HTTPError` on a 4xx [verified 2026-09-10] — a
scalar `surface_ids="1"` produced
`{"title":"Invalid Meta Content Library ID","detail":"The provided Meta Content
Library ID is invalid. Try searching again with a different ID.",
"error_subcode":3790088,"status":400}` as the message, with the same JSON on
`e.response.json()`:

```python
import requests

try:
    resp = client.get(path="instagram/accounts/preview", params={"q": term, "limit": 10})
    results = safe_get_data(resp.text)
except requests.exceptions.HTTPError as e:
    err = e.response.json() if e.response is not None else {}
    print("Error:", err.get("error_subcode"), err.get("title"), flush=True)
    results = None

if results is not None:
    print("Found", len(results), "results")
```

## Debugging with the OpenAPI spec — [documented; mirrors languages/r/common_errors.md]

Facts: `references/common_errors.md` § "Debugging with OpenAPI Spec"

```python
spec = client.openapi_spec()
paths = list(spec["paths"])

# Find relevant endpoints
relevant = [p for p in paths if "your_keyword" in p.lower()]
print(relevant)

# Check specific endpoint parameters
endpoint_spec = spec["paths"]["/instagram/posts/preview"]
print([p["name"] for p in endpoint_spec["get"]["parameters"]])
```

## Debugging response structure — [documented; mirrors languages/r/common_errors.md]

Facts: `references/common_errors.md` § "Debugging Response Structure"

```python
import pandas as pd

response = client.get(path="some/endpoint", params={...})

# 1. Raw JSON
print(response.text[:2000])

# 2. Parsed structure
parsed = mcl_from_json(response.text)
print("Top-level fields:", ", ".join(parsed))

# 3. Inspect each field
for fn, val in parsed.items():
    print(f"  {fn}: type={type(val).__name__}, length={len(val) if hasattr(val, '__len__') else 1}")
    if isinstance(val, list) and val and isinstance(val[0], dict):
        df = pd.json_normalize(val)
        print("    rows:", len(df), "cols:", ", ".join(df.columns))

# 4. Confirm every ID field came out as str
if isinstance(parsed.get("data"), list) and parsed["data"]:
    df = pd.json_normalize(parsed["data"])
    id_cols = [c for c in df.columns if MCL_ID_PATTERN.search(c)]
    print(df[id_cols].dtypes)          # all should be object, none float64
```

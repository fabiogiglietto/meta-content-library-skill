# ID handling — Python

> **Language layer: Python — [documented], not yet run.** Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Why Python needs a helper — [documented]

Facts: `SKILL.md` § "ID Handling (IDs Are Strings)"

`json.loads()` keeps an unquoted 17-digit ID exact — Python integers are
arbitrary precision, so the parse step that bites R does not bite here. The
hazard moves one step downstream, into pandas:

- `pd.json_normalize()` gives an ID column dtype `int64` — exact — **until a
  single `null` appears in it**, at which point pandas stores the column as
  `float64`, and every value above 2^53 is silently rounded. The same happens
  to any `int64` column that meets a `float64` one in `pd.concat()`.
- A float ID in an f-string renders as `1.784e+16`, so a path built from it is
  garbage and the API answers subcode 3790088 — the same failure the R layer
  describes, reached by a different road.
- `astype(str)` on such a column yields the string `"nan"` for missing values
  (the analogue of R's `"NA"` string), which then joins and de-duplicates as if
  it were an ID.
- `pd.read_csv()` re-infers ID columns as `int64` or, with nulls, `float64`.
- `int64` itself tops out at 9,223,372,036,854,775,807 (19 digits). MCL IDs are
  documented as up to 19 digits; whether any exceed that ceiling is **open**.

So the rule is the same as in R — **IDs are `str`, end to end** — and the
helper enforces it at parse time, before pandas ever sees a number.

## mcl_from_json — [documented; mirrors languages/r/ids.md, verified from R]

Facts: `SKILL.md` § "ID Handling (IDs Are Strings)"

Walk the parsed JSON and cast every value under an ID-shaped key to `str`.
The key pattern is the one the R helper uses, and it matches the same names:
`id`, `post_id`, `surface_ids`, `parent_id`, and the nested `author.id` /
`producer.id` (the recursion carries the inner key, so `{"author": {"id": …}}`
is caught without flattening).

```python
import json
import re

# Matches id, post_id, surface_ids, parent_id, and the nested author.id / producer.id
MCL_ID_PATTERN = re.compile(r"(^|[._])ids?$")


def mcl_fix_ids(obj, name=""):
    if isinstance(obj, dict):
        return {k: mcl_fix_ids(v, k) for k, v in obj.items()}
    if isinstance(obj, list):                        # arrays of IDs keep the parent key's name
        return [mcl_fix_ids(v, name) for v in obj]
    if MCL_ID_PATTERN.search(name) and isinstance(obj, (int, float)) and not isinstance(obj, bool):
        return f"{obj:.0f}" if isinstance(obj, float) else str(obj)   # full digits, never scientific notation
    return obj                                       # None stays None, never the string "None"


# Use this for EVERY MCL response text
def mcl_from_json(text):
    return mcl_fix_ids(json.loads(text))


# ... and for a job's saved .json file
def mcl_load_json(path):
    with open(path, encoding="utf-8") as f:
        return mcl_fix_ids(json.load(f))
```

Every example in this skill parses responses with `mcl_from_json()` instead of
a bare `json.loads()`, and saved files with `mcl_load_json()`. Building a table
afterwards is safe because the IDs are already strings:

```python
import pandas as pd

d = mcl_from_json(resp.text)
df = pd.json_normalize(d["data"])   # id, author.id, … arrive as object (str) columns
```

`json_normalize` produces the same dotted column names (`statistics.reactions`,
`author.id`) that jsonlite's `flatten = TRUE` produces in R, so the field tables
in `references/field_reference.md` read the same in both languages.

## Rules that follow — [documented]

Facts: `SKILL.md` § "ID Handling (IDs Are Strings)"

| Do | Don't |
|----|-------|
| `mcl_from_json(resp.text)` | `json.loads(resp.text)` then `pd.json_normalize(...)` on raw ints |
| `mcl_load_json("results/job.json")` | `pd.read_json("results/job.json")` — its large-integer handling is version-dependent |
| `pd.read_csv(f, dtype=str)` (or `dtype={"id": str, ...}`) | `pd.read_csv(f)` — re-infers ID columns as numbers |
| `f"instagram/posts/{post_id}/comments/preview"` with `post_id` a `str` | the same f-string with a float — renders `9.6378e+14` |
| `df["id"].astype(str)` **only** on an `int64` column with no nulls | `astype(str)` on a `float64` column — yields `"nan"` and rounded digits |
| Keep IDs as `str` in `merge()`, `drop_duplicates()`, and ID parameters | Comparing or merging on numeric IDs |
| Hard-code IDs as quoted strings: `"963780196442228"` | A bare numeric literal — exact in Python, but it will be sent and stored as a number and become a float the first time it meets a null |

`pd.set_option("display.float_format", ...)` only changes **display** — the
value is still a float and still rounds above 2^53. It is not a fix.

If an ID reaches you as a float from somewhere else (a CSV read without
`dtype=str`, a spreadsheet, a DataFrame that met a null), format it with
`f"{x:.0f}"` immediately — and treat anything at or above 2^53 as already
corrupted, since re-fetching it from MCL is the only way back.

# Producer lists — Python

> **Language layer: Python — [documented], not yet run.** Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

Every snippet parses with `mcl_from_json()` (`languages/python/ids.md`
§ "mcl_from_json") so that producer ids arrive as `str`; `safe_get_data()` is
in `languages/python/jobs.md` § "Safe response handling".

## ID parameters are arrays — [documented]

Facts: `references/producer_lists.md` § "Critical: ID Parameters Must Be Arrays"

```python
# ✓ Correct - a list, even for one ID
params[id_param] = list(ids)

# ✗ Wrong - a bare str is a scalar, and the API rejects it
params[id_param] = ids[0]
```

The reticulate hazard the R layer describes — a length-1 vector collapsing to
a string — does not exist in Python; a one-element `list` stays a list. The
API-side rule is the same: `languages/python/query_params.md` § "ID parameters
are arrays".

## Recipe: producer list from active commenters — [documented; mirrors languages/r/producer_lists.md]

Facts: `references/producer_lists.md` § "Recipe: producer list from active commenters"

`top_commenters` is one row per account, aggregated from comment records parsed
with `mcl_from_json()` (so the handle is `owner.username` and the display name
is `owner.name`).

```python
import pandas as pd

# Weights for the activity blend — tune these, don't bury them in the formula
W = {"comments": 0.4, "posts": 0.3, "reactions": 0.2, "days": 0.1}

producers = top_commenters.copy()

# 1. Keep only public accounts: both a display name and a username.
#    No username -> no URL -> cannot be imported.
producers = producers[
    producers["owner.username"].fillna("").str.strip().ne("")
    & producers["owner.name"].fillna("").str.strip().ne("")
]

# 2. Safety net in case the upstream table isn't already one row per account —
#    duplicates would silently burn slots against the 1,000 cap
producers["username"] = producers["owner.username"].str.strip().str.lower()
producers = producers.drop_duplicates("username", keep="first")

# 3. Score activity as a weighted blend of percentile ranks, so no single
#    heavy-tailed metric dominates
pct = lambda s: s.rank(pct=True)
producers["activity_score"] = (
    W["comments"]  * pct(producers["n_comments"])
    + W["posts"]     * pct(producers["n_distinct_posts"])
    + W["reactions"] * pct(producers["n_reactions"])
    + W["days"]      * pct(producers["n_active_days"])
)

# 4. Keep the top quartile, then cap at the 1,000-producer import limit
cut = producers["activity_score"].quantile(0.75)
producers = producers[producers["activity_score"] >= cut].sort_values("activity_score", ascending=False)

if len(producers) > 1000:
    print("Top quartile has", len(producers), "accounts - dropping",
          len(producers) - 1000, "below the 1,000 import cap", flush=True)
producers = producers.head(1000)

# 5. Write the one-column import file (literal header, space and capitals)
(pd.DataFrame({"Producer URL": "https://www.facebook.com/" + producers["owner.username"]})
   .to_csv("producer_import.csv", index=False))   # index=False: no row-number column
```

`index=False` matters: the default writes a row-number column, which would
make the file two-column and break the import. `rank(pct=True)` is pandas'
percentile rank; it ranks ties by average, where R's `percent_rank()` ranks
them by minimum, so the two layers can differ at the quartile boundary.

## List all producer lists — [documented; mirrors languages/r/producer_lists.md]

Facts: `references/producer_lists.md` § "List All Producer Lists"

```python
from metacontentlibraryapi import MetaContentLibraryAPIClient as client

client.set_default_version(client.LATEST_VERSION)

lists = mcl_from_json(client.get(path="lists/producers").text)

# View available lists
print(lists)
```

## Resolving a list by name — [documented; mirrors languages/r/producer_lists.md, verified 2026-08-21 from R]

Facts: `references/producer_lists.md` § "Resolving a list by name — names are NOT unique"

```python
import pandas as pd

ll = mcl_from_json(client.get(path="lists/producers").text)
d = pd.json_normalize(ll["data"] if isinstance(ll, dict) and "data" in ll else ll)
hit = d[d["name"].str.strip().str.lower() == TARGET_NAME.lower()]
assert len(hit) == 1          # 2 matches is a real, observed case
list_id = hit["id"].iloc[0]
```

`assert len(hit) == 1` is the guard the neutral file calls "necessary but not
sufficient": when it fails on two or three ids, follow the tie-break procedure
there (fetch each candidate, compare producer-id sets).

## Get producer list details — [documented; mirrors languages/r/producer_lists.md]

Facts: `references/producer_lists.md` § "Get Producer List Details"

The `producers` payload is a list of objects with `id`, `name`, `type` — not a
bare list of IDs.

```python
import pandas as pd

list_id = "2026-03-29-bqtm"

list_data = mcl_from_json(client.get(path=f"lists/producers/{list_id}").text)

# Response structure:
# list_data["id"]        - str: list ID
# list_data["name"]      - str: list name
# list_data["platform"]  - str: "facebook" or "instagram"
# list_data["producers"] - list of {"id", "name", "type"}

print("List name:", list_data["name"])
print("Platform:", list_data["platform"])
print("Producer count:", len(list_data["producers"]))

# The producers as a table
producers = pd.DataFrame(list_data["producers"])
producers.head()
#          id                    name   type
# 0 252084...  DICO NO All'unione...   page
# 1 250547...     Emanuele Tesauro     page
# 2 249073...        Mauro Fagiolo  profile

# Just the IDs as a list (str, thanks to mcl_from_json)
ids = producers["id"].tolist()
assert all(isinstance(i, str) for i in ids)   # an int here means json.loads was used raw
```

`len(list_data["producers"])` is the count to size batching arithmetic from,
not the UI's figure.

## Auto-detect platform pattern — [documented; mirrors languages/r/producer_lists.md]

Facts: `references/producer_lists.md` § "Auto-Detect Platform Pattern"

```python
# Get list metadata first
list_data = mcl_from_json(client.get(path=f"lists/producers/{list_id}").text)
platform = list_data["platform"].lower()
ids = [p["id"] for p in list_data["producers"]]  # Note: producers[].id, not a top-level ids

# Build correct parameter name
id_param = "account_ids" if platform == "instagram" else "surface_ids"

# Build parameters
params = {
    "since": "2024-01-01",
    "until": "2024-12-31",
    "limit": 100,
    "mode": "SNAPSHOT",
    "name": "Posts from Producer List",
    "description": "Researcher: X, IRB: Y",
}
params[id_param] = list(ids)   # a list, not a comma-joined string

# Submit job
response = client.post(path=f"{platform}/posts/job", params=params)
job_data = mcl_from_json(response.text)
job_id = job_data["id"]
```

## Batching large producer lists — [documented; mirrors languages/r/producer_lists.md]

Facts: `references/producer_lists.md` § "Batching Large Producer Lists"

`batch_ids()` is defined here and reused by the metadata sections below.

```python
import time


def batch_ids(ids, batch_size=50):
    ids = list(ids)
    return [ids[i:i + batch_size] for i in range(0, len(ids), batch_size)]


# Process each batch
batches = batch_ids(ids, batch_size=50)
all_job_ids = []

for i, batch in enumerate(batches, start=1):
    print("Batch", i, "of", len(batches), "-", len(batch), "IDs", flush=True)

    params = {
        "since": "2024-01-01",
        "until": "2024-12-31",
        "limit": 100,
        "mode": "SNAPSHOT",
        "name": f"Batch {i} of {len(batches)}",
        "description": "Batched producer list query",
    }
    params[id_param] = list(batch)   # a list, even if the batch has 1 ID

    response = client.post(path=f"{platform}/posts/job", params=params)
    job_data = mcl_from_json(response.text)
    all_job_ids.append(job_data["id"])

    # Rate limit: 1 async query per minute
    if i < len(batches):
        print("Waiting 60s for rate limit...", flush=True)
        time.sleep(60)
```

## Instagram account metadata — [documented; mirrors languages/r/producer_lists.md]

Facts: `references/producer_lists.md` § "Instagram Accounts"

```python
# Batch IDs (max ~50 per query for reliability)
id_batches = batch_ids(ids, batch_size=50)

for batch in id_batches:
    params = {
        "account_ids": list(batch),
        "limit": 100,
    }

    response = client.get(path="instagram/accounts/preview", params=params)
    # Process results...
```

## Facebook page metadata — [documented; mirrors languages/r/producer_lists.md]

Facts: `references/producer_lists.md` § "Facebook Pages"

```python
for batch in id_batches:
    params = {
        "surface_ids": list(batch),
        "limit": 100,
    }

    response = client.get(path="facebook/pages/preview", params=params)
    # Process results...
```

## Cross-platform account matching — [documented; mirrors languages/r/producer_lists.md]

Facts: `references/producer_lists.md` § "Cross-Platform Account Matching"

Jaro–Winkler needs a third-party package — `rapidfuzz` or `jellyfish`. Whether
either is on the SRE's pip mirror is **open**; install with the Pip channel
(`languages/python/utilities.md` § "Installing packages"). The recipe below
uses `jellyfish.jaro_winkler_similarity`.

```python
import re
import time
import pandas as pd
import jellyfish  # Install via: Pip.get_instance().install("jellyfish")

# 1. Get FB producers (names already included in response)
list_data = mcl_from_json(client.get(path=f"lists/producers/{list_id}").text)
fb_producers = pd.DataFrame(list_data["producers"])

# 2. Search IG accounts for each FB name
ig_candidates = []
for i, row in enumerate(fb_producers.itertuples(index=False), start=1):
    term = re.sub(r"[^\w\s]", " ", row.name)
    term = re.sub(r"\s+", " ", term).strip()
    if len(term) < 3:
        continue

    print(f"[{i}/{len(fb_producers)}] Searching IG for: '{term}'", flush=True)

    try:
        results = safe_get_data(client.get(
            path="instagram/accounts/preview",
            params={"q": term, "limit": 10},
        ).text)
    except Exception as e:          # narrow this once the client's exception class is known
        print("  Error:", e)
        results = None

    if results is not None:
        results["fb_source_id"] = row.id
        results["fb_source_name"] = row.name
        ig_candidates.append(results)

    time.sleep(1.5)  # Sync rate limit

# 3. Score by name similarity (Jaro-Winkler)
ig_all = pd.concat(ig_candidates, ignore_index=True)
jw = jellyfish.jaro_winkler_similarity
ig_all["name_sim"] = [jw(str(a).lower(), str(b).lower()) for a, b in zip(ig_all["name"], ig_all["fb_source_name"])]
ig_all["user_sim"] = [jw(str(a).lower(), re.sub(r"[^A-Za-z0-9]", "", str(b)).lower())
                      for a, b in zip(ig_all["username"], ig_all["fb_source_name"])]
ig_all["best_sim"] = ig_all[["name_sim", "user_sim"]].max(axis=1)
scored = ig_all.drop_duplicates("id", keep="first").copy()
scored["tier"] = pd.cut(scored["best_sim"],
                        bins=[-1, 0.60, 0.75, 0.90, 1.01],
                        labels=["REVIEW", "LOW", "MEDIUM", "HIGH"],
                        right=False)
scored = scored.sort_values("best_sim", ascending=False)
```

`pd.concat()` on `ig_candidates` keeps `id` as `str` because every batch was
parsed with `mcl_from_json()`; had any batch carried numeric IDs, the whole
column would silently turn `float64`.

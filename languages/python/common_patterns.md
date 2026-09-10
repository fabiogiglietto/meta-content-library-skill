# Common analysis patterns — Python

> **Language layer: Python — [documented] unless a section is stamped `[verified DATE]`.** First run from a Python kernel in the SRE on 2026-09-10 (Step 0, Step 0b, Tests 1.1 and 10.1; no job submitted). Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

Recipes are pandas, with matplotlib for the plots. Every result set is assumed
loaded with `mcl_load_json()` / `mcl_from_json()` (`languages/python/ids.md`
§ "mcl_from_json") and normalised with `pd.json_normalize()`, so field names
are the dotted ones (`statistics.reactions`) — the same names the R layer's
`flatten = TRUE` produces — and ID columns are `str`. `creation_time` is
parsed once, up front:

```python
import pandas as pd

posts["creation_time"] = pd.to_datetime(posts["creation_time"], utc=True)
```

## Combining results with mismatched columns — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Combining Results with Mismatched Columns"

`pd.concat()` aligns columns by name and fills the gaps with `NaN`, so the R
layer's `rbind()` failure has no Python counterpart. The hazard that remains
is dtype: a numeric `id` in one batch turns the whole column `float64`.

```python
import os
import pandas as pd

# Collect multiple job results
all_results = []

for job_id in job_ids:
    job = client.get_async_job(job_id=job_id)

    mcl_wait_for_job(job)   # SKILL.md § "Waiting for a Job"; never compare status
                            # case-sensitively, and never treat an unknown status
                            # as "done"

    job.write_data_to_file(directory="results", filename=f"{job_id}.json")
    result = pd.json_normalize(mcl_load_json(os.path.join("results", f"{job_id}.json")))
    all_results.append(result)

# ✓ Handles different columns gracefully — missing ones become NaN
combined = pd.concat(all_results, ignore_index=True)
```

`mcl_wait_for_job()` is in `languages/python/jobs.md` § "Waiting for a job".

**pd.concat() behavior:**
- Fills missing columns with `NaN`
- Preserves all columns from all DataFrames
- Silently promotes a column to `float64` if any batch holds it as a number —
  which is why every batch goes through `mcl_load_json()` first

## ID hygiene in analysis — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "ID Hygiene in Analysis"

```python
# Joins and dedup — string keys only
combined = pd.concat(all_results, ignore_index=True).drop_duplicates("id", keep="first")

posts_with_meta = posts.merge(accounts, left_on="post_owner.id", right_on="id",
                              how="left", suffixes=("", "_account"))   # both str, or the join silently misses

# Round-tripping through CSV: force str on read
posts.to_csv("posts.csv", index=False)
posts = pd.read_csv("posts.csv", dtype=str)
# or per column: dtype={"id": str, "post_owner.id": str}

# ✗ Never do this - re-introduces the float
posts["id"] = pd.to_numeric(posts["id"])

# Sanity check before any join/dedup/export
# (list columns hold lists of IDs, already fixed element-wise by mcl_fix_ids;
#  boolean flags such as is_invalid_id are left alone by design)
id_cols = [c for c in posts.columns if MCL_ID_PATTERN.search(c)]
assert not any(pd.api.types.is_numeric_dtype(posts[c]) and posts[c].dtype != bool for c in id_cols)
```

`MCL_ID_PATTERN` and `mcl_fix_ids()` come from `languages/python/ids.md`
§ "mcl_from_json". Parquet and pickle preserve the `str` dtype; CSV does not,
so prefer `to_parquet()` (needs `pyarrow` — availability in the SRE is
**open**) or `to_pickle()` for intermediate artifacts that contain IDs.

## Daily post volume — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Daily Post Volume"

```python
import matplotlib.pyplot as plt

daily_volume = (posts.assign(date=posts["creation_time"].dt.date)
                     .groupby("date").size().rename("n_posts").reset_index())

# Plot
ax = daily_volume.plot(x="date", y="n_posts", legend=False)
daily_volume.set_index("date")["n_posts"].rolling(7, center=True).mean().plot(ax=ax, color="blue")
ax.set(title="Daily Post Volume", xlabel="Date", ylabel="Number of Posts")
plt.show()
```

## Hourly patterns — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Hourly Patterns"

```python
hourly_pattern = (posts["creation_time"].dt.hour.value_counts().sort_index()
                       .rename("n").reset_index().rename(columns={"index": "hour", "creation_time": "hour"}))
hourly_pattern["pct"] = hourly_pattern["n"] / hourly_pattern["n"].sum() * 100

ax = hourly_pattern.plot.bar(x="hour", y="pct", color="steelblue", legend=False)
ax.set(title="Posting Activity by Hour (UTC)", xlabel="Hour", ylabel="% of Posts")
plt.show()
```

## Rolling averages — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Rolling Averages"

```python
rolling_engagement = (posts.assign(date=posts["creation_time"].dt.date)
                           .groupby("date")["statistics.reactions"].sum()
                           .rename("total_reactions").sort_index().to_frame())
rolling_engagement["rolling_7d"] = rolling_engagement["total_reactions"].rolling(7).mean()
```

## Basic engagement metrics — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Basic Engagement Metrics"

```python
engagement_summary = pd.Series({
    "n_posts": len(posts),
    "total_reactions": posts["statistics.reactions"].sum(),
    "total_comments": posts["statistics.comments"].sum(),
    "total_shares": posts["statistics.shares"].sum(),
    "total_views": posts["statistics.views"].sum(),
    "avg_reactions": posts["statistics.reactions"].mean(),
    "median_reactions": posts["statistics.reactions"].median(),
})
```

## Engagement by account type — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Engagement by Account Type"

```python
engagement_by_type = (posts.groupby("post_owner.type")     # page, group, event, profile
                           .agg(n_posts=("id", "size"),
                                avg_reactions=("statistics.reactions", "mean"),
                                avg_shares=("statistics.shares", "mean"),
                                total_reach=("statistics.views", "sum"))
                           .sort_values("total_reach", ascending=False)
                           .reset_index())
```

## Top performing content — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Top Performing Content"

```python
top_posts = (posts.assign(engagement_score=posts["statistics.reactions"]
                                           + posts["statistics.comments"] * 2
                                           + posts["statistics.shares"] * 3)
                  .sort_values("engagement_score", ascending=False)
                  .head(100)[["id", "post_owner.name", "engagement_score", "creation_time"]])

# Note: Cannot export actual post text
```

## Engagement distribution — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Engagement Distribution"

```python
engagement_dist = (pd.cut(posts["statistics.reactions"],
                          bins=[0, 10, 100, 1000, 10000, float("inf")],
                          labels=["0-10", "11-100", "101-1K", "1K-10K", "10K+"],
                          include_lowest=True)
                     .value_counts().sort_index().rename("n").reset_index())
engagement_dist["pct"] = engagement_dist["n"] / engagement_dist["n"].sum() * 100
```

## Language distribution — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Language Distribution"

```python
language_dist = posts["lang"].value_counts().rename("n").reset_index()
language_dist["pct"] = language_dist["n"] / language_dist["n"].sum() * 100
language_dist = language_dist.head(10)
```

## Media type analysis — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Media Type Analysis"

```python
media_analysis = posts["media_type"].value_counts().rename("n").reset_index()
media_analysis["pct"] = media_analysis["n"] / media_analysis["n"].sum() * 100

# Engagement by media type
media_engagement = (posts.groupby("media_type")
                         .agg(n=("id", "size"),
                              avg_reactions=("statistics.reactions", "mean"),
                              avg_views=("statistics.views", "mean"))
                         .reset_index())
```

## Hashtag extraction (Instagram) — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Hashtag Extraction (Instagram)"

`extract_hashtags()` is defined here.

```python
import re

HASHTAG = re.compile(r"#\w+")


# Instagram post text is in `caption`; Facebook post text is in `text`
def extract_hashtags(text):
    if not isinstance(text, str):
        return []
    return HASHTAG.findall(text)


hashtag_counts = (posts["caption"].map(extract_hashtags).explode().dropna()
                       .value_counts().rename("n").reset_index().head(50))
```

## Cross-posting (reshares) — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Cross-Posting (Reshares)"

```python
reshares = posts[posts["shared_post_id"].notna()]

crossposts = (reshares.groupby(["post_owner.id", "shared_post_id"]).size()
                      .rename("n").sort_values(ascending=False).reset_index())

# Accounts that appear as resharers
resharer_activity = (reshares.groupby(["post_owner.id", "post_owner.name"]).size()
                             .rename("n_reshares").sort_values(ascending=False).reset_index())
```

## Reply networks from comments — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Reply Networks from Comments"

```python
has_parent = comments["parent_id"].notna() & comments["parent_id"].astype(str).str.len().gt(0)
edges = comments.loc[has_parent, ["owner.id", "parent_id"]].rename(columns={"owner.id": "from", "parent_id": "to"})
```

## Comparative analysis — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Comparative Analysis"

```python
# posts_a, posts_b: two result sets already loaded with mcl_load_json()
both = pd.concat([posts_a.assign(group="renewable energy"),
                  posts_b.assign(group="fossil fuels")], ignore_index=True)
both["engagement"] = both["statistics.reactions"] + both["statistics.shares"]

comparison = (both.groupby("group")
                  .agg(n_posts=("id", "size"),
                       n_accounts=("post_owner.id", "nunique"),
                       total_engagement=("engagement", "sum"),
                       avg_engagement=("engagement", "mean"))
                  .reset_index())
```

## Aggregate statistics (exportable) — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Aggregate Statistics (Exportable)"

```python
# These aggregate outputs can typically be exported
exportable_summary = (posts.assign(date=posts["creation_time"].dt.date)
                           .groupby("date")
                           .agg(n_posts=("id", "size"),
                                n_unique_accounts=("post_owner.id", "nunique"),
                                total_reactions=("statistics.reactions", "sum"),
                                total_shares=("statistics.shares", "sum"),
                                avg_reactions=("statistics.reactions", "mean"))
                           .reset_index())

# Save for export request
exportable_summary.to_csv("aggregate_daily_stats.csv", index=False)
```

## Export-ready visualizations — [documented; mirrors languages/r/common_patterns.md]

Facts: `references/common_patterns.md` § "Create Export-Ready Visualizations"

```python
import matplotlib.pyplot as plt

# Save plots as PNG (can be exported after review)
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(exportable_summary["date"], exportable_summary["n_posts"])
ax.set(title="Daily Post Volume", xlabel="Date", ylabel="Posts")
fig.savefig("daily_volume_chart.png", dpi=300, bbox_inches="tight")
```

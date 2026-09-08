# Common Analysis Patterns

> All examples parse responses with the language helper — `languages/r/ids.md`
> § "mcl_fromJSON" / `languages/python/ids.md` § "mcl_from_json" — which keeps
> every ID field a string. A parser that types IDs as floats corrupts them.

This file covers what you do with results **after** they are collected. For
collecting them, see SKILL.md § "Async Query Template" (single query) and
`references/chunking.md` (date windows, batching, combining chunks).

Field names below are the **flattened** dotted names that both language layers
produce (jsonlite `flatten = TRUE`, pandas `json_normalize`), so engagement
counts are written `statistics.reactions`, not as a nested object. See
`references/field_reference.md` for the field tables and the names a live
response actually returns.

## Table of Contents
1. [Combining and Cleaning Results](#combining-and-cleaning-results)
2. [Time Series Analysis](#time-series-analysis)
3. [Engagement Analysis](#engagement-analysis)
4. [Content Analysis](#content-analysis)
5. [Network Analysis](#network-analysis)
6. [Comparative Analysis](#comparative-analysis)
7. [Export Preparation](#export-preparation)

## Combining and Cleaning Results

### Combining Results with Mismatched Columns

When combining multiple job results (e.g. from batched or chunked queries),
concatenate by **column name**, not by position: different batches may return
different optional fields depending on content type, so a positional row-bind
fails with a column-count mismatch. A name-aware concatenation fills the missing
columns with nulls and preserves every column from every batch.

**Type mismatch, not just column mismatch:** a name-aware concatenation still
refuses to combine the same column when its *type* differs across batches — an
`id` that is a string in one batch and a number in the next. That is exactly
what a parser that only converts IDs above 2^53 produces, batch by batch. The
ID-safe helpers coerce every ID field unconditionally, so all batches agree.

The loop itself is: for each job id, wait for the job (SKILL.md § "Waiting for a
Job" — never compare status case-sensitively, and never treat an unknown status
as "done"), write its data to a file, parse the file with the ID-safe helper,
and collect the tables; then concatenate by name.

Code: `languages/r/common_patterns.md` § "Combining results with mismatched columns" · `languages/python/common_patterns.md` § "Combining results with mismatched columns"

### ID Hygiene in Analysis

Once loaded as strings, keep IDs that way through the whole pipeline:

- **Joins and de-duplication on string keys only.** Joining a string key to a
  numeric one silently misses every row.
- **Round-tripping through CSV**: CSV does not carry types, so a re-read guesses
  ID columns as numeric. Force every ID column to string on read.
- **Never coerce an ID column to numeric** — it re-introduces the float.
- **Sanity-check before any join, dedup or export** that no ID-named column
  (`id`, `post_id`, `post_owner.id`, `surface_ids`, …) is numeric. List-valued
  ID columns hold vectors of strings, already fixed element-wise by the helper;
  logical flags such as `is_invalid_id` are left alone by design.

Opening a CSV of IDs in Excel converts them to scientific notation on sight.
Prefer a typed format (Parquet, or the language's native serialization) for
intermediate artifacts that contain IDs.

Code: `languages/r/common_patterns.md` § "ID hygiene in analysis" · `languages/python/common_patterns.md` § "ID hygiene in analysis"

## Time Series Analysis

### Daily Post Volume

Count posts per calendar day of `creation_time` (UTC), then plot the daily count
as a line with a loess smoother over it.

Code: `languages/r/common_patterns.md` § "Daily post volume" · `languages/python/common_patterns.md` § "Daily post volume"

### Hourly Patterns

Count posts by hour of `creation_time` (0–23, **UTC** — the API does not
localise timestamps) and express each hour as a percentage of all posts; plot as
a bar chart with one bar per hour.

Code: `languages/r/common_patterns.md` § "Hourly patterns" · `languages/python/common_patterns.md` § "Hourly patterns"

### Rolling Averages

Sum `statistics.reactions` per day, order by date, and take a 7-day trailing
(right-aligned) mean; the first six days have no value.

Code: `languages/r/common_patterns.md` § "Rolling averages" · `languages/python/common_patterns.md` § "Rolling averages"

## Engagement Analysis

### Basic Engagement Metrics

One summary row over the corpus: post count; totals of `statistics.reactions`,
`statistics.comments`, `statistics.shares`, `statistics.views`; mean and median
reactions. Missing values are skipped, not treated as zero — `views` is absent
on non-video posts (`references/field_reference.md` § "Engagement Statistics").

Code: `languages/r/common_patterns.md` § "Basic engagement metrics" · `languages/python/common_patterns.md` § "Basic engagement metrics"

### Engagement by Account Type

Group by `post_owner.type` (page, group, event, profile) and summarise post
count, mean reactions, mean shares and total views ("reach"); sort by total
views descending.

For Instagram posts the equivalent grouping column is `producer_type`
(business / creator) — see `references/field_reference.md`.

Code: `languages/r/common_patterns.md` § "Engagement by account type" · `languages/python/common_patterns.md` § "Engagement by account type"

### Top Performing Content

Engagement score = reactions + 2 × comments + 3 × shares. Rank descending, keep
the top 100, and carry only `id`, `post_owner.name`, the score and
`creation_time`.

Note: the actual post text cannot be exported, so a top-posts table is an
in-enclave view, not a deliverable.

Code: `languages/r/common_patterns.md` § "Top performing content" · `languages/python/common_patterns.md` § "Top performing content"

### Engagement Distribution

Bucket `statistics.reactions` into 0–10, 11–100, 101–1K, 1K–10K, 10K+ (lowest
bound inclusive) and report the share of posts in each bucket.

Code: `languages/r/common_patterns.md` § "Engagement distribution" · `languages/python/common_patterns.md` § "Engagement distribution"

## Content Analysis

### Language Distribution

Count posts by the detected post language `lang` (ISO 639-1), as a percentage of
all posts; the top 10 is usually enough.

Code: `languages/r/common_patterns.md` § "Language distribution" · `languages/python/common_patterns.md` § "Language distribution"

### Media Type Analysis

Share of posts by `media_type`, and per media type the post count, mean
reactions and mean views.

Code: `languages/r/common_patterns.md` § "Media type analysis" · `languages/python/common_patterns.md` § "Media type analysis"

### Hashtag Extraction (Instagram)

Extract every `#\w+` token from the post text, one row per hashtag, and count
the top 50. Instagram posts also carry a documented `hashtags` list field, with
no Facebook equivalent (`references/field_reference.md` § "Instagram Posts").

Code: `languages/r/common_patterns.md` § "Hashtag extraction (Instagram)" · `languages/python/common_patterns.md` § "Hashtag extraction (Instagram)"

## Network Analysis

### Cross-Posting (Reshares)

A reshare carries `shared_post_id` — the ID of the original post — but no field
for the original *account*. Count reshare relationships directly, or resolve the
originals first via `post_ids` (see `references/field_reference.md` § "Reshares").
Two counts: (resharer `post_owner.id`, `shared_post_id`) pairs, i.e. who reshared
what; and reshares per resharer account (`post_owner.id`, `post_owner.name`).

Code: `languages/r/common_patterns.md` § "Cross-posting (reshares)" · `languages/python/common_patterns.md` § "Cross-posting (reshares)"

### Reply Networks from Comments

Comment records name the commenter under `owner.*`, and a reply carries
`parent_id` = the comment it answers, so the edge list is `from = owner.id`,
`to = parent_id` over comments whose `parent_id` is non-empty.

A post-keyed comments pull returns **top-level comments only**, whose `parent_id`
is empty — so that filter is empty until you fetch the replies in a second
pull keyed on comment IDs. See `references/field_reference.md` § "Replies: one
job with `fetch_all`, or a second pull".

Code: `languages/r/common_patterns.md` § "Reply networks from comments" · `languages/python/common_patterns.md` § "Reply networks from comments"

## Comparative Analysis

Compare corpora by collecting each one separately (one query per topic or
platform, per SKILL.md § "Async Query Template"), then labelling each result set
with a `group` column, concatenating, and summarising per group: post count,
distinct `post_owner.id`, total and mean engagement (reactions + shares).

The same shape works across platforms — label with `platform` instead of `group`.
Compare only fields both platforms have: Facebook posts report
`statistics.reactions`, Instagram posts report `statistics.likes`, so rename to a
common column before combining rather than assuming they align.

Code: `languages/r/common_patterns.md` § "Comparative analysis" · `languages/python/common_patterns.md` § "Comparative analysis"

## Export Preparation

### Aggregate Statistics (Exportable)

Aggregate outputs can typically be exported. The daily summary is: per day of
`creation_time`, post count, distinct `post_owner.id`, total reactions, total
shares, mean reactions — written to a CSV (e.g. `aggregate_daily_stats.csv`) for
the export request.

Code: `languages/r/common_patterns.md` § "Aggregate statistics (exportable)" · `languages/python/common_patterns.md` § "Aggregate statistics (exportable)"

### Create Export-Ready Visualizations

Save plots as PNG (300 dpi, e.g. 10 × 6 in) — image files can be exported after
review.

Code: `languages/r/common_patterns.md` § "Export-ready visualizations" · `languages/python/common_patterns.md` § "Export-ready visualizations"

### What Cannot Be Exported

Do not attempt to export:

- Raw post text/content
- Individual user IDs
- Personal information
- Full post URLs
- Raw data files

These will be rejected during disclosure review.

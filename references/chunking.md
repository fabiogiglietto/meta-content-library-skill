# Handling Large Datasets (Chunking)

When `expected_complete = FALSE`, split queries to avoid truncation.

> **The ~100,000-result cap is per query.** A single async query returns at most
> ~100,000 results. Depending on the endpoint this shows up either as silent
> truncation (`expected_complete = FALSE` on the estimate) or as a hard failure
> with `error_subcode 3790057` ("Estimated response size too large"). When
> `estimated_results` exceeds ~100k, split by **date** into smaller windows —
> and/or query fewer `surface_ids` per call — so each query stays under the cap.

> **Parse every chunk with the language's ID-safe helper** —
> `languages/r/ids.md` § "mcl_fromJSON" / `languages/python/ids.md`
> § "mcl_from_json". Chunking is where a raw parse bites hardest: one chunk may
> hold an ID above 2^53 and another not, so the ID column comes out with a
> different type per chunk, concatenation fails or silently coerces, and
> de-duplication on rounded IDs collides. With IDs as strings in every chunk,
> the columns always match.

## Automatic Date Chunking

One function does the whole loop:

1. Split `[start_date, end_date]` into consecutive windows of `chunk_size`
   days (the last one shorter).
2. For each window, call `{platform}/{content_type}/estimate` with the same
   `q`, `since`, `until`; if `expected_complete` is not true, warn that the
   chunk still exceeds the cap and needs a smaller `chunk_size`.
3. Submit `{platform}/{content_type}/job` for the window with
   `mode = "SNAPSHOT"`, a `name` that carries the window, and a `description`
   that carries the chunk index ("Chunk i of N").
4. Keep the job `id` (a string) per chunk.
5. **Sleep 60 seconds between submissions** — async queries are limited to one
   per minute (`SKILL.md` § "Rate Limits & Budget").

It returns the list of job ids in window order.

Code: `languages/r/chunking.md` § "Automatic date chunking" · `languages/python/chunking.md` § "Automatic date chunking"

## Combining Chunked Results

For each job id, in order: fetch the job with `get_async_job`, wait with the
language's wait helper (a bare status comparison is unsafe — `SKILL.md`
§ "Waiting for a Job"), write the results to one file per chunk
(`chunk_{i}_{job_id}.json`), load that file with the ID-safe helper, tag every
row with its source chunk index and job id, and collect. Then concatenate,
**assert the `id` column is still a string** before de-duplicating on it, drop
duplicate `id`s (posts at a window boundary can appear in two chunks), report
the before/after count, and save the combined table.

Code: `languages/r/chunking.md` § "Combining chunked results" · `languages/python/chunking.md` § "Combining chunked results"

## Chunk Size Guidelines

| Estimated Results | Recommended Chunk |
|-------------------|-------------------|
| < 100,000 | No chunking needed |
| 100k - 500k | Quarterly (90 days) |
| 500k - 1M | Monthly (30 days) |
| > 1M | Weekly (7 days) or add filters |

ID batch size is a separate limit — a query can need chunking on both axes: date
windows for the result cap, ID batches for the parameter cap. See
`references/query_params.md` § "ID Parameter Batch Limits".

## Collecting Only the Latest N Results

When you want the most recent N posts rather than the full history, iterate date
windows **newest-first** and stop once N is reached — this avoids paying for
older windows you'd discard, and keeps every query under the cap:

- Start with `until` at the newest date of interest and a window of
  `window_days` (7 by default); `since` is `until − window_days`.
- Submit each window as a **LIVE** job (exploration; no snapshot slot spent)
  with `limit = 100`, a name carrying the window index, and the fixed base
  parameters.
- Append the window's rows, count, and stop when the running total reaches
  `n_target`; otherwise slide `until` back to the previous `since`. Cap the
  loop at `max_windows` (52 by default) so an empty range cannot run forever.
- Sort the pooled rows by `creation_time` descending and keep the first
  `n_target`.

Code: `languages/r/chunking.md` § "Collecting only the latest N results" · `languages/python/chunking.md` § "Collecting only the latest N results"

# Collections and Query Management

> Parse every response with the language helper — `languages/r/ids.md` §
> "mcl_fromJSON" / `languages/python/ids.md` § "mcl_from_json" — so that every
> ID field stays a string (SKILL.md § "ID Handling (IDs Are Strings)").

## Collections (Folders)

A collection is a folder for queries. Four calls manage them:

| Action | Call |
|---|---|
| Create | `POST async/collections`, body `name` + `description`; the response carries the new `id` |
| Set as default | `POST async/collections/{collection_id}`, body `default = true` — new queries are auto-added to the default collection |
| List | `GET async/collections` |
| Delete | `DELETE async/collections/{collection_id}` — the queries it held remain |

Code: `languages/r/collections.md` § "Managing collections" · `languages/python/collections.md` § "Managing collections"

## Query Management

| Action | Call |
|---|---|
| List all queries | `GET async/queries` |
| One query, with all its jobs | `GET async/queries/{query_id}` |
| Update metadata | `POST async/queries/{query_id}`, body `name` / `description` (e.g. append `PUBLISHED` and a DOI once the paper is out) |
| Move to a collection | `POST async/queries/{query_id}`, body `collection_id` |
| Make public, for sharing | `POST async/queries/{query_id}`, body `visibility = "PUBLIC"` |
| Delete | `DELETE async/queries/{query_id}` — **deletes all of its jobs too** |

Code: `languages/r/collections.md` § "Managing queries" · `languages/python/collections.md` § "Managing queries"

## Job Management

`GET async/jobs` lists every job; **the payload is under the `jobs` key, not
`data`** (see the warning below). Each row carries `id`, `creation_time`,
`update_time`, `status`, `mode`, `query_id`.

`GET async/jobs/{job_id}` returns one job's metadata: `id`, `status`, `mode`,
`query_id`, `creation_time`.

Code: `languages/r/collections.md` § "Listing jobs" · `languages/python/collections.md` § "Listing jobs"

### ⚠ The `async/jobs` envelope key is `jobs`, not `data` — [verified 2026-08-24]

Most list-shaped responses in this API wrap their payload in `data`, so the common
defensive idiom is "take `data` if present, otherwise the whole response".

Against `async/jobs` that idiom **falls through silently**: `data` is absent, so
the fallback is the whole envelope, its `mode` is null, and any summary computed
from it is wrong *without erroring*. On 2026-08-24 this reported `0 of 100
snapshot slots used` on an account with 434 jobs; the true figure was 5. A wrong
number that looks plausible is worse than a failure, and the only thing that
caught it was probing the response shape rather than trusting the idiom.

```
class(jl):  list          names(jl):  jobs
jl$jobs:    'data.frame': 434 obs. of 6 variables
```

Two further properties of the listing:

- **`creation_time` and `update_time` are integer epoch seconds here**, not the ISO-8601
  strings `creation_time` carries on a *post* record. Same field name, different type,
  different endpoint.
- **There is no `name` column.** The `name` supplied at submission is not readable back
  from the job listing, so **jobs cannot be identified by name from this endpoint** —
  which matters if you are trying to detect an already-submitted duplicate. That lives
  on the query (`async/queries`), which was returning **502** on the same date; see
  `../docs/OPEN_QUESTION_ASYNC_QUERIES_502.md`.

Counting SNAPSHOT slots against the 100-concurrent cap correctly means reading
`jobs` explicitly and counting rows with `mode == "SNAPSHOT"` and `status !=
"FAILED"`. The same section shows the two per-job calls: `POST
async/jobs/{job_id}/snapshot` converts a LIVE job to SNAPSHOT (preserving its
data) and `DELETE async/jobs/{job_id}` deletes a job.

Code: `languages/r/collections.md` § "The `data` fallback idiom is wrong for async/jobs" · `languages/python/collections.md` § "The `data` fallback idiom is wrong for async/jobs"

### Nothing inside the SRE reliably survives the month — the job least of all

⚠ **This section previously said the opposite.** It advised recovering after a
wipe by re-reading the job, on the strength of Meta's documented one-year
SNAPSHOT retention. **Measured 2026-09-02: every job was `EXPIRED` after a wipe,
SNAPSHOT included**, and ids from a week earlier resolved to `error_subcode
3790112`. SKILL.md § "SNAPSHOT vs LIVE Mode" owns that finding.

So the recovery path this section used to recommend **does not exist**:

| | documented | measured 2026-09-02 |
|---|---|---|
| Server-side job data | held up to a year, re-readable | **all jobs `EXPIRED`** |
| Your files in the SRE | deleted monthly | **survived** on the account tested |

The file survival is *probably* the documented exception for approved EU
systemic-risk programmes, and it is **one observation on one account** — do not
plan on it either. `references/utilities.md` § "The monthly wipe" owns the wipe.

**The only durable artefact is one that has left the enclave, or lives in a
notebook input/markdown cell.** Download a job's results the same calendar month
you submit it, and export what the study needs before the boundary. Budget is
charged at submission and never refunded, so a re-run after losing both the job
and the file costs the full amount again.

### The 100-Snapshot Cap

SNAPSHOT-mode jobs are capped at **100 concurrent per user**; exceeding it fails
with `error_subcode 3790172` ("Exceeded async snapshots limit"). **LIVE jobs do
not count against the cap.**

When reproducibility isn't needed for a given pull, submit it with `mode =
"LIVE"` — it does not consume a snapshot slot — and save the results to disk.

A LIVE job can be promoted later if it turns out to be worth preserving:
`POST async/jobs/{job_id}/snapshot`.

Free slots by deleting finished snapshots — either job by job (`DELETE
async/jobs/{job_id}`) or a whole query (`DELETE async/queries/{query_id}`, which
deletes its jobs with it).

Retention differs: LIVE data is kept ~30 days, SNAPSHOT up to 1 year.

Code: `languages/r/collections.md` § "Staying under the 100-snapshot cap" · `languages/python/collections.md` § "Staying under the 100-snapshot cap"

## Reproducibility: Sharing & Copying

`POST async/queries/{other_query_id}/copy` copies another researcher's public
query together with its COMPLETE SNAPSHOT jobs. **The jobs are rerun, and the
reruns count toward *your* budget.**

`POST async/collections/{other_collection_id}/copy` copies an entire public
collection.

Code: `languages/r/collections.md` § "Copying a public query or collection" · `languages/python/collections.md` § "Copying a public query or collection"

## Naming Best Practices

**Collections**: Project-level names
```
"Climate Change Research 2024-2025"
"Election Misinformation Study"
```

**Queries**: Specific + Time period
```
"Climate Posts - 2024 Q1 - US Only"
"Vaccine Discourse - Instagram - Jan 2024"
```

**Descriptions**: Include everything
```
description = "
  WHAT: Facebook posts mentioning 'climate change'
  WHEN: Q1 2024 (Jan 1 - Mar 31)
  WHY: Baseline for discourse analysis
  WHO: Dr. Smith (PI), IRB #2024-001
  RELATED: See 'Climate Posts Q2' for continuation
"
```

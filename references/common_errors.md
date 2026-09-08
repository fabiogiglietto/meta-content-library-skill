# Common Errors and Solutions

> All examples parse responses with the language's ID-safe helper —
> `languages/r/ids.md` § "mcl_fromJSON" / `languages/python/ids.md`
> § "mcl_from_json". Never parse an MCL response raw into a data frame: IDs
> come back as floats.

> This file is the **full** error catalog. `SKILL.md` § "Common Errors" carries
> only the subset that changes how you write a first query. Errors that exist
> only because of how one language talks to the client are in
> `languages/r/common_errors.md` and `languages/python/common_errors.md`.

## ID / Numeric Precision Errors

| Error / symptom | Cause | Solution |
|-----------------|-------|----------|
| "Invalid Meta Content Library ID" (subcode 3790088) with an ID you copied from a search result | The ID became a float somewhere, so it was rendered as `9.6378e+14` in the URL or parameter | Parse with the ID-safe helper; hard-code IDs as quoted strings (`"963780196442228"`, never bare digits) |
| Chunks of the same query disagree on the ID column's type; concatenation fails or silently coerces | An ID above 2^53 in one chunk and not in another, so a raw parse typed the column differently per chunk | Coerce every ID field unconditionally — the ID-safe helper does this on every chunk |
| Joins and de-duplication silently miss matches; IDs end in unexpected digits | IDs above 2^53 (~9.0e15) lost precision when parsed as a float (`...123` → `...124`) | Re-parse from the raw response/file with the ID-safe helper. Rounded IDs are unrecoverable |
| An ID column full of a literal missing-value string (`"NA"`, `"nan"`) | A blanket numeric-to-string cast over a column containing JSON `null` | The ID-safe helper keeps `null` as missing, never as a string |
| IDs read back from a CSV are floats again | CSV readers type-guess numeric ID columns | Read ID columns as strings — the language file says how |
| Nested `author.id` / `producer.id` still numeric | The ID pattern did not account for the flattened dotted names | Match with `"(^|[._])ids?$"` (what the helpers use) |

Code: `languages/r/common_errors.md` § "Errors that only exist in R" · `languages/python/common_errors.md` § "Errors that only exist in Python"

## Producer List Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 404 "Path '/meta-content-library/producer-lists/{id}' was not found" | Wrong endpoint path | Use `lists/producers/{id}` not `producer-lists/{id}`. |
| A producer list visible in the UI is **absent from `lists/producers`** and also errors at `lists/producers/{id}` | **No API ID has been generated for that list.** The id is created on demand, not automatically | In the UI: *Producers lists* → *View* → the **down-arrow next to `Share`** → **Create API list ID**. The `···` menu does *not* offer this. See `producer_lists.md` § "Share producer lists between the UI and the API" |
| Producer count from the API disagrees with the count shown in the UI | The API ID is a **snapshot**; the list was edited after the id was generated | Regenerate the API ID and record which id the analysis used |
| The ID vector is empty or the code errors while splitting it | Reading a top-level `ids` field, which does not exist | The producer list response has a `producers` array of objects with `id`, `name`, `type`. Read the `id` of each producer |

## Response Handling Errors

An API response may be empty, carry no `data`, or carry something that is not a
table. Every language funnels responses through a `safe_get_data()` that parses
with the ID-safe helper, validates, and returns either the rows or nothing —
and wraps the call so one failed request in a loop is logged rather than fatal.
Language-specific symptoms of skipping that funnel (indexing a missing field,
counting rows of nothing) are in the language files.

Code: `languages/r/jobs.md` § "Safe response handling" · `languages/python/jobs.md` § "Safe response handling"

## Instagram Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing required parameters. Input at least one parameter [q, post_ids, account_ids]" | Used `surface_ids` for Instagram | Use `post_ids` for posts, `account_ids` for accounts |
| "Invalid Meta Content Library ID" (subcode 3790088) | Used a raw Instagram URL ID, or the post/account is not in MCL | MCL IDs are library-specific and differ from the numeric IDs in Instagram URLs. Look the account up with `instagram/accounts/preview` (search with `q`) and use the returned `id`. If a search-returned ID still fails, the post may be private, deleted, or from an account with <1K followers. |
| "Invalid Meta Content Library ID" (subcode 3790088) with a valid MCL ID | ID held as a float, so the nested path was built as `.../1.784e+16/comments/preview` | Parse with the ID-safe helper so `post_id` is a string before it reaches the URL |
| "Invalid Meta Content Library ID" on comments endpoint | Wrong endpoint pattern | Use nested URL `/instagram/posts/{id}/comments/preview` instead of parameter-based query |

## Facebook Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Missing required parameters" | Wrong ID parameter | Use `surface_ids` for Facebook entities |
| "Invalid Meta Content Library ID" (subcode 3790088) | Used the numeric ID from a Facebook group/page URL as `surface_ids` | URL IDs are never valid MCL IDs. Search by name (e.g. `facebook/groups/preview` with `q`) and use the returned `id`. Private or non-indexed groups don't appear in search and aren't queryable. |
| "Invalid Meta Content Library ID" (subcode 3790088) with a valid MCL ID | `surface_ids` built from float IDs → each value is sent as `9.6378e+14` | Keep IDs as strings end-to-end (the ID-safe helper), or format them with full digits before building the array |
| "Invalid parameter" with a correct `surface_ids` / `account_ids` / `post_ids` name | ID param sent as a scalar — a single ID not wrapped in an array, or a comma-joined string | Pass an array at every length — `references/query_params.md` § "ID Parameters Are Arrays of Strings" |

| "Invalid Meta Content Library ID" (3790088) when resolving a reshare | The reshared original is out of scope for the Content Library, and one bad ID rejects the **whole** `post_ids` call | Bisect the batch and skip the offenders — see `references/field_reference.md` § "Reshares" |

## Scope and Quota Errors

| Error | Cause | Solution |
|-------|-------|----------|
| "Estimated response size too large" (subcode 3790057) | A single query would return more than ~100,000 results | Split by date window and/or query fewer `surface_ids` — see `references/chunking.md` |
| "Exceeded async snapshots limit" (subcode 3790172) | More than 100 concurrent SNAPSHOT jobs | Run `mode = "LIVE"` where reproducibility isn't needed, and delete finished snapshots — see `references/collections.md` § "The 100-Snapshot Cap" |
| A producer-list post query estimates ~0 results | The list is mostly ordinary profiles, whose posts aren't in the queryable dataset | Only public profiles that are verified or have 100+ followers qualify (v6.0; it was 1,000 in v5.0 and 25,000 before that) — see `references/field_reference.md` § "Data Scope" |
| "Invalid Keyword Search" (subcode 3790184) | The query used a double-quoted phrase | Drop the double quotes; use single-word tokens joined with `OR` — see `references/query_params.md` § "Query Syntax (`q`)" |
| "Invalid time range" (subcode **3790079**) | `until` is in the future, or `since` is not before `until` | **[verified 2026-08-29]** `until` must be strictly **before the current epoch time**. Verbatim: *"The since time must come before the until time, and the until time must come before current_epoch_time."* A window ending "today or later" fails outright |

## Failures that return HTTP 200 — **[verified 2026-08-29]**

The worst class: the call succeeds, the rows look plausible, and the filter never
ran. A row count is not evidence a parameter was honoured. **Score every filter
against a control that must return nothing** — e.g. a URL nobody could have
shared — and treat "same rows as without the filter" as *ignored*, not *working*.

| Symptom | Cause | Solution |
|---|---|---|
| `q` + `link` returns a full page of posts unrelated to the URL | The `link` matched nothing, so it was **dropped from the query** and you got the `q`-only result set (Jaccard 1.0 against `q` alone) | Drop `q`. `link` alone works and returns 0 correctly for an unmatched URL — see `references/query_params.md` § "The `link` parameter" |
| `estimate` reports millions for a link query | The same bug reaches `estimate`, so a mistyped URL is sized as if unfiltered | Size link queries with `link` alone, no `q` — magnitudes in `query_params.md` § "The `link` parameter" |
| An Instagram query with `link` returns unfiltered results | `instagram/posts` has no link filter and **silently ignores** the parameter | There is no link search on Instagram. Filter client-side on `link_attachment` — see `references/query_params.md` § Instagram |
| `link` returns 0 for a URL you know was shared | The exact string is not a key Meta has seen — **not** proof nobody shared it | Try the publisher's canonical form; see the false-zero rates in `query_params.md` § "The `link` parameter" |
| A `fields` name returns no column | Unknown names are dropped silently | Send a positive control (`statistics{like_count}`) in the same request — see `references/query_params.md` |

## General Errors

| Error | Cause | Solution |
|-------|-------|----------|
| Type mismatch | An integer parameter arrived as a float | Send integers as integers — `references/query_params.md` § "Integer Parameters" |
| Method not allowed | GET on /job endpoint | Use POST for async job endpoints |
| Budget exceeded | Quota depleted | Wait for 7-day rolling reset, check with `/budgets` |
| `'list' object has no attribute 'items'` | `params` was not a mapping — the client calls `.items()` on it | Omit `params` when there are none, or pass a mapping — `references/query_params.md` § "Never Pass an Empty `params`" |

## Debugging with OpenAPI Spec

When encountering parameter or endpoint errors, check the OpenAPI spec
(`SKILL.md` § "OpenAPI Spec"): list `paths`, filter them for a keyword, and read
one endpoint's `get.parameters` names.

Code: `languages/r/common_errors.md` § "Debugging with the OpenAPI spec" · `languages/python/common_errors.md` § "Debugging with the OpenAPI spec"

## Debugging Response Structure

When an API response causes unexpected errors, inspect the raw structure in
four steps: print the first ~2,000 characters of the raw response text; parse
it with the ID-safe helper and list the top-level fields; for each field print
its type and length (and, for a table, its row count and column names); and
confirm every ID-named column came out as a string — none showing `e+15` or
`e+16`.

Code: `languages/r/common_errors.md` § "Debugging response structure" · `languages/python/common_errors.md` § "Debugging response structure"

# Changelog

All notable changes to the `mcl-api-r` skill. This file is the single home for
the version history — `SKILL.md` and `README.md` link here rather than
maintaining their own copies.

## v1.8.0 (2026-08-18)

**Removed: examples using a client API that does not exist.** Three files
documented `MCLClient$new()`, `client$search_fb_posts()` /
`search_ig_posts()` / `search_fb_comments()`, `library(metacontentlibrary)`,
and cursor pagination via `response$paging$next_cursor`. None of these exist —
the real client is `client$get(path=, params=)` / `client$post(...)` via
reticulate, as `SKILL.md` has always documented. Code copied from those files
could not run.

Removed with them, as unverifiable rather than merely undocumented:
`min_reactions`, `min_shares`, `min_comments`, `min_views`, `search_fields`,
`producer_list_id`, `media_type` as a query filter, and `start_date` /
`end_date` (the API uses `since` / `until`). These were deliberately **not**
rewritten into correct-looking `client$get(params = ...)` form, which would have
made unverified guesses indistinguishable from tested behavior. Rediscover them,
if they exist, via `client$openapi_spec()`.

**Fixed: `statistics$reactions` → `statistics.reactions`.** `mcl_fromJSON()`
parses with `flatten = TRUE`, so engagement counts are flat columns, not a
nested list-column. Roughly a dozen snippets in `common_patterns.md` used the
nested form and would have failed on copy. Facebook posts also group by
`post_owner.type`, not `producer_type` (an Instagram field).

**Resolved contradictions:**
- `shared_from_id` removed from `field_reference.md`; `shared_post_id` (v1.7.0)
  is the verified field name for a reshare's original post.
- Two conflicting Instagram-account field tables reduced to one. The verified
  set (v1.2.0) lives in `producer_lists.md`; `field_reference.md` points to it.
  Note `biography` not `bio`, `is_verified` not `verified`.
- `get_id_param_name()` deleted from `producer_lists.md`. It returned `post_ids`
  for Instagram twenty lines after the auto-detect pattern returned
  `account_ids`. These are different jobs, not conflicting answers:
  `account_ids` filters posts **by account**, `post_ids` selects **specific
  posts**. Both files now say so.
- Instagram comment fields aligned to `owner.*`, matching the verified Facebook
  comment schema, and marked unverified.
- Threads: the querying claim is dropped from the skill description and README.
  No Threads endpoint path has been confirmed; the field table stays, flagged
  unverified.

**Consolidated — one owner per fact.** Duplicated content had already drifted
(Critical Requirements: 6 items in `SKILL.md` vs 13 in `README.md`; the
rate-limit table in `README.md` was missing the 100-snapshot row). Each fact now
has one home, and every other mention is a pointer. `SKILL.md` keeps the errors
that change how you write a *first* query; the diagnostic long tail moved to
`common_errors.md`.

**Structure:**
- `references/query_syntax.md` deleted. Its two verified sections — boolean
  operators, and the 3790184 no-double-quoted-phrases rule with the full error
  JSON — moved into `references/query_params.md` § "Query Syntax (`q`)".
- Version history extracted from `SKILL.md` and `README.md` into this file.
- `TESTING_PROCEDURE.md` moved to `docs/`, so it is no longer part of the skill
  payload. Suites testing removed content were dropped; the offline
  `mcl_fix_ids` unit test (Test 10.1) is kept.
- `SKILL.md` cut from 459 to ~300 lines. The two near-identical OpenAPI sections
  are merged into one.

## v1.7.0 (2026-08-18)

Consolidated verified API behaviors: MCL IDs != URL IDs (3790088); ID params
must be arrays; empty-params reticulate pitfall; no double-quoted phrases
(3790184); 100k single-query cap (3790057) -> date windows; SNAPSHOT cap
(3790172) vs LIVE + LIVE->SNAPSHOT conversion; profile post-inclusion thresholds
(verified/25k+ followers); comment (`owner.*`) vs post (`post_owner.*`) schemas;
replies require a second `parent_ids` pull; reshares carry `shared_post_id`
resolved via `post_ids`; producer-list CSV import format (`Producer URL`, max
1000).

## v1.6.0 (2026-08-17)

Documented that the API rejects double-quoted phrase searches (subcode 3790184)
even though the UI supports them; use single-word `OR` tokens.

## v1.5.0 (2026-08-17)

- Documented creating producer lists via the GUI CSV import: single `Producer URL`
  column of `https://www.facebook.com/<username>` URLs, max 1,000 producers, import
  is by URL not by MCL id. Added a recipe for building a list from active public
  commenters.
- Clarified that `surface_ids` / `account_ids` / `post_ids` must be passed as
  **arrays** (`as.list(ids)`); a scalar is rejected with "Invalid parameter",
  including a length-1 vector reticulate converts to a string. Updated every
  affected example.

## v1.4.0 (2026-08-16)

- **IMPORTANT**: All IDs (surface, post, comment, account, job, query) must be
  loaded as **character**. Added an "ID Handling" section with `mcl_fromJSON()` /
  `mcl_fix_ids()`, which combine `bigint_as_char = TRUE` (exactness above 2^53)
  with unconditional `sprintf("%.0f", ...)` coercion of every ID field (no
  scientific notation, no per-batch type drift).
- Folded ID coercion into `safe_get_data()` and switched every example in
  `SKILL.md` and the reference files from `fromJSON()` to `mcl_fromJSON()`.
- Prevents silent precision loss above 2^53, scientific notation in URLs and
  parameters (a second cause of subcode 3790088), and per-chunk `bind_rows()`
  type mismatches.
- Added error rows for scientific-notation 3790088, `bind_rows()` type mismatch,
  and silent precision loss in joins/dedup; added ID-hygiene guidance for joins,
  dedup, and CSV round-trips, plus offline and live ID tests in
  `TESTING_PROCEDURE.md`.

## v1.3.0 (2026-08-13)

**IMPORTANT**: Documented that MCL IDs are library-specific and differ from
Facebook/Instagram URL IDs. Added a "Finding Surface IDs" section with per-entity
lookup endpoints and error rows for subcode 3790088 and the empty-`params`
reticulate pitfall.

## v1.2.0 (2026-03-29)

- **BREAKING**: Fixed producer list endpoint: `lists/producers/{id}` not
  `producer-lists/{id}`
- **BREAKING**: Producer list response uses `$producers` data.frame (cols: id,
  name, type), not `$ids` vector
- Added safe response handling pattern for API responses (prevents `nrow()` on NULL)
- Added Instagram accounts response field documentation (id, name, username,
  biography, account_type, is_verified, follower_count, following_count,
  creation_date, website)
- Added cross-platform account matching workflow to `producer_lists.md`
- Added producer endpoint to Key Endpoints section
- Updated `common_errors.md` with 404 producer list, NULL response, and `nrow()`
  errors

## v1.1.0 (2025-01-04)

- Fixed Instagram parameter documentation (`post_ids` not `surface_ids`)
- Added nested endpoints documentation for Instagram comments/replies
- Added OpenAPI spec discovery pattern for debugging
- Added `common_errors.md` reference file
- Clarified platform-specific ID parameter differences

## v1.0.0 (2025-01-04)

- Initial release
- Core async query patterns with integer `L` suffix handling
- SNAPSHOT mode documentation
- Producer list support with platform auto-detection
- Quota monitoring from verified working code
- Package installation via `fbrir`
- Job retrieval patterns
- Large dataset chunking
- Collection management
- OpenAPI spec access

---

## Release checklist

When updating this skill:

1. Bump the version in **three** places: `SKILL.md` frontmatter `version:`, the
   `> **Skill Version:**` line below the `SKILL.md` title, and `README.md`.
2. Update the `updated:` date in the `SKILL.md` frontmatter.
3. Add an entry here — and only here.
4. Check that any new fact has exactly one owner (see `SKILL.md` § References);
   add a pointer elsewhere rather than a second copy.
5. Update `docs/TESTING_PROCEDURE.md` if behavior changed.

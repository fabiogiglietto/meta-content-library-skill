# Changelog

All notable changes to the `mcl-api-r` skill. This file is the single home for
the version history — `SKILL.md` and `README.md` link here rather than
maintaining their own copies.

## v1.9.1 (2026-08-21)

Patch release. No documented API behavior changed; this removes a silent-failure
class from the skill's own code and files the question behind it.

**Fixed: no status comparison is case-sensitive any more.** The sweep found six,
failing in two directions. `SKILL.md`'s Async Query Template, `chunking.md` and
the example script used `while (status != "COMPLETE")`, which spins forever
against a lowercase `complete`. `common_patterns.md` used
`while (status == "IN_PROGRESS")`, which is worse — against `in_progress` it
exits on the first check and reads a half-written result as final. `utilities.md`
gated on `status == "COMPLETE"` and would misreport. All now route through
`mcl_wait_for_job()` (SKILL.md § "Waiting for a Job"), which upper-cases and
trims before comparing, enforces a wall-clock timeout, raises on `FAILED`, and
treats an unrecognized status as "keep waiting" rather than as success. This is
correct under either casing, so it did not need the question below answered.

**Added: `docs/OPEN_QUESTION_ENUM_CASING.md`** — the casing question itself is
still open, now as documentation rather than as a live hazard. The file records
which public pages were checked and came back empty (there is no public
async-jobs page at all, and neither `get-api-code` nor `api-search-id` prints a
`mode` value), a Claude for Chrome prompt for sweeping what the check missed, and
a zero-budget in-SRE diagnostic that reads the OpenAPI enum and an
already-finished job rather than submitting anything.

**Corrected in the v1.9.0 entry below:** it claimed a fix to
`top_italian_politicians_week.R`, but that file is listed in `.gitignore` and has
never been tracked, so the fix was not in the release and the file does not exist
in this repository. The paragraph has been removed rather than left describing a
change no reader can see.

## v1.9.0 (2026-08-21)

Synced with the Meta Content Library changelog through 2026-04-30.

**Fixed: the follower threshold was three versions stale.** Four files said a
Facebook profile's posts are queryable only if it is verified or has **25,000+**
followers. That number predates v5.0. It went to 1,000 in v5.0 (2024-11-11) and
to **100** in v6.0 (2025-11-10), and the same 100-follower rule governs which
Instagram personal accounts are included. The stale figure was load-bearing:
`common_errors.md` used it to explain why a producer-list post query estimates
~0 results, which sent researchers looking for a fault in lists that were fine.
`field_reference.md` § "Data Scope" now carries the version history, and notes
that the 25,000 floor still documented for the ICPSR/CASD *downloadable* dataset
is a different product from the API. "Verified" now also covers paid Meta
Verified subscriptions.

**Added: `references/surfaces.md`** — the surfaces that arrived after the
endpoint list was last written: Facebook channels and channel messages
(2026-03-12), WhatsApp channels and channel updates (2026-04-30), Instagram
channels and channel messages, Marketplace listings, Facebook and Instagram
fundraisers, and Facebook donations. Parameters, filters, sort enums and node
fields for each. Flagged as documented-but-untested, in the style already used
for the Threads table — it is transcribed from Meta's guides and Data
dictionary, not confirmed against a live response.

**Fixed: the endpoint grammar no longer holds for every surface.** SKILL.md's
`/{resource}/{preview|job|estimate}` line would lead you to guess
`facebook/channels/job` and `facebook/marketplace/preview`; both 404. Async
message jobs hyphenate the resource at the platform root
(`facebook/channel-messages/job`, `whatsapp/channel-updates/job`) while the sync
read hangs off the parent channel node, and no `estimate` endpoint is documented
for any of the new surfaces.

**Added: the Facebook post filter set** to `query_params.md`, which had only
ever documented `q` / `since` / `until` / `limit` / `lang` / `country` and the ID
params. Notably `sort` now defaults to `most_to_least_views` rather than
newest-first, so an old query silently returns a different sample; `media_types`
is deprecated in favour of `content_types` (v1.8.0 dropped `media_type` as
unverifiable - this is its documented replacement, with a source); and
`search_scope = "post_text_and_image_text"` is how you reach text-in-images
search. Enum *values* are lowercase after the 2025-11-10 REST-ful pass.

**Clarified: two different caps were conflated as "1000".** A sync search pages
through 1000 results *in total*; the per-page `limit` maximum was separately cut
from 500 to 100 on 2025-07-15, and is 0-50 (default 10) for channel message and
update previews.

**Added: Test Suite 11** to `docs/TESTING_PROCEDURE.md` (five sync-only,
zero-async-budget tests) so the new surfaces can be promoted from documented to
verified in one SRE session. It also asks the tester to record whether `mode`
accepts a lowercase value and where the `limit` ceiling actually falls.

Not changed: `mode = "SNAPSHOT"` / `"LIVE"` stay uppercase. The 2025-11-10
"enums are now lowercase" note is real but demonstrably applies to value enums
like `sort` and `content_types`; the uppercase modes are what this skill has
tested, and rewriting dozens of samples on a documentation inference is exactly
the trade v1.8.0 refused.

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

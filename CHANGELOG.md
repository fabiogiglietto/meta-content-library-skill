# Changelog

All notable changes to the `mcl-api-r` skill. This file is the single home for
the version history — `SKILL.md` and `README.md` link here rather than
maintaining their own copies.

## v1.11.1 (2026-08-23)

### Removed `docs/SRE_AUTOMATION_SURFACE.md` — it was a stale copy of someone else's fact

**Deleted, not moved.** The file was a 621-line snapshot, last touched
2026-08-22, of a document that had since grown to 1309 lines in the `mcl-agent`
client repo. Two copies, one owner: the copy here was already wrong about the
paste channel, about modifier keys, and about what the AppStream Functions
toolbar makes possible — every one of those settled *after* this snapshot was
taken. Nobody reading it here would have known.

This is release-checklist rule 4 enforced against the repo itself: *"check that
any new fact has exactly one owner; add a pointer elsewhere rather than a second
copy."* The rule was written for new facts and the violation was an old one.

**The scope line, stated so this cannot recur:** this skill holds only what is
needed to write reliable, functional code against the Meta Content Library
API — endpoints, parameters, schemas, ID handling, caps, error subcodes, and the
patterns that make them work. **How the SRE is driven is not an API fact.** It
belongs to the `mcl-agent` client, which owns the browser automation surface, the
driver design and the egress policy. A fact that would still be true for a
different research question on a different corpus, and is about the API, lives
here; if it is about driving the enclave, it does not.

No pointer file replaces it. A stub about SRE automation would be the same
scope violation in miniature, and the client repo is not published, so a link
would dangle for anyone reading this repo on GitHub.

### Three inbound references rewritten to stand alone

All three cited the deleted file and would have dangled:

- `CHANGELOG.md` (the v1.11.0 ML-models entry) and
  `docs/ML_MODELS_OPEN_QUESTIONS.md` both borrowed the deleted file's
  four-tag sourcing convention. The four tags — **[verified]**,
  **[documented]**, **[inferred]**, **[open]** — are generic method, not an SRE
  fact, so they are now **stated inline** rather than cited across repos. This
  removes a cross-repo dependency the skill never needed.
- `docs/ML_MODELS_OPEN_QUESTIONS.md` § "Automation note" cross-referenced a
  section on reading the session by screenshot. Rewritten to record the
  *provenance* of that reading and to name the owner, without restating the
  driver fact.

## v1.11.0 (2026-08-22)

**Note for `docs/stage3-first-run`:** that branch's CHANGELOG also claims
v1.11.0. This one merged first and took the number, so stage3 must be renumbered
to **v1.12.0** before it merges.

### Deleting a job does not refund budget — learned at a cost of ~74,000 records

**[verified 2026-08-23, by the researcher]** A submission cell ran twice on an unstable SRE
stream, creating six SNAPSHOT jobs for three tiers. Deleting the duplicates **frees the
snapshot slots but does not return the records** — budget is consumed at submission and is
gone. `SKILL.md` § "SNAPSHOT vs LIVE Mode" now states this, with the one-line
`file.exists()` guard that would have made the re-run a no-op. **Every cell that submits a job
should carry that guard.** There is no cheap way to learn this fact; write it into the cell.

### CORRECTION: `link_attachment` works — four false negatives traced to one naming error

**[verified 2026-08-22]** An earlier entry in this changelog claimed
`link_attachment_fields` was documented but not served. **That was wrong.** The property is
**`link_attachment`**; `link_attachment_fields` is the data dictionary's *display label*, not a
field name. Requested correctly it returns `link_attachment.{description,link,name,caption}`.

**Link URLs, titles and captions are obtainable.** Co-sharing analysis, domain-level media-diet
measurement and URL-based diffusion **are** buildable on this API.

The root cause of four consecutive false negatives was transliterating display labels into field
names, compounded by `fields` dropping unknown names silently. **The fix is a rule, now the
opening of `field_reference.md`: take field names from
`client$openapi_spec()$components$schemas$FacebookPost$properties`, never from the data
dictionary's labels.** The spec is free, in-session, complete and deployment-specific.

The same read produced the full 16-property `FacebookPost` schema, the `LinkAttachment` and
`Multimedia` sub-schemas (`multimedia` also has `id` and `tags`), and three undocumented
parameters — notably **`surface_ids_to_exclude`**, which does server-side exclusion.

Also corrected: `is_verified` / `activity_type` / `activity_name` were likewise tested under
label-derived names. The schema has `activities` (array of `FacebookActivity`); there is no
`is_verified` property, though `is_surface_verified` exists as a *parameter*. Those earlier
negatives are withdrawn as unfounded rather than restated.

### `link_attachment_fields`: documented for Facebook posts, not served

**[verified 2026-08-22]** Meta's data dictionary lists `link_attachment_fields.{link,name,
caption,description}` as Facebook Post fields (entries 33–36). **The API does not return them.**

Established with a properly controlled test after three inadequate ones: brace syntax, a
positive control that passed, and `content_types = list("links")` so every sampled row actually
has an attachment. Three surfaces — page list, group, broad `q` search — 25/15/25 rows, all
`content_type = links`, and in every case the response was `id, content_type` only.

**Consequence: a shared link's URL cannot be obtained from a Facebook post.** Co-sharing
analysis, domain-level media-diet measurement and URL-based diffusion **cannot be built on this
API**. `shared_post_id` is the only artifact-identity field that actually arrives. Same status
for `is_verified`, `activity_type`, `activity_name`.

The three failed attempts are recorded in `field_reference.md` because each failure mode is
generic: invented names; right names in dot syntax; right names and syntax but a sample where
the field could not be populated (an all-`NULL` column is dropped, so absence-in-sample looks
exactly like absence-in-schema).

### Multimedia URLs and image-text matching ARE available — two earlier negatives reversed

**[verified 2026-08-22]** Careful reading of the data dictionary plus retesting with brace syntax
and a positive control overturned two conclusions this skill nearly recorded:

- **`multimedia{url}` works.** Sub-fields returned: `type`, `duration`, `url`. But the URLs are
  **presigned, ephemeral links** to `prod-fortapis-api-async-uploads.s3.amazonaws.com`, median
  **1,803 characters**. Media is therefore **retrievable in principle but the URL is not an
  identifier** — the same image in two posts yields two different URLs, so any dedup or
  diffusion analysis keyed on media URL is invalid.
- **`match_type` works — it just needs a `q` search.** With
  `search_scope = post_text_and_image_text`, a 25-row sample returned `image_text 5 |
  post_text 24`. Requesting `match_type` alongside `surface_ids` with no query returns nothing,
  which is an easy false negative. **In-image text is searchable and matching posts are
  identifiable, though the OCR text itself is never returned.**

Confirmed genuinely absent, with a passing control in the same request:
`link_attachment_fields`, `is_verified`, `activity_type`, `activity_name`.

**Doc gap filed:** "Post surface type" is documented as "Pages, profiles" — **groups are
omitted**, though group surface queries plainly work.

### `fields` uses brace syntax — and drops unknown names silently

**[verified 2026-08-22]** Nested sub-fields are requested as `statistics{like_count,haha_count}`,
**not** `statistics.like_count`. The dots in the data dictionary are *naming*; the response comes
back flattened to dots again, but the request must use braces. New `query_params.md` § "Field
expansion" owns this, with Meta's own example.

**The more dangerous half: an unknown field name is not an error.** The call succeeds and the
column is simply missing — indistinguishable from the field being present but empty. In this
session that produced two unsound conclusions in a row (first from invented names `image_text`
and `link_url`, then from correct names in the wrong dot syntax).

**The fix is a positive control**: include a field known to work in the same request. With
`statistics{like_count,haha_count}` as control, the result is unambiguous —
`link_attachment_fields` and `match_type` return nothing while the control returns cleanly, so
those fields genuinely are not served. That discipline is now written into `query_params.md`.

### The data dictionary is segmented by product — and we read the wrong section

**[verified 2026-08-22]** Meta's post data dictionary covers several product surfaces on one
page, distinguished only by URL anchor. The `#dd-fb-post-3pcleanroom` section describes the
**Third-Party Cleanroom** schema. `link_attachment_fields.*`, `multimedia.url`,
`multimedia.user_tags` and `match_type` are documented there and are **not returned by the
Content Library API** — tested on group and page surfaces, in parent and dotted form.

The `fields` parameter **drops unknown names silently**, so asking for a cleanroom field yields
a successful response with fewer columns — indistinguishable from the field being empty. New
`field_reference.md` § "The data dictionary is segmented by product" owns this.

Two facts recovered from the same read:

- **`multimedia` sub-fields vary by item type.** A photo-heavy group corpus shows only
  `multimedia.type`; a video-heavy page corpus shows `type, duration`. **`multimedia.duration`
  is real** — do not conclude a sub-field is absent from a single sample.
- **`image_text` is a `match_type` value, not a returned field.** OCR text is **searchable but
  never retrievable**: `search_scope = post_text_and_image_text` makes `q` match text inside
  images, but no post surface returns an OCR column. Research designs that assume an
  `image_text` field to analyse are not implementable against this API.

### Spec-verified: producer lists are GET-only, and Marketplace has an `estimate`

`client$openapi_spec()` read live on 2026-08-22 settled three things that were
previously asserted without a source:

- **`/lists/producers` and `/lists/producers/{alias_id}` are `get` only.** There
  is **no POST**: producer lists cannot be created or modified through the API.
  `SKILL.md` and `producer_lists.md` already said so; that claim is now
  **verified** rather than inherited from Meta's prose. Worth stating plainly
  because every other collection-shaped resource here (`async/jobs`,
  `async/queries`, marketplace-listings jobs) *does* accept a POST — producer
  lists are the exception.
- **The path parameter is `{alias_id}`, not `{list_id}`** — wording consistent
  with the API ID being a snapshot *alias*, not a live pointer.
- **`/lists/shared-searches/{alias_id}` exists** (`get`), the saved-search
  analogue of a shared producer list. Previously undocumented here.

**Correction to `surfaces.md`: Marketplace DOES have an `estimate` endpoint.**
That file said "No `estimate` endpoint is documented for any of these surfaces."
The spec shows the full trio — `preview` / `estimate` / `job`, plus per-`alias_id`
variants and `/{mcl_id}`. The guides' silence was a documentation gap, not an API
one. The lesson generalises: **when the guides are silent, read the spec — it is
free, it is in-session, and it is the authority.** Claims about channels,
fundraisers and donations were not covered by this read and remain unverified.

### The API-ID flow, walked end to end and written down properly

The § "Share producer lists between the UI and the API" steps are now
**[verified]** rather than transcribed, having been driven to completion on two
real lists. Three things Meta's page does not tell you, each of which cost time:

- **The caret is to the RIGHT of `Share`** — Meta says only "adjacent". The
  control on the left is `···`, a different menu.
- **Its accessible label is `Copy`.** Searching for a control labelled "Open
  Dropdown" or "API" finds the wrong one, or nothing. Locate it by
  `aria-haspopup="menu"` sitting right of the `Share` button.
- **A bare `element.click()` does not open it.** The app requires a full pointer
  sequence (`pointerover → pointerdown → mousedown → pointerup → mouseup →
  click`). Worth knowing for anyone scripting the Content Library UI.

**And the id format is self-documenting.** Per the dialog: *"the today's date in
YYYY-MM-DD format, followed by a randomly generated string."* So the date in
`2026-08-17-cwqm` is **when the ID was generated — the snapshot date — not when
the list was created.** Combined with the snapshot semantics above, this means an
id carries its own provenance: a date long before your collection window is a
visible warning that the snapshot may be stale.

### The API ID step — a documented mechanism this skill was missing entirely

**A producer list created in the UI is invisible to the API until you generate an
API ID for it.** Not mis-addressed — *absent*: it does not appear in
`lists/producers` and it errors at `lists/producers/{id}`. The id is generated on
demand via *Producers lists* → *View* → the **down-arrow next to `Share`** →
**Create API list ID**.

`producer_lists.md` cross-referenced a section called "Share producer lists
between the UI and API" that **did not exist in the file** — a dangling
reference, so the one place a reader would look for this said nothing. The
section now exists and owns the fact. Source:
[Share a producer list](https://developers.facebook.com/docs/content-library-and-api/appendix/share-producer-list) (v4.0+).

This was found the expensive way: a live session could not resolve two lists that
were plainly visible in the UI, and the hypothesis under test — a GUI→API
propagation lag — was **wrong**. See `mcl-agent`
`docs/run_log/2026-08-22-phase0b-sre-recon.md`.

**The id is a SNAPSHOT of the list**, per Meta's own wording. It binds to the
list as it stood when the id was generated, so editing a list afterwards is not
guaranteed to be reflected. Curate first, generate second, and record the id with
its generation date — two analyses citing "the same list" under different ids may
not share the same producers, and nothing in the results would reveal it. New
`producer_lists.md` § "Share producer lists between the UI and the API" owns
this; `common_errors.md` gains two symptom rows; `SKILL.md` § endpoint summary
now mentions the step.

Also corrected: `common_errors.md` told readers the UI "shows the correct path
when you click the API ID button" — a button it never located, in a menu that
does not contain it. That sentence is gone.

Still open: whether `lists/producers` accepts a **POST**. Meta's docs show only
`GET`, and both `SKILL.md` and `producer_lists.md` assert UI-only creation, but
**neither has been checked against `client$openapi_spec()`**. Tagged as
documented-not-verified.

### Corrections to claims this skill was already making

**`Export`: the exported notebook is scrubbed — verified by exporting one.** `SKILL.md` and `README.md` said
export was "entire notebook only", which reads as *you get the notebook, results
included*. Meta's export page says otherwise: code, markdown and **images**
survive; **cell outputs, stdout, stderr and HTML are removed** — each replaced
by a literal `[NOTICE] N output(s) filtered out`. Numbers do not
leave as numbers — anything you need to keep must be rendered as an image, and
that is a decision to make before a long run, not after. New
`references/utilities.md` § "Getting Results Out" owns this. The S3-bucket
feature is not an alternative: its bucket is Secure-Research-Environment-owned,
and Meta states it is not supported for Meta Content Library.

**Inference from R is fine.** An earlier commit on this branch told readers that
inference was "easiest left in Python" because of `**kwargs` unpacking. Tested
and false: passing `input_ids`/`attention_mask` by name avoids the unpacking, and
mean pooling is ordinary reticulate arithmetic. A 384-dim embedding took 0.7 s
end to end. The working recipe replaced the discouragement.

**The first drift-check "change" was our own transcription.** Corrected in
`references/ml_models_approved.md` rather than left asserting a false edit date
on Meta's page.

### Added

**ML models in the SRE** — `references/utilities.md` § "Download Machine Learning
Models", now largely **[verified]** in a live session rather than transcribed:

- `fbri.package_managers.huggingface` imports from R-side reticulate; reticulate
  binds `/opt/conda/bin/python3` (3.11), the same conda env as the kernels.
- Downloads land at `~/huggingface/<repo>/<revision>`, org prefix kept — read
  from the module's source, then confirmed by downloading.
- **`output_dir` replaces the whole path**, so two models sharing one directory
  overwrite each other's `config.json`.
- **Both helpers return `None`** despite docstrings promising a path string.
- **`hf_list_files(repo, revision)`** — undocumented by Meta; probes a repo, and
  the approval gate, without downloading.
- **`hf_download_repo` pulls every file**: MiniLM's ~90 MB of weights cost
  **931 MB** because ONNX, OpenVINO, TensorFlow and Rust variants come too.
  Throughput ~16 MB/s.
- **The org prefix is mandatory.** Every bare legacy alias (`t5-small`,
  `bert-base-uncased`, `xlm-roberta-large`, …) returns 400 — the proxy does not
  follow Hugging Face's rename redirects, and those bare names are exactly what
  Meta's page prints.
- **400 vs 404**: 400 is repo-level and cannot distinguish "wrong id" from "not
  approved"; **404 means the repo resolved and passed the gate**, only the
  revision is wrong.
- **Revision pinning works** — full and 7-char SHAs, each getting its own
  directory beside `main/`. Pin by SHA for reproducible work.
- **No offline configuration needed**: `from_pretrained()` on a local path makes
  no hub call.
- **`sentence_transformers` is not installed**, though two approved models are
  Sentence-Transformers models; use `AutoModel` + manual mean pooling.

**GPU servers** — `references/utilities.md` § "CPU or GPU Server". CPU or GPU is
chosen when the notebook server starts and switchable mid-session via **File** >
**Hub Control Panel** without losing work. Verified real: `torch 2.4.0+cu118`,
CUDA available.

**`references/ml_models_approved.md`** — the approved list as a diff target,
with **12 of 13 repo ids resolved by probing**. #11 DeBERTaV3 resists:
`microsoft/mdeberta-v3-base` lists while `microsoft/deberta-v3-base` and
`-large` do not, so the org is right and the gate is per-model. A 400 cannot
separate "wrong id" from "not approved", so probing cannot settle it —
`docs/SUPPORT_TICKET_DRAFT.md` asks Meta.

**`docs/ML_MODELS_OPEN_QUESTIONS.md`** — the 20-question inventory and its
results log; 19 closed, all without spending MCL budget.

**A monthly drift check** — routine `trig_015jzBacsSw43Np7E23p3obe` re-fetches
Meta's model list, diffs it against the snapshot, and opens a PR only when
something changed. Paired with an at-use freshness check in `SKILL.md`: before
answering which models are available, re-fetch and compare.

## v1.10.0 (2026-08-21)

**Added: how to download machine learning models in the SRE**
(`references/utilities.md` § "Download Machine Learning Models"). The SRE has no
internet access, so `from_pretrained("facebook/mbart-...")` cannot reach
huggingface.co — an approved model must be downloaded first through
`fbri.package_managers.huggingface` (`hf_download_repo` for a whole repo,
`hf_download_file` for one file, filename before repo) and then loaded from
`~/huggingface/<REPO>/<REVISION>`, where `<REPO>` keeps its org prefix. The
section records the approved-model families as fetched 2026-08-21, the
restrictions (text models with open-source licenses only; unlisted models need a
support ticket), and the GPU-machine note.

This sits next to "Install R Packages" because the two are easy to confuse:
`fbrir`/`CRAN$new()` installs R packages from Meta's CRAN mirror,
`fbri.package_managers.huggingface` downloads models — different package, different
manager.

Sourcing follows the four-tag convention. The Python signatures,
paths and restrictions are **[documented]** from
[Machine Learning Models](https://developers.facebook.com/docs/researcher-platform/features/ml-models).
The reticulate wrapper is **[inferred]** and marked untested — `fbri` is a
different package from `metacontentlibraryapi`, so whether it imports from the
R-side reticulate Python is unverified; the section gives a Python-cell fallback
that works either way. `docs/TESTING_PROCEDURE.md` Test 1.6 settles it.
Inference is deliberately left in Python rather than translated to `do.call()`
and `py_get_item()`.

**Also:** `SKILL.md` § Environment gains a "No internet access" bullet — the fact
both package managers follow from.

## v1.9.1 (2026-08-21)

Patch release. No documented API behavior changed; this removes a silent-failure
class from the skill's own code and files the question behind it.

**Fixed: no status comparison is case-sensitive any more.** The sweep found nine,
failing in two directions. `SKILL.md`'s Async Query Template, `chunking.md` and
the example script used `while (status != "COMPLETE")`, which spins forever
against a lowercase `complete`. `common_patterns.md` used
`while (status == "IN_PROGRESS")`, which is worse — against `in_progress` it
exits on the first check and reads a half-written result as final. `utilities.md`
gated on `status == "COMPLETE"` and would misreport. `docs/TESTING_PROCEDURE.md`
held one of each plus a raw `get_status()` comparison — the worst place for them,
since a tester would have run the broken pattern while verifying the fix. All now
route through `mcl_wait_for_job()` (SKILL.md § "Waiting for a Job"), which
upper-cases and
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

# Open question: did the 2025-11-10 lowercasing reach job status?

**Status: half answered, 2026-08-21.** `mode` is settled — **UPPERCASE**,
verified against the OpenAPI spec inside the SRE. Job **status is still open**,
but it is no longer a documentation question: the spec does not declare it, so
only a live job can answer, which makes it a **Stage 3 item** rather than a recon
one. Do not delete this file until that is recorded.

---

## ANSWERED: `mode` takes `"SNAPSHOT"` / `"LIVE"`, uppercase

**[verified 2026-08-21]** Observed in a live SRE session by calling
`client$openapi_spec()` and searching the serialised spec (512,717 characters):

```
"mode": {"type": "string", "enum": ["LIVE", "SNAPSHOT"],
         "description": "Execution mode of async job, i.e. live mode or snapshot mode"}
```

Five occurrences, **every one inside an `enum` list** — the authoritative form
this file asked for. The 2025-11-10 "enums are now lowercase" note did **not**
reach `mode`.

**Action required: none.** Every example in `mcl-api-r` already passes
`"SNAPSHOT"`. The `grep -rn '"SNAPSHOT"\|"LIVE"'` sweep this file contemplated is
not needed. What *is* worth doing is promoting this from inference to verified in
`CHANGELOG.md`.

### The trap this exposed, which is worth keeping

`mode`'s own `description` says "live mode or snapshot mode" — lowercase — while
its `enum` says `["LIVE", "SNAPSHOT"]`. **Prose casing in this spec is the
opposite of enum casing.** Any inference about `status` drawn from its
description ("in progress, completed, failed, etc.") is therefore worthless.

## STILL OPEN: what `status` returns

**[verified 2026-08-21]** The spec declares no vocabulary for it:

```
"status": {"type": "string",
           "description": "Execution status of the async job, i.e. in progress, completed, failed, etc."}
```

No `enum`. Of the 12 enums in the whole spec, none is a status vocabulary — the
only close match is an unrelated product-availability list.

**[verified 2026-08-21]** `GET async/jobs` returned **zero rows** in the
workspace used for the recon, so `get_status()` could not be observed. Steps 2
and 3 of the diagnostic below are unchanged and still cost nothing — they just
need an environment that has actually run a job.

**Where this now belongs:** the first real run of the client loop submits a
job. Record the literal `get_status()` string then, per
a client's feedback protocol. Note that a lowercase `completed`
(past participle) is at least as likely as `complete`, and neither this file's
original regexes nor `mcl_wait_for_job()`'s comparisons should assume the stem.

**The hazard this described is already fixed.** v1.9.0 replaced every
status comparison in the skill with `mcl_wait_for_job()` (SKILL.md § "Waiting for
a Job"), which upper-cases before comparing, times out, and treats an
unrecognized status as "keep waiting". That is correct under either casing and
needed no answer. What remains is a documentation question — what the API
*actually* returns — worth settling but no longer urgent.

## The question, and why it mattered

The 2025-11-10 REST-ful pass states that "enums are now lowercase." Before
v1.9.0 the skill compared job status case-sensitively in six places, and the two
possible failures were both silent:

- `while (status != "COMPLETE")` against `"complete"` — spins forever, no error.
  This was in `SKILL.md`'s Async Query Template, the most-copied snippet in the
  skill, plus `chunking.md` and the example script.
- `while (status == "IN_PROGRESS")` against `"in_progress"` — exits immediately
  and reads a half-written result as final. This was in `common_patterns.md`,
  and it is the worse of the two: wrong data rather than a hang.

~~Still open: whether `mode` must be `"SNAPSHOT"` or `"snapshot"`, and what
`get_status()` literally returns.~~ **Superseded 2026-08-21** — see the top of
this file. `mode` is `"SNAPSHOT"`; `get_status()` is still unobserved.

## What has already been ruled out (don't redo this)

Fetched 2026-08-21. None of these print a job status or a `mode` value:

| Page | Result |
|------|--------|
| `/docs/content-library-api/quick-start` | Sync `client.get()` only. No async, no `mode`, no status |
| `/docs/content-library-api/overview` | Data scope and geography only |
| `/docs/content-library-api/get-api-code` | Describes the generated code block; does not show it |
| `/docs/content-library-and-api/appendix/api-search-id` | R and Python samples, all sync `preview`. Mentions `POST /facebook/posts/job/{alias_id}` but shows no sample |
| `/docs/content-library-api/guides/*` (all 20) | Surface guides. `bulk-comments` shows `client.post(... /job)` with **no `mode`** |
| `.../guides/async-search`, `/docs/content-library-api/guides/async-search` | 404 — no public async-jobs page exists |

The `metacontentlibraryapi` client is distributed only inside the SRE, so its
source is not on the public web either. **Conclusion: the public documentation
cannot answer this.** Prompt A below exists to catch a page this sweep missed;
expect it to come back negative.

---

## Prompt A — Claude for Chrome, documentation sweep

**Do not run this. Superseded 2026-08-21.** It was written to hunt the public web
for the OpenAPI spec, on the theory that "the spec is where the enum is actually
declared, so this is the highest-value target." That theory was right and the
target was reachable — just not on the public web. `client$openapi_spec()` returns
it from inside the SRE in one call, which is how `mode` was settled. Kept below
only as a record of what was tried.

> Search Meta's Content Library documentation for the literal values the API
> uses for asynchronous job **status** and for the **`mode`** parameter.
>
> I need to know one thing: does the API return job status as `COMPLETE`
> (uppercase) or `complete` (lowercase), and does `mode` take `SNAPSHOT` or
> `snapshot`? A 2025-11-10 changelog entry says "enums are now lowercase" and I
> need to know whether that applied to these two.
>
> Start at https://developers.facebook.com/docs/content-library-and-api/ and
> work outward. I have ALREADY checked and ruled out these pages — do not
> re-read them: the changelog, overview, quick-start, get-api-code,
> api-search-id, and all 20 pages under content-library-api/guides/.
>
> Still worth checking:
> - https://developers.facebook.com/docs/researcher-platform and everything
>   under it (the SRE docs are a separate tree from the API docs)
> - Any page describing the "async jobs tool" added on 2025-11-10 — the
>   changelog names the feature but does not link it
> - Whether the OpenAPI specification is served at a public URL. Try
>   `/docs/content-library-api/openapi`, `.../openapi.json`, `.../spec`, and
>   look for a download link on any API reference page. The spec is where the
>   enum is actually declared, so this is the highest-value target
> - developers.facebook.com/community and any Meta research-platform forum for
>   posts quoting a job status string
>
> Report back with: the exact quoted string and the URL it came from, or
> "not documented" plus the list of pages you checked. Do not guess from other
> Meta APIs — Graph API conventions do not carry over here. Do not attempt to
> log in to anything.

---

## Prompt B — Claude for Chrome, run the check in the SRE

### Read this before running it

The SRE runs in **Amazon WorkSpaces Secure Browser**, which streams a remote
browser as pixels into a canvas. **No browser extension can read the DOM inside that session, and this is a
guarantee of the product rather than a limitation of any particular extension
version.** AWS documents it plainly: "Web content is streamed to the user's web
browser, while the actual browser and web content is isolated in AWS", and the
service "pixel streams web content to the browser, preventing data from residing
on the local device or in the web browser"
([AWS](https://aws.amazon.com/workspaces-family/secure-browser/faqs/)). Only
encrypted pixels cross to your machine. A DOM-based tool — Claude for Chrome,
Playwright, a userscript, anything driving CDP — sees the streaming client's own
`<canvas>`, never JupyterLab's cells. Preventing exactly that is the point of the
product, so this will not change with a newer extension.

What remains architecturally possible is screenshots and keystrokes, since that
is how a human uses the session at all. Whether a given extension sends
keystrokes into the stream *reliably enough to trust unverified* is the open
part, and it is why the diagnostic below is **short enough to type by hand**
rather than a block you paste, and why the prompt makes Claude declare its mode
before it touches anything.

Two further points before you run it:

- Claude will be operating a session authenticated to Meta's research platform.
  Start that session yourself; do not have Claude handle credentials or MFA.
- Confirm that driving the SRE with a browser agent is permitted under your data
  use agreement. The manual fallback is a few lines of typing, so there is no
  cost to choosing it.

The prompt below is written to **adapt** rather than to assume: it asks Claude to
establish up front whether it can type into the streamed session and verify what
landed. If it can, it drives. If it can't, it dictates and reads the output back.
The pixel-streaming constraint is real; how much of it a given extension version
can work around is not something this file asserts.

### The prompt

> I am going to log in to the Meta Content Library Secure Research Environment
> myself. Once I am at the JupyterLab screen, I need your help running a short
> R diagnostic and reading the output back to me exactly.
>
> Context you need: the SRE renders inside Amazon WorkSpaces Secure Browser,
> which pixel-streams a remote browser into a canvas. You will **not** be able
> to read the DOM of anything inside the session — that is by design, not a bug
> to work around, so do not spend turns trying. The clipboard into the session
> may also be disabled.
>
> **Establish one thing before you touch anything: can you send keystrokes into
> the stream and confirm from a screenshot that they landed?** Try it in the
> notebook's first cell with a throwaway line like `1 + 1`. Then declare which
> mode you are in:
>
> - **Drive mode** — you can type and confirm what landed. Type each line, take
>   a screenshot after each one, and compare what you see against what you sent.
>   Stop and tell me the moment they diverge; a mistyped character in a streamed
>   session is easy to miss and expensive to debug.
> - **Dictate mode** — you cannot reliably type or verify. Read me one line at a
>   time and wait for me to confirm I have typed it before giving me the next.
>
> Steps:
> 1. Wait for me to say I am at JupyterLab with an R notebook open and the
>    client set up (`client <- import(...)`,
>    `client$set_default_version(client$LATEST_VERSION)`).
> 2. Screenshot and confirm an empty code cell is visible and focused.
> 3. Work through the diagnostic in whichever mode you established.
> 4. After each cell runs, screenshot the output and transcribe it to me
>    **verbatim, preserving capitalization exactly**. Capitalization is the
>    entire point of this exercise — do not normalize it, do not tidy it, and
>    if a character is ambiguous in the screenshot, say so rather than guessing.
>
> Report at the end:
> - the literal string `get_status()` returned, in brackets
> - the `status` and `mode` values from the jobs table
> - whether `SNAPSHOT`/`snapshot` appeared in the spec as an `enum` value or
>   only inside a prose `description`

### The diagnostic — zero query budget

No job is submitted and no search is run, so this costs nothing against either
the query or the comment budget.

**Step 1 — `mode`, from the spec.** This is the authoritative answer and needs no
API call at all; SKILL.md already directs readers to settle exactly this kind of
question with `openapi_spec()`.

```r
spec <- client$openapi_spec()
s <- tryCatch(reticulate::import("json")$dumps(spec),
              error = function(e) as.character(
                jsonlite::toJSON(spec, auto_unbox = TRUE, null = "null")))
regmatches(s, gregexpr('.{0,60}"(SNAPSHOT|snapshot|LIVE|live)".{0,60}', s, perl = TRUE))
regmatches(s, gregexpr('.{0,60}"(COMPLETE|complete|IN_PROGRESS|in_progress)".{0,60}', s, perl = TRUE))
```

Each match shows up to 60 characters of context, so you can see whether the value
sits in an `enum` list or merely in a prose `description`. **Only an `enum`
occurrence is authoritative.** The `tryCatch` fallback matters: the reticulate
round-trip can choke on nulls, and you do not want that to dead-end the session.

**Step 2 — what a finished job reports.** The spec cannot tell you what the
*client wrapper* returns, and the wrapper is what the skill calls. List your
recent jobs:

```r
jobs <- jsonlite::fromJSON(client$get(path = "async/jobs")$text,
                           flatten = TRUE, bigint_as_char = TRUE)
d <- jobs$data
if (is.numeric(d$id)) d$id <- sprintf("%.0f", d$id)   # else it prints 9.6378e+14
print(d[, intersect(c("id", "status", "state", "mode"), names(d))])
```

Two traps defused there. `bigint_as_char` alone converts an id only when a value
in the batch exceeds 2^53, so a 15-digit job id would print in scientific
notation and the id you copy into step 3 would be rejected with subcode 3790088 —
the trap SKILL.md devotes a section to. And `intersect()` keeps the print from
erroring if the field is named `state`, or if `mode` is absent from the list
payload. Note that `params` is omitted entirely rather than passed as
`list()`, which would fail with `'list' object has no attribute 'items'`.

**Step 3 — the wrapper.** Take any `id` whose status is terminal:

```r
j <- client$get_async_job(job_id = "PASTE_A_FINISHED_JOB_ID")
cat("[", j$get_status(), "]\n")                     # brackets reveal whitespace
cat("a bare != \"COMPLETE\" loop would spin forever:",
    j$get_status() != "COMPLETE", "\n")
```

Steps 2 and 3 can disagree — REST may return `complete` while the wrapper
uppercases it, or the reverse. Record both; the wrapper's answer is the one the
skill's code depends on.

**Optional, and this one costs a query.** If the spec was ambiguous about `mode`,
submit a deliberately empty job with a lowercase value and see whether it is
accepted:

```r
r <- tryCatch(client$post(path = "facebook/posts/job", params = list(
  "q" = "zzqqxxunlikelytokenxxqqzz", "since" = "2026-08-01", "until" = "2026-08-02",
  "limit" = 10L, "mode" = "live",
  "name" = "ENUM CASE TEST", "description" = "delete after reading")),
  error = function(e) e)
print(r)
```

Delete the job afterwards either way.

---

## What to do with the answer

| Outcome | Action |
|---------|--------|
| `COMPLETE` uppercase | Record as verified in `CHANGELOG.md`; delete this file. No code changes — `mcl_wait_for_job()` already handles it |
| `complete` lowercase | Same: no code changes needed, because nothing compares case-sensitively any more. Update the status set in `SKILL.md` § "Core Concepts" to the observed casing and delete this file |
| `mode` requires lowercase | This one **does** need edits — every example passes `"SNAPSHOT"`. Sweep with `grep -rn '"SNAPSHOT"\|"LIVE"' --include=*.md --include=*.R .` and ship a patch release |
| Wrapper and REST disagree | Record both in `field_reference.md`; the wrapper's value is what the skill's code sees |

`docs/TESTING_PROCEDURE.md` Test Suite 11.2 also asks the tester to record the
status string. If you run that suite, you have answered step 3 already — bring
the result back here rather than running it twice.

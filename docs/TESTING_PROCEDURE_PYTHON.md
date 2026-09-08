# MCL API Skill — Python layer testing procedure

> **Version:** 2.0
> **Last Updated:** 2026-09-08
> **Purpose:** Run the R-layer test suites against `languages/python/`. A passing
> test is the promotion path: it turns a `[documented]` section into a
> `[verified DATE]` one.

## Overview

`docs/TESTING_PROCEDURE.md` is the R procedure: thirteen suites, each test
naming the file and section it exercises, the code to paste, the expected
outcome and whether a screenshot is required. **This file does not repeat
it.** The Python layer mirrors the R layer section for section, so every test
there has a Python twin at the same address:

- **Same suite and test numbers.** Python Test 3.2 is R Test 3.2 run from
  `languages/python/jobs.md` § "Async query template". Shared numbering is what
  makes a Python run comparable to the R record.
- **Same location, different directory.** Where the R test's `**Location:**`
  line names `languages/r/<file>.md` § "<Title>", the Python code is
  `languages/python/<file>.md` under the same title. Where it names a
  `references/` section (a fact), the Python code is the section that
  `references/` file's `Code:` line points to.
- **Same expected outcome.** The API does not know which language called it.
  A different outcome is a finding, not a Python quirk — file it (below).

### Testing Environment Requirements

- Meta Research Platform access (Amazon WorkSpaces Secure Browser)
- JupyterLab with a **Python 3 kernel** (`/opt/conda/bin/python3`, 3.11)
- `metacontentlibraryapi` importable from that kernel; pandas available
- MCL API v6.0 access
- Active query budget (check before testing — Test 1.1 is first for a reason)

### Testing Approach

Code cannot be executed automatically. Each test is:

1. Copied from the Python section into a notebook cell on a Python kernel
2. Executed manually
3. Compared with the R test's expected outcome
4. Screenshot captured where the R test requires one
5. Recorded (below) — a run that writes nothing down did not happen

---

## Pre-Testing Setup

### Step 0: Verify Environment

**Location:** `languages/python/setup.md` § "Load the client"

```python
from metacontentlibraryapi import MetaContentLibraryAPIClient as client
import json, re, time
import pandas as pd

client.set_default_version(client.LATEST_VERSION)

# ID-safe parsing helper - required by every test below.
# Paste MCL_ID_PATTERN, mcl_fix_ids(), mcl_from_json() and mcl_load_json()
# from languages/python/ids.md § "mcl_from_json", and mcl_job_status() /
# mcl_wait_for_job() from languages/python/jobs.md § "Waiting for a job".
# Those files are the single canonical copy; do not maintain a second one here.
```

**Expected Outcome:**
- No errors; the import succeeds from the Python kernel without reticulate
- `client.LATEST_VERSION` prints the current version
- The helpers are defined

**Also record, once, in the report:**
- `import sys; sys.executable` and `sys.version` — settles whether the Python
  kernel is the interpreter reticulate binds (open in
  `docs/ML_MODELS_OPEN_QUESTIONS.md` Q2)
- `dir(client)` — the client's real surface; the R layer only ever used
  `get`, `post`, `delete`, `openapi_spec`, `set_default_version`,
  `LATEST_VERSION`, `get_async_job`
- `from metacontentlibraryapi import MetaContentLibraryAPIAsyncUtils` and
  `dir(MetaContentLibraryAPIAsyncUtils)` — what it offers is open

**Screenshot Required:** Yes

### Step 0b: The open questions the R layer could not answer

These cost nothing beyond one sync call and settle things every Python section
currently marks **open**. Run them right after Step 0 and put the answers in
the report:

| Question | How to settle it | Where the answer lands |
|---|---|---|
| What does a response expose beyond `.text`? | `resp = client.get(path="budgets"); print(type(resp)); print([a for a in dir(resp) if not a.startswith("_")])` | `languages/python/jobs.md` § "Async query template" |
| Which exception does an HTTP error raise, and is the error JSON in it? | `try: client.get(path="facebook/posts/preview", params={"surface_ids": "1"}) except Exception as e: print(type(e), e)` — the scalar ID is the intended failure (subcode 3790088 or "Invalid parameter") | `languages/python/common_errors.md` |
| Is `params={}` accepted? Is `params=None`? | `client.get(path="budgets", params={})` then `params=None` | `languages/python/query_params.md` § "Never pass an empty params" |
| Is an integral float rejected? | `client.get(path="facebook/posts/preview", params={"q": "climate", "limit": 5.0})` | `languages/python/query_params.md` § "Integer parameters" |
| Does an empty result carry `"data": []` or omit `data`? | A preview whose `q` is a nonsense token, e.g. `"qzxv1234zz"`; print `list(mcl_from_json(resp.text))` | `languages/python/jobs.md` § "Safe response handling" |
| What is the saved file's shape? | After Test 3.4: `type(mcl_load_json(...))` — `list` means an array of records, `dict` means an envelope | `languages/python/jobs.md` § "Async query template" |
| What does `openapi_spec()` return? | `type(client.openapi_spec())` | `languages/python/query_params.md` § "Reading the OpenAPI spec" |

---

## The suites

Run them in the R procedure's order and numbering. For each test:

| Field | Value |
|---|---|
| **Mirror of** | R Test N.M in `docs/TESTING_PROCEDURE.md` |
| **Code** | `languages/python/<file>.md`, the section whose title matches the R test's Location (or the section the `references/` file's `Code:` line names) |
| **Expected outcome** | identical to the R test's |
| **Screenshot** | as the R test requires |
| **On pass** | stamp that Python section's heading `[verified YYYY-MM-DD]`, replacing its `[documented …]` tag; leave the R stamp untouched |
| **On divergence** | a field report, kind *correction*, language *Python* — see "Recording" below. If the cause is the API, the neutral owner is wrong for both languages; if the cause is the Python call, only `languages/python/` changes |

Suites that do not apply, and why:

| Suite / test | Python status |
|---|---|
| 1.2 Install R packages | R-only. Its Python twin is the pip channel — `languages/python/utilities.md` § "Installing packages": `from fbri.package_managers import Pip; Pip.get_instance().install("pkg")`, expected outcome: the package imports afterwards |
| 5.2 Combining chunked results with `bind_rows` | The mismatched-columns hazard is a `bind_rows` hazard; `pd.concat` aligns columns by name and fills missing ones with `NaN`. Run the Python section anyway and confirm the row count and the ID column dtype (`object`, never `float64`) |
| 9.1 Integer type error (intentional failure) | The R failure is a double reaching Python as `100.0`. The Python twin is the integral-float probe in Step 0b |
| 10.1 Helper unit test (offline) | Runs anywhere, including on your own machine — no SRE needed. Feed `mcl_fix_ids` the R test's fixtures (a 17-digit unquoted ID, a null, a nested `author.id`, a list under `surface_ids`) and assert every ID comes back as `str` and `None` stays `None` |
| 13.x The `link` parameter | Verified from R on 2026-08-29. Run 13.2 (the q-coupling gate) first, as the R procedure says; the rest are promotions |

---

## Recording

A Python run produces two artefacts:

1. **Stamps.** Each passing section's heading in `languages/python/` gains
   `[verified YYYY-MM-DD]` in place of `[documented …]`. That edit, the date,
   and one line per section go into `CHANGELOG.md` under the next version
   (release checklist step 3). No neutral file changes on a pass.
2. **A field report per divergence** — `references/field_report.md` owns the
   shape; the issue form has a Language dropdown. Kind *correction* if the
   Python outcome contradicts the R record, *addition* if it answered one of
   the Step 0b questions, *open* if it is not reproducible.

Never any data. Counts, field names, dtypes, messages and subcodes are fine;
rows are not.

## Before release

Run from the repository root after a Python run, before tagging:

- Every `file.md § "Heading"` reference and every `Code:` line resolves to an
  existing heading in both language files. A `Code:` line names both
  languages, R first, with identical titles.
- Every helper is defined exactly once, under `languages/`, never under
  `references/`: `mcl_fix_ids`, `mcl_fromJSON` / `mcl_from_json`,
  `mcl_load_json`, `mcl_job_status`, `mcl_wait_for_job`, `safe_get_data`,
  `check_ids`, `batch_ids`, `query_with_chunking`, `combine_chunk_results`,
  `collect_latest`, `resolve_originals`, `extract_hashtags`.
- The R and Python mirrors carry the same section titles in the same order;
  a section present in one and absent from the other says why.
- The count of each `error_subcode` across the tree did not go down.

## Test Completion Checklist

- [ ] Step 0 recorded: interpreter, `dir(client)`, `dir(MetaContentLibraryAPIAsyncUtils)`
- [ ] Step 0b: the seven open questions answered and filed
- [ ] Suites 1–13 run in order; each pass stamped, each divergence reported
- [ ] `CHANGELOG.md` entry lists every promoted section
- [ ] "Before release" checks pass

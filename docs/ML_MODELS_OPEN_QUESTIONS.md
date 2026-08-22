# Open question: how ML models actually work in the SRE

**Status: documented, almost nothing verified. 2026-08-22.**
`references/utilities.md` § "Download Machine Learning Models" was written by
transcribing
[Meta's ML models page](https://developers.facebook.com/docs/researcher-platform/features/ml-models)
(fetched 2026-08-21). Every Python signature and path in it is **[documented]**;
the reticulate wrapper is **[inferred]**; *nothing* has been run. This file is
the plan for closing that gap, and the place results get recorded until they are
folded into `utilities.md`.

Tags follow `docs/SRE_AUTOMATION_SURFACE.md`: **[verified]** (observed live, with
date), **[documented]** (stated by Meta, not observed), **[inferred]** (follows
from those, not itself observed), **[open]**.

Delete this file once every question below is answered and the answers live in
`utilities.md` — the same rule `OPEN_QUESTION_ENUM_CASING.md` carried.

---

## The gap inventory

Nothing here costs MCL query budget. The cost column is download size and human
time.

| # | Question | Now | Why it matters | Phase |
|---|----------|-----|----------------|-------|
| 1 | Does `fbri.package_managers.huggingface` import from **R-side reticulate**? | [inferred] | The whole R section rests on it. If no, the Python-cell fallback becomes the primary path | A |
| 2 | Is reticulate's Python the **same interpreter** as the notebook's Python kernel? | [open] | Decides whether a failed import means "unsupported" or "wrong env, fix with `use_python()`" | A |
| 3 | Real **signatures and defaults** of the two helpers | [documented] | We assert `hf_download_file(filename, repo, ...)` — filename first. Reversed is a silent wrong-arg | A |
| 4 | Does the download path **keep the org prefix**? | [inferred] | We tell readers `~/huggingface/facebook/mbart-.../main`. One doc example is the only evidence | A/B |
| 5 | What does `output_dir` replace — the whole path, or the parent? | [open] | Anyone redirecting downloads to scratch space needs this | B |
| 6 | What do the helpers **return**? | [open] | If they return the path, every example should use it instead of rebuilding the path by hand | B |
| 7 | How does an **unapproved** model fail, and is that error distinguishable from a typo'd repo id? | [open] | Test 1.6 depends on telling these apart. So does every reader who mistypes an org | D |
| 8 | The **canonical repo ids** of approved models | [open] | Meta's page names owners ("UKP Lab"), not ids. A reader cannot construct `sentence-transformers/all-MiniLM-L6-v2` from it | A/D |
| 9 | Is the approved list available **programmatically**? | [open] | Would replace our hand-copied table with something that cannot go stale | A |
| 10 | Are any models **pre-downloaded** in the image? | [open] | Changes the first step from "download" to "check first" | A |
| 11 | Does `revision` accept a **commit SHA / branch** other than `main`, and is it validated? | [open] | Pinning a revision is the difference between a reproducible pipeline and a moving one | E |
| 12 | Is a **GPU** actually available, and how is a GPU machine selected? | **[documented 2026-08-22]** — yes: CPU/GPU chosen at server start, switchable via File > Hub Control Panel without losing work. Now in `utilities.md` § "CPU or GPU Server". **Still open:** GPU model, memory, disk, session time limit, whether access is uniform across institutions | Answered the how; specs remain | A/E |
| 13 | Which ML libraries are preinstalled, at what **versions**? | [open] | `from_pretrained` on a new model against an old `transformers` fails confusingly | A |
| 14 | **Disk quota** — will `nllb-200-3.3B` (~17 GB) even fit? | [open] | Determines whether the large translation models are usable at all | A/E |
| 15 | Do downloads **persist across sessions**? | [open] | If home is ephemeral, every session re-downloads and the workflow changes shape | E |
| 16 | Any **egress restriction on model outputs**? | [open] | Embeddings and classifications derived from MCL data still leave via notebook export | F |
| 17 | Is inference realistically drivable **from R**, or is a Python cell the honest recommendation? | [inferred] | utilities.md currently says "leave it in Python". That should be tested, not assumed | C |
| 18 | Do downloads consume any **quota** (MCL or otherwise)? | [inferred] | We claim zero MCL budget. Almost certainly right, worth confirming | B |
| 19 | **Offline gotcha**: does `from_pretrained(local_path)` still try to reach the hub? | [open] | Classic failure: it phones home for `config.json` and hangs. May need `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` | C |
| 20 | How long does a **large** download take? | [open] | Sets expectations, and whether it survives a session timeout | E |

---

## Phases

Each phase is one paste into the SRE and one result back. Ordered so the
cheapest evidence lands first and each phase's design depends on the last.

### Phase A — recon, zero downloads
**Settles 1, 2, 3, 9, 10, 12, 13, 14; likely 4.**
Two cells (R + Python). The R cell reports the interpreter, module availability,
the helpers' real signatures, hardware, disk, and — the important one —
`inspect.getsource()` of both helpers. If `fbri` is plain Python in
site-packages, its source gives the *actual* path construction, the real
`output_dir` default, and any hardcoded approved list, settling several rows
without downloading a byte. The Python cell cross-checks that both languages see
the same interpreter.

### Phase B — one tiny file
**Settles 4, 5, 6, 18.**
`hf_download_file(".gitattributes", "facebook/mbart-large-50-many-to-many-mmt")` —
a few hundred bytes, and the docs' own example. Uses the **only repo id that
appears verbatim** on Meta's page, so the sole unknown under test is where the
file lands, not whether the id was right. Then `find` it and compare against the
path we currently document.

### Phase C — a small model, downloaded and used
**Settles 17, 19; confirms 4.**
Smallest approved model (MiniLM, ~90 MB). Download the repo, load it, embed one
string. Run it from R via reticulate *and* from a Python cell, so the "inference
is easiest in Python" claim is tested rather than asserted. Watch for a hang on
first load — that is question 19 showing up.

### Phase D — the approval boundary
**Settles 7, 8.**
Three downloads, all tiny, all expected to *fail or succeed informatively*:
one approved model with the **right** org prefix, one with a **wrong** prefix,
and one **clearly unapproved but famous** model (`gpt2`). The point is to read
the three error messages side by side and learn whether "not approved", "no such
repo", and "no network" are distinguishable. This is observing a documented
restriction, not working around it.

### Phase E — scale, pinning, persistence
**Settles 11, 14, 15, 20.**
Only worth running if A–D succeed. Download a large approved model, time it, pin
a non-`main` revision, then check whether it is still there in the next session.

### Phase F — the actual research workflow
**Settles 16.**
The payoff phase, and the one that belongs in the skill: pull MCL posts with an
async job, embed or classify them with a local model, and export. This is where
we find out whether the ML section should live next to the query patterns rather
than in `utilities.md`.

---

## Tracking Meta's model list for drift

The approved list **grows** — Meta's page says so, and `references/surfaces.md`
records five surfaces arriving over 18 months. Our table is a hand-copy with a
fetch date, so it is stale the moment Meta edits the page, and nothing tells us.

**Snapshot.** `references/ml_models_approved.md` holds the list exactly as
fetched, with the date. That file is the diff target: a re-fetch that differs
from it is the signal.

**Re-check cadence.** Monthly, plus once before any release that touches the ML
section (added to the `CHANGELOG.md` release checklist).

**What a check does:**
1. Fetch the page.
2. Diff the model list against `references/ml_models_approved.md`.
3. If unchanged: update the "last confirmed" date, nothing else.
4. If changed: update the snapshot, update the `utilities.md` table, note the
   arrival in `CHANGELOG.md` the way `surfaces.md` notes new surfaces.

**Mechanism: a monthly scheduled cloud agent** (decided 2026-08-22). It fetches
the page, diffs against the snapshot, and reports only when something changed —
a quiet month produces a date bump and nothing else. The snapshot file is what
makes the diff possible; without it the agent can only say "here is the list",
which is not a signal.

---

## Recording results

As each phase lands, write the answer **in the table above** with a
`[verified YYYY-MM-DD]` tag, then move the durable version into
`utilities.md` and drop the `[inferred]` banner there. `docs/TESTING_PROCEDURE.md`
Test 1.6 is Phase A/B in test form; extend that suite as phases pass rather than
letting this file become a second home for the same facts.

---

## Leads found while sourcing the GPU answer

The Researcher Platform features index lists pages this skill has never read.
Two bear directly on questions above; recorded so they are not lost:

| Page | Bears on |
|------|----------|
| [Upload files to an S3 bucket](https://developers.facebook.com/docs/researcher-platform/features/S3-bucket) | Question 16 (egress). The skill currently tells readers export is "entire notebook only" — an S3 path would make that wrong |
| [Install Python packages yourself](https://developers.facebook.com/docs/researcher-platform/pip) | `utilities.md` § "Install R Packages" documents only the R side; the Python side is what `fbri` lives in |
| [Export Jupyter notebooks](https://developers.facebook.com/docs/researcher-platform/features/notebook-export) | Confirms or corrects the export claim in `SKILL.md` § Environment |
| [Share R notebooks](https://developers.facebook.com/docs/researcher-platform/features/share-notebooks) | Unexamined |
| [Compare SRE to RStudio](https://developers.facebook.com/docs/researcher-platform/features/r-studio) | Unexamined |

Out of scope for the ML work, in scope for the skill.

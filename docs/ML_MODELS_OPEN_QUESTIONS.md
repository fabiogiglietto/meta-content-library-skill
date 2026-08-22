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
| 1 | Does `fbri.package_managers.huggingface` import from **R-side reticulate**? | **[verified 2026-08-22] YES** — `fbri`, `fbri.package_managers` and `fbri.package_managers.huggingface` all report OK | The whole R section rested on it. Now the supported path, not a guess | **A done** |
| 2 | Is reticulate's Python the **same interpreter** as the notebook's Python kernel? | **[verified 2026-08-22]** reticulate binds `/opt/conda/bin/python3`, Python **3.11** — the shared conda env. Cell A2 still worth running to confirm `sys.executable` matches exactly | Explains *why* Q1 resolves; no `use_python()` needed | **A mostly done** |
| 3 | Real **signatures and defaults** of the two helpers | **[verified 2026-08-22] as documented.** `hf_download_repo(repo: str, revision: str = 'main', output_dir: Optional[str] = None) -> None`; `hf_download_file(filename: str, repo: str, revision: str = 'main', output_dir: Optional[str] = None) -> None` | Filename-before-repo confirmed from source | **A done** |
| 4 | Does the download path **keep the org prefix**? | **[verified 2026-08-22] YES**, read from source: `output_dir = os.path.join(os.path.expanduser("~"), "huggingface", repo, revision)` — `repo` is the full id, org prefix included | Our documented path was right | **A done** |
| 5 | What does `output_dir` replace — the whole path, or the parent? | **[verified 2026-08-22] the WHOLE path.** When set, the `huggingface/<repo>/<revision>` nesting is skipped entirely and files land at `os.path.join(output_dir, filename)` | **Collision hazard:** two models sharing one `output_dir` overwrite each other's like-named files (`config.json`…) | **A done** |
| 6 | What do the helpers **return**? | **[verified 2026-08-22] `None`, both — the docstrings are WRONG.** Full source now read: neither function has a `return` statement, while both docstrings promise "str: The path" | Do not assign the return value — build the path yourself | **A done** |
| 7 | How does an **unapproved** model fail, and is that error distinguishable from a typo'd repo id? | **[verified 2026-08-22] NO — they are IDENTICAL.** Both `gpt2` (real, unapproved) and a nonexistent repo return `HTTPError: 400 Client Error: Bad Request`. No 403, no 404, no message naming approval | A 400 means *either* wrong id *or* unapproved. The reader must disambiguate by hand against the list | **B done** |
| 8 | The **canonical repo ids** of approved models | **[verified 2026-08-22] 12 of 13 resolved** by listing; only #11 DeBERTaV3 resists. **The org prefix is mandatory** — every bare legacy alias (`t5-small`, `bert-base-uncased`, `xlm-roberta-large`, …) returns 400 because the proxy does not follow Hugging Face's rename redirects | Meta's page prints the bare names, so copying its own text produces a 400 | **B done bar #11** |
| 9 | Is the approved list available **programmatically**? | **[verified 2026-08-22] no list function** — but the module exports an **undocumented third function, `hf_list_files(repo, revision)`**, plus the constant `HF_ENDPOINT` | `hf_list_files` probes a repo without downloading it; `HF_ENDPOINT` is where gating must live | **A done** |
| 10 | Are any models **pre-downloaded** in the image? | **[verified 2026-08-22] NO** — `~/huggingface` does not exist on a fresh server. Home is `/home/jovyan`, as documented | First step really is download | **A done** |
| 11 | Does `revision` accept a **commit SHA / branch** other than `main`, and is it validated? | [open] | Pinning a revision is the difference between a reproducible pipeline and a moving one | E |
| 12 | Is a **GPU** actually available, and how is a GPU machine selected? | **[verified 2026-08-22] GPU is real**: `torch 2.4.0+cu118`, `torch$cuda$is_available()` **TRUE** on the tested server. Selection procedure **[documented]** in `utilities.md` § "CPU or GPU Server". **Still open:** GPU model, VRAM, session time limit | Confirmed end to end | **A done** |
| 13 | Which ML libraries are preinstalled, at what **versions**? | **[verified 2026-08-22]** `transformers` OK, `torch` OK, **`sentence_transformers` NOT AVAILABLE**. Versions still unread (section 4 not yet seen) | The missing one bites: Meta lists two Sentence-Transformers models that the usual `SentenceTransformer()` call cannot load | **A partly done** |
| 14 | **Disk quota** — will `nllb-200-3.3B` (~17 GB) even fit? | **[verified 2026-08-22]** `/home/jovyan` on `/dev/nvme2n1`: **32G total, 8.6G used, 23G available (28%)**; RAM 64 GB | Fits with ~6 GB spare — two large models will not coexist | **A done** |
| 15 | Do downloads **persist across sessions**? | [open] | If home is ephemeral, every session re-downloads and the workflow changes shape | E |
| 16 | Any **egress restriction on model outputs**? | [open] | Embeddings and classifications derived from MCL data still leave via notebook export | F |
| 17 | Is inference realistically drivable **from R**, or is a Python cell the honest recommendation? | [inferred] | utilities.md currently says "leave it in Python". That should be tested, not assumed | C |
| 18 | Do downloads consume any **quota** (MCL or otherwise)? | **[verified 2026-08-22]** the traffic goes to `prod-fortapis-graph-api.fb-researchtool.com`, a different host from the MCL API, and touches no MCL endpoint. No budget interaction | Confirmed by the endpoint value | **B done** |
| 19 | **Offline gotcha**: does `from_pretrained(local_path)` still try to reach the hub? | [open] | Classic failure: it phones home for `config.json` and hangs. May need `HF_HUB_OFFLINE=1` / `TRANSFORMERS_OFFLINE=1` | C |
| 20 | How long does a **large** download take? | [open] | Sets expectations, and whether it survives a session timeout | E |

---

## Results log

### Phase A, run 2026-08-22 — partial

Read off a live session by screenshot (see the automation note below). Sections
1, 2 and 5 captured; **sections 3, 4 and 6 not yet read** — the signatures, the
torch/CUDA lines and the `getsource()` dump are still outstanding, and section 6
is the one that could settle questions 4, 5 and 9 at a stroke.

```
== 1. which python is reticulate using ==
  python                 /opt/conda/bin/python3
  version                3.11

== 2. module availability ==
  metacontentlibraryapi              OK
  fbri                               OK
  fbri.package_managers              OK
  fbri.package_managers.huggingface  OK
  transformers                       OK
  torch                              OK
  sentence_transformers              NOT AVAILABLE
```

Also observed on the session chrome: R **4.5.3**; kernels offered are Python 3
(ipykernel), Julia 1.12, Pluto, R and Stata; status bar reads
`Disk: 8.51 / 31.20 GB | Mem: 1.51 / 64.00 GB`.

**The `sentence_transformers` gap is the actionable surprise.** Two of Meta's
thirteen approved models are Sentence-Transformers models, and the library that
normally loads them is absent — so the obvious `SentenceTransformer(path)` call
fails on a model Meta approves. `utilities.md` now says so.

### Phase A, completed 2026-08-22 — sections 3-6

```
== 3. the huggingface helper ==
  module file       /opt/conda/lib/python3.11/site-packages/fbri/package_managers/huggingface.py
  hf_download_repo  (repo: str, revision: str = 'main', output_dir: Optional[str] = None) -> None
  hf_download_file  (filename: str, repo: str, revision: str = 'main', output_dir: Optional[str] = None) -> None
  exports           HF_ENDPOINT, Optional, Sequence, hf_download_file, hf_download_repo,
                    hf_list_files, os, requests

== 4. hardware ==
  torch version     2.4.0+cu118
  cuda available    TRUE

== 5. filesystem ==
  home                   /home/jovyan
  ~/huggingface exists   FALSE
  free space             /dev/nvme2n1  32G  8.6G  23G  28%  /home/jovyan
```

The source dump, which is what made the rest of the table collapse:

```python
def hf_download_repo(repo, revision="main", output_dir=None) -> None:
    files = hf_list_files(repo, revision)
    for file in files:
        hf_download_file(file, repo, revision, output_dir)

def hf_download_file(filename, repo, revision="main", output_dir=None) -> None:
    URL = f"{HF_ENDPOINT}/{repo}/resolve/{revision}/{filename}"
    if output_dir is None:
        output_dir = os.path.join(
            os.path.expanduser("~"), "huggingface", repo, revision
        )
    filepath = os.path.join(output_dir, filename)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    print(f"Downloading '{repo}/{filename}' to '{output_dir}'...")
    response = requests.get(URL, allow_redirects=True, stream=True)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded_size = 0
    with open(filepath, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024 * 1024):   # 1 MB
            if chunk:
                f.write(chunk)
                downloaded_size += len(chunk)
                print(
                    f"Downloading '{repo}/{filename}' to '{output_dir}': "
                    f"{downloaded_size / total_size * 100:.2f}%",
                    end="\r",
                )
    print(f"\nDownload Finished to '{output_dir}'")
```

That is the whole function — **no `return` statement**, confirming the `-> None`
annotation over the docstring.

**Four things fall out of those twelve lines.**

1. **The documented path is right, and now for a stated reason.** `repo` goes
   into the path whole, org prefix included. `~/huggingface/<repo>/<revision>`.
2. **`output_dir` replaces the entire path**, not the parent — the
   `huggingface/<repo>/<revision>` nesting is skipped when you pass it. Two
   models pointed at one `output_dir` will overwrite each other's `config.json`.
   Give each model its own directory.
3. **The docstrings are wrong about the return value.** Both functions are
   annotated `-> None` while both docstrings promise `str: The path to the
   downloaded …`. `hf_download_repo` has no `return` statement at all, so it is
   `None` for certain. `hf_download_file`'s tail is still unread, so whether it
   returns `filepath` despite the annotation is the one loose end. **Build the
   path yourself either way** — that is what `utilities.md` already tells
   readers to do.
4. **There is a third, undocumented function: `hf_list_files(repo, revision)`.**
   Meta's page never mentions it. `hf_download_repo` is a thin loop over it, so
   it probes a repo — and therefore the approval gate — **without downloading
   anything**. That makes it a better Phase B probe than fetching
   `.gitattributes`.

**Two hazards visible in the tail**, both worth a reader's attention:

- **Division by zero if the response has no `content-length`.**
  `total_size = int(response.headers.get("content-length", 0))` defaults to
  **0**, and the very first chunk then evaluates `downloaded_size / total_size`.
  A response served chunked, or a proxy that strips the header, raises
  `ZeroDivisionError` on the first megabyte. *Whether Meta's proxy always sends
  `content-length` is unconfirmed* — this is read from source, not observed. But
  it is a real branch, and it fires **after** the first write.
- **A failed download leaves a partial file, and nothing cleans it up.** The
  file is opened `"wb"` before the loop, so any mid-loop failure — the
  `ZeroDivisionError` above, a dropped connection, a full disk — leaves a
  truncated file sitting at the final path. There is no checksum, no `.tmp`
  staging, no resume, and no size check afterwards. A later
  `from_pretrained()` then fails on a corrupt weight file rather than on a
  missing one, which is a much more confusing error.

  **Practical consequence:** after any download that did not print
  `Download Finished`, delete the target directory and start again. Do not trust
  a file's mere existence.

**Where the approval gate must live:** every request goes to
`{HF_ENDPOINT}/{repo}/resolve/{revision}/{filename}`. There is no allow-list in
this module — no list of model names, no check before the request. So approval is
enforced **server-side at `HF_ENDPOINT`**, a Meta-controlled proxy, and an
unapproved model must fail as an HTTP error surfaced by `raise_for_status()`.
Reading `HF_ENDPOINT`'s value and provoking that error is now Phase B/D.

### Phase B, run 2026-08-22 — done, and it folded in most of D

Zero downloads: `hf_list_files` asks the endpoint what a repo contains.

```
HF_ENDPOINT: https://prod-fortapis-graph-api.fb-researchtool.com/public/external-proxy/https://huggingface.co

facebook/mbart-large-50-many-to-many-mmt   [approved, verbatim]
   -> OK  12 files  |  .gitattributes, README.md, config.json, flax_model.msgpack
facebook/nllb-200-distilled-600M           [approved, org GUESSED]
   -> OK   9 files  |  .gitattributes, README.md, config.json, generation_config.json
sentence-transformers/all-MiniLM-L6-v2     [approved, org GUESSED]
   -> OK  30 files  |  .gitattributes, 1_Pooling/config.json, README.md, config.json
facebook/mbart-large-50-many-to-many-XXX   [typo: no such repo]
   -> ERR requests.exceptions.HTTPError: 400 Client Error: Bad Request for url:
          .../public/external-proxy/https://huggingface.co/api/models/facebook/mbart-large-5…
gpt2                                       [real model, NOT on the list]
   -> ERR requests.exceptions.HTTPError: 400 Client Error: Bad Request for url:
          .../public/external-proxy/https://huggingface.co/api/models/gpt2/revision/main
```

**The endpoint is a Meta-operated reverse proxy in front of huggingface.co**,
on `fb-researchtool.com` — a different host from the MCL API, which is why none
of this touches query budget. Two URL shapes are now known:

| Call | URL |
|------|-----|
| list | `{HF_ENDPOINT}/api/models/{repo}/revision/{revision}` |
| download | `{HF_ENDPOINT}/{repo}/resolve/{revision}/{filename}` |

**Both guessed org prefixes were right.** `facebook/nllb-200-distilled-600M` and
`sentence-transformers/all-MiniLM-L6-v2` resolve, so two more of Meta's thirteen
now have confirmed ids. More importantly, `hf_list_files` means **nobody ever has
to guess again** — it costs nothing and answers in one call.

**The finding that changes our guidance: an unapproved model and a typo are
indistinguishable.** `gpt2` is a real, public, resolvable repo; a nonexistent
mbart variant is not. Both come back `400 Client Error: Bad Request`. The proxy
does gate — the three approved repos returned listings — but it reports *every*
refusal the same way. No 403, no 404, no message mentioning approval.

So a researcher who sees a 400 cannot tell whether they mistyped the org prefix
or picked a model Meta has not approved, and the error will not tell them. That
ambiguity is exactly what `TESTING_PROCEDURE.md` Test 1.6 was written to worry
about; it is now confirmed real rather than hypothetical, and the fix is
procedural: **check the id against `ml_models_approved.md` first, then treat a
400 as "not approved".**

### Phase B2, run 2026-08-22 — repo ids resolved, 12 of 13

Sixteen probes, nothing downloaded. Every bare legacy alias failed and every
org-qualified form succeeded:

```
#1  OK  12  facebook/nllb-200-3.3B
#3  ERR 400 t5-base            | OK  11  google-t5/t5-base
#4  ERR 400 t5-small           | OK  20  google-t5/t5-small
#5  ERR 400 bert-base-uncased  | OK  16  google-bert/bert-base-uncased
#6  OK   9  facebook/mbart-large-50
#9  ERR 400 distilbert-base-uncased-finetuned-sst-2-english
    OK  17  distilbert/distilbert-base-uncased-finetuned-sst-2-english
#10 ERR 400 xlm-roberta-large  | OK  17  FacebookAI/xlm-roberta-large
#11 ERR 400 microsoft/deberta-v3-base   ERR 400 microsoft/deberta-v3-large
#12 OK   9  microsoft/mdeberta-v3-base
#13 OK  28  sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

**The proxy does not follow Hugging Face's legacy-name redirects.** That is the
practical headline: the bare names are what Meta's own page prints in its
parentheticals and what every tutorial uses, and they all 400 — indistinguishably
from "not approved".

**#11 is a genuine open question, not a guessing failure.** `microsoft/mdeberta-v3-base`
lists fine while `microsoft/deberta-v3-base` and `-large` do not, so the org is
right and the gate is per-model. Either an unguessed variant is the approved one,
or the page lists something the allow-list lacks. Since a 400 cannot separate
those, **probing cannot settle it** — this one needs a support ticket.

### Automation note — how this was read

**[verified 2026-08-22]** `SRE_AUTOMATION_SURFACE.md` § 1 established that the
accessibility tree is empty, so `read_page` yields nothing from inside the
session. **Screenshots do work**: the AppStream pixel stream renders into a
capturable surface, and notebook output is legible in a screenshot. Clicking the
streamed browser's tab strip also works.

**Scrolling does not.** Every `scroll` sent to the stream (three attempts, two
coordinates) bounced the streamed browser to a different tab instead of moving
the notebook. So the practical channel is: Claude can *see* any pane the human
puts on screen, and can click, but the human drives scrolling. That is enough to
run the rest of the testing plan without transcription.

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

**Two mechanisms, deliberately** — they fail in different directions:

| | Fires when | Catches | Misses |
|---|---|---|---|
| **At use** — instruction in `utilities.md` and `SKILL.md` | someone asks what models are available | drift at the exact moment it would mislead a researcher | drift nobody happens to ask about; anything when Claude has no web access |
| **Monthly** — scheduled agent | 1st of the month, unattended | drift nobody asked about; keeps the snapshot honest | up to a month of lag |

Neither alone is enough: the at-use check only runs if someone asks, and the
monthly check only runs monthly.

**Re-check cadence.** Monthly, plus once before any release that touches the ML
section (added to the `CHANGELOG.md` release checklist).

**What a check does:**
1. Fetch the page.
2. Diff the model list against `references/ml_models_approved.md`.
3. If unchanged: update the "last confirmed" date, nothing else.
4. If changed: update the snapshot, update the `utilities.md` table, note the
   arrival in `CHANGELOG.md` the way `surfaces.md` notes new surfaces.

**Mechanism: a monthly scheduled cloud agent** — live since 2026-08-22.

| | |
|---|---|
| Routine | `trig_015jzBacsSw43Np7E23p3obe` — [console](https://claude.ai/code/routines/trig_015jzBacsSw43Np7E23p3obe) |
| Schedule | `0 7 1 * *` — 1st of the month, 07:00 UTC / 09:00 Europe/Rome |
| Target | this branch, `docs/sre-ml-models` |
| On change | opens a PR against this branch updating the snapshot, the `utilities.md` table and `CHANGELOG.md` |
| On no change | writes nothing; the run log is the record |

### Merge-time checklist for this branch

The routine and the branch are coupled to each other in ways that break
**silently** — a check that stops reporting is indistinguishable from a quiet
month. Work through all four before deleting the branch:

- [ ] **Re-point the routine at `main`.** Its prompt names
      `docs/sre-ml-models` and checks it out by name; deleting the branch after
      merge breaks the check with no error anyone sees.
- [ ] **Update the routine's CHANGELOG target.** The prompt tells the agent to
      add its bullet under the heading ``## Unreleased — branch
      `docs/sre-ml-models` `` — and that heading is *renamed to a version number*
      at merge, by design. After merge the agent looks for a heading that no
      longer exists.
- [ ] **Assign the version number and bump all three stamps** — `SKILL.md`
      frontmatter, the `> **Skill Version:**` line, `README.md`. They currently
      read **1.10.0** because this branch deliberately left its number
      unassigned; release-checklist item 1 cannot be satisfied until someone
      picks it.
- [ ] **Check the number against `docs/stage3-first-run`**, which already claims
      **v1.11.0**. Whichever merges second takes the next number. It fetches
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

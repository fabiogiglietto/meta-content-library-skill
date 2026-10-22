# MCL API Utilities

> All examples parse responses with the language's ID-safe helper —
> `languages/r/ids.md` § "mcl_fromJSON" / `languages/python/ids.md`
> § "mcl_from_json". It keeps every ID field a string; a raw parse turns IDs
> into floats.

Facts about the SRE's utilities, verified from R except where a section
carries its own sourcing tag ([documented] / [inferred]), which means it was
transcribed rather than run. The calls themselves are in
`languages/r/utilities.md` and `languages/python/utilities.md`.

## Check Quota Status

`GET budgets` returns one object per pool. For the `queries` pool (posts,
pages, groups, events, accounts) read `total_usage` and `max_usage_limit` and
report the difference as available records; report
`preallocated_rows_for_running_queries` when it is above zero; then do the
same for the separate `comments` pool.

Code: `languages/r/utilities.md` § "Check quota status" · `languages/python/utilities.md` § "Check quota status"

### Observed response shape

[verified 2026-09-02]

```json
{
  "timestamp": "Wednesday, September 02, 2026 12:48:07 PM CEST",
  "queries":    { "current_usage": 309000, "preallocated_rows_for_running_queries": 0,
                  "total_usage": 309000, "max_usage_limit": 1000000 },
  "comments":   { "current_usage": 246000, "preallocated_rows_for_running_queries": 0,
                  "total_usage": 246000, "max_usage_limit": 1000000 },
  "multimedia": { "total_usage": 0, "max_usage_limit": 1000 }
}
```

Three things the four-field description above does not cover:

- There is a top-level **`timestamp`**, server-side, formatted in the account's
  locale — useful for pinning a reading to a moment without trusting the client.
- There is a **third pool, `multimedia`**, carrying only *two* fields and a
  1,000 ceiling. It is not governed like the other two and is **cleanroom-only,
  not available in the SRE** (SKILL.md § "Rate Limits & Budget").
- `current_usage` equalled `total_usage` in this read, with
  `preallocated_rows_for_running_queries` at 0 and nothing in flight — which is
  what makes the pair worth reading together: a gap between them means budget is
  reserved by a running job and is not coming back.

**The pool is per *account*, not per study.** On an account running two studies
concurrently, 85% of trailing-7-day query usage belonged to the other one.
Compute headroom from the endpoint at submission time; never reason from what
your own study has spent.

### Quota Thresholds

Read as fractions of `max_usage_limit`, not as absolute counts — the ceiling is
per-account (see "Quota increases" below). The record column is the 500,000
default worked out.

| Share of limit | At the 500k default | Status | Recommendation |
|----------------|---------------------|--------|----------------|
| >= 40% | >= 200,000 | Excellent | Full analysis |
| >= 20% | >= 100,000 | Good | Moderate analysis |
| >= 10% | >= 50,000 | Fair | Reduced parameters |
| >= 2% | >= 10,000 | Low | Minimal analysis |
| < 2% | < 10,000 | Critical | Wait for reset |
| <= 0 | <= 0 | Over quota | Cannot run queries |

### Quota Reset
- **Rolling window**: 7 days
- Each query's usage expires exactly 7 days after submission
- Check daily to see quota freeing up

### Quota increases

`max_usage_limit` is a per-account setting, not an API constant. Meta support
raises it on request — as a **doubling, for three months at a time**, applied to
the Content Library UI and the API together. The grant carries an expiry date,
and the limit reverts silently when it passes: code that compared against a
hard-coded 500,000 will not notice either the increase or the reversion. Always
compute headroom from the endpoint.

**The doubling is real and reaches the API** — verified 2026-09-02 on a raised
account, which read `max_usage_limit: 1000000` on **both** the `queries` and
`comments` pools. It is not a UI-only change.

**The expiry is not exposed.** `budgets` returns **no expiry, end-date or grant
field of any kind**. The reversion is therefore undetectable from the API except
by watching `max_usage_limit` itself change value. So:

> **Record `max_usage_limit` at the start of every collection window** and treat
> a drop as an event that forces re-planning, not as an anomaly. A window sized
> against a raised ceiling and executed after reversion will overrun with no
> error raised — the ceiling is enforced, but its change is not announced.

[doubling, and that it reaches the API: **verified 2026-09-02** · three-month
term and silent reversion: documented from Meta support 2026-08-31, not yet
observed]

## Installing packages

The SRE has no direct route to CRAN or PyPI: standard `install.packages()`
and `pip install` do not work. Meta ships package managers that *are* the
connection — `fbrir` on the R side (a custom CRAN mirror, and a conda-forge
channel), `fbri.package_managers.Pip` on the Python side (a private PyPI
mirror), plus the Hugging Face helper for models. The four channels, their
proxies and their gotchas are in § "The package-manager table above is
incomplete — there are four channels, not two" below.

Code: `languages/r/utilities.md` § "Installing packages" · `languages/python/utilities.md` § "Installing packages"

## Download Machine Learning Models

> ### Check this list is current before you answer
>
> **Whenever the question is which models are available** — "can I use X?",
> "what's approved?", "is there an embedding model?" — re-fetch
> [Meta's ML models page](https://developers.facebook.com/docs/researcher-platform/features/ml-models)
> and compare it against `references/ml_models_approved.md` **before answering**.
> The list grows, and the table below is a hand transcription with a date on it.
>
> - **Fetched, and it matches the snapshot** → answer from it; say nothing about
>   the check.
> - **Fetched, and it differs** → answer from what you fetched, not from this
>   file. Tell the user the skill's copy is stale, and offer to update the
>   snapshot, the table below, and `CHANGELOG.md`.
> - **No web access** → answer from the snapshot and say so, with the date it
>   was last confirmed. A stale answer labelled stale is fine; one presented as
>   current is not.
>
> This costs one fetch and prevents the failure the whole section is built to
> avoid: telling a researcher a model is unavailable when Meta added it last
> month. A monthly scheduled agent catches drift nobody asked about
> (`docs/ML_MODELS_OPEN_QUESTIONS.md`); this catches it at the moment it would
> mislead someone.
>
> **You have web access here even though the SRE does not.** The no-internet
> rule below applies to code executed inside the SRE, not to you — you are
> running on the researcher's own machine.

Two package managers sit side by side in the SRE, and they are not
interchangeable:

| You want | Use |
|----------|-----|
| An R package from CRAN | `fbrir` → `CRAN$new()$InstallPackages()` (§ "Installing packages") |
| A pre-trained model from Hugging Face | `fbri.package_managers.huggingface` (below) |

**The rule the rest of this section follows from: the SRE has no internet
access** (SKILL.md § Environment). `from_pretrained("facebook/mbart-large-50-many-to-many-mmt")` cannot
reach huggingface.co and will fail. You download an **approved** model first
through the `fbri` helper, then load it from its local path.

> **[documented]** — the Python signatures, paths and restrictions below are
> transcribed from
> [Machine Learning Models](https://developers.facebook.com/docs/researcher-platform/features/ml-models)
> (fetched 2026-08-21). **The import works from R: [verified 2026-08-22]** in a
> live SRE session — see "Calling the helper from either kernel". The download *call* itself is
> still untested.

### Downloading, as documented

Two functions in `fbri.package_managers.huggingface`:
`hf_download_repo(repo, revision="main", output_dir=None)` fetches a whole
repository, and `hf_download_file(filename, repo, revision="main",
output_dir=None)` fetches one file — **note the argument order: filename
first, then repo**.

Code: `languages/r/utilities.md` § "Downloading a model" · `languages/python/utilities.md` § "Downloading a model"

Downloads land in `~/huggingface/<REPO>/<REVISION>` — where `<REPO>` keeps its
**org prefix**, so the default revision of the model above is at
`/home/jovyan/huggingface/facebook/mbart-large-50-many-to-many-mmt/main`.
Dropping the `facebook/` gives a path that does not exist.

**[verified 2026-08-22]** — read from the module's own source
(`/opt/conda/lib/python3.11/site-packages/fbri/package_managers/huggingface.py`),
not inferred:

```
if output_dir is None:
    output_dir = os.path.join(os.path.expanduser("~"), "huggingface", repo, revision)
filepath = os.path.join(output_dir, filename)
```

Three consequences worth knowing before you rely on either function:

- **`output_dir` replaces the whole path, not the parent.** Pass it and the
  `huggingface/<repo>/<revision>` nesting disappears entirely — files land
  directly in the directory you named. **Give every model its own `output_dir`**,
  or two models will overwrite each other's `config.json`, `tokenizer.json` and
  friends with no warning.
- **Neither function returns the path**, whatever their docstrings say. Both are
  annotated `-> None`, neither has a `return` statement, and both docstrings
  promise `str: The path to the downloaded …`. Build the path yourself, as the R
  example below does. Assigning the result gets you `NULL`.
- **There is a third, undocumented function: `hf_list_files(repo, revision)`.**
  Meta's page does not mention it, and `hf_download_repo` is just a loop over it.
  Use it to check a repo id — and your access to it — **before** committing to a
  multi-gigabyte download. Code: `languages/r/utilities.md` § "Listing a repo's
  files" · `languages/python/utilities.md` § "Listing a repo's files".

**Verify a download finished before you use it.** The helper streams to the
final path with no staging file, no checksum and no resume, and nothing cleans
up after a failure — so a dropped connection or an error mid-download leaves a
**truncated file that looks present**. `from_pretrained()` then fails on a
corrupt weight file, which is far more confusing than a missing one.

The function prints `Download Finished to '<dir>'` on success. **If you did not
see that line, delete the directory and download again** — do not treat a file's
existence as evidence it is complete.

Code: `languages/r/utilities.md` § "Cleaning up a failed download" · `languages/python/utilities.md` § "Cleaning up a failed download"

**`hf_download_repo` downloads every file in the repo — budget ~10× the weights.**
**[measured 2026-08-22]** `all-MiniLM-L6-v2`, whose PyTorch weights are about
90 MB, consumed **931 MB** and 57 seconds: the loop pulls `model.safetensors`
*and* `onnx/model_O1.onnx`, `onnx/model_O2.onnx`, OpenVINO, TensorFlow and Rust
variants indiscriminately. There is no format filter.

With ~23 GB of home directory available that matters. For anything large, list
first and fetch only what you need — the config, tokenizer, vocab and
special-tokens files plus the `.safetensors` weights.

Code: `languages/r/utilities.md` § "Fetching only the files you need" · `languages/python/utilities.md` § "Fetching only the files you need"

Throughput measured at roughly **16 MB/s**, so a 17 GB repository is on the order
of 18 minutes.

There is also a **division-by-zero branch** in the progress printer: it reads
`content-length` from the response, defaults it to `0` when absent, and divides
by it on the first megabyte. If a download dies with `ZeroDivisionError` after
printing nothing, that is what happened — the bytes were being written, so clean
up as above and consider fetching the files individually with `hf_download_file`.

**How approval is enforced — and why the error will not help you.**
**[verified 2026-08-22]** `HF_ENDPOINT` is a Meta-operated reverse proxy in front
of Hugging Face:

```
https://prod-fortapis-graph-api.fb-researchtool.com/public/external-proxy/https://huggingface.co
```

The module holds **no allow-list at all**, so approval is enforced entirely at
that proxy. It is a different host from the MCL API, which is why none of this
touches your query budget.

> **A refused model and a mistyped one look exactly the same.** Both return
> `requests.exceptions.HTTPError: 400 Client Error: Bad Request`. `gpt2` — a
> real, public model that is simply not on Meta's list — and a repo id that does
> not exist anywhere give the **identical** status and message. There is no 403,
> no 404, and nothing naming approval.

**Read the status code first — 400 and 404 mean different things:**

| Status | Meaning | Next step |
|--------|---------|-----------|
| **400** | Repo-level: the id is wrong **or** the model is not approved. These are *indistinguishable* | Check the id against `references/ml_models_approved.md`, then the org prefix |
| **404** | The repo resolved **and passed the approval gate** — only the *revision* is wrong | Fix the revision. The model itself is available to you |

A 404 is good news about the model. A 400 is the ambiguous one, and you work it
out in this order:

1. **Check the id against `references/ml_models_approved.md`.** If the model is
   not on Meta's list, a 400 is the expected answer and the route forward is a
   support ticket with a use-case justification.
2. **If it is on the list, suspect the org prefix** — copy the id exactly as
   Meta's page prints it (it has printed the full `org/repo` since 2026-10), not
   from a tutorial. Check it with `hf_list_files()`, which costs nothing —
   `sentence-transformers/all-MiniLM-L6-v2` at `main` lists 30 files.

3. **If it is a multimedia model (§ "Multimedia models" below), check your
   environment.** Those six are approved for Meta Content Library API
   environments only. **[inferred]** Elsewhere in the SRE they should fail like
   any unapproved model — a 400.

A revision mistake never reaches this ladder — it announces itself as a 404.

### Pinning a revision for reproducible work

**[verified 2026-08-22]** `revision` accepts a **full 40-character commit SHA and
the 7-character short form**, and a pinned download gets its **own directory**
beside `main/` — so a pinned pipeline cannot be quietly changed by a later `main`
download, and both can coexist.

Resolve the current commit without downloading anything — `GET
{HF_ENDPOINT}/api/models/{REPO}/revision/main` through the proxy returns
`sha` (e.g. `1110a243fdf4706b3f48f1d95db1a4f5529b4d41`) — then download with
that SHA as the `revision`; the files land in `~/huggingface/{REPO}/{SHA}`.

Code: `languages/r/utilities.md` § "Pinning a revision" · `languages/python/utilities.md` § "Pinning a revision"

That metadata call also returns `lastModified`, `tags`, `pipeline_tag`,
`library_name`, `downloads` and `author` — the proxy passes Hugging Face's model
info through intact.

**Record the SHA in your analysis script**, not just the model name. `main` moves;
a SHA does not, and it is what makes a re-run reproducible a year later.

**Budget for two copies.** A pinned revision does not replace `main/` — it sits
next to it. MiniLM at `main` plus one pinned SHA is ~1.9 GB, not 931 MB.

### Always use the org-qualified repo id

**[verified 2026-08-22] — this is the mistake most likely to cost you an hour.**
Bare legacy model names return `400`, the same error as an unapproved model.
Hugging Face redirects them to their canonical org-qualified repos; **Meta's
proxy does not follow that redirect.**

**Since 2026-10-12 Meta's page prints the full id for every entry** ("Use each
repository ID as shown") — copy from there and you are safe. The table below is
for ids taken from tutorials, model cards and older notes, which still use the
bare forms (as Meta's own page did until then):

| Tutorials print | You must use |
|--------------------|--------------|
| `t5-base` / `t5-small` | `google-t5/t5-base` / `google-t5/t5-small` |
| `bert-base-uncased` | `google-bert/bert-base-uncased` |
| `distilbert-base-uncased-finetuned-sst-2-english` | `distilbert/distilbert-base-uncased-finetuned-sst-2-english` |
| `xlm-roberta-large` | `FacebookAI/xlm-roberta-large` |
| `all-MiniLM-L6-v2` | `sentence-transformers/all-MiniLM-L6-v2` |

The full table — nineteen entries, nineteen ids, the page's printed id and its
href agreeing in every case — is `references/ml_models_approved.md`.
`hf_list_files()` then confirms in one free call that the id is downloadable from
your environment.

### Calling the helper from either kernel

**[verified 2026-08-22]** — `fbri`, `fbri.package_managers` and
`fbri.package_managers.huggingface` all import from R-side reticulate in a live
SRE session. reticulate binds to `/opt/conda/bin/python3` (Python **3.11**), the
same conda environment the notebook kernels use, which is why the import
resolves. Importing it from R is therefore the supported path, not a guess. The
**download call** has not been run yet — that is Phase B in
`docs/ML_MODELS_OPEN_QUESTIONS.md`.

A Python cell remains valid if anything goes wrong on the R side — run the
download there and use the model path from R; the files are on disk either
way.

Code: `languages/r/utilities.md` § "Downloading a model" · `languages/python/utilities.md` § "Downloading a model"

**One preinstalled-library gotcha, [verified 2026-08-22]:** `transformers` and
`torch` are available, but **`sentence_transformers` is NOT**. Models Meta lists
under Sentence-BERT / Sentence-Transformers (`all-MiniLM-L6-v2`,
`paraphrase-multilingual-MiniLM-L12-v2`) therefore cannot be loaded with the
`SentenceTransformer(...)` one-liner most tutorials use. Load them through
`transformers` directly (`AutoModel` + `AutoTokenizer`, then mean-pool the token
embeddings yourself), or install the package first — § "Installing packages".

### Inference from R works — [verified 2026-08-22]

An earlier version of this section said inference was "easiest left in Python".
**That was wrong, and it is corrected here.** The `**kwargs` unpacking that made
Meta's example look awkward is avoidable: pass the tensors by name. Loading and
embedding took 0.7 s in total, entirely from R. The recipe: load
`AutoTokenizer` and `AutoModel` from the local model directory, tokenize with
padding and truncation as PyTorch tensors, run the model with `input_ids` and
`attention_mask`, then mean-pool `last_hidden_state` under the attention mask
— what SentenceTransformer does internally, and what you must do yourself
because it is not installed. The result is one 384-dimensional row per text.

Code: `languages/r/utilities.md` § "Inference with transformers" · `languages/python/utilities.md` § "Inference with transformers"

**No offline configuration is needed.** `from_pretrained()` on a local path does
not contact the hub — it loaded in 0.1 s with no `TRANSFORMERS_OFFLINE` or
`HF_HUB_OFFLINE` set. If a load ever *hangs*, that is the symptom to suspect, but
it did not occur here.

For **generation** models (mBART, NLLB, T5) the same approach applies, but
`generate()` takes `forced_bos_token_id = tokenizer$lang_code_to_id["de_DE"]`,
which needs `py_get_item(tok$lang_code_to_id, "de_DE")` in reticulate. A Python
cell is genuinely simpler for that one argument; embedding and classification are
not affected.

### Approved models

Only models on Meta's approved list can be downloaded. **As fetched 2026-10-21
the list has 19 entries, one repository each, in two groups** — 13 available in
every SRE environment, and 6 multimedia models (added 2026-10-12) available only
in **Meta Content Library API environments**. Repo ids are exactly as Meta's page
prints them:

| Use | Repo id | Where |
|-----|---------|-------|
| Translation | `facebook/nllb-200-3.3B`, `facebook/nllb-200-distilled-600M`, `facebook/mbart-large-50`, `facebook/mbart-large-50-many-to-many-mmt`, `google-t5/t5-base`, `google-t5/t5-small` | all SRE |
| Text embeddings | `sentence-transformers/all-MiniLM-L6-v2`, `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | all SRE |
| Text classification / NLU | `google-bert/bert-base-uncased`, `distilbert/distilbert-base-uncased-finetuned-sst-2-english`, `FacebookAI/xlm-roberta-large`, `microsoft/mdeberta-v3-base` | all SRE |
| Zero-shot text classification | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | all SRE |
| Speech transcription | `openai/whisper-large-v3` (multilingual), `facebook/wav2vec2-base-960h` (English; also audio embeddings) | MCL API only |
| Image–text similarity, zero-shot image labelling | `openai/clip-vit-large-patch14` | MCL API only |
| Image embeddings | `facebook/dinov2-large` | MCL API only |
| Image and video segmentation | `facebook/sam2.1-hiera-large` | MCL API only |
| Object detection | `facebook/detr-resnet-50` | MCL API only |

The thirteen text models are **probe-verified** from inside the SRE
(2026-08-22/26); the six multimedia models are **[documented]** only — run
`hf_list_files()` on one before planning around it.

**Two mDeBERTa entries, two different tools.** `microsoft/mdeberta-v3-base` is a
plain multilingual encoder to fine-tune; the `MoritzLaurer/…-xnli-…` entry is an
XNLI-finetuned **zero-shot classifier** with the NLI head already trained. Until
2026-10 Meta's page titled the first with the English DeBERTaV3 *paper*, which
sent people to `microsoft/deberta-v3-base` — **not approved**, 400
**[verified by probing 2026-08-22]**. The page's titles are now accurate. History:
`references/ml_models_approved.md`.

`references/ml_models_approved.md` holds the verbatim list as Meta prints it.
The list grows — check the
[page](https://developers.facebook.com/docs/researcher-platform/features/ml-models)
rather than trusting this table.

### Multimedia models (MCL API environments) — [documented 2026-10-12]

Six models for audio, images and video, announced on both Meta changelogs on
2026-10-12. Nothing below has been run in the SRE; sizes and file lists are read
from Hugging Face's public API on 2026-10-21, everything about the SRE side is
**[inferred]** from the verified behaviour of the text models.

**Do not `hf_download_repo()` these.** It pulls every weight format in the repo
(§ "Downloading, as documented"), and for these repos that is 2–8× what you
need — and for Whisper, more than the disk:

| Repo | Whole repo | Files you need (PyTorch) | Needed size |
|------|-----------:|--------------------------|------------:|
| `openai/whisper-large-v3` | **24.7 GB** | `model.safetensors` + `config.json`, `generation_config.json`, `preprocessor_config.json`, `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`, `added_tokens.json`, `special_tokens_map.json`, `normalizer.json` | 3.1 GB |
| `openai/clip-vit-large-patch14` | 6.9 GB | `model.safetensors` + `config.json`, `preprocessor_config.json`, `tokenizer.json`, `tokenizer_config.json`, `vocab.json`, `merges.txt`, `special_tokens_map.json` | 1.7 GB |
| `facebook/dinov2-large` | 2.4 GB | `model.safetensors` + `config.json`, `preprocessor_config.json` | 1.2 GB |
| `facebook/sam2.1-hiera-large` | 1.8 GB | `model.safetensors` + `config.json`, `preprocessor_config.json`, `processor_config.json`, `video_preprocessor_config.json` | 0.9 GB |
| `facebook/detr-resnet-50` | 0.3 GB | `model.safetensors` + `config.json`, `preprocessor_config.json` — **from the `no_timm` revision**, see below | 0.2 GB |
| `facebook/wav2vec2-base-960h` | 1.1 GB | `model.safetensors` + `config.json`, `preprocessor_config.json`, `feature_extractor_config.json`, `tokenizer_config.json`, `vocab.json`, `special_tokens_map.json` | 0.4 GB |

With ~23 GB free in `/home/jovyan` **[verified 2026-08-22]**, a whole-repo Whisper
download fails part-way and leaves the truncated files described in § "Downloading, as
documented". Whisper's repo also carries **two fp32 shards**
(`model.fp32-0000{1,2}-of-00002.safetensors`, 6.2 GB) beside the fp16
`model.safetensors`; the generic `\.safetensors$` filter in § "Fetching only the
files you need" would take both. Use the explicit lists above.

The generic filter has a second gap for every model here: it skips
`preprocessor_config.json` (and Whisper's `generation_config.json`), which
`AutoProcessor` / `AutoImageProcessor` need. A text model never needed them.

Code: `languages/r/utilities.md` § "Fetching a multimedia model" · `languages/python/utilities.md` § "Fetching a multimedia model"

**Model-specific traps, all [inferred] from the repos' configs:**

- **DETR wants a second download it cannot make.** `facebook/detr-resnet-50` on
  `main` builds its ResNet-50 backbone through **`timm`** and, by default, asks
  timm for *pretrained* backbone weights — a hub fetch the SRE cannot make, and
  `timm` may not be installed. The repo has a **`no_timm` branch** that uses
  `transformers`' own ResNet; download with `revision = "no_timm"` (the files land
  in `~/huggingface/facebook/detr-resnet-50/no_timm`). A non-`main` revision of an
  approved repo is accepted by the proxy **[verified for SHAs 2026-08-22]**; this
  branch is untested.
- **SAM 2.1 needs a recent `transformers`.** Its config declares
  `Sam2VideoModel`, written by `transformers` 4.56. The SRE's `transformers`
  version has not been read (`docs/ML_MODELS_OPEN_QUESTIONS.md` Q13); on an older
  one, loading fails with an unknown `model_type: sam2_video`. The repo also ships
  `sam2.1_hiera_large.pt` + a YAML for Meta's standalone `sam2` package — skip
  them unless you install that package.
- **Audio needs a decoder.** Whisper and wav2vec 2.0 take a 16 kHz waveform, not a
  file. Turning an MP4 or OGG into one needs `ffmpeg`, `librosa`, `soundfile` or
  `torchaudio`, none of which has been checked in the SRE — § "Installing
  packages" (conda-forge carries `ffmpeg`).
- **Whisper on a CPU server is impractically slow** at 1.55 B parameters. Use a
  GPU server (§ "CPU or GPU Server") and load in `float16`.

**Where the media comes from is still open.** These models are only useful if
the image, audio and video bytes reach your notebook. Posts expose presigned S3
download URLs on request (`references/field_reference.md` § "`multimedia{url}` DOES work"), but
fetching them from an SRE cell has not been tested, and the "multimedia queries"
quota in SKILL.md is documented for third-party cleanrooms, not the SRE. Meta
shipping vision and speech models into MCL API environments suggests the path
exists; until someone runs it, treat it as **[open]** —
`docs/ML_MODELS_OPEN_QUESTIONS.md` Q21–Q24.

### Restrictions

- **Approved list only.** No internet access means an unlisted model cannot be
  fetched at all, by any route.
- **Six of the 19 are MCL-API-environment only** — the multimedia models above.
- **Open-source license required.** Only models on the Hugging Face Hub under an
  open-source license can be considered. *(Until 2026-10 the page also required
  text-based models; that condition is gone.)*
- **Unlisted models require a support ticket** with a link to the model and a use
  case tied to your approved research agenda. A model approved this way is made
  available to all researchers.
- **Use a GPU server** for inference — models are optimized for GPU and the
  page says runtimes are faster. Choosing one is a server-start decision, not a
  code one: see "CPU or GPU Server" below.

## CPU or GPU Server

**Yes — the SRE lets you run your notebook on a GPU server**, and you pick which
at server start rather than requesting it in advance. The option has existed
since **June 2022**.

> **[documented]** — from
> [GPU server option](https://developers.facebook.com/docs/researcher-platform/features/GPU)
> and the [platform changelog](https://developers.facebook.com/docs/researcher-platform/changelog)
> (fetched 2026-08-22). Not yet observed in a live session.

**Choosing one.** When you log in to the Jupyter environment you are offered the
server type: choose **CPU** or **GPU**, then click **Start**.

**Switching mid-project**, without losing work:

1. **File** > **Hub Control Panel** in JupyterLab's top navigation
2. **Stop My Server**
3. Once it has stopped, **Start My Server** appears — click it
4. Choose CPU or GPU again

Meta's page states switching server type does **not** lose work. Note that a
**GPU server takes longer to launch** than a CPU one.

**Confirming you got one.** On a GPU server a **dashboards icon** appears in the
left navigation bar — it is absent on CPU servers — giving GPU dashboards
powered by NVDashboard. From code, `torch$cuda$is_available()` (see the ML
section above) is the programmatic check.

**What is not documented**, and is worth knowing before planning a large job:
the GPU model and specs, memory, disk, any time limit on a GPU session, and
whether GPU access is uniform across institutions. `docs/ML_MODELS_OPEN_QUESTIONS.md`
question 12 tracks these.

When to bother: a GPU is worth the slower launch for **inference over many
records** — embedding or classifying a full MCL result set. For a handful of
strings, or for writing and debugging the query itself, CPU starts faster.

## Getting Results Out

### The monthly wipe — everything but the notebook goes

**[added 2026-08-25]** Source:
[Data deletion](https://developers.facebook.com/docs/content-library-and-api/content-library-api/guides/data-deletion).

Export is not the only deadline. **Every 30 days the Secure Research Environment
deletes almost everything you have produced**, whether or not you are finished
with it:

| Deleted | Kept |
|---|---|
| **All output cells** in every notebook | The `.ipynb` files themselves |
| **All non-notebook files** on persistent storage | Input cells — code and markdown |
| **All S3 bucket files**, including uploads, async query output and **all query results** | Graphics embedded in notebook cells |

The wipe runs in a **monthly maintenance window from 12:00 AM PST on the first of
the month through 11:59 PM PST that same day**, during which **JupyterHub is
unavailable**. Approved research programmes studying systemic risks in the
European Union are exempt.

**Do not confuse this with SNAPSHOT retention.** They are two different
thirty-days:

| | What it is | Documented | Measured 2026-09-02 |
|---|---|---|---|
| **Server-side SNAPSHOT data** | Meta's copy of a job's results | up to a **year**, refreshed every 30 days, shareable | **every job `EXPIRED` after the wipe** |
| **Your files in the SRE** | Saved `.json`/`.csv`, S3 uploads, cell outputs | wiped **monthly**, no exceptions | **survived**, on the account tested |

⚠ **This block used to conclude: "a completed SNAPSHOT job is still there after
the wipe and can be re-read; the CSV you wrote from it is not." Both halves were
wrong on the account measured** — the jobs were gone and the files were not.
SKILL.md § "SNAPSHOT vs LIVE Mode" owns the job-expiry finding.

Treat **neither** as durable. The job expiry is measured and the file survival
is a single observation, plausibly the documented EU systemic-risk exemption —
so the safe reading is that a wipe may take either. **Download job results the
same calendar month you submit them, and export anything the study needs.**

**Three consequences for how you write notebooks:**

1. **Write notebooks to be re-run, not to be read.** Input cells survive, so the
   recovery path after a wipe is "run it again" — which only works if the whole
   pipeline is in cells rather than in a file some earlier cell produced.
2. **Guard submission cells anyway.** Re-running a notebook re-submits its jobs,
   and budget is charged at submission with no refund. The
   `if (file.exists("jobs.rds")) stop(...)` guard from SKILL.md § "SNAPSHOT vs
   LIVE Mode" is *itself* wiped — the file disappears, the guard opens. After a
   wipe, re-run against existing `query_id`s (`references/collections.md`
   § "Query Management") rather than re-submitting.
3. **Time long analyses away from the first of the month**, and export anything
   you need before it.

Meta's own note is worth repeating: regenerated outputs will **not** include
content that no longer meets visibility requirements. A re-run after a wipe is
not guaranteed to reproduce the earlier numbers — which is an argument for
SNAPSHOT mode and for rendering key results as images while you have them.

### Notebook export

> **[verified 2026-08-22]** — a real notebook was exported from a live session
> and the resulting file inspected. Sourced from
> [Export Jupyter notebooks](https://developers.facebook.com/docs/researcher-platform/features/notebook-export)
> and [Upload files to an S3 bucket](https://developers.facebook.com/docs/researcher-platform/features/S3-bucket).

**Plan for this before you compute anything.** The export path is narrower than
"export the notebook" suggests, and discovering that after a long run is
expensive.

### Notebook export strips your outputs

Exporting does not hand you your results. The exported file is **scrubbed**:

| Kept | Removed |
|------|---------|
| Code | Cell outputs — stdout, stderr, HTML |
| Markdown | Raw cell data |
| **Images** | |

So a data.frame printed in a cell, a `cat()` summary, a model's embeddings, a
table of classifications — **none of it leaves**. The scrubbed notebook still
runs, so a recipient with data access can reproduce your results, but the numbers
themselves stay inside.

**What it looks like.** Exporting a five-cell notebook of probe output produced a
file in which every cell's source was intact and every cell's output had been
replaced by a single stream:

```
[NOTICE] 2 output(s) filtered out
```

The outputs are not merely dropped — they are substituted with a count, so the
export tells you what it removed. Nothing of the original text survives: not
`stdout`, not printed values, not the paths or numbers this session recorded.
Verified against an export of the ML probe notebook whose results are in
`docs/ML_MODELS_OPEN_QUESTIONS.md` — none of that output is present in the
exported file.

*Scope of the check:* that export contained only code cells, so **code survives
and outputs do not** is directly observed. Markdown and image retention is
Meta's documented behaviour, not yet something we have tested.

**The consequence: anything you need to take away must be an image.** Render
summary tables as figures, plot what you would otherwise print, and save charts
into the notebook rather than to disk. A `ggplot` object displayed in a cell
survives; the data.frame behind it does not.

Procedure:

1. Right-click the notebook name in the JupyterLab left navigation →
   **Export Notebook**
2. Check your **email** for a download link and click it
3. The file appears in your downloads with **`-scrubbed`** appended to its name

Two caveats: the number of exports **per time period is limited** (you get an
error beyond it), and **not every environment offers the feature** — if the menu
item is absent, export is not available to you.

### The S3 bucket feature is not an exit

`fbri.common.user_data_manager.UserDataManager` uploads `.csv`/`.tsv` files
(5 GB per upload) into an S3 bucket — but that bucket is
**Secure-Research-Environment-owned**, so the data stays inside the enclave. It
is storage for further analysis and joins, not egress to your own AWS account or
laptop.

It also does not apply here: *"Uploading to an S3 bucket is supported for the Ad
Targeting dataset and the URL Shares dataset. It is not supported for Meta
Content Library."*

## Retrieve Completed Job Data

A job id (a date-slug such as `2025-11-30-xxx-xxx`) is enough to come back to a
finished job: `get_async_job(job_id=…)` returns the job object, its status is
read through the wait helper's normalizer (comparing the raw return value is
unsafe — `SKILL.md` § "Waiting for a Job"), and when it is `COMPLETE`,
`write_data_to_file(directory=, filename=)` saves the results, which the
ID-safe helper then loads from disk.

Code: `languages/r/utilities.md` § "Retrieving a completed job" · `languages/python/utilities.md` § "Retrieving a completed job"

### Get Job Metadata

`GET async/jobs/{job_id}` returns the job's `mode`, `query_id` and
`creation_time` (an epoch second), among other fields.

Code: `languages/r/utilities.md` § "Reading job metadata" · `languages/python/utilities.md` § "Reading job metadata"

### Get Query Information

`GET async/queries/{query_id}` returns the query's `name`, `platform`,
`entity_type` and `params`.

Code: `languages/r/utilities.md` § "Reading query information" · `languages/python/utilities.md` § "Reading query information"

## List All Jobs

`GET async/jobs` returns the account's jobs under the **`jobs`** key (not
`data` — `references/collections.md` § "⚠ The `async/jobs` envelope key is
`jobs`, not `data`"), each with `id`, `status`, `mode` and `query_id`.

Code: `languages/r/utilities.md` § "Listing all jobs" · `languages/python/utilities.md` § "Listing all jobs"

## Verify IDs Loaded as Strings

Run `check_ids()` on any table before joining, deduplicating, or exporting — it
fails loudly if an ID-named column (`"(^|[._])ids?$"`) slipped through as a
number, and reports how many ID columns carry 16+ digit values, since digits
above 2^53 that were ever rounded cannot be repaired.

Code: `languages/r/utilities.md` § "Verifying ID columns" · `languages/python/utilities.md` § "Verifying ID columns"

## SNAPSHOT vs LIVE Data Retention

SNAPSHOT data is documented as kept up to a year and is shareable; LIVE data is
kept ~30 days and is not. SNAPSHOT jobs refresh every 30 days with updated data,
including `updated_fields` and `is_invalid_id` flags for redacted content.

⚠ **The one-year figure does not survive a month boundary** — measured
2026-09-02, every job was `EXPIRED` after a wipe. SKILL.md § "SNAPSHOT vs LIVE
Mode" owns this; do not plan recovery around re-reading a job.

Full comparison and the 100-snapshot cap: `references/collections.md` § "The
100-Snapshot Cap". Note that this is **server-side** retention — your own files
in the SRE are wiped monthly regardless, see § "The monthly wipe" above.

## The package-manager table above is incomplete — there are four channels, not two

**[verified 2026-08-23, in a live SRE session]** `dir()` on the module, read from R:

```
fbri                     -> common, package_managers
fbri.package_managers    -> Pip, PipException, huggingface, pip
```

So `huggingface` is one of **two** Python-side channels, and R has **two** of its own.
Meta documents all four; this file previously named only CRAN and Hugging Face.

| You want | Use | Source |
|---|---|---|
| An R package from CRAN | `fbrir` → `CRAN$new()$InstallPackages("abglasso")` | [Install R packages](https://developers.facebook.com/docs/researcher-platform/features/install-r) |
| An R package (or **any conda-forge package**, including native binaries) | `fbrir` → `Conda$new()$Install("r-treemap")` | same page |
| A Python package | `from fbri.package_managers import Pip; Pip.get_instance().install("pkg")` | [Install Python packages](https://developers.facebook.com/docs/researcher-platform/pip) |
| A pre-trained model from Hugging Face | `fbri.package_managers.huggingface` (above) | ML models page |

Code: `languages/r/utilities.md` § "Installing packages" · `languages/python/utilities.md` § "Installing packages"

**Both routes go through a Meta proxy**, and neither needs an approval step: R packages via
`https://mesa-override-graph-api.test.fb-researchtool.com/public/external-proxy/`, Python via a
private **AWS CodeArtifact** PyPI mirror whose credentials are configured for you.

**The `Conda` channel is the consequential one.** conda-forge carries **native binaries**, not
just R and Python libraries — which means capabilities the approved-model list does not cover
(an OCR engine, image and video tooling) may be installable without touching that list at all.
A classical engine is not a pre-trained model, and the two gates are separate.

Meta's own operating advice, worth following: **use a notebook dedicated to installs**, restart
the kernel afterwards, and **only uninstall what you installed** — removing system-level packages
breaks the environment.

## "No internet access" is too strong — it is *Meta-proxied hosts only*

**[verified 2026-08-23]** This file and `SKILL.md` both say the SRE has no internet access. The
measured behaviour is narrower and more useful:

| Target | Result |
|---|---|
| `prod-fortapis-api-async-uploads.s3.amazonaws.com` (a presigned `multimedia{url}`) | **HTTP 200, 208,284 bytes, `image/jpg`** — fetched from a cell with `requests` |
| `HF_ENDPOINT` (Meta's Hugging Face reverse proxy) | works — a pinned model downloaded through it |
| `cran.r-project.org` via `available.packages()` | **hung until the kernel was interrupted** |

So outbound network from a cell **does** work, to **Meta-operated or Meta-proxied hosts**. That is
why the `fbri`/`fbrir` package managers exist at all: they are not conveniences wrapping a direct
connection, they are the connection. Code that assumes a public endpoint will hang rather than
fail fast — budget a timeout.

> **This does not settle the Terms question.** Fetching media into the enclave is an *import*, and
> Terms §4 puts imports under the Import & Export Policy. What is recorded here is what the
> network does, not what the contract permits.

### ⚠ `Conda$new()$Install()` reports "Failed install" for non-R packages — even when conda succeeds

**[verified 2026-08-24]** `conda$Install("tesseract")` printed conda's own transaction log
through to completion:

```
[142] "Downloading and Extracting Packages: ...working... done"
[143] "Preparing transaction: ...working... done"
[144] "Verifying transaction: ...working... done"
[145] "Executing transaction: ...working... done"
[1]   "Failed install: tesseract, from channel: https://conda.anaconda.org/conda-forge/linux-64"
```

`Sys.which("tesseract")` came back **empty** afterwards. So the wrapper's verdict and conda's own
output disagree: **conda resolved and executed a 138-package transaction, then `fbrir` declared
the install failed.**

The likely cause is in the wrapper, not the channel: Meta's page says *"R package names begin
with `r-`"*, so `Conda$Install` is written for **R packages** and presumably verifies by looking
for an installed R library. A native binary satisfies no such check, so it reports failure
regardless of what conda did. Packages install into `/home/jovyan/.fort/user_packages/conda`,
which is **not on `PATH`** — another reason `Sys.which()` finds nothing even on success.

**Before concluding a native package is unavailable, check the filesystem, not the verdict:**
test for `/home/jovyan/.fort/user_packages/conda/bin/<binary>` and run it by
absolute path with `--version`.

Code: `languages/r/utilities.md` § "Checking a conda-installed binary" · `languages/python/utilities.md` § "Checking a conda-installed binary"

**[verified 2026-08-24] The files ARE there — the `Failed install` message is cosmetic.**

```
EXISTS TRUE | bin-files 273
VER tesseract 5.5.3
List of available languages in ".../user_packages/conda/share/tessdata/" (125): ... ita ita_old ...
```

A 138-package conda transaction installed a working `tesseract 5.5.3` with **125 language
models**, and the wrapper called it a failure. **So `Conda$Install` does install native
conda-forge packages, and its success/failure verdict cannot be trusted for anything that is not
an R package.** Verify from the filesystem and run the binary by absolute path — `Sys.which()`
will not find it because the prefix is not on `PATH`.

This matters beyond one package: it means the SRE can be given **capabilities the approved-model
list does not cover** — OCR here — through Meta's own documented channel, without routing model
weights around that list.

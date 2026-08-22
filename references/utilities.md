# MCL API Utilities

> All examples parse responses with `mcl_fromJSON()`, defined in SKILL.md §
> "ID Handling (Always Load IDs as Character)". It keeps every ID field a
> character string — plain `fromJSON()` turns IDs into doubles.

Verified working code for common utility tasks — except where a section
carries its own sourcing tag ([documented] / [inferred]), which means it was
transcribed rather than run.

## Check Quota Status

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "budgets")
budgets <- mcl_fromJSON(response$text)

# Extract query budget (posts, pages, groups, events, accounts)
queries <- budgets$queries
queries_used <- as.numeric(queries$total_usage)
queries_limit <- as.numeric(queries$max_usage_limit)
queries_avail <- queries_limit - queries_used

cat("Query Budget:\n")
cat(sprintf("  Used:      %s / %s\n", format(queries_used, big.mark=","), format(queries_limit, big.mark=",")))
cat(sprintf("  Available: %s records\n", format(queries_avail, big.mark=",")))

# In-progress queries (preallocated)
if (queries$preallocated_rows_for_running_queries > 0) {
  cat(sprintf("  In Progress: %s records\n", format(queries$preallocated_rows_for_running_queries, big.mark=",")))
}

# Separate comments budget
comments <- budgets$comments
comments_avail <- as.numeric(comments$max_usage_limit) - as.numeric(comments$total_usage)
cat(sprintf("\nComments Budget: %s available\n", format(comments_avail, big.mark=",")))
```

### Quota Thresholds

| Available Records | Status | Recommendation |
|-------------------|--------|----------------|
| >= 200,000 | Excellent | Full analysis |
| >= 100,000 | Good | Moderate analysis |
| >= 50,000 | Fair | Reduced parameters |
| >= 10,000 | Low | Minimal analysis |
| < 10,000 | Critical | Wait for reset |
| <= 0 | Over quota | Cannot run queries |

### Quota Reset
- **Rolling window**: 7 days
- Each query's usage expires exactly 7 days after submission
- Check daily to see quota freeing up

## Install R Packages

The Meta SRE uses a custom CRAN mirror. Use `fbrir` to install packages:

```r
library(fbrir)

# Initialize CRAN instance
cran <- CRAN$new()

# Install single package
cran$InstallPackages("flextable", dependencies = TRUE)

# Install multiple packages
cran$InstallPackages(c("ggplot2", "dplyr", "tidyr"), dependencies = TRUE)
```

**Note**: Standard `install.packages()` does not work in the SRE.

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
| An R package from CRAN | `fbrir` → `CRAN$new()$InstallPackages()` (above) |
| A pre-trained model from Hugging Face | `fbri.package_managers.huggingface` (below) |

**The rule the rest of this section follows from: the SRE has no internet
access** (SKILL.md § Environment). `from_pretrained("facebook/mbart-large-50-many-to-many-mmt")` cannot
reach huggingface.co and will fail. You download an **approved** model first
through the `fbri` helper, then load it from its local path.

> **[documented]** — the Python signatures, paths and restrictions below are
> transcribed from
> [Machine Learning Models](https://developers.facebook.com/docs/researcher-platform/features/ml-models)
> (fetched 2026-08-21). **The import works from R: [verified 2026-08-22]** in a
> live SRE session — see "Downloading from R". The download *call* itself is
> still untested.

### Downloading (Python, as documented)

```python
# Whole repository
from fbri.package_managers.huggingface import hf_download_repo
hf_download_repo(repo="facebook/mbart-large-50-many-to-many-mmt", revision="main", output_dir=None)

# A single file — NOTE the argument order: filename first, then repo
from fbri.package_managers.huggingface import hf_download_file
repo = "facebook/mbart-large-50-many-to-many-mmt"
filename = ".gitattributes"
hf_download_file(filename, repo, revision="main", output_dir=None)
```

Downloads land in `~/huggingface/<REPO>/<REVISION>` — where `<REPO>` keeps its
**org prefix**, so the default revision of the model above is at
`/home/jovyan/huggingface/facebook/mbart-large-50-many-to-many-mmt/main`.
Dropping the `facebook/` gives a path that does not exist.

**[verified 2026-08-22]** — read from the module's own source
(`/opt/conda/lib/python3.11/site-packages/fbri/package_managers/huggingface.py`),
not inferred:

```python
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
  multi-gigabyte download:

  ```r
  hf <- import("fbri.package_managers.huggingface")
  files <- hf$hf_list_files("facebook/mbart-large-50-many-to-many-mmt", "main")
  length(files); head(files)
  ```

**Verify a download finished before you use it.** The helper streams to the
final path with no staging file, no checksum and no resume, and nothing cleans
up after a failure — so a dropped connection or an error mid-download leaves a
**truncated file that looks present**. `from_pretrained()` then fails on a
corrupt weight file, which is far more confusing than a missing one.

The function prints `Download Finished to '<dir>'` on success. **If you did not
see that line, delete the directory and download again** — do not treat a file's
existence as evidence it is complete:

```r
model_dir <- file.path(path.expand("~"), "huggingface", REPO, "main")
unlink(model_dir, recursive = TRUE)   # start clean after any failed attempt
```

**`hf_download_repo` downloads every file in the repo — budget ~10× the weights.**
**[measured 2026-08-22]** `all-MiniLM-L6-v2`, whose PyTorch weights are about
90 MB, consumed **931 MB** and 57 seconds: the loop pulls `model.safetensors`
*and* `onnx/model_O1.onnx`, `onnx/model_O2.onnx`, OpenVINO, TensorFlow and Rust
variants indiscriminately. There is no format filter.

With ~23 GB of home directory available that matters. For anything large, list
first and fetch only what you need:

```r
files <- unlist(hf$hf_list_files(REPO, "main"))
want  <- files[grepl("^(config|tokenizer|vocab|special_tokens)|\\.safetensors$", files)]
for (f in want) hf$hf_download_file(f, REPO, "main")
```

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
2. **If it is on the list, suspect the org prefix** — Meta names owners, not repo
   ids. Resolve it with `hf_list_files()`, which costs nothing:

   ```r
   hf$hf_list_files("sentence-transformers/all-MiniLM-L6-v2", "main")   # 30 files
   ```

A revision mistake never reaches this ladder — it announces itself as a 404.

### Pinning a revision for reproducible work

**[verified 2026-08-22]** `revision` accepts a **full 40-character commit SHA and
the 7-character short form**, and a pinned download gets its **own directory**
beside `main/` — so a pinned pipeline cannot be quietly changed by a later `main`
download, and both can coexist.

Resolve the current commit without downloading anything, then pin to it:

```r
requests <- import("requests")
info <- requests$get(paste0(hf$HF_ENDPOINT, "/api/models/", REPO, "/revision/main"))$json()
SHA  <- info$sha        # e.g. "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

hf$hf_download_repo(REPO, SHA)
model_dir <- file.path(path.expand("~"), "huggingface", REPO, SHA)
```

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

| Meta's page prints | You must use |
|--------------------|--------------|
| `t5-base` / `t5-small` | `google-t5/t5-base` / `google-t5/t5-small` |
| `bert-base-uncased` | `google-bert/bert-base-uncased` |
| `distilbert-base-uncased-finetuned-sst-2-english` | `distilbert/distilbert-base-uncased-finetuned-sst-2-english` |
| `xlm-roberta-large` | `FacebookAI/xlm-roberta-large` |
| `all-MiniLM-L6-v2` (owner given as "UKP Lab") | `sentence-transformers/all-MiniLM-L6-v2` |

The full table of twelve verified ids is `references/ml_models_approved.md`.
When in doubt, `hf_list_files()` settles it in one free call.

### Downloading from R

**[verified 2026-08-22]** — `fbri`, `fbri.package_managers` and
`fbri.package_managers.huggingface` all import from R-side reticulate in a live
SRE session. reticulate binds to `/opt/conda/bin/python3` (Python **3.11**), the
same conda environment the notebook kernels use, which is why the import
resolves. `import()` below is therefore the supported path, not a guess. The
**download call** has not been run yet — that is Phase B in
`docs/ML_MODELS_OPEN_QUESTIONS.md`:

```r
library(reticulate)

hf <- import("fbri.package_managers.huggingface")
hf$hf_download_repo(repo = "facebook/mbart-large-50-many-to-many-mmt")

model_path <- file.path(path.expand("~"), "huggingface",
                        "facebook/mbart-large-50-many-to-many-mmt", "main")
list.files(model_path)
```

The Python-cell fallback remains valid if anything goes wrong — run the download
there and use `model_path` from R; the files are on disk either way.

**One preinstalled-library gotcha, [verified 2026-08-22]:** `transformers` and
`torch` are available, but **`sentence_transformers` is NOT**. Models Meta lists
under Sentence-BERT / Sentence-Transformers (`all-MiniLM-L6-v2`,
`paraphrase-multilingual-MiniLM-L12-v2`) therefore cannot be loaded with the
`SentenceTransformer(...)` one-liner most tutorials use. Load them through
`transformers` directly (`AutoModel` + `AutoTokenizer`, then mean-pool the token
embeddings yourself), or install the package first — see "Install R Packages"
above for the R side and Meta's pip page for the Python side.

### Inference from R works — [verified 2026-08-22]

An earlier version of this section said inference was "easiest left in Python".
**That was wrong, and it is corrected here.** The `**kwargs` unpacking that made
Meta's example look awkward is avoidable: pass the tensors by name. Loading and
embedding took 0.7 s in total, entirely from R.

```r
library(reticulate)
REPO  <- "sentence-transformers/all-MiniLM-L6-v2"
MDIR  <- file.path(path.expand("~"), "huggingface", REPO, "main")

tf_   <- import("transformers")
torch <- import("torch")
tok   <- tf_$AutoTokenizer$from_pretrained(MDIR)
mod   <- tf_$AutoModel$from_pretrained(MDIR)

texts <- list("Meta Content Library research", "a second document")
enc   <- tok(texts, padding = TRUE, truncation = TRUE, return_tensors = "pt")
out   <- mod(input_ids = enc$input_ids, attention_mask = enc$attention_mask)

# mean-pool the token embeddings, masking padding — what SentenceTransformer
# does internally, and what you must do yourself because it is not installed
m   <- enc$attention_mask$unsqueeze(-1L)$float()
emb <- torch$sum(out$last_hidden_state * m, dim = 1L) /
       torch$clamp(m$sum(dim = 1L), min = 1e-9)

embeddings <- as.matrix(emb$detach()$numpy())   # rows = texts, cols = 384
dim(embeddings)
```

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

Only models on Meta's approved list can be downloaded. As fetched 2026-08-22 the
list covers three families (still 13 models; entry #11's on-page name grew a
subtitle since the 2026-08-21 fetch — see `references/ml_models_approved.md`):

| Use | Models |
|-----|--------|
| Translation | Facebook NLLB-200 (`nllb-200-3.3B`, `nllb-200-distilled-600M`), Facebook mBART-50 and mBART many-to-many, Google T5 and T5-small |
| Embeddings | UKP Lab Sentence-BERT (`all-MiniLM-L6-v2`), Sentence-Transformers (`paraphrase-multilingual-MiniLM-L12-v2`) |
| Classification / NLU | Google BERT base (uncased), DistilBERT (`distilbert-base-uncased-finetuned-sst-2-english`), XLM-RoBERTa large, DeBERTaV3 and mDeBERTa v3 multilingual |

The page names **owners**, not full Hugging Face repo ids — only
`facebook/mbart-large-50-many-to-many-mmt` appears verbatim, and the parenthesised
names above are the page's, without their org prefix. Since the prefix is part of
the repo id and of the download path, read it off the
[page](https://developers.facebook.com/docs/researcher-platform/features/ml-models)
before downloading; guessing it fails as an approval or path error, not as a
missing model. Check the same page for the current list rather than trusting this
table — it grows.

### Restrictions

- **Approved list only.** No internet access means an unlisted model cannot be
  fetched at all, by any route.
- **Text models with an open-source license only** qualify for approval.
- **Unlisted models require a support ticket** justifying the use case.
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

> **[documented 2026-08-22]** from
> [Export Jupyter notebooks](https://developers.facebook.com/docs/researcher-platform/features/notebook-export)
> and [Upload files to an S3 bucket](https://developers.facebook.com/docs/researcher-platform/features/S3-bucket).
> Not yet observed in a live session.

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

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

job_id <- "2025-11-30-xxx-xxx"  # Your job ID

# Get job object
job <- client$get_async_job(job_id = job_id)

# Check status. mcl_job_status() upper-cases and trims; comparing the raw
# return value is unsafe — see SKILL.md § "Waiting for a Job".
status <- mcl_job_status(job)
cat("Status:", status, "\n")

if (status == "COMPLETE") {
  # Save to file
  output_dir <- "retrieved_jobs"
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)
  
  filename <- paste0("job_", job_id, ".json")
  job$write_data_to_file(directory = output_dir, filename = filename)
  
  # Load into R
  filepath <- file.path(output_dir, filename)
  job_data <- mcl_fromJSON(filepath)
  
  cat("Retrieved", nrow(job_data), "records\n")
}
```

### Get Job Metadata

```r
# Full job details
job_response <- client$get(path = paste0("async/jobs/", job_id))
job_metadata <- mcl_fromJSON(job_response$text)

cat("Mode:", job_metadata$mode, "\n")
cat("Query ID:", job_metadata$query_id, "\n")
cat("Created:", as.POSIXct(job_metadata$creation_time, origin = "1970-01-01"), "\n")
```

### Get Query Information

```r
query_response <- client$get(path = paste0("async/queries/", job_metadata$query_id))
query_info <- mcl_fromJSON(query_response$text)

cat("Query Name:", query_info$name, "\n")
cat("Platform:", query_info$platform, "\n")
cat("Entity Type:", query_info$entity_type, "\n")
cat("Parameters:", query_info$params, "\n")
```

## List All Jobs

```r
jobs_response <- client$get(path = "async/jobs")
jobs_data <- mcl_fromJSON(jobs_response$text)

# View summary
print(jobs_data$jobs[, c("id", "status", "mode", "query_id")])
```

## Verify IDs Loaded as Character

Run this on any data.frame before joining, deduplicating, or exporting — it fails
loudly if an ID slipped through as a double:

```r
check_ids <- function(df) {
  id_cols <- grep(MCL_ID_PATTERN, names(df), value = TRUE)   # "(^|[._])ids?$"
  bad <- id_cols[vapply(df[id_cols], is.numeric, logical(1))]   # logical is_invalid_id is fine

  if (length(bad)) {
    stop("Numeric ID column(s): ", paste(bad, collapse = ", "),
         " — re-parse the source with mcl_fromJSON()")
  }
  # Digits above 2^53 are already rounded and cannot be repaired
  risky <- vapply(df[id_cols], function(x) {
    if (!is.character(x)) return(FALSE)
    any(nchar(x) >= 16, na.rm = TRUE)
  }, logical(1))

  cat(sprintf("%d ID column(s) OK (%d with 16+ digit values)\n",
              length(id_cols), sum(risky)))
  invisible(TRUE)
}

check_ids(posts)
```

## SNAPSHOT vs LIVE Data Retention

SNAPSHOT data is kept up to a year and is shareable; LIVE data is kept ~30 days
and is not. SNAPSHOT jobs refresh every 30 days with updated data, including
`updated_fields` and `is_invalid_id` flags for redacted content.

Full comparison and the 100-snapshot cap: `references/collections.md` § "The
100-Snapshot Cap".

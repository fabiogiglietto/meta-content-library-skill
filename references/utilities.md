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
Dropping the `facebook/` gives a path that does not exist. `output_dir`
overrides the location.

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

Inference itself is easiest left in Python. The documented mBART example
(`MBartForConditionalGeneration.from_pretrained(model_path)`, then
`tokenizer.lang_code_to_id["de_DE"]`) relies on `**kwargs` unpacking and Python
item access, which reticulate expresses as `do.call()` and `py_get_item()` —
more translation than it is worth for a one-off. Call it from a Python cell and
bring the results back into R as a data.frame.

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

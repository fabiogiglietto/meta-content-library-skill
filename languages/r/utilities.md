# Utilities — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Budget headroom

Facts: `SKILL.md` § "Rate Limits & Budget"

Read `max_usage_limit` from `budgets` rather than hard-coding 500,000 — the
ceiling is a per-account setting:

```r
budget <- mcl_fromJSON(client$get(path = "budgets")$text)
cat("Available:", budget$queries$max_usage_limit - budget$queries$total_usage, "\n")
```

## Check quota status — [verified 2026-09-02]

Facts: `references/utilities.md` § "Check Quota Status"

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

## Installing packages — [verified 2026-08-23]

Facts: `references/utilities.md` § "Installing packages"

The Meta SRE uses a custom CRAN mirror. Standard `install.packages()` does not
work; use `fbrir`:

```r
library(fbrir)

# Initialize CRAN instance
cran <- CRAN$new()

# Install single package
cran$InstallPackages("flextable", dependencies = TRUE)

# Install multiple packages
cran$InstallPackages(c("ggplot2", "dplyr", "tidyr"), dependencies = TRUE)
```

The conda-forge channel is reached through the same package, and R packages
there are prefixed `r-`:

```r
library(fbrir)
cran <- CRAN$new();  cran$InstallPackages(c("abctools", "abdiv"))
conda <- Conda$new(); conda$Install(c("r-timetk", "r-timereg"))   # R packages are prefixed "r-"
```

The Python pip channel is `languages/python/utilities.md` § "Installing
packages"; it is reachable from R through `import("fbri.package_managers")$Pip`
as well, but the R-side channels above are the documented route for R.

## Download Machine Learning Models — [verified 2026-08-22]

Facts: `references/utilities.md` § "Download Machine Learning Models"

### Downloading a model

Facts: `references/utilities.md` § "Calling the helper from either kernel"

`fbri.package_managers.huggingface` imports from R-side reticulate, which binds
`/opt/conda/bin/python3` (3.11). The import is verified; the download call
itself has not been run yet.

```r
library(reticulate)

hf <- import("fbri.package_managers.huggingface")
hf$hf_download_repo(repo = "facebook/mbart-large-50-many-to-many-mmt")

model_path <- file.path(path.expand("~"), "huggingface",
                        "facebook/mbart-large-50-many-to-many-mmt", "main")
list.files(model_path)
```

### Listing a repo's files

Facts: `references/utilities.md` § "Download Machine Learning Models"

Costs nothing, and checks both the repo id and your access to it before a
multi-gigabyte download:

```r
hf <- import("fbri.package_managers.huggingface")
files <- hf$hf_list_files("facebook/mbart-large-50-many-to-many-mmt", "main")
length(files); head(files)
```

```r
hf$hf_list_files("sentence-transformers/all-MiniLM-L6-v2", "main")   # 30 files
```

### Cleaning up a failed download

Facts: `references/utilities.md` § "Download Machine Learning Models"

```r
model_dir <- file.path(path.expand("~"), "huggingface", REPO, "main")
unlink(model_dir, recursive = TRUE)   # start clean after any failed attempt
```

### Fetching only the files you need

Facts: `references/utilities.md` § "Download Machine Learning Models"

```r
files <- unlist(hf$hf_list_files(REPO, "main"))
want  <- files[grepl("^(config|tokenizer|vocab|special_tokens)|\\.safetensors$", files)]
for (f in want) hf$hf_download_file(f, REPO, "main")
```

### Pinning a revision — [verified 2026-08-22]

Facts: `references/utilities.md` § "Pinning a revision for reproducible work"

```r
requests <- import("requests")
info <- requests$get(paste0(hf$HF_ENDPOINT, "/api/models/", REPO, "/revision/main"))$json()
SHA  <- info$sha        # e.g. "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

hf$hf_download_repo(REPO, SHA)
model_dir <- file.path(path.expand("~"), "huggingface", REPO, SHA)
```

### Inference with transformers — [verified 2026-08-22]

Facts: `references/utilities.md` § "Inference from R works"

Pass the tensors by name — no `**kwargs` unpacking is needed from R.

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

For **generation** models, `generate()` takes
`forced_bos_token_id = tokenizer$lang_code_to_id["de_DE"]`, which needs
`py_get_item(tok$lang_code_to_id, "de_DE")` in reticulate — a Python cell is
genuinely simpler for that one argument.

## Retrieving a completed job

Facts: `references/utilities.md` § "Retrieve Completed Job Data"

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

## Reading job metadata

Facts: `references/utilities.md` § "Get Job Metadata"

```r
# Full job details
job_response <- client$get(path = paste0("async/jobs/", job_id))
job_metadata <- mcl_fromJSON(job_response$text)

cat("Mode:", job_metadata$mode, "\n")
cat("Query ID:", job_metadata$query_id, "\n")
cat("Created:", as.POSIXct(job_metadata$creation_time, origin = "1970-01-01"), "\n")
```

## Reading query information

Facts: `references/utilities.md` § "Get Query Information"

```r
query_response <- client$get(path = paste0("async/queries/", job_metadata$query_id))
query_info <- mcl_fromJSON(query_response$text)

cat("Query Name:", query_info$name, "\n")
cat("Platform:", query_info$platform, "\n")
cat("Entity Type:", query_info$entity_type, "\n")
cat("Parameters:", query_info$params, "\n")
```

## Listing all jobs

Facts: `references/utilities.md` § "List All Jobs"

```r
jobs_response <- client$get(path = "async/jobs")
jobs_data <- mcl_fromJSON(jobs_response$text)

# View summary
print(jobs_data$jobs[, c("id", "status", "mode", "query_id")])
```

## Verifying ID columns

Facts: `references/utilities.md` § "Verify IDs Loaded as Strings"

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

## Checking a conda-installed binary — [verified 2026-08-24]

Facts: `references/utilities.md` § "⚠ `Conda$new()$Install()` reports "Failed install" for non-R packages — even when conda succeeds"

`Sys.which()` will not find it because the conda prefix is not on `PATH`:

```r
p <- "/home/jovyan/.fort/user_packages/conda/bin/tesseract"
file.exists(p); system2(p, "--version")
```

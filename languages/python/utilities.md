# Utilities — Python

> **Language layer: Python — [documented] unless a section is stamped `[verified DATE]`.** First run from a Python kernel in the SRE on 2026-09-10 (Step 0, Step 0b, Tests 1.1 and 10.1; no job submitted). Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Budget headroom — [documented; mirrors languages/r/utilities.md]

Facts: `SKILL.md` § "Rate Limits & Budget"

Read `max_usage_limit` from `budgets` rather than hard-coding 500,000 — the
ceiling is a per-account setting:

```python
budget = mcl_from_json(client.get(path="budgets").text)
print("Available:", budget["queries"]["max_usage_limit"] - budget["queries"]["total_usage"])
```

## Check quota status — [documented; mirrors languages/r/utilities.md, verified 2026-09-02 from R]

Facts: `references/utilities.md` § "Check Quota Status"

```python
from metacontentlibraryapi import MetaContentLibraryAPIClient as client

client.set_default_version(client.LATEST_VERSION)

budgets = mcl_from_json(client.get(path="budgets").text)

# Extract query budget (posts, pages, groups, events, accounts)
queries = budgets["queries"]
queries_used = int(queries["total_usage"])
queries_limit = int(queries["max_usage_limit"])
queries_avail = queries_limit - queries_used

print("Query Budget:")
print(f"  Used:      {queries_used:,} / {queries_limit:,}")
print(f"  Available: {queries_avail:,} records")

# In-progress queries (preallocated)
if queries["preallocated_rows_for_running_queries"] > 0:
    print(f"  In Progress: {queries['preallocated_rows_for_running_queries']:,} records")

# Separate comments budget
comments = budgets["comments"]
comments_avail = int(comments["max_usage_limit"]) - int(comments["total_usage"])
print(f"\nComments Budget: {comments_avail:,} available")
```

## Installing packages — [documented; Meta's pip page]

Facts: `references/utilities.md` § "Installing packages"

Standard `pip install` does not work in the SRE; the documented route is Meta's
`Pip` manager, which talks to a private PyPI mirror:

```python
from fbri.package_managers import Pip
pip = Pip.get_instance()
pip.install("package"); pip.install(["a", "b"]); pip.install("pkg", upgrade=True)
pip.list(); pip.uninstall("pkg"); pip.purge()      # purge removes ALL user-installed packages
```

The CRAN and conda-forge channels are exposed through the R package `fbrir`
(`languages/r/utilities.md` § "Installing packages"). Whether the conda channel
is reachable from a Python kernel without going through R is **open**.

## Download Machine Learning Models — [documented]

Facts: `references/utilities.md` § "Download Machine Learning Models"

### Downloading a model — [documented; Meta's ML models page, fetched 2026-08-21]

Facts: `references/utilities.md` § "Downloading, as documented"

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

Neither function returns the path; build it yourself:

```python
import os

model_path = os.path.join(os.path.expanduser("~"), "huggingface",
                          "facebook/mbart-large-50-many-to-many-mmt", "main")
os.listdir(model_path)
```

### Listing a repo's files — [documented; source read 2026-08-22]

Facts: `references/utilities.md` § "Download Machine Learning Models"

Undocumented on Meta's page, present in the module. Costs nothing, and checks
both the repo id and your access to it before a multi-gigabyte download:

```python
from fbri.package_managers.huggingface import hf_list_files

files = hf_list_files("facebook/mbart-large-50-many-to-many-mmt", "main")
len(files); files[:5]
```

```python
hf_list_files("sentence-transformers/all-MiniLM-L6-v2", "main")   # 30 files
```

### Cleaning up a failed download — [documented]

Facts: `references/utilities.md` § "Download Machine Learning Models"

```python
import os, shutil

model_dir = os.path.join(os.path.expanduser("~"), "huggingface", REPO, "main")
shutil.rmtree(model_dir, ignore_errors=True)   # start clean after any failed attempt
```

### Fetching only the files you need — [documented]

Facts: `references/utilities.md` § "Download Machine Learning Models"

```python
import re

files = hf_list_files(REPO, "main")
want = [f for f in files if re.match(r"^(config|tokenizer|vocab|special_tokens)", f) or f.endswith(".safetensors")]
for f in want:
    hf_download_file(f, REPO, "main")
```

### Pinning a revision — [documented; mirrors languages/r/utilities.md, verified 2026-08-22 from R]

Facts: `references/utilities.md` § "Pinning a revision for reproducible work"

```python
import os
import requests
from fbri.package_managers import huggingface as hf

info = requests.get(f"{hf.HF_ENDPOINT}/api/models/{REPO}/revision/main").json()
SHA = info["sha"]        # e.g. "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"

hf.hf_download_repo(REPO, SHA)
model_dir = os.path.join(os.path.expanduser("~"), "huggingface", REPO, SHA)
```

### Inference with transformers — [documented; mirrors languages/r/utilities.md, verified 2026-08-22 from R]

Facts: `references/utilities.md` § "Inference from R works"

`sentence_transformers` is not installed in the SRE; `transformers` and
`torch` are. Mean-pool the token embeddings yourself:

```python
import os
import torch
from transformers import AutoModel, AutoTokenizer

REPO = "sentence-transformers/all-MiniLM-L6-v2"
MDIR = os.path.join(os.path.expanduser("~"), "huggingface", REPO, "main")

tok = AutoTokenizer.from_pretrained(MDIR)
mod = AutoModel.from_pretrained(MDIR)

texts = ["Meta Content Library research", "a second document"]
enc = tok(texts, padding=True, truncation=True, return_tensors="pt")
out = mod(input_ids=enc["input_ids"], attention_mask=enc["attention_mask"])

# mean-pool the token embeddings, masking padding — what SentenceTransformer
# does internally, and what you must do yourself because it is not installed
m = enc["attention_mask"].unsqueeze(-1).float()
emb = torch.sum(out.last_hidden_state * m, dim=1) / torch.clamp(m.sum(dim=1), min=1e-9)

embeddings = emb.detach().numpy()   # rows = texts, cols = 384
embeddings.shape
```

For **generation** models, `generate()` takes
`forced_bos_token_id=tok.lang_code_to_id["de_DE"]` directly — the argument the
R layer needs `py_get_item()` for.

## Retrieving a completed job — [documented; mirrors languages/r/utilities.md]

Facts: `references/utilities.md` § "Retrieve Completed Job Data"

```python
import os
import pandas as pd

job_id = "2025-11-30-xxx-xxx"  # Your job ID

# Get job object
job = client.get_async_job(job_id=job_id)

# Check status. mcl_job_status() upper-cases and trims; comparing the raw
# return value is unsafe — see SKILL.md § "Waiting for a Job".
status = mcl_job_status(job)
print("Status:", status)

if status == "COMPLETE":
    # Save to file
    output_dir = "retrieved_jobs"
    os.makedirs(output_dir, exist_ok=True)

    filename = f"job_{job_id}.json"
    job.write_data_to_file(directory=output_dir, filename=filename)

    # Load — the saved file is an array of records [inferred from R]
    job_data = pd.json_normalize(mcl_load_json(os.path.join(output_dir, filename)))

    print("Retrieved", len(job_data), "records")
```

## Reading job metadata — [documented; mirrors languages/r/utilities.md]

Facts: `references/utilities.md` § "Get Job Metadata"

```python
from datetime import datetime, timezone

# Full job details
job_metadata = mcl_from_json(client.get(path=f"async/jobs/{job_id}").text)

print("Mode:", job_metadata["mode"])
print("Query ID:", job_metadata["query_id"])
print("Created:", datetime.fromtimestamp(job_metadata["creation_time"], tz=timezone.utc))
```

## Reading query information — [documented; mirrors languages/r/utilities.md]

Facts: `references/utilities.md` § "Get Query Information"

```python
query_info = mcl_from_json(client.get(path=f"async/queries/{job_metadata['query_id']}").text)

print("Query Name:", query_info["name"])
print("Platform:", query_info["platform"])
print("Entity Type:", query_info["entity_type"])
print("Parameters:", query_info["params"])
```

## Listing all jobs — [documented; mirrors languages/r/utilities.md]

Facts: `references/utilities.md` § "List All Jobs"

```python
import pandas as pd

jobs_data = mcl_from_json(client.get(path="async/jobs").text)

# View summary — the envelope key is `jobs`, not `data`
print(pd.json_normalize(jobs_data["jobs"])[["id", "status", "mode", "query_id"]])
```

## Verifying ID columns — [documented; mirrors languages/r/utilities.md]

Facts: `references/utilities.md` § "Verify IDs Loaded as Strings"

Run this on any DataFrame before joining, deduplicating, or exporting — it
fails loudly if an ID slipped through as a number:

```python
import pandas as pd
from pandas.api.types import is_numeric_dtype, is_object_dtype, is_string_dtype


def check_ids(df):
    id_cols = [c for c in df.columns if MCL_ID_PATTERN.search(c)]   # "(^|[._])ids?$"
    bad = [c for c in id_cols if is_numeric_dtype(df[c]) and df[c].dtype != bool]   # bool is_invalid_id is fine

    if bad:
        raise ValueError(f"Numeric ID column(s): {', '.join(bad)} — re-parse the source with mcl_from_json()")
    # Digits above 2^53 are already rounded and cannot be repaired
    risky = sum(
        1 for c in id_cols
        if (is_object_dtype(df[c]) or is_string_dtype(df[c]))
        and df[c].dropna().astype(str).str.len().ge(16).any()
    )

    print(f"{len(id_cols)} ID column(s) OK ({risky} with 16+ digit values)")
    return True


check_ids(posts)
```

## Checking a conda-installed binary — [documented; mirrors languages/r/utilities.md, verified 2026-08-24 from R]

Facts: `references/utilities.md` § "⚠ `Conda$new()$Install()` reports "Failed install" for non-R packages — even when conda succeeds"

`shutil.which()` will not find it because the conda prefix is not on `PATH`:

```python
import os, subprocess

p = "/home/jovyan/.fort/user_packages/conda/bin/tesseract"
print(os.path.exists(p)); subprocess.run([p, "--version"])
```

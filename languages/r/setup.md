# Setup — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

## Load the client — [verified 2026-08-21]

Facts: `SKILL.md` § "Setup"

The MCL client is a Python package, `metacontentlibraryapi`, already installed
in the SRE. R reaches it through reticulate, which binds `/opt/conda/bin/python3`
(3.11) — the same interpreter as the notebook's Python kernel.

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
async_utils <- import("metacontentlibraryapi")$MetaContentLibraryAPIAsyncUtils
client$set_default_version(client$LATEST_VERSION)
```

Every method is called on the class itself, never on an instance — there is no
`client()` call. `async_utils` is imported for parity with Meta's examples; no
example in this skill uses it.

Also define `mcl_fromJSON()` from `languages/r/ids.md` § "mcl_fromJSON" — every
example in this skill parses responses with it instead of `fromJSON()` — and
`mcl_wait_for_job()` from `languages/r/jobs.md` § "Waiting for a job".

## Pinning the version

`client$LATEST_VERSION` follows Meta; a notebook re-run after a version bump
queries a different corpus than the paper described (`SKILL.md` § "Citing the
Data"). Pin explicitly when that matters:

```r
client$set_default_version("6.0")
```

## Real-time output in Jupyter

`cat()` output is buffered in the R kernel. Follow every progress `cat()` with
`flush.console()` so a polling loop shows its status lines as they happen.

## What reticulate changes

Three marshalling rules follow from R talking to a Python client. Each is
explained where it bites; this is the list:

| Rule | Why | Where |
|---|---|---|
| Integer parameters take the `L` suffix (`limit = 100L`) | an R `100` is a double and reaches Python as `100.0` | `languages/r/query_params.md` § "Integer parameters" |
| ID parameters go through `as.list()` at every length | a length-1 R vector becomes a Python scalar, and the API rejects a scalar ID | `languages/r/query_params.md` § "ID parameters are arrays" |
| Never pass `params = list()` | an empty unnamed list becomes a Python `[]`, and the client calls `.items()` on it | `languages/r/query_params.md` § "Never pass an empty params" |

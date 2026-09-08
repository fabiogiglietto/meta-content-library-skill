# Setup — Python

> **Language layer: Python — [documented], not yet run.** Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Load the client — [documented; Meta quick-start Python tab]

Facts: `SKILL.md` § "Setup"

The MCL client is the Python package `metacontentlibraryapi`, already installed
in the SRE. Meta's quick-start shows exactly this:

```python
from metacontentlibraryapi import MetaContentLibraryAPIClient as client

client.set_default_version(client.LATEST_VERSION)
```

Every method is called on the class itself, never on an instance — the R layer
does the same through reticulate, and that is `[verified]`. Meta's R example also
imports `MetaContentLibraryAPIAsyncUtils`; no example in this skill uses it, and
what it offers is **open** — `dir(MetaContentLibraryAPIAsyncUtils)` in the SRE
and file a field report.

Also define `mcl_from_json()` from `languages/python/ids.md` § "mcl_from_json" —
every example in this skill parses responses with it instead of a bare
`json.loads()` — and `mcl_wait_for_job()` from `languages/python/jobs.md`
§ "Waiting for a job".

The notebook's Python kernel is `/opt/conda/bin/python3` (3.11) — the interpreter
reticulate binds from R, `[verified 2026-08-22]` from the R side; whether the
Python *kernel* is the same interpreter is tracked in
`docs/ML_MODELS_OPEN_QUESTIONS.md` Q2.

## Pinning the version

`client.LATEST_VERSION` follows Meta; a notebook re-run after a version bump
queries a different corpus than the paper described (`SKILL.md` § "Citing the
Data"). Pin explicitly when that matters:

```python
client.set_default_version("6.0")
```

## Real-time output in Jupyter

`print()` is line-buffered in a notebook cell but a long polling loop can still
lag; use `print(..., flush=True)` for status lines. This is the analogue of the
R layer's `flush.console()`.

## What reticulate changes — and Python does not

The R layer carries three marshalling rules (`languages/r/setup.md` § "What
reticulate changes"). None of them exists here: integers are integers, a
one-element `list` is a list, and an empty `dict` is a dict. The hazards that
**remain** are the API's own — ID parameters must be arrays, IDs must stay
strings — and `languages/python/query_params.md` and `languages/python/ids.md`
say how.

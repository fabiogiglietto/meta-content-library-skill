# Setup — Python

> **Language layer: Python — [documented] unless a section is stamped `[verified DATE]`.** First run from a Python kernel in the SRE on 2026-09-10 (Step 0, Step 0b, Tests 1.1 and 10.1; no job submitted). Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Load the client — [verified 2026-09-10]

Facts: `SKILL.md` § "Setup"

The MCL client is the Python package `metacontentlibraryapi`, already installed
in the SRE. Meta's quick-start shows exactly this:

```python
from metacontentlibraryapi import MetaContentLibraryAPIClient as client

client.set_default_version(client.LATEST_VERSION)
```

Every method is called on the class itself, never on an instance — the R layer
does the same through reticulate, and that is `[verified]`.

**`client.LATEST_VERSION` is the string `"latest"`, not a version number
[verified 2026-09-10].** The client then requests `latest/budgets`, an alias the API
resolves. After `set_default_version("6.0")` the same call goes to
`6.0/budgets`. So the pinning below is not cosmetic: a notebook that keeps
`LATEST_VERSION` cannot say which corpus it queried.

**The client's whole surface [verified 2026-09-10]** — `dir(client)`:
`LATEST_VERSION, delete, get, get_async_job, has_next_page, migrate_path,
openapi_spec, post, query_next_page, set_default_version`. Signatures:

```text
client.get(path: str, estimate: bool = False, version: str | None = None, params: dict | None = None) -> requests.models.Response
client.post(path: str, version=None, params: dict | None = None, body: dict | None = None) -> requests.models.Response
client.delete(path: str, version=None, params=None) -> requests.models.Response
client.get_async_job(job_id: str) -> MetaContentLibraryAPIAsyncJob
client.has_next_page(response) -> bool          # languages/python/query_params.md § "Paging a preview"
client.query_next_page(response) -> requests.models.Response
client.migrate_path(path: str, estimate: bool = False, version=None, params=None) -> requests.models.Response
client.openapi_spec(version=None) -> dict
client.set_default_version(version: str) -> None
```

`get(estimate=True)` is **not** the estimate endpoint: it rewrote a preview
request to `…/preview?…&limit=0&summary=True` and returned `{"data": …}` with
no `estimated_results`. Use `path=".../estimate"` as every example here does.
What `migrate_path` does is **open**.

Meta's R example also imports `MetaContentLibraryAPIAsyncUtils`. Its surface
[verified 2026-09-10]: `get_all_async_queries(version=None)`,
`get_data(response, version=None)`, `get_status(response, version=None)` and
`write_data_to_file(response, filename=None, directory=None, version=None)`,
each taking the `requests.models.Response` of a job call. No example in this
skill uses it; the job object from `get_async_job()` covers the same ground.

Every response is a **`requests.models.Response`** [verified 2026-09-10]:
`.text`, `.json()`, `.status_code` and `.raise_for_status()` are all there.
The client echoes each request into the cell output as a line such as
`GET latest/budgets` — a free transcript of what was actually sent (it omits a
float `limit` while still sending it; `languages/python/query_params.md`
§ "Integer parameters").

Also define `mcl_from_json()` from `languages/python/ids.md` § "mcl_from_json" —
every example in this skill parses responses with it instead of a bare
`json.loads()` — and `mcl_wait_for_job()` from `languages/python/jobs.md`
§ "Waiting for a job".

The notebook's Python 3 kernel is `/opt/conda/bin/python`, Python 3.11.9
(conda-forge, IPython 8.26.0), with pandas 2.3.3 — the same conda interpreter
reticulate binds from R `[verified 2026-09-10]`, which closes
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

# Async jobs — Python

> **Language layer: Python — [documented] unless a section is stamped `[verified DATE]`.** First run from a Python kernel in the SRE on 2026-09-10 (Step 0, Step 0b, Tests 1.1 and 10.1; no job submitted). Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Waiting for a job — [documented; mirrors languages/r/jobs.md, verified 2026-08-21 from R]

Facts: `SKILL.md` § "Waiting for a Job"

`job.get_status()` returned `COMPLETE`, uppercase, on every job observed from R.
The helper is correct under either casing: it cannot spin forever, and it
treats an unrecognized status as "keep waiting" rather than as success.

```python
import time


def mcl_job_status(job):
    return str(job.get_status()).strip().upper()


def mcl_wait_for_job(job, poll=5, timeout=3600):
    deadline = time.monotonic() + timeout
    while True:
        st = mcl_job_status(job)
        if st == "COMPLETE":
            return st
        if st == "FAILED":
            raise RuntimeError(f"Job failed (status: {st})")
        if time.monotonic() > deadline:
            raise TimeoutError(f"Job did not finish within {timeout}s (last status: {st})")
        print("Status:", st, flush=True)
        time.sleep(poll)
```

Every wait in this skill goes through `mcl_wait_for_job()`. If you compare a
status yourself, compare `mcl_job_status(job)`, never the raw return value.

## Safe response handling — [verified 2026-09-10]

Facts: `SKILL.md` § "Safe Response Handling"

This is the single funnel for MCL data — it parses with `mcl_from_json()`
(`languages/python/ids.md` § "mcl_from_json"), so IDs come out as `str`, and it
validates before anything counts rows:

```python
import pandas as pd


def safe_get_data(response_text):
    parsed = mcl_from_json(response_text)          # IDs as str, see ID handling
    data = parsed.get("data") if isinstance(parsed, dict) else None
    if isinstance(data, list) and len(data) > 0:
        return pd.json_normalize(data)
    return None


# Usage
resp = client.get(path="instagram/accounts/preview", params={"q": "test", "limit": 10})
results = safe_get_data(resp.text)
if results is not None:
    print("Found", len(results), "results")

# ✗ Wrong - raises KeyError on a response without `data`, and keeps IDs numeric
results = pd.json_normalize(json.loads(resp.text)["data"])
if len(results) > 0: ...
```

**An empty result is `{"data": []}` with no `paging` key [verified 2026-09-10]**
(a preview whose `q` matched nothing). A non-empty preview is
`{"data": [...], "paging": {"cursors": {"after": …}}}`. Live: three rows through
`safe_get_data()` came back with `id` dtype `object`, every value a 15-digit
`str`.

## Async query template — [documented; mirrors languages/r/jobs.md]

Facts: `SKILL.md` § "Async Query Template"

```python
# 1. Check estimate
estimate_response = client.get(
    path="facebook/posts/estimate",
    params={"q": "climate change", "since": "2024-01-01", "until": "2024-12-31"},
)
estimate = mcl_from_json(estimate_response.text)
print("Estimated:", estimate["estimated_results"], "| Complete:", estimate["expected_complete"], flush=True)

# 2. Submit job (creates query + first job)
response = client.post(
    path="facebook/posts/job",
    params={
        "q": "climate change",
        "since": "2024-01-01",
        "until": "2024-12-31",
        "limit": 100,            # a Python int already is an integer — no suffix needed
        "mode": "SNAPSHOT",
        "name": "Climate Change - 2024 Full Year",
        "description": "Baseline dataset. PI: Dr. Smith, IRB #2024-001",
    },
)
job_data = mcl_from_json(response.text)
job_id = job_data["id"]            # str (a date-slug)
query_id = job_data["query_id"]    # str

# 3. Monitor status (see "Waiting for a job" for mcl_wait_for_job)
job = client.get_async_job(job_id=job_id)
mcl_wait_for_job(job)

# 4. Save results, then load with IDs as str
job.write_data_to_file(directory="results", filename="climate_2024.json")
posts = pd.json_normalize(mcl_load_json("results/climate_2024.json"))
```

The keyword names — `path=`, `params=`, `job_id=`, `directory=`, `filename=` —
are the client's real signature (`languages/python/setup.md` § "Load the
client" lists all of them, [verified 2026-09-10]). `response` is a
`requests.models.Response`, so `.status_code` and `.json()` exist beside
`.text`; an HTTP error raises `requests.exceptions.HTTPError` with the error
JSON as its message and the 400 `Response` on `.response`
(`languages/python/common_errors.md`). What is still **open**, because no job
has been submitted from Python, is the exact shape of the saved file.
**[inferred from R]**: the R layer parses the saved file straight into a table,
so it is a JSON array of records rather than a `{"data": [...]}` envelope —
which is why step 4 above passes the loaded list to `json_normalize` directly.

## Guarding a submission cell — [documented]

Facts: `SKILL.md` § "SNAPSHOT vs LIVE Mode"

Budget is consumed at submission and a deleted job does not refund it, so a
re-run of the submission cell must be a no-op:

```python
from pathlib import Path

if Path("jobs.json").exists():
    raise RuntimeError("already submitted - delete jobs.json to resubmit")
```

## Promoting a LIVE job to a snapshot — [documented]

Facts: `SKILL.md` § "SNAPSHOT vs LIVE Mode"

```python
client.post(path=f"async/jobs/{job_id}/snapshot")
```

## Rerunning a query — [documented]

Facts: `SKILL.md` § "Rerun a Query"

```python
# Creates new job for existing query
rerun_response = client.post(
    path=f"async/queries/{query_id}/job",
    body={"mode": "SNAPSHOT"},
)
new_job_id = mcl_from_json(rerun_response.text)["id"]
```

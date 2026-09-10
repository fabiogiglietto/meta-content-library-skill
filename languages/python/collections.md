# Collections and query management — Python

> **Language layer: Python — [documented] unless a section is stamped `[verified DATE]`.** First run from a Python kernel in the SRE on 2026-09-10 (Step 0, Step 0b, Tests 1.1 and 10.1; no job submitted). Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

Every snippet parses with `mcl_from_json()` (`languages/python/ids.md`
§ "mcl_from_json"), so IDs come out as `str`.

## Managing collections — [documented; mirrors languages/r/collections.md]

Facts: `references/collections.md` § "Collections (Folders)"

```python
# Create collection
response = client.post(
    path="async/collections",
    body={
        "name": "Climate Research 2024",
        "description": "PI: Dr. Smith, IRB #2024-001, NSF Grant #12345",
    },
)
collection_id = mcl_from_json(response.text)["id"]

# Set as default (new queries auto-added here)
client.post(
    path=f"async/collections/{collection_id}",
    body={"default": True},
)

# List all collections
collections = mcl_from_json(client.get(path="async/collections").text)

# Delete collection (queries remain)
client.delete(path=f"async/collections/{collection_id}")
```

## Managing queries — [documented; mirrors languages/r/collections.md]

Facts: `references/collections.md` § "Query Management"

```python
# List all queries
queries = mcl_from_json(client.get(path="async/queries").text)

# Get specific query with all its jobs
query_details = mcl_from_json(client.get(path=f"async/queries/{query_id}").text)

# Update query metadata
client.post(
    path=f"async/queries/{query_id}",
    body={
        "name": "Updated Name - PUBLISHED",
        "description": "Updated with DOI: 10.1234/paper.2025",
    },
)

# Move query to collection
client.post(
    path=f"async/queries/{query_id}",
    body={"collection_id": collection_id},
)

# Make query public (for sharing)
client.post(
    path=f"async/queries/{query_id}",
    body={"visibility": "PUBLIC"},
)

# Delete query (deletes all jobs too!)
client.delete(path=f"async/queries/{query_id}")
```

## Listing jobs — [documented; mirrors languages/r/collections.md, verified 2026-08-24 from R]

Facts: `references/collections.md` § "Job Management"

The listing sits under `jobs`, not `data`; the `assert` is there because
reading the wrong key fails silently (next section).

```python
import pandas as pd

# List all jobs -- the payload is under "jobs", NOT "data". See the warning below.
jl = mcl_from_json(client.get(path="async/jobs").text)
assert "jobs" in jl                          # assert; the wrong key fails silently
jobs = pd.json_normalize(jl["jobs"])         # id, creation_time, update_time,
                                             # status, mode, query_id

# Get job metadata
job_meta = mcl_from_json(client.get(path=f"async/jobs/{job_id}").text)
# Returns: id, status, mode, query_id, creation_time
```

## The `data` fallback idiom is wrong for async/jobs — [documented; mirrors languages/r/collections.md, verified 2026-08-24 from R]

Facts: `references/collections.md` § "⚠ The `async/jobs` envelope key is `jobs`, not `data`"

The common defensive idiom for list-shaped responses:

```python
d = x.get("data", x)     # WRONG for async/jobs
```

Against `async/jobs` it falls through silently: there is no `data`, so `d`
becomes the whole envelope and `d["mode"]` raises `KeyError` — or, worse,
`d.get("mode")` returns `None`. Read `jobs` explicitly instead:

```python
# Counting SNAPSHOT slots against the 100-concurrent cap, correctly:
jobs = pd.json_normalize(mcl_from_json(client.get(path="async/jobs").text)["jobs"])
int(((jobs["mode"] == "SNAPSHOT") & (jobs["status"] != "FAILED")).sum())

# Convert LIVE to SNAPSHOT (preserve data)
client.post(path=f"async/jobs/{job_id}/snapshot")

# Delete job
client.delete(path=f"async/jobs/{job_id}")
```

## Staying under the 100-snapshot cap — [documented; mirrors languages/r/collections.md]

Facts: `references/collections.md` § "The 100-Snapshot Cap"

Run a pull LIVE when reproducibility isn't needed for it:

```python
params["mode"] = "LIVE"      # does not consume a snapshot slot
```

Promote a LIVE job later if it turns out to be worth preserving (the same call
as `languages/python/jobs.md` § "Promoting a LIVE job to a snapshot"):

```python
client.post(path=f"async/jobs/{job_id}/snapshot")
```

Free slots by deleting finished snapshots — job by job, or a whole query:

```python
client.delete(path=f"async/jobs/{job_id}")        # one job
client.delete(path=f"async/queries/{query_id}")   # query + all its jobs
```

## Copying a public query or collection — [documented; mirrors languages/r/collections.md]

Facts: `references/collections.md` § "Reproducibility: Sharing & Copying"

```python
# Copy another researcher's public query
response = client.post(path=f"async/queries/{other_query_id}/copy")
# Copies query + COMPLETE SNAPSHOT jobs
# Jobs are rerun (counts toward YOUR budget)

# Copy entire public collection
response = client.post(path=f"async/collections/{other_collection_id}/copy")
```

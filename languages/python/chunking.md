# Chunking — Python

> **Language layer: Python — [documented], not yet run.** Setup and client calls
> are transcribed from the Python tab of Meta's documentation; helpers and pandas
> handling mirror calls that are `[verified]` from R against the same
> `metacontentlibraryapi` client (keyword arguments pass through reticulate
> unchanged). Nothing here has been executed from a Python kernel. Claims about
> pandas and the standard library are claims about those libraries, not about
> MCL. A section earns `[verified DATE]` through a field report — `SKILL.md`
> § "Contributing Back", kind *promotion*, language *Python*. Where the client's
> behaviour is unknown, the section says so.

## Automatic date chunking — [documented; mirrors languages/r/chunking.md]

Facts: `references/chunking.md` § "Automatic Date Chunking"

```python
import time
from datetime import date, timedelta


def query_with_chunking(query_text, start_date, end_date, platform="facebook",
                        content_type="posts", chunk_size=90):
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)

    # Generate date chunks
    chunks = []
    current = start
    while current <= end:
        chunk_end = min(current + timedelta(days=chunk_size - 1), end)
        chunks.append({"since": current.isoformat(), "until": chunk_end.isoformat()})
        current = chunk_end + timedelta(days=1)

    print("Split into", len(chunks), "chunks", flush=True)

    all_job_ids = []

    for i, chunk in enumerate(chunks, start=1):
        print("Chunk", i, ":", chunk["since"], "to", chunk["until"], flush=True)

        # Check estimate first
        est = mcl_from_json(client.get(
            path=f"{platform}/{content_type}/estimate",
            params={"q": query_text, "since": chunk["since"], "until": chunk["until"]},
        ).text)

        if not est.get("expected_complete"):
            print("  Warning: Chunk exceeds 100k, consider smaller chunks")

        # Submit job
        response = client.post(
            path=f"{platform}/{content_type}/job",
            params={
                "q": query_text,
                "since": chunk["since"],
                "until": chunk["until"],
                "mode": "SNAPSHOT",
                "name": f"{query_text} - {chunk['since']} to {chunk['until']}",
                "description": f"Chunk {i} of {len(chunks)} for large query",
            },
        )

        job_data = mcl_from_json(response.text)
        all_job_ids.append(job_data["id"])   # str

        print("  Job ID:", job_data["id"], flush=True)

        # Rate limit: 1 async per minute
        if i < len(chunks):
            print("  Waiting 60s for rate limit...", flush=True)
            time.sleep(60)

    return all_job_ids


# Usage
job_ids = query_with_chunking(
    query_text="climate change",
    start_date="2024-01-01",
    end_date="2024-12-31",
    chunk_size=30,  # 30-day chunks
)
```

## Combining chunked results — [documented; mirrors languages/r/chunking.md]

Facts: `references/chunking.md` § "Combining Chunked Results"

Every chunk is parsed with `mcl_load_json()`, so the `id` column is `str` in
all of them. `pd.concat()` aligns columns by name and fills gaps with `NaN`,
so the R layer's mismatched-columns hazard does not exist here — but a numeric
`id` column in one chunk would still silently turn the whole column `float64`,
which is what the assertion guards.

```python
import os
import pandas as pd


def combine_chunk_results(job_ids, output_dir="results"):
    os.makedirs(output_dir, exist_ok=True)

    all_data = []

    for i, job_id in enumerate(job_ids, start=1):
        print("Processing job", i, ":", job_id, flush=True)

        job = client.get_async_job(job_id=job_id)

        # Wait for completion — mcl_wait_for_job() is defined in
        # languages/python/jobs.md § "Waiting for a job". A bare != "COMPLETE"
        # loop spins forever if the status comes back lowercase.
        mcl_wait_for_job(job, poll=10)

        # Save to file
        filename = f"chunk_{i}_{job_id}.json"
        job.write_data_to_file(directory=output_dir, filename=filename)

        # Load data (IDs as str, so chunk column types always match)
        data = pd.json_normalize(mcl_load_json(os.path.join(output_dir, filename)))
        if len(data) > 0:
            data["source_chunk"] = i
            data["source_job_id"] = job_id
            all_data.append(data)

        print("  Retrieved", len(data), "records", flush=True)

    # Combine and deduplicate
    combined = pd.concat(all_data, ignore_index=True) if all_data else pd.DataFrame()

    if "id" in combined.columns:
        assert combined["id"].map(type).eq(str).all()   # guard: never dedup on numeric IDs
        before = len(combined)
        combined = combined.drop_duplicates("id", keep="first").reset_index(drop=True)
        print(f"\nDeduplicated: {before} -> {len(combined)} records")

    # Save combined
    combined.to_parquet(os.path.join(output_dir, "combined_deduplicated.parquet"))

    return combined


# Usage
all_data = combine_chunk_results(job_ids)
```

`to_parquet` needs `pyarrow`; whether it is installed in the SRE is **open** —
`to_pickle` is the standard-library fallback and keeps dtypes just as well.

## Collecting only the latest N results — [documented; mirrors languages/r/chunking.md]

Facts: `references/chunking.md` § "Collecting Only the Latest N Results"

`run_job()` stands for your submit-wait-load sequence
(`languages/python/jobs.md` § "Async query template").

```python
from datetime import date, timedelta
import pandas as pd


def collect_latest(params_base, until, n_target, window_days=7, max_windows=52):
    collected = []
    n_have = 0
    end = date.fromisoformat(until)

    for i in range(1, max_windows + 1):
        start = end - timedelta(days=window_days)
        params = dict(params_base,
                      since=start.isoformat(),
                      until=end.isoformat(),
                      limit=100,
                      mode="LIVE",
                      name=f"Latest N - window {i}",
                      description="Newest-first collection, stops at target")

        # ... submit the job, wait, read results into `chunk` ...
        chunk = run_job(params)

        if chunk is not None and len(chunk) > 0:
            collected.append(chunk)
            n_have += len(chunk)
            print(f"Window {start}..{end}: +{len(chunk)} (total {n_have}/{n_target})", flush=True)

        if n_have >= n_target:
            break
        end = start

    return (pd.concat(collected, ignore_index=True)
              .sort_values("creation_time", ascending=False)
              .head(n_target))
```

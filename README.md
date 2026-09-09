# MCL API Skill

> **Version:** 2.0.2 — see [CHANGELOG.md](CHANGELOG.md)

An [Agent Skill](https://agentskills.io) that teaches Claude and Codex how to
query the **Meta Content Library (MCL) API v6.0 from R or Python**. Install it once, then
ask in plain language ("top posts from my producer list this week") and get
code that runs correctly inside Meta's Secure Research Environment (SRE) or the
SOMAR Virtual Data Enclave (VDE) — with the integer typing, string IDs,
SNAPSHOT mode and status polling that the API silently punishes you for
forgetting.

The skill has one language-neutral core and two language layers. **R** (via
reticulate) is the **verified** layer: its code has been run in live SRE
sessions and carries dated `[verified]` stamps. **Python** (the
`metacontentlibraryapi` client with pandas) is **documented, not yet
field-tested**: transcribed from Meta's own Python examples and mirrored from
the verified R calls, section for section, and promoted to `[verified]` as
field reports arrive. When a request does not say which language, the skill
writes R and says so.

Everything the skill teaches is in **[SKILL.md](SKILL.md)**, the `references/`
files it links (API facts, language-neutral), and `languages/r/` and
`languages/python/` (the calls). This README is the front door: what the skill
covers, how to install it in each tool, and what a first query looks like end
to end.

Upstream documentation:
<https://developers.facebook.com/docs/content-library-and-api>. Where this skill
and Meta's docs disagree, the skill records both and keeps whichever claim was
checked against a live response — see `references/field_reference.md` § "Where
the docs and this file disagree".

## What it covers

- **Async query patterns** with integers that arrive as integers (`L` suffix
  in R; nothing to do in Python)
- **SNAPSHOT mode** for reproducible research, and when to use LIVE instead
- **IDs always as strings** (`mcl_fromJSON()` in R, `mcl_from_json()` in
  Python) — no scientific notation, no precision loss above 2^53, no per-batch
  type drift
- **Two language layers that mirror each other** — the same section titles in
  `languages/r/` and `languages/python/`, so a fact checked in one is findable
  in the other
- **Producer lists** — UI CSV import, endpoint paths, response shape, batching,
  and cross-platform account matching
- **Newer surfaces** — Facebook, Instagram and WhatsApp channels and their
  messages/updates, Marketplace listings, fundraisers and donations
- **Safe response handling** for NULL and empty responses
- **Large dataset chunking** for queries over the ~100,000-result cap
- **Quota monitoring**, collections, and job management
- **`q` search syntax** — the symbol operators (`&`, `|`, `-`), precedence, exact
  tokenization, and which fields each endpoint actually searches
- **API search IDs** — replay a Content Library UI search from code, and read its
  filters before running it
- **Verified error subcodes** (3790088, 3790184, 3790057, 3790172) with fixes
- **Citation DOIs** for the API and the Library, and why they are version-specific
- **The monthly wipe** — what the SRE deletes every 30 days, and what survives
- **OpenAPI spec access** for anything the skill doesn't answer
- **A staleness check** — a dated documentation baseline, a one-page tripwire, and
  a map from each of Meta's doc pages to the file here that owns it, plus a
  monthly GitHub Action that opens an issue when Meta's changelog moves

## Installation

The skill is a folder with a `SKILL.md` at its root plus `references/` and
`languages/`. Every tool below reads that same layout; only the location and
the trigger differ.

| Where you work | Where the skill goes | How you trigger it |
|---|---|---|
| Claude Code (CLI, IDE, desktop app) | `~/.claude/skills/mcl-api/` or `<project>/.claude/skills/mcl-api/` | automatic, or `/mcl-api` |
| claude.ai and Claude Desktop | upload a zip under **Customize → Skills** | automatic |
| Codex (CLI, IDE extension) | `~/.agents/skills/mcl-api/` or `<repo>/.agents/skills/mcl-api/` | automatic, or `$mcl-api` |

Nothing here auto-updates. However you install it, you get a snapshot of the
repository at that moment — watch [CHANGELOG.md](CHANGELOG.md) for new versions
and repeat the update step for your tool.

### Claude Code

Clone once, then symlink the clone into your personal skills directory. The
command name comes from the *directory* name, so link it as `mcl-api`:

```bash
git clone https://github.com/fabiogiglietto/meta-content-library-skill.git ~/skills/mcl-api
mkdir -p ~/.claude/skills
ln -s ~/skills/mcl-api ~/.claude/skills/mcl-api
```

For a project-local install, symlink into that project's `.claude/skills/`
instead — or clone straight into `.claude/skills/mcl-api` if collaborators
should get the skill with the repository.

**Update:** `git pull` in the clone. Claude Code watches the skills directory,
so a pulled `SKILL.md` is picked up without a restart — but a conversation that
has already invoked the skill keeps the copy it loaded, so start a new session
after pulling. Files under `references/` are read on demand and are current as
soon as the pull lands.

### claude.ai and Claude Desktop

Upload the skill as a zip under **Customize → Skills → Add**. The zip must have
the skill folder as its root, not the files loose at the top level:

```
mcl-api.zip
└── mcl-api/
    ├── SKILL.md
    ├── references/
    └── languages/
```

```bash
git clone https://github.com/fabiogiglietto/meta-content-library-skill.git mcl-api
zip -r mcl-api.zip mcl-api -x 'mcl-api/.git/*'
```

**Update:** build a fresh zip from a newer clone and upload it again.

### Codex

Codex reads skills from `~/.agents/skills/` (personal) and from `.agents/skills/`
inside a repository (shared with collaborators). The `SKILL.md` frontmatter
already carries the `name` and `description` Codex requires, so the clone is
the skill — no packaging step.

Clone once and symlink it, exactly as for Claude Code; Codex follows symlinked
skill folders:

```bash
git clone https://github.com/fabiogiglietto/meta-content-library-skill.git ~/skills/mcl-api
mkdir -p ~/.agents/skills
ln -s ~/skills/mcl-api ~/.agents/skills/mcl-api
```

Or let Codex's built-in installer fetch it for you — type this in a Codex
session:

```
$skill-installer install https://github.com/fabiogiglietto/meta-content-library-skill
```

Either way, invoke it explicitly with `$mcl-api` at the start of a prompt, or
just describe the task — Codex picks the skill from its description when the
question is about MCL queries in R or Python. Codex detects new skills automatically; if
`$mcl-api` does not autocomplete, restart Codex.

Older Codex releases looked in `~/.codex/skills/` instead; if the skill is not
found, symlink it there as well. To disable it without deleting it, add to
`~/.codex/config.toml`:

```toml
[[skills.config]]
path = "/home/you/skills/mcl-api/SKILL.md"
enabled = false
```

**Update:** `git pull` in the clone (or re-run the installer command).

### Migrating from `mcl-api-r` (versions before 2.0.0)

The skill was named `mcl-api-r` and the repository
`meta-content-library-r-skill` through v1.19.0. Both names changed in 2.0.0,
when the skill gained a Python layer. The command name follows the directory
name, so the migration is a rename plus a pull:

```bash
# Claude Code
mv ~/.claude/skills/mcl-api-r ~/.claude/skills/mcl-api
git -C ~/skills/mcl-api-r remote set-url origin git@github.com:fabiogiglietto/meta-content-library-skill.git
git -C ~/skills/mcl-api-r pull
# Codex: same two steps against ~/.agents/skills/, then update the path in
# ~/.codex/config.toml if you had one
```

GitHub redirects the old repository URL, so a clone that never updates its
remote keeps working; update it anyway. On claude.ai and Claude Desktop, build
`mcl-api.zip` as above, upload it, and **delete the old `mcl-api-r` skill** —
two installed copies with different names both trigger, and the older one wins
often enough to be confusing. Invoke the skill as `/mcl-api` or `$mcl-api` from
then on.

## Your first query, end to end

The skill is used from **outside** the SRE: you talk to Claude or Codex on your
own machine, they write code against the skill, and you paste the result into a
JupyterLab notebook inside the SRE, which has no internet access. Three steps,
shown in R — the verified layer. Ask for Python and the same three steps come
back from `languages/python/`, with the same helpers under Python names:

The same round trip, four stations, as a page with copy buttons and a mock-up of the SRE
notebook: **[visual walkthrough](https://fabiogiglietto.github.io/meta-content-library-skill/first-query.html)**
(GitHub Pages, served from [`docs/first-query.html`](docs/first-query.html)).

**1. Ask.** In claude.ai, Claude Code or Codex:

> Using the mcl-api skill, write R for the SRE that collects Facebook posts
> mentioning "climate change" from January to March 2026 as a SNAPSHOT job,
> waits for it, and tells me how many posts came back.

**2. Read what comes back.** The code carries the skill's habits — the R kernel
setup through reticulate, `mcl_fromJSON()` so IDs stay character, an estimate
before the job, `limit = 100L`, `mode = "SNAPSHOT"`, a name and description, and
a wait loop that cannot spin forever:

```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

# IDs are 15–19 digit numbers: parse them as character, always
MCL_ID_PATTERN <- "(^|[._])ids?$"
mcl_fix_ids <- function(x, name = "") {
  if (is.data.frame(x)) { x[] <- Map(mcl_fix_ids, x, names(x)); return(x) }
  if (is.list(x)) {
    nms <- names(x); if (is.null(nms)) nms <- rep(name, length(x))
    x[] <- Map(mcl_fix_ids, x, nms); return(x)
  }
  if (grepl(MCL_ID_PATTERN, name) && is.numeric(x)) {
    out <- rep(NA_character_, length(x)); ok <- !is.na(x)
    out[ok] <- sprintf("%.0f", x[ok]); return(out)
  }
  x
}
mcl_fromJSON <- function(txt) mcl_fix_ids(fromJSON(txt, flatten = TRUE, bigint_as_char = TRUE))

# 1. Estimate before spending budget
est <- mcl_fromJSON(client$get(
  path = "facebook/posts/estimate",
  params = list("q" = "climate change", "since" = "2026-01-01", "until" = "2026-03-31")
)$text)
cat("Estimated:", est$estimated_results, "| complete:", est$expected_complete, "\n"); flush.console()

# 2. Submit the async job (SNAPSHOT = reproducible, citable)
resp <- client$post(
  path = "facebook/posts/job",
  params = list(
    "q" = "climate change", "since" = "2026-01-01", "until" = "2026-03-31",
    "limit" = 100L, "mode" = "SNAPSHOT",
    "name" = "Climate change FB posts 2026 Q1",
    "description" = "First query. PI: your name, project id"
  )
)
job_id <- mcl_fromJSON(resp$text)$id
cat("Submitted job:", job_id, "\n"); flush.console()

# 3. Wait — case-insensitive, with a timeout
mcl_job_status  <- function(job) toupper(trimws(job$get_status()))
mcl_wait_for_job <- function(job, poll = 5, timeout = 3600) {
  deadline <- Sys.time() + timeout
  repeat {
    st <- mcl_job_status(job)
    if (st == "COMPLETE") return(st)
    if (st == "FAILED")   stop("Job failed (status: ", st, ")")
    if (Sys.time() > deadline) stop("Timed out; last status: ", st)
    cat("Status:", st, "\n"); flush.console(); Sys.sleep(poll)
  }
}
job <- client$get_async_job(job_id = job_id)
mcl_wait_for_job(job)

# 4. Save and load with IDs as character
dir.create("results", showWarnings = FALSE)
job$write_data_to_file(directory = "results", filename = "climate_2026q1.json")
posts <- mcl_fromJSON(file.path("results", "climate_2026q1.json"))
cat("Retrieved", nrow(posts), "posts\n")
```

**3. Paste and run in the SRE.** Open JupyterLab in the Meta Research Platform
(the US or Ireland portal your access was granted for), start a notebook on the
**R** kernel, paste the code into a cell and run it. Poll output appears as it
happens thanks to `flush.console()`; the job id looks like `2026-09-03-abc-xyz`.

Two SRE rules the skill keeps reminding you of: download job results **the
same calendar month** you submit them (the SRE wipes results and files on the
1st), and remember that the exported notebook is **scrubbed** — anything you
need to take out must be rendered as an image in a cell.

### More prompts that trigger the skill

- "Help me query Facebook posts about climate change using MCL API"
- "How do I check my MCL quota?"
- "Create an async query for Instagram posts from my producer list"
- "How do I handle large datasets that exceed 100,000 results?"
- "Find Instagram accounts matching my Facebook producer list"
- "Why do my post IDs show up as 9.6378e+14?"

## Key files

| File | Purpose |
|------|---------|
| `SKILL.md` | The language-neutral core: environment, critical requirements, choosing the language, ID handling, endpoints, jobs, errors, and the routing to everything below |
| `languages/r/` | The R layer, verified — one file per topic, mirroring `references/` by basename; the helpers live here |
| `languages/python/` | The Python layer, documented and not yet field-tested — same files, same section titles |
| `references/query_params.md` | Search parameters, filters, `q` syntax, batch limits |
| `references/producer_lists.md` | Producer lists: creation, endpoint paths, response structure, cross-platform matching |
| `references/chunking.md` | Large dataset handling and date-based splitting |
| `references/collections.md` | Query organization, SNAPSHOT vs LIVE, the 100-snapshot cap |
| `references/field_reference.md` | Available fields by entity type, reshare resolution, data scope |
| `references/common_patterns.md` | Analysis patterns for collected results |
| `references/surfaces.md` | Channels (FB/IG/WhatsApp), Marketplace, fundraisers, donations |
| `references/common_errors.md` | Full error catalog and debugging patterns |
| `references/utilities.md` | Quota checking, package and ML model installation, job retrieval |
| `references/ml_models_approved.md` | The approved pre-trained ML model list, with canonical repo ids |
| `references/field_report.md` | The field report template and routes — how a session's findings travel back here |
| `references/staying_current.md` | The documentation check in full; the baseline and the owner map stay in `SKILL.md` |
| `docs/TESTING_PROCEDURE.md` | Manual verification procedure for the R layer |
| `docs/TESTING_PROCEDURE_PYTHON.md` | The same suites for the Python layer — running one is how a Python section earns its `[verified]` stamp |
| `docs/first-query.html` | The visual walkthrough (prompt, R code, SRE notebook, the field report at the end); GitHub Pages serves it from `/docs` at the link above |
| `.github/ISSUE_TEMPLATE/field-report.yml` | The Field report issue form; one field per template heading |
| `.github/workflows/meta-docs-check.yml` | Monthly check of Meta's changelog; opens an issue on drift |
| `.github/scripts/check_meta_docs.py` | The checker — run `--check` locally, `--update` after reconciling |

## Requirements

- Meta Research Platform access (Amazon WorkSpaces Secure Browser with JupyterLab)
- R with the reticulate package, or Python 3 with pandas — both kernels are in
  the SRE, and the MCL client is a Python package either way
- MCL API v6.0 access

Export from the SRE is by notebook only, and the exported notebook is
**scrubbed**: code, markdown and images are kept, but cell outputs are removed.
Anything you need to take away has to be rendered as an image. Separately, the
SRE **deletes all non-notebook files and all query results every 30 days** — plan
for notebooks that can be re-run rather than files that persist.

## Contributing

The contribution this skill wants most is a **field report**: one thing a live
MCL response taught that the skill did not know — a documented claim that was
wrong, a "documented, not tested" claim that held, an error subcode or field
the skill does not mention. The skill asks for these itself: when a session
ends with something learned, it offers once to write the report, and
`SKILL.md` § "Contributing Back" says what counts and where it goes.

- **Open a [Field report](https://github.com/fabiogiglietto/meta-content-library-skill/issues/new?template=field-report.yml)** —
  the form's fields are the template's headings
  (`references/field_report.md`), so a drafted report pastes in section by
  section.
- **Or open a pull request** with the report as its body and the edit at the
  file that owns the fact, following the release checklist at the end of
  [CHANGELOG.md](CHANGELOG.md).

Reports carry error messages, subcodes, endpoints, parameters, field names
and counts — never MCL content. Each report names the language it ran in.
**The most valuable contribution right now is a Python field report**: every
section of `languages/python/` is documented-not-tested, and one successful
call from a Python kernel promotes it.

## License

MIT License — see [LICENSE](LICENSE) for details.

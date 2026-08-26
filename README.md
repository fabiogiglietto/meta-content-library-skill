# MCL API R Skill for Claude

> **Version:** 1.13.2 — see [CHANGELOG.md](CHANGELOG.md)

A Claude skill for working with the Meta Content Library (MCL) API v6.0 using R.

Upstream documentation:
<https://developers.facebook.com/docs/content-library-and-api>. Where this skill
and Meta's docs disagree, the skill records both and keeps whichever claim was
checked against a live response — see `references/field_reference.md` § "Where
the docs and this file disagree".

## Overview

This skill helps researchers query Facebook, Instagram and WhatsApp public
content using R via reticulate in Meta's Secure Research Environment (SRE) or the
SOMAR Virtual Data Enclave (VDE).

Everything the skill teaches is in **[SKILL.md](SKILL.md)** and the
`references/` files it links. This README is just the front door.

## What it covers

- **Async query patterns** with proper integer handling (`L` suffix)
- **SNAPSHOT mode** for reproducible research, and when to use LIVE instead
- **IDs always as character** (`mcl_fromJSON()`) — no scientific notation, no
  precision loss above 2^53, no per-batch type drift
- **Producer lists** — UI CSV import, endpoint paths, response shape, batching,
  and cross-platform account matching
- **Newer surfaces** — Facebook, Instagram and WhatsApp channels and their
  messages/updates, Marketplace listings, fundraisers and donations
- **Safe response handling** for NULL and empty responses
- **Large dataset chunking** for queries over the ~100,000-result cap
- **Quota monitoring**, collections, and job management
- **`q` search syntax** — the symbol operators (`&`, `|`, `-`), precedence, exact
  tokenization, and which fields each endpoint actually searches
- **API search IDs** — replay a Content Library UI search from R, and read its
  filters before running it
- **Verified error subcodes** (3790088, 3790184, 3790057, 3790172) with fixes
- **Citation DOIs** for the API and the Library, and why they are version-specific
- **The monthly wipe** — what the SRE deletes every 30 days, and what survives
- **OpenAPI spec access** for anything the skill doesn't answer
- **A staleness check** — a dated documentation baseline, a one-page tripwire, and
  a map from each of Meta's doc pages to the file here that owns it, plus a
  monthly GitHub Action that opens an issue when Meta's changelog moves

## Installation

Nothing here auto-updates. However you install it, you get a snapshot of the
repository at that moment — watch [CHANGELOG.md](CHANGELOG.md) for new versions
and re-run the update step below.

### Claude Code

Clone once, then symlink the clone into your personal skills directory. The
command name comes from the *directory* name, so link it as `mcl-api-r`:

```bash
git clone https://github.com/fabiogiglietto/mcl-api-r-skil.git ~/skills/mcl-api-r-skil
ln -s ~/skills/mcl-api-r-skil ~/.claude/skills/mcl-api-r
```

For a project-local install, symlink into that project's `.claude/skills/`
instead — or clone straight into `.claude/skills/mcl-api-r` if collaborators
should get the skill with the repository.

Update with `git pull` in the clone. Claude Code watches the skills directory,
so a pulled `SKILL.md` is picked up without a restart — but a conversation that
has already invoked the skill keeps the copy it loaded, so start a new session
after pulling. Files under `references/` are read on demand and are current as
soon as the pull lands.

### claude.ai and Claude Desktop

Upload the skill as a zip under **Customize → Skills → Add**. The zip must have
the skill folder as its root, not the files loose at the top level:

```
mcl-api-r.zip
└── mcl-api-r/
    ├── SKILL.md
    └── references/
```

```bash
git clone https://github.com/fabiogiglietto/mcl-api-r-skil.git mcl-api-r
zip -r mcl-api-r.zip mcl-api-r -x 'mcl-api-r/.git/*'
```

To update, build a fresh zip from a newer clone and upload it again.

## Usage

Claude uses this skill automatically when you ask about MCL API queries in R,
Facebook/Instagram content library research, producer lists, or quota and budget
monitoring.

### Example prompts

- "Help me query Facebook posts about climate change using MCL API"
- "How do I check my MCL quota?"
- "Create an async query for Instagram posts from my producer list"
- "How do I handle large datasets that exceed 100,000 results?"
- "Find Instagram accounts matching my Facebook producer list"
- "Why do my post IDs show up as 9.6378e+14?"

## Key files

| File | Purpose |
|------|---------|
| `SKILL.md` | Setup, critical requirements, ID handling, first-query errors |
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
| `docs/TESTING_PROCEDURE.md` | Manual verification procedure for the code examples |
| `.github/workflows/meta-docs-check.yml` | Monthly check of Meta's changelog; opens an issue on drift |
| `.github/scripts/check_meta_docs.py` | The checker — run `--check` locally, `--update` after reconciling |

## Requirements

- Meta Research Platform access (Amazon WorkSpaces Secure Browser with JupyterLab)
- R with the reticulate package
- MCL API v6.0 access

Export from the SRE is by notebook only, and the exported notebook is
**scrubbed**: code, markdown and images are kept, but cell outputs are removed.
Anything you need to take away has to be rendered as an image. Separately, the
SRE **deletes all non-notebook files and all query results every 30 days** — plan
for notebooks that can be re-run rather than files that persist.

## Contributing

Contributions are welcome. Please open an issue or pull request. When changing
documented behavior, follow the release checklist at the end of
[CHANGELOG.md](CHANGELOG.md).

## License

MIT License — see [LICENSE](LICENSE) for details.

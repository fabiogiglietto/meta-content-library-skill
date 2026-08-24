# MCL API R Skill for Claude

> **Version:** 1.11.2 — see [CHANGELOG.md](CHANGELOG.md)

A Claude skill for working with the Meta Content Library (MCL) API v6.0 using R.

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
- **Verified error subcodes** (3790088, 3790184, 3790057, 3790172) with fixes
- **OpenAPI spec access** for anything the skill doesn't answer

## Installation

### Claude Desktop / Claude Code

```json
{
  "skills": [
    {
      "source": "github:fabiogiglietto/mcl-api-r-skil"
    }
  ]
}
```

### Manual

1. Download the latest release
2. Extract to your skills directory
3. Reference the skill in your Claude configuration

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
| `docs/TESTING_PROCEDURE.md` | Manual verification procedure for the code examples |

## Requirements

- Meta Research Platform access (Amazon WorkSpaces Secure Browser with JupyterLab)
- R with the reticulate package
- MCL API v6.0 access

Export from the SRE is by notebook only, and the exported notebook is
**scrubbed**: code, markdown and images are kept, but cell outputs are removed.
Anything you need to take away has to be rendered as an image.

## Contributing

Contributions are welcome. Please open an issue or pull request. When changing
documented behavior, follow the release checklist at the end of
[CHANGELOG.md](CHANGELOG.md).

## License

MIT License — see [LICENSE](LICENSE) for details.

# MCL API R Skill for Claude

A Claude skill for working with Meta Content Library (MCL) API v6.0 using R.

## Overview

This skill helps researchers query Facebook, Instagram, and Threads public content using R via reticulate in Meta's Secure Research Environment (SRE) or SOMAR Virtual Data Enclave (VDE).

## Features

- **Async query patterns** with proper integer handling (`L` suffix)
- **SNAPSHOT mode** for reproducible research (data preserved up to 1 year)
- **Producer list workflows** with auto-detect platform (surface_ids vs account_ids)
- **Quota monitoring** and budget management
- **Large dataset chunking** strategies for 100K+ result queries
- **Collection organization** for managing research projects
- **OpenAPI spec access** for programmatic API discovery

## Installation

### For Claude Desktop / Claude Code

Add to your Claude configuration:

```json
{
  "skills": [
    {
      "source": "github:YOUR_USERNAME/mcl-api-r-skill"
    }
  ]
}
```

### Manual Installation

1. Download the latest release
2. Extract to your skills directory
3. Reference the skill in your Claude configuration

## Usage

Once installed, Claude will automatically use this skill when you ask about:

- MCL API queries in R
- Facebook/Instagram/Threads content library research
- Meta Research Platform workflows
- Producer list management
- Quota and budget monitoring

### Example Prompts

- "Help me query Facebook posts about climate change using MCL API"
- "How do I check my MCL quota?"
- "Create an async query for Instagram posts from my producer list"
- "How do I handle large datasets that exceed 100,000 results?"

## Key Files

| File | Purpose |
|------|---------|
| `SKILL.md` | Core patterns, setup, and critical requirements |
| `references/utilities.md` | Quota checking, package installation, job retrieval |
| `references/producer_lists.md` | Working with producer lists (platform detection) |
| `references/chunking.md` | Large dataset handling and date-based splitting |
| `references/collections.md` | Query organization and reproducibility |
| `references/query_params.md` | Search parameters and filters |
| `references/query_syntax.md` | Boolean operators and search syntax |
| `references/field_reference.md` | Available fields by entity type |
| `references/common_patterns.md` | Reusable code patterns |

## Critical Requirements

1. **Always use async queries** (`POST` to `/job` endpoints) for research
2. **Integer literals**: Use `L` suffix (e.g., `limit = 100L`)
3. **Always document**: Include `name`, `description`, `mode = "SNAPSHOT"` in every query
4. **Use `flush.console()`** after `cat()` in Jupyter for real-time output
5. **Platform IDs**: Facebook uses `surface_ids`, Instagram uses `account_ids`
6. **Instagram IDs**: Use `post_ids` (not `surface_ids`) for Instagram posts
7. **Nested endpoints**: Instagram comments require post ID in URL path, not as parameter

## Environment

- **Platform**: Amazon WorkSpaces Secure Browser with JupyterLab
- **Language**: R with Python client via reticulate
- **Export**: Entire notebook only (no copy/paste from SRE)

## Rate Limits

| Resource | Limit |
|----------|-------|
| Sync queries | 60/minute |
| Async queries | 1/minute |
| Query budget | 500,000 records/7-day rolling |
| Comment budget | 500,000 comments/7-day rolling (separate) |
| Max async results | ~100,000 per query |

## Requirements

- Meta Research Platform access (Amazon WorkSpaces Secure Browser)
- R with reticulate package
- MCL API v6.0 access

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Changelog

### v1.0.0 (2025-01)
- Initial release
- Core async query patterns
- Producer list support with platform auto-detection
- Quota monitoring utilities
- Large dataset chunking
- Collection management

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

## How to Use This Repository

This repository contains a Claude **skill** that teaches Claude how to help you work with the Meta Content Library (MCL) API using R. You can use this skill in three different ways depending on your Claude platform:

### Option 1: Claude Code (CLI)

If you're using [Claude Code](https://docs.anthropic.com/en/docs/claude-code/overview) from the command line:

1. **Add the skill to your Claude Code configuration:**

   Edit your Claude configuration file (`.claude/config.json` or global config):

   ```json
   {
     "skills": [
       {
         "source": "github:fabiogiglietto/mcl-api-r-skil"
       }
     ]
   }
   ```

2. **Use Claude Code in your project:**

   ```bash
   cd your-mcl-research-project
   claude
   ```

3. **Ask Claude for help:**

   Claude will automatically use this skill when you ask about MCL API queries. For example:
   - "Help me create an async query for Facebook posts about climate change"
   - "How do I check my MCL quota?"
   - "Show me how to retrieve Instagram posts from my producer list"

### Option 2: Claude Desktop

If you're using the Claude Desktop app:

1. **Add the skill to your Claude Desktop configuration:**

   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

   ```json
   {
     "skills": [
       {
         "source": "github:fabiogiglietto/mcl-api-r-skil"
       }
     ]
   }
   ```

2. **Restart Claude Desktop**

3. **Start a new conversation** and ask Claude to help with MCL API tasks

### Option 3: Claude Projects (Web - claude.ai)

If you're using Claude on the web at [claude.ai](https://claude.ai):

1. **Create a new Project** or open an existing one

2. **Add this repository as project knowledge:**
   - Click "Add Content" in the Project Knowledge section
   - Select "Add GitHub Repository"
   - Enter: `https://github.com/fabiogiglietto/mcl-api-r-skil`
   - Click "Import"

3. **Use the project** for your MCL research:
   - All conversations in this project will have access to the skill knowledge
   - Claude will automatically reference the skill documentation when helping with MCL API queries

**Note:** When using Claude Projects, the skill files are treated as reference documentation rather than executable skills. Claude will read and apply the patterns from `SKILL.md` and the reference files when answering your questions.

## What You Can Ask

Once the skill is available (via any method above), Claude can help you with:

- **MCL API queries in R** - Create async queries for Facebook, Instagram, or Threads content
- **Producer list management** - Work with producer lists, handle platform-specific ID parameters
- **Quota monitoring** - Check your budget and avoid hitting rate limits
- **Large dataset handling** - Split queries to work around the 100K result limit
- **Collection organization** - Organize queries into collections for reproducibility
- **Error troubleshooting** - Debug common API errors and parameter issues

### Example Prompts

- "Help me query Facebook posts about climate change from January to December 2024 using MCL API"
- "How do I check my remaining MCL quota?"
- "Create an async query for Instagram posts from my producer list with account IDs"
- "My query has more than 100,000 results - how do I handle this?"
- "Show me how to retrieve comments for a specific Instagram post"
- "How do I create a collection to organize my research queries?"

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

### v1.2.0 (2026-01)
- **BREAKING**: Fixed producer lists endpoint (`/lists/producers` not `/producer-lists`)
- **BREAKING**: Fixed producer ID extraction (`list_data$producers$id` not `list_data$ids`)
- Added `account_ids` and `surface_ids` limit of 250 per request
- Added batching pattern for large producer lists
- Added `dplyr::bind_rows()` recommendation for combining results
- Added new common errors and solutions
- Added complete working example for posts + comments retrieval

### v1.1.0 (2025-01-04)
- Fixed Instagram parameter documentation (`post_ids` not `surface_ids`)
- Added nested endpoints documentation for Instagram comments/replies
- Added OpenAPI spec discovery pattern for debugging
- Added common_errors.md reference file
- Clarified platform-specific ID parameter differences

### v1.0.0 (2025-01)
- Initial release
- Core async query patterns
- Producer list support with platform auto-detection
- Quota monitoring utilities
- Large dataset chunking
- Collection management

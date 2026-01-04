# Query Syntax Reference

## Table of Contents
1. [Basic Queries](#basic-queries)
2. [Boolean Operators](#boolean-operators)
3. [Phrase Matching](#phrase-matching)
4. [Field-Specific Searches](#field-specific-searches)
5. [Date Filtering](#date-filtering)
6. [Engagement Filters](#engagement-filters)
7. [Geographic Filters](#geographic-filters)

## Basic Queries

Simple keyword search matches posts containing the term:

```r
# Single keyword
client$search_fb_posts(q = "election")

# Multiple keywords (implicit OR)
client$search_fb_posts(q = "election voting ballot")
```

## Boolean Operators

Combine terms with AND, OR, NOT:

```r
# AND - both terms required
client$search_fb_posts(q = "climate AND policy")

# OR - either term
client$search_fb_posts(q = "climate OR environment")

# NOT - exclude term
client$search_fb_posts(q = "vaccine NOT covid")

# Complex combinations with parentheses
client$search_fb_posts(q = "(climate OR environment) AND (policy OR legislation)")
```

## Phrase Matching

Exact phrase matching with quotes:

```r
# Exact phrase
client$search_fb_posts(q = '"climate change"')

# Phrase with other terms
client$search_fb_posts(q = '"climate change" policy')

# Multiple phrases
client$search_fb_posts(q = '"global warming" OR "climate change"')
```

## Field-Specific Searches

Target specific content fields:

```r
# Search in post text only
client$search_fb_posts(
  q = "election",
  search_fields = c("text")
)

# Search in text and image OCR
client$search_fb_posts(
  q = "vote",
  search_fields = c("text", "image_text")
)

# Available search fields:
# - text: Post body text
# - image_text: OCR-extracted text from images (last 180 days)
# - link_title: Title of shared links
# - link_description: Description of shared links
```

## Date Filtering

Filter by creation date:

```r
# Date range (required for most queries)
client$search_fb_posts(
  q = "election",
  start_date = "2024-01-01",
  end_date = "2024-03-31"
)

# Single day
client$search_fb_posts(
  q = "superbowl",
  start_date = "2024-02-11",
  end_date = "2024-02-11"
)

# Date format: YYYY-MM-DD (ISO 8601)
# Maximum range: Varies by endpoint, typically 1 year
```

## Engagement Filters

Filter by engagement metrics:

```r
# Minimum reactions
client$search_fb_posts(
  q = "breaking news",
  min_reactions = 1000
)

# Minimum shares
client$search_fb_posts(
  q = "viral",
  min_shares = 500
)

# Minimum comments
client$search_fb_posts(
  q = "controversial",
  min_comments = 100
)

# Combined engagement filters
client$search_fb_posts(
  q = "trending",
  min_reactions = 500,
  min_shares = 100,
  min_comments = 50
)

# Minimum views (where available)
client$search_fb_posts(
  q = "video",
  min_views = 10000,
  media_type = "video"
)
```

## Geographic Filters

Filter by location:

```r
# Country filter (ISO 3166-1 alpha-2)
client$search_fb_posts(
  q = "election",
  country = "US"
)

# Multiple countries
client$search_fb_posts(
  q = "EU policy",
  country = c("DE", "FR", "IT", "ES")
)

# Language filter (ISO 639-1)
client$search_fb_posts(
  q = "election",
  lang = "en"
)

# Multiple languages
client$search_fb_posts(
  q = "climate",
  lang = c("en", "es", "fr")
)

# Combined geo and language
client$search_fb_posts(
  q = "politik",
  country = "DE",
  lang = "de"
)
```

## Verified Account Filter

Filter by verification status:

```r
# Only verified accounts
client$search_fb_posts(
  q = "announcement",
  verified = TRUE
)

# Only unverified accounts
client$search_fb_posts(
  q = "local news",
  verified = FALSE
)

# All accounts (default)
client$search_fb_posts(
  q = "news",
  verified = NULL
)
```

## Media Type Filters

Filter by content type:

```r
# Posts with photos
client$search_fb_posts(
  q = "landscape",
  media_type = "photo"
)

# Posts with videos
client$search_fb_posts(
  q = "tutorial",
  media_type = "video"
)

# Reels only (Instagram)
client$search_ig_posts(
  q = "dance",
  media_type = "reel"
)

# Posts with links
client$search_fb_posts(
  q = "article",
  media_type = "link"
)
```

## Producer Lists

Search within specific account collections:

```r
# Create producer list (in UI first, then reference by ID)
client$search_fb_posts(
  q = "policy",
  producer_list_id = "your_producer_list_id"
)

# Useful for:
# - Tracking specific news outlets
# - Monitoring political figures
# - Following brand accounts
```

## Query Limits and Best Practices

1. **Keep queries specific** - Broad queries hit rate limits faster
2. **Use date ranges** - Always specify start/end dates
3. **Leverage filters** - Country, language, engagement filters reduce result size
4. **Test in UI first** - Validate queries in Content Library UI before API
5. **Escape special characters** - Use backslash for literal quotes, parentheses
6. **Avoid stop words** - Common words (the, a, is) may be ignored

## Error Messages

| Error | Cause | Solution |
|-------|-------|----------|
| `INVALID_QUERY` | Syntax error in query | Check quotes, parentheses balance |
| `DATE_RANGE_TOO_LARGE` | Range exceeds limit | Split into smaller date chunks |
| `RATE_LIMIT_EXCEEDED` | Too many requests | Wait and retry, or use async |
| `FIELD_NOT_AVAILABLE` | Invalid field requested | Check field_reference.md |

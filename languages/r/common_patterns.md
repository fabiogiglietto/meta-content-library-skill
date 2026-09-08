# Common analysis patterns — R

> **Language layer: R via reticulate — the verified layer.** A section stamped
> `[verified DATE]` was run in a live SRE session on that date; an unstamped one
> was transcribed. API facts live in `references/`; this file shows the call.

Recipes are tidyverse (`dplyr`, `tidyr`, `purrr`, `stringr`, `lubridate`,
`ggplot2`). Every result set is assumed loaded with `mcl_fromJSON()`
(`languages/r/ids.md` § "mcl_fromJSON"), so field names are the `flatten = TRUE`
dotted ones (`statistics.reactions`) and ID columns are character.

## Combining results with mismatched columns

Facts: `references/common_patterns.md` § "Combining Results with Mismatched Columns"

Use `dplyr::bind_rows()` instead of `rbind()` to handle data frames with
different columns:

```r
library(dplyr)

# Collect multiple job results
all_results <- list()

for (job_id in job_ids) {
  job <- client$get_async_job(job_id = job_id)

  mcl_wait_for_job(job)   # SKILL.md § "Waiting for a Job"; never compare status
                          # case-sensitively, and never treat an unknown status
                          # as "done"

  job$write_data_to_file(directory = "results", filename = paste0(job_id, ".json"))
  result <- mcl_fromJSON(file.path("results", paste0(job_id, ".json")))
  all_results[[length(all_results) + 1]] <- result
}

# ✗ WRONG - Fails when columns don't match
# combined <- do.call(rbind, all_results)
# Error: numbers of columns of arguments do not match

# ✓ CORRECT - Handles different columns gracefully
combined <- bind_rows(all_results)
```

`mcl_wait_for_job()` is in `languages/r/jobs.md` § "Waiting for a job".

**bind_rows() behavior:**
- Fills missing columns with `NA`
- Preserves all columns from all dataframes
- Works with lists of dataframes

**Type mismatch, not just column mismatch:** `bind_rows()` also refuses to combine
the same column when its type differs across batches — *"Can't combine `id`
<character> and `id` <double>"*. That is exactly what plain `fromJSON()` produces,
because `bigint_as_char` converts a column only in the batches that happen to
contain an ID above 2^53. `mcl_fromJSON()` coerces every ID field unconditionally,
so all batches agree.

## ID hygiene in analysis

Facts: `references/common_patterns.md` § "ID Hygiene in Analysis"

```r
# Joins and dedup — character keys only
combined <- bind_rows(all_results) %>%
  distinct(id, .keep_all = TRUE)

posts_with_meta <- posts %>%
  left_join(accounts, by = c("post_owner.id" = "id"))   # both character, or the join silently misses

# Round-tripping through CSV: force character on read
write_csv(posts, "posts.csv")
posts <- read_csv("posts.csv", col_types = cols(.default = col_character()))
# or per column: cols(id = col_character(), post_owner.id = col_character())

# ✗ Never do this - re-introduces the double
posts$id <- as.numeric(posts$id)

# Sanity check before any join/dedup/export
# (list-columns hold vectors of IDs, already fixed element-wise by mcl_fix_ids;
#  logical flags such as is_invalid_id are left alone by design)
stopifnot(!any(vapply(posts[grep(MCL_ID_PATTERN, names(posts))], is.numeric, logical(1))))
```

`MCL_ID_PATTERN` and `mcl_fix_ids()` come from `languages/r/ids.md` §
"mcl_fromJSON". `.rds` preserves the character type (as does `.parquet`); CSV
does not, so prefer `saveRDS()` for intermediate artifacts that contain IDs.

## Daily post volume

Facts: `references/common_patterns.md` § "Daily Post Volume"

```r
daily_volume <- posts %>%
  mutate(date = as_date(creation_time)) %>%
  count(date, name = "n_posts")

# Plot
ggplot(daily_volume, aes(x = date, y = n_posts)) +
  geom_line() +
  geom_smooth(method = "loess", se = FALSE, color = "blue") +
  labs(
    title = "Daily Post Volume",
    x = "Date",
    y = "Number of Posts"
  ) +
  theme_minimal()
```

## Hourly patterns

Facts: `references/common_patterns.md` § "Hourly Patterns"

```r
hourly_pattern <- posts %>%
  mutate(hour = hour(creation_time)) %>%
  count(hour) %>%
  mutate(pct = n / sum(n) * 100)

ggplot(hourly_pattern, aes(x = hour, y = pct)) +
  geom_col(fill = "steelblue") +
  scale_x_continuous(breaks = 0:23) +
  labs(
    title = "Posting Activity by Hour (UTC)",
    x = "Hour",
    y = "% of Posts"
  ) +
  theme_minimal()
```

## Rolling averages

Facts: `references/common_patterns.md` § "Rolling Averages"

```r
rolling_engagement <- posts %>%
  mutate(date = as_date(creation_time)) %>%
  group_by(date) %>%
  summarise(
    total_reactions = sum(statistics.reactions, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(date) %>%
  mutate(
    rolling_7d = zoo::rollmean(total_reactions, 7, fill = NA, align = "right")
  )
```

## Basic engagement metrics

Facts: `references/common_patterns.md` § "Basic Engagement Metrics"

```r
engagement_summary <- posts %>%
  summarise(
    n_posts = n(),
    total_reactions = sum(statistics.reactions, na.rm = TRUE),
    total_comments = sum(statistics.comments, na.rm = TRUE),
    total_shares = sum(statistics.shares, na.rm = TRUE),
    total_views = sum(statistics.views, na.rm = TRUE),
    avg_reactions = mean(statistics.reactions, na.rm = TRUE),
    median_reactions = median(statistics.reactions, na.rm = TRUE)
  )
```

## Engagement by account type

Facts: `references/common_patterns.md` § "Engagement by Account Type"

```r
engagement_by_type <- posts %>%
  group_by(post_owner.type) %>%     # page, group, event, profile
  summarise(
    n_posts = n(),
    avg_reactions = mean(statistics.reactions, na.rm = TRUE),
    avg_shares = mean(statistics.shares, na.rm = TRUE),
    total_reach = sum(statistics.views, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(desc(total_reach))
```

## Top performing content

Facts: `references/common_patterns.md` § "Top Performing Content"

```r
top_posts <- posts %>%
  mutate(
    engagement_score = statistics.reactions +
                       statistics.comments * 2 +
                       statistics.shares * 3
  ) %>%
  arrange(desc(engagement_score)) %>%
  head(100) %>%
  select(id, post_owner.name, engagement_score, creation_time)

# Note: Cannot export actual post text
```

## Engagement distribution

Facts: `references/common_patterns.md` § "Engagement Distribution"

```r
engagement_dist <- posts %>%
  mutate(
    reaction_bucket = cut(
      statistics.reactions,
      breaks = c(0, 10, 100, 1000, 10000, Inf),
      labels = c("0-10", "11-100", "101-1K", "1K-10K", "10K+"),
      include.lowest = TRUE
    )
  ) %>%
  count(reaction_bucket) %>%
  mutate(pct = n / sum(n) * 100)
```

## Language distribution

Facts: `references/common_patterns.md` § "Language Distribution"

```r
language_dist <- posts %>%
  count(lang, sort = TRUE) %>%
  mutate(pct = n / sum(n) * 100) %>%
  head(10)
```

## Media type analysis

Facts: `references/common_patterns.md` § "Media Type Analysis"

```r
media_analysis <- posts %>%
  count(media_type) %>%
  mutate(pct = n / sum(n) * 100)

# Engagement by media type
media_engagement <- posts %>%
  group_by(media_type) %>%
  summarise(
    n = n(),
    avg_reactions = mean(statistics.reactions, na.rm = TRUE),
    avg_views = mean(statistics.views, na.rm = TRUE),
    .groups = "drop"
  )
```

## Hashtag extraction (Instagram)

Facts: `references/common_patterns.md` § "Hashtag Extraction (Instagram)"

`extract_hashtags()` is defined here (`stringr` + `purrr` + `tidyr`).

```r
# Instagram post text is in `caption`; Facebook post text is in `text`
extract_hashtags <- function(text) {
  if (is.na(text)) return(character(0))
  str_extract_all(text, "#\\w+")[[1]]
}

hashtag_counts <- posts %>%
  mutate(hashtags = map(caption, extract_hashtags)) %>%
  unnest(hashtags) %>%
  count(hashtags, sort = TRUE) %>%
  head(50)
```

## Cross-posting (reshares)

Facts: `references/common_patterns.md` § "Cross-Posting (Reshares)"

```r
crossposts <- posts %>%
  filter(!is.na(shared_post_id)) %>%
  count(post_owner.id, shared_post_id, sort = TRUE)

# Accounts that appear as resharers
resharer_activity <- posts %>%
  filter(!is.na(shared_post_id)) %>%
  count(post_owner.id, post_owner.name, sort = TRUE, name = "n_reshares")
```

## Reply networks from comments

Facts: `references/common_patterns.md` § "Reply Networks from Comments"

```r
edges <- comments %>%
  filter(!is.na(parent_id), nzchar(parent_id)) %>%
  select(from = owner.id, to = parent_id)
```

## Comparative analysis

Facts: `references/common_patterns.md` § "Comparative Analysis"

```r
# posts_a, posts_b: two result sets already loaded with mcl_fromJSON()
comparison <- bind_rows(
  posts_a %>% mutate(group = "renewable energy"),
  posts_b %>% mutate(group = "fossil fuels")
) %>%
  group_by(group) %>%
  summarise(
    n_posts          = n(),
    n_accounts       = n_distinct(post_owner.id),
    total_engagement = sum(statistics.reactions + statistics.shares, na.rm = TRUE),
    avg_engagement   = mean(statistics.reactions + statistics.shares, na.rm = TRUE),
    .groups = "drop"
  )
```

## Aggregate statistics (exportable)

Facts: `references/common_patterns.md` § "Aggregate Statistics (Exportable)"

```r
# These aggregate outputs can typically be exported
exportable_summary <- posts %>%
  mutate(date = as_date(creation_time)) %>%
  group_by(date) %>%
  summarise(
    n_posts = n(),
    n_unique_accounts = n_distinct(post_owner.id),
    total_reactions = sum(statistics.reactions, na.rm = TRUE),
    total_shares = sum(statistics.shares, na.rm = TRUE),
    avg_reactions = mean(statistics.reactions, na.rm = TRUE),
    .groups = "drop"
  )

# Save for export request
write_csv(exportable_summary, "aggregate_daily_stats.csv")
```

## Export-ready visualizations

Facts: `references/common_patterns.md` § "Create Export-Ready Visualizations"

```r
# Save plots as PNG (can be exported after review)
p <- ggplot(exportable_summary, aes(x = date, y = n_posts)) +
  geom_line() +
  labs(title = "Daily Post Volume", x = "Date", y = "Posts") +
  theme_minimal()

ggsave("daily_volume_chart.png", p, width = 10, height = 6, dpi = 300)
```

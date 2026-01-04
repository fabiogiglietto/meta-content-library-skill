# Common Analysis Patterns

## Table of Contents
1. [Setup and Data Collection](#setup-and-data-collection)
2. [Time Series Analysis](#time-series-analysis)
3. [Engagement Analysis](#engagement-analysis)
4. [Content Analysis](#content-analysis)
5. [Network Analysis](#network-analysis)
6. [Comparative Analysis](#comparative-analysis)
7. [Export Preparation](#export-preparation)

## Setup and Data Collection

### Load Required Libraries

```r
# Pre-installed in MCL environment
library(metacontentlibrary)
library(tidyverse)
library(lubridate)

# Initialize client
client <- MCLClient$new()
```

### Robust Data Collection with Pagination

```r
collect_all_posts <- function(client, query, start_date, end_date, ...) {
  all_results <- list()
  cursor <- NULL
  page <- 1
  
  repeat {
    message(sprintf("Fetching page %d...", page))
    
    response <- tryCatch({
      client$search_fb_posts(
        q = query,
        start_date = start_date,
        end_date = end_date,
        limit = 1000,
        cursor = cursor,
        ...
      )
    }, error = function(e) {
      message(sprintf("Error on page %d: %s", page, e$message))
      return(NULL)
    })
    
    if (is.null(response)) break
    
    all_results <- c(all_results, list(response$data))
    
    if (is.null(response$paging$next_cursor)) break
    cursor <- response$paging$next_cursor
    page <- page + 1
    
    Sys.sleep(0.5)  # Rate limit courtesy
  }
  
  bind_rows(all_results)
}

# Usage
posts <- collect_all_posts(
  client,
  query = "climate change",
  start_date = "2024-01-01",
  end_date = "2024-03-31",
  lang = "en"
)
```

### Chunk Large Date Ranges

```r
collect_by_month <- function(client, query, start_date, end_date, ...) {
  dates <- seq(
    ymd(start_date),
    ymd(end_date),
    by = "month"
  )
  
  all_data <- map_dfr(seq_along(dates[-length(dates)]), function(i) {
    chunk_start <- dates[i]
    chunk_end <- dates[i + 1] - days(1)
    
    message(sprintf("Collecting %s to %s", chunk_start, chunk_end))
    
    collect_all_posts(
      client, query,
      start_date = as.character(chunk_start),
      end_date = as.character(chunk_end),
      ...
    )
  })
  
  all_data
}
```

## Time Series Analysis

### Daily Post Volume

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

### Hourly Patterns

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

### Rolling Averages

```r
rolling_engagement <- posts %>%
  mutate(date = as_date(creation_time)) %>%
  group_by(date) %>%
  summarise(
    total_reactions = sum(statistics$reactions, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(date) %>%
  mutate(
    rolling_7d = zoo::rollmean(total_reactions, 7, fill = NA, align = "right")
  )
```

## Engagement Analysis

### Basic Engagement Metrics

```r
engagement_summary <- posts %>%
  summarise(
    n_posts = n(),
    total_reactions = sum(statistics$reactions, na.rm = TRUE),
    total_comments = sum(statistics$comments, na.rm = TRUE),
    total_shares = sum(statistics$shares, na.rm = TRUE),
    total_views = sum(statistics$views, na.rm = TRUE),
    avg_reactions = mean(statistics$reactions, na.rm = TRUE),
    median_reactions = median(statistics$reactions, na.rm = TRUE)
  )
```

### Engagement by Account Type

```r
engagement_by_type <- posts %>%
  group_by(producer_type) %>%
  summarise(
    n_posts = n(),
    avg_reactions = mean(statistics$reactions, na.rm = TRUE),
    avg_shares = mean(statistics$shares, na.rm = TRUE),
    total_reach = sum(statistics$views, na.rm = TRUE),
    .groups = "drop"
  ) %>%
  arrange(desc(total_reach))
```

### Top Performing Content

```r
top_posts <- posts %>%
  mutate(
    engagement_score = statistics$reactions + 
                       statistics$comments * 2 + 
                       statistics$shares * 3
  ) %>%
  arrange(desc(engagement_score)) %>%
  head(100) %>%
  select(id, producer_name, engagement_score, creation_time)

# Note: Cannot export actual post text
```

### Engagement Distribution

```r
engagement_dist <- posts %>%
  mutate(
    reaction_bucket = cut(
      statistics$reactions,
      breaks = c(0, 10, 100, 1000, 10000, Inf),
      labels = c("0-10", "11-100", "101-1K", "1K-10K", "10K+"),
      include.lowest = TRUE
    )
  ) %>%
  count(reaction_bucket) %>%
  mutate(pct = n / sum(n) * 100)
```

## Content Analysis

### Language Distribution

```r
language_dist <- posts %>%
  count(lang, sort = TRUE) %>%
  mutate(pct = n / sum(n) * 100) %>%
  head(10)
```

### Media Type Analysis

```r
media_analysis <- posts %>%
  count(media_type) %>%
  mutate(pct = n / sum(n) * 100)

# Engagement by media type
media_engagement <- posts %>%
  group_by(media_type) %>%
  summarise(
    n = n(),
    avg_reactions = mean(statistics$reactions, na.rm = TRUE),
    avg_views = mean(statistics$views, na.rm = TRUE),
    .groups = "drop"
  )
```

### Hashtag Extraction (Instagram)

```r
# Extract hashtags from text field
extract_hashtags <- function(text) {
  if (is.na(text)) return(character(0))
  str_extract_all(text, "#\\w+")[[1]]
}

hashtag_counts <- posts %>%
  mutate(hashtags = map(text, extract_hashtags)) %>%
  unnest(hashtags) %>%
  count(hashtags, sort = TRUE) %>%
  head(50)
```

## Network Analysis

### Co-occurrence Matrix

```r
# Which accounts frequently post about same topics?
account_topics <- posts %>%
  select(producer_id, producer_name) %>%
  distinct()

# Cross-posting analysis
crossposts <- posts %>%
  filter(!is.na(shared_from_id)) %>%
  count(producer_id, shared_from_id, sort = TRUE)
```

### Interaction Networks

```r
# Build reply/mention network from comments
comments <- client$search_fb_comments(
  post_ids = posts$id[1:100],
  fields = c("id", "author_id", "parent_id", "creation_time")
)

# Create edge list
edges <- comments %>%
  filter(!is.na(parent_id)) %>%
  select(from = author_id, to = parent_id)
```

## Comparative Analysis

### A/B Topic Comparison

```r
compare_topics <- function(client, topic_a, topic_b, start_date, end_date) {
  posts_a <- collect_all_posts(client, topic_a, start_date, end_date)
  posts_b <- collect_all_posts(client, topic_b, start_date, end_date)
  
  comparison <- bind_rows(
    posts_a %>% mutate(topic = topic_a),
    posts_b %>% mutate(topic = topic_b)
  ) %>%
  group_by(topic) %>%
  summarise(
    n_posts = n(),
    n_accounts = n_distinct(producer_id),
    total_engagement = sum(statistics$reactions + statistics$shares, na.rm = TRUE),
    avg_engagement = mean(statistics$reactions + statistics$shares, na.rm = TRUE),
    .groups = "drop"
  )
  
  comparison
}

# Usage
comparison <- compare_topics(
  client,
  topic_a = "renewable energy",
  topic_b = "fossil fuels",
  start_date = "2024-01-01",
  end_date = "2024-06-30"
)
```

### Cross-Platform Comparison

```r
# Compare same topic across Facebook and Instagram
fb_posts <- collect_all_posts(client, "climate", "2024-01-01", "2024-03-31")
ig_posts <- collect_all_ig_posts(client, "climate", "2024-01-01", "2024-03-31")

platform_comparison <- bind_rows(
  fb_posts %>% mutate(platform = "Facebook"),
  ig_posts %>% mutate(platform = "Instagram")
) %>%
group_by(platform) %>%
summarise(
  n_posts = n(),
  avg_engagement = mean(statistics$reactions, na.rm = TRUE)
)
```

## Export Preparation

### Aggregate Statistics (Exportable)

```r
# These aggregate outputs can typically be exported
exportable_summary <- posts %>%
  mutate(date = as_date(creation_time)) %>%
  group_by(date) %>%
  summarise(
    n_posts = n(),
    n_unique_accounts = n_distinct(producer_id),
    total_reactions = sum(statistics$reactions, na.rm = TRUE),
    total_shares = sum(statistics$shares, na.rm = TRUE),
    avg_reactions = mean(statistics$reactions, na.rm = TRUE),
    .groups = "drop"
  )

# Save for export request
write_csv(exportable_summary, "aggregate_daily_stats.csv")
```

### Create Export-Ready Visualizations

```r
# Save plots as PNG (can be exported after review)
p <- ggplot(exportable_summary, aes(x = date, y = n_posts)) +
  geom_line() +
  labs(title = "Daily Post Volume", x = "Date", y = "Posts") +
  theme_minimal()

ggsave("daily_volume_chart.png", p, width = 10, height = 6, dpi = 300)
```

### What Cannot Be Exported

```r
# DO NOT attempt to export:
# - Raw post text/content
# - Individual user IDs
# - Personal information
# - Full post URLs
# - Raw data files

# These will be rejected during disclosure review
```

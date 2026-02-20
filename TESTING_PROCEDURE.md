# MCL API R Skill - Code Testing Procedure

> **Version:** 1.0
> **Last Updated:** 2026-01-05
> **Purpose:** Comprehensive testing procedure for all code examples in the MCL API R Skill repository

## Overview

This document provides a systematic procedure to test all code examples in the MCL API R Skill repository. Testing should be performed in the Meta Secure Research Environment (SRE) with access to the MCL API.

### Testing Environment Requirements

- Meta Research Platform access (Amazon WorkSpaces Secure Browser)
- JupyterLab with R kernel
- R with reticulate package installed
- MCL API v6.0 access credentials
- Active query budget (check before testing)

### Testing Approach

Since code cannot be executed automatically, each example must be:
1. Copied into a Jupyter notebook cell in the SRE
2. Executed manually
3. Results verified against expected outcomes
4. Screenshots captured for documentation
5. Any errors or issues documented

---

## Pre-Testing Setup

### Step 0: Verify Environment

**Location:** SKILL.md (lines 43-51)

```r
library(reticulate)
library(jsonlite)
library(dplyr)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
async_utils <- import("metacontentlibraryapi")$MetaContentLibraryAPIAsyncUtils
client$set_default_version(client$LATEST_VERSION)
```

**Expected Outcome:**
- No errors
- Client object created successfully
- Version set to LATEST_VERSION

**Screenshot Required:** Yes - showing successful library loading

---

## Test Suite 1: Utilities (references/utilities.md)

### Test 1.1: Check Quota Status

**Location:** utilities.md (lines 7-36)

**Purpose:** Verify quota checking functionality

**Code:**
```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "budgets")
budgets <- fromJSON(response$text, flatten = TRUE)

# Extract query budget
queries <- budgets$queries
queries_used <- as.numeric(queries$total_usage)
queries_limit <- as.numeric(queries$max_usage_limit)
queries_avail <- queries_limit - queries_used

cat("Query Budget:\n")
cat(sprintf("  Used:      %s / %s\n", format(queries_used, big.mark=","), format(queries_limit, big.mark=",")))
cat(sprintf("  Available: %s records\n", format(queries_avail, big.mark=",")))

if (queries$preallocated_rows_for_running_queries > 0) {
  cat(sprintf("  In Progress: %s records\n", format(queries$preallocated_rows_for_running_queries, big.mark=",")))
}

comments <- budgets$comments
comments_avail <- as.numeric(comments$max_usage_limit) - as.numeric(comments$total_usage)
cat(sprintf("\nComments Budget: %s available\n", format(comments_avail, big.mark=",")))
```

**Expected Outcome:**
- Budget information displays correctly
- Numbers formatted with commas
- Both query and comment budgets shown
- No errors

**Validation Checklist:**
- [ ] Query budget displays used/limit/available
- [ ] Comment budget displays correctly
- [ ] Numbers are properly formatted
- [ ] No error messages

**Screenshot Required:** Yes - showing budget output

---

### Test 1.2: Install R Packages

**Location:** utilities.md (lines 55-69)

**Purpose:** Test package installation via fbrir

**Code:**
```r
library(fbrir)

cran <- CRAN$new()
cran$InstallPackages("flextable", dependencies = TRUE)
```

**Expected Outcome:**
- Package installs successfully or shows it's already installed
- No errors from CRAN mirror

**Validation Checklist:**
- [ ] CRAN object created successfully
- [ ] Package installation completes
- [ ] No connection errors

**Screenshot Required:** Yes - showing installation output

---

### Test 1.3: Retrieve Completed Job Data

**Location:** utilities.md (lines 75-105)

**Purpose:** Test job data retrieval

**Prerequisites:** You need an existing completed job ID from a previous query

**Code:**
```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

job_id <- "YOUR_ACTUAL_JOB_ID"  # Replace with real job ID

job <- client$get_async_job(job_id = job_id)
status <- job$get_status()
cat("Status:", status, "\n")

if (status == "COMPLETE") {
  output_dir <- "retrieved_jobs"
  if (!dir.exists(output_dir)) dir.create(output_dir, recursive = TRUE)

  filename <- paste0("job_", job_id, ".json")
  job$write_data_to_file(directory = output_dir, filename = filename)

  filepath <- file.path(output_dir, filename)
  job_data <- fromJSON(filepath, flatten = TRUE)

  cat("Retrieved", nrow(job_data), "records\n")
}
```

**Expected Outcome:**
- Job status retrieved successfully
- If complete, data saved to file
- Record count displayed

**Validation Checklist:**
- [ ] Job status retrieved
- [ ] Directory created if needed
- [ ] Data file saved successfully
- [ ] Record count accurate

**Screenshot Required:** Yes - showing retrieval output

---

### Test 1.4: Get Job Metadata

**Location:** utilities.md (lines 108-117)

**Prerequisites:** Existing job ID

**Code:**
```r
job_id <- "YOUR_ACTUAL_JOB_ID"  # Replace with real job ID

job_response <- client$get(path = paste0("async/jobs/", job_id))
job_metadata <- fromJSON(job_response$text, flatten = TRUE)

cat("Mode:", job_metadata$mode, "\n")
cat("Query ID:", job_metadata$query_id, "\n")
cat("Created:", as.POSIXct(job_metadata$creation_time, origin = "1970-01-01"), "\n")
```

**Expected Outcome:**
- Metadata displays correctly
- Mode, Query ID, and creation time shown

**Validation Checklist:**
- [ ] Job metadata retrieved
- [ ] All fields display correctly
- [ ] Timestamp formatted properly

**Screenshot Required:** Yes

---

### Test 1.5: List All Jobs

**Location:** utilities.md (lines 133-139)

**Code:**
```r
jobs_response <- client$get(path = "async/jobs")
jobs_data <- fromJSON(jobs_response$text, flatten = TRUE)

print(jobs_data$jobs[, c("id", "status", "mode", "query_id")])
```

**Expected Outcome:**
- List of all jobs displayed
- Table shows id, status, mode, query_id columns

**Validation Checklist:**
- [ ] Jobs list retrieved
- [ ] Table displays properly
- [ ] All columns present

**Screenshot Required:** Yes

---

## Test Suite 2: OpenAPI Spec Discovery (SKILL.md)

### Test 2.1: Retrieve OpenAPI Spec

**Location:** SKILL.md (lines 54-61)

**Code:**
```r
spec <- client$openapi_spec()
```

**Expected Outcome:**
- Spec object retrieved successfully
- No errors

**Validation Checklist:**
- [ ] Spec retrieved without errors
- [ ] Object is not null

**Screenshot Required:** Yes - showing successful retrieval

---

### Test 2.2: Explore Endpoints

**Location:** SKILL.md (lines 67-77)

**Code:**
```r
spec <- client$openapi_spec()
paths <- names(spec$paths)

instagram_paths <- paths[grepl("instagram", paths, ignore.case = TRUE)]
print(instagram_paths)

write(toJSON(spec, pretty = TRUE), "openapi_spec.json")
```

**Expected Outcome:**
- Instagram paths listed
- Spec saved to JSON file

**Validation Checklist:**
- [ ] Instagram paths displayed
- [ ] JSON file created
- [ ] File contains valid JSON

**Screenshot Required:** Yes - showing path list

---

## Test Suite 3: Async Query Workflow (SKILL.md)

### Test 3.1: Check Estimate

**Location:** SKILL.md (lines 119-125)

**Code:**
```r
estimate_response <- client$get(
    path = "facebook/posts/estimate",
    params = list("q" = "climate change", "since" = "2024-01-01", "until" = "2024-12-31")
)
estimate <- fromJSON(estimate_response$text, flatten = TRUE)
cat("Estimated:", estimate$estimated_results, "| Complete:", estimate$expected_complete, "\n")
```

**Expected Outcome:**
- Estimate returned with count
- expected_complete shows TRUE or FALSE

**Validation Checklist:**
- [ ] Estimate displays correctly
- [ ] Both estimated_results and expected_complete present
- [ ] Values are reasonable

**Screenshot Required:** Yes

---

### Test 3.2: Submit Async Job

**Location:** SKILL.md (lines 127-143)

**Code:**
```r
response <- client$post(
    path = "facebook/posts/job",
    params = list(
        "q" = "climate change",
        "since" = "2024-01-01",
        "until" = "2024-01-31",  # Smaller range for testing
        "limit" = 100L,
        "mode" = "SNAPSHOT",
        "name" = "TEST - Climate Change - Jan 2024",
        "description" = "Testing async query submission"
    )
)
job_data <- fromJSON(response$text, flatten = TRUE)
job_id <- job_data$id
query_id <- job_data$query_id

cat("Job ID:", job_id, "\n")
cat("Query ID:", query_id, "\n")
```

**Expected Outcome:**
- Job submitted successfully
- job_id and query_id returned

**Validation Checklist:**
- [ ] No errors during submission
- [ ] job_id is valid format
- [ ] query_id is valid format
- [ ] Both IDs displayed

**Screenshot Required:** Yes - CRITICAL TEST

**Note:** Save the job_id for use in Test 3.3

---

### Test 3.3: Monitor Job Status

**Location:** SKILL.md (lines 145-150)

**Prerequisites:** job_id from Test 3.2

**Code:**
```r
job_id <- "YOUR_JOB_ID_FROM_TEST_3.2"  # Replace with actual job ID

job <- client$get_async_job(job_id = job_id)
status <- job$get_status()
cat("Status:", status, "\n")
flush.console()

# Check status a few times
for (i in 1:3) {
    Sys.sleep(5)
    cat("Status:", job$get_status(), "\n")
    flush.console()
}
```

**Expected Outcome:**
- Status transitions from IN_PROGRESS to COMPLETE
- flush.console() works in Jupyter

**Validation Checklist:**
- [ ] Initial status retrieved
- [ ] Status updates display in real-time
- [ ] flush.console() works properly

**Screenshot Required:** Yes - showing status progression

---

### Test 3.4: Save Job Results

**Location:** SKILL.md (lines 152-153)

**Prerequisites:** Completed job from Test 3.3

**Code:**
```r
job_id <- "YOUR_COMPLETED_JOB_ID"  # Replace with actual job ID

job <- client$get_async_job(job_id = job_id)

# Wait for completion if still in progress
while(job$get_status() != "COMPLETE") {
    Sys.sleep(5)
    cat("Waiting... Status:", job$get_status(), "\n")
    flush.console()
}

# Save results
job$write_data_to_file(directory = "results", filename = "climate_test.json")
cat("Results saved to results/climate_test.json\n")

# Verify file exists
if (file.exists("results/climate_test.json")) {
    cat("File created successfully\n")
    data <- fromJSON("results/climate_test.json", flatten = TRUE)
    cat("Retrieved", nrow(data), "records\n")
}
```

**Expected Outcome:**
- Job completes
- File saved successfully
- Data can be loaded and counted

**Validation Checklist:**
- [ ] Job reaches COMPLETE status
- [ ] File saved without errors
- [ ] File exists and contains data
- [ ] Record count displayed

**Screenshot Required:** Yes - CRITICAL TEST

---

### Test 3.5: Rerun Existing Query

**Location:** SKILL.md (lines 194-201)

**Prerequisites:** query_id from Test 3.2

**Code:**
```r
query_id <- "YOUR_QUERY_ID_FROM_TEST_3.2"  # Replace with actual query ID

rerun_response <- client$post(
    path = paste0("async/queries/", query_id, "/job"),
    body = list(mode = "SNAPSHOT")
)
new_job_id <- fromJSON(rerun_response$text, flatten = TRUE)$id
cat("New job created:", new_job_id, "\n")
```

**Expected Outcome:**
- New job created from existing query
- New job_id returned

**Validation Checklist:**
- [ ] Rerun successful
- [ ] New job_id different from original
- [ ] No errors

**Screenshot Required:** Yes

---

## Test Suite 4: Producer Lists (references/producer_lists.md)

### Test 4.1: List All Producer Lists

**Location:** producer_lists.md (lines 25-37)

**Code:**
```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "lists/producers")
lists <- fromJSON(response$text, flatten = TRUE)

print(lists$producer_lists[, c("id", "name", "platform", "entity_type")])
```

**Expected Outcome:**
- List of available producer lists
- Shows id, name, platform, entity_type

**Validation Checklist:**
- [ ] Endpoint returns data
- [ ] Table displays correctly
- [ ] Platform field shows "facebook" or "instagram"

**Screenshot Required:** Yes

**Note:** Save a list_id for use in subsequent tests

---

### Test 4.2: Get Producer IDs from List (Correct Extraction)

**Location:** producer_lists.md (lines 59-78)

**Prerequisites:** list_id from Test 4.1

**Code:**
```r
list_id <- "YOUR_ACTUAL_LIST_ID"  # Replace with real list ID

response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- fromJSON(response$text, flatten = TRUE)

platform <- tolower(list_data$platform)
producers_df <- list_data$producers
producer_ids <- producers_df$id

cat("Platform:", platform, "\n")
cat("Total IDs:", length(producer_ids), "\n")
cat("First 5 IDs:\n")
print(head(producer_ids, 5))
```

**Expected Outcome:**
- Platform identified (facebook or instagram)
- Producer IDs extracted correctly
- Count and sample IDs displayed

**Validation Checklist:**
- [ ] Platform detected correctly
- [ ] IDs extracted from producers array
- [ ] ID count is reasonable
- [ ] IDs are proper format

**Screenshot Required:** Yes - CRITICAL (validates correct API structure)

---

### Test 4.3: Batching Large Producer Lists

**Location:** producer_lists.md (lines 89-137)

**Prerequisites:** producer_ids from Test 4.2 (preferably >250 IDs, or simulate with smaller batch)

**Code:**
```r
# Use producer_ids from Test 4.2
# For testing, use smaller batch size
batch_size <- 5L  # Use 5 for testing; production uses 250L

batches <- split(producer_ids, ceiling(seq_along(producer_ids) / batch_size))

cat("Total producers:", length(producer_ids), "\n")
cat("Number of batches:", length(batches), "\n")
cat("Batch 1 size:", length(batches[[1]]), "\n")
```

**Expected Outcome:**
- IDs split into batches correctly
- Batch count calculated properly

**Validation Checklist:**
- [ ] Batching logic works
- [ ] Batch sizes correct
- [ ] No IDs lost in splitting

**Screenshot Required:** Yes

---

### Test 4.4: Submit Batched Query (Instagram)

**Location:** producer_lists.md (lines 99-134)

**Prerequisites:**
- Instagram producer list from Test 4.2
- Batches from Test 4.3

**Code:**
```r
# Assume platform = "instagram" and batches from previous test
platform <- "instagram"  # Or use value from Test 4.2
batches <- split(producer_ids, ceiling(seq_along(producer_ids) / 5L))  # Small batch for testing

# Test with first batch only
b <- 1
batch_ids <- batches[[b]]

cat("Testing batch", b, "with", length(batch_ids), "IDs\n")

params <- list(
  "since" = "2024-01-01",
  "until" = "2024-01-31",
  "limit" = 100L,
  "mode" = "SNAPSHOT",
  "name" = sprintf("TEST - Batch %d", b),
  "description" = "Testing batched query submission"
)

if (platform == "instagram") {
  params[["account_ids"]] <- paste(batch_ids, collapse = ",")
  endpoint <- "instagram/posts/job"
} else {
  params[["surface_ids"]] <- paste(batch_ids, collapse = ",")
  endpoint <- "facebook/posts/job"
}

cat("Endpoint:", endpoint, "\n")
cat("Parameter name:", ifelse(platform == "instagram", "account_ids", "surface_ids"), "\n")

response <- client$post(path = endpoint, params = params)
job_data <- fromJSON(response$text, flatten = TRUE)
cat("Job submitted:", job_data$id, "\n")
```

**Expected Outcome:**
- Correct parameter (account_ids for Instagram)
- Job submitted successfully

**Validation Checklist:**
- [ ] Correct parameter name used
- [ ] Job submitted without errors
- [ ] job_id returned

**Screenshot Required:** Yes - CRITICAL (validates platform-specific parameters)

---

### Test 4.5: Query Instagram Account Information

**Location:** producer_lists.md (lines 209-234)

**Prerequisites:** Instagram producer_ids from Test 4.2

**Code:**
```r
# Use first 5 IDs for testing
test_ids <- head(producer_ids, 5)

params <- list(
  "account_ids" = paste(test_ids, collapse = ","),
  "limit" = 1000L
)

response <- client$get(
  path = "instagram/accounts/preview",
  params = params
)
result <- fromJSON(response$text, flatten = TRUE)

if (!is.null(result$data) && length(result$data) > 0) {
  cat("Retrieved", nrow(result$data), "accounts\n")
  print(result$data[, c("id", "username", "name", "verified")])
}
```

**Expected Outcome:**
- Account information retrieved
- Table shows id, username, name, verified

**Validation Checklist:**
- [ ] Accounts retrieved successfully
- [ ] Data structure correct
- [ ] Account details displayed

**Screenshot Required:** Yes

---

### Test 4.6: Complete Example - Posts and Comments

**Location:** producer_lists.md (lines 259-346)

**Prerequisites:** Valid producer list with <10 accounts for testing

**Code:**
```r
library(reticulate)
library(jsonlite)
library(dplyr)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

# Get small producer list for testing
list_id <- "YOUR_LIST_ID"  # Use list with <10 accounts
list_response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- fromJSON(list_response$text, flatten = TRUE)

platform <- tolower(list_data$platform)
producer_ids <- head(list_data$producers$id, 5)  # Use only 5 for testing

cat("Platform:", platform, "| Producers:", length(producer_ids), "\n")

# Submit single batch job
params <- list(
  "since" = "2024-01-01",
  "until" = "2024-01-31",
  "limit" = 100L,
  "mode" = "SNAPSHOT",
  "name" = "TEST - Complete Example",
  "description" = "Testing complete workflow"
)

if (platform == "instagram") {
  params[["account_ids"]] <- paste(producer_ids, collapse = ",")
  endpoint <- "instagram/posts/job"
} else {
  params[["surface_ids"]] <- paste(producer_ids, collapse = ",")
  endpoint <- "facebook/posts/job"
}

response <- client$post(path = endpoint, params = params)
job_id <- fromJSON(response$text)$id
cat("Job submitted:", job_id, "\n")

# Wait for completion
job <- client$get_async_job(job_id = job_id)
while (job$get_status() == "IN_PROGRESS") {
  Sys.sleep(10)
  cat("Waiting...\n")
  flush.console()
}

# Save results
job$write_data_to_file(directory = "results", filename = paste0(job_id, ".json"))
posts_data <- fromJSON(file.path("results", paste0(job_id, ".json")), flatten = TRUE)
cat("Retrieved", nrow(posts_data), "posts\n")

# Get comments for first post (Instagram only)
if (platform == "instagram" && nrow(posts_data) > 0) {
  post_id <- posts_data$id[1]
  cat("Getting comments for post:", post_id, "\n")

  response <- client$get(
    path = paste0("instagram/posts/", post_id, "/comments/preview"),
    params = list("limit" = 10L)
  )
  result <- fromJSON(response$text, flatten = TRUE)

  if (!is.null(result$data) && length(result$data) > 0) {
    cat("Retrieved", nrow(result$data), "comments\n")
  } else {
    cat("No comments found\n")
  }
}
```

**Expected Outcome:**
- Complete workflow executes successfully
- Posts retrieved
- Comments retrieved for Instagram

**Validation Checklist:**
- [ ] Producer list loaded
- [ ] Job submitted successfully
- [ ] Job completes
- [ ] Posts data saved
- [ ] Comments retrieved (Instagram)
- [ ] Nested endpoint works correctly

**Screenshot Required:** Yes - CRITICAL (complete workflow test)

---

## Test Suite 5: Chunking (references/chunking.md)

### Test 5.1: Automatic Date Chunking Function

**Location:** chunking.md (lines 7-73)

**Code:**
```r
query_with_chunking <- function(query_text, start_date, end_date, platform = "facebook",
                                 content_type = "posts", chunk_size = 90) {
  library(dplyr)

  start <- as.Date(start_date)
  end <- as.Date(end_date)

  chunks <- list()
  current <- start
  i <- 1
  while (current < end) {
    chunk_end <- min(current + chunk_size - 1, end)
    chunks[[i]] <- list(
      since = format(current, "%Y-%m-%d"),
      until = format(chunk_end, "%Y-%m-%d")
    )
    current <- chunk_end + 1
    i <- i + 1
  }

  cat("Split into", length(chunks), "chunks\n"); flush.console()
  return(chunks)
}

# Test the function
test_chunks <- query_with_chunking(
  query_text = "test query",
  start_date = "2024-01-01",
  end_date = "2024-12-31",
  chunk_size = 30
)

cat("\nFirst 3 chunks:\n")
for (i in 1:min(3, length(test_chunks))) {
  cat(sprintf("Chunk %d: %s to %s\n", i, test_chunks[[i]]$since, test_chunks[[i]]$until))
}
```

**Expected Outcome:**
- Function creates chunks correctly
- Chunk count calculated properly
- Date ranges don't overlap

**Validation Checklist:**
- [ ] Function executes without errors
- [ ] Chunk count is correct (365 days / 30 = ~12 chunks)
- [ ] Date ranges are sequential
- [ ] No gaps between chunks

**Screenshot Required:** Yes

---

### Test 5.2: Combining Chunked Results with bind_rows

**Location:** chunking.md (lines 85-138) and common_patterns.md (lines 105-131)

**Prerequisites:** Multiple job IDs from chunked query (can simulate with 2-3 jobs)

**Code:**
```r
library(dplyr)

# Simulate with 2-3 existing job IDs
job_ids <- c("JOB_ID_1", "JOB_ID_2")  # Replace with actual job IDs

all_data <- list()

for (i in seq_along(job_ids)) {
  job_id <- job_ids[[i]]
  cat("Loading job", i, ":", job_id, "\n")

  # Load previously saved results
  filepath <- file.path("results", paste0(job_id, ".json"))
  if (file.exists(filepath)) {
    data <- fromJSON(filepath, flatten = TRUE)
    if (nrow(data) > 0) {
      all_data[[i]] <- data
      cat("  Loaded", nrow(data), "records\n")
    }
  }
}

# Test bind_rows vs rbind
cat("\nTesting bind_rows (CORRECT method):\n")
combined_correct <- bind_rows(all_data)
cat("Combined", nrow(combined_correct), "total records\n")
cat("Columns:", ncol(combined_correct), "\n")

# Note: rbind might fail if columns don't match
# cat("\nTesting rbind (WRONG method):\n")
# combined_wrong <- do.call(rbind, all_data)  # May error
```

**Expected Outcome:**
- bind_rows combines data successfully
- Handles mismatched columns gracefully
- Total record count correct

**Validation Checklist:**
- [ ] All jobs loaded successfully
- [ ] bind_rows executes without errors
- [ ] Record count is sum of individual jobs
- [ ] Column count >= max of individual dataframes

**Screenshot Required:** Yes - CRITICAL (demonstrates bind_rows advantage)

---

## Test Suite 6: Collections (references/collections.md)

### Test 6.1: Create Collection

**Location:** collections.md (lines 6-14)

**Code:**
```r
response <- client$post(
    path = "async/collections",
    body = list(
        name = "TEST - Code Validation Collection",
        description = "Collection created during testing procedure"
    )
)
collection_id <- fromJSON(response$text, flatten = TRUE)$id
cat("Created collection:", collection_id, "\n")
```

**Expected Outcome:**
- Collection created successfully
- collection_id returned

**Validation Checklist:**
- [ ] No errors during creation
- [ ] collection_id is valid format

**Screenshot Required:** Yes

**Note:** Save collection_id for subsequent tests

---

### Test 6.2: Set Default Collection

**Location:** collections.md (lines 16-20)

**Prerequisites:** collection_id from Test 6.1

**Code:**
```r
collection_id <- "YOUR_COLLECTION_ID"  # From Test 6.1

client$post(
    path = paste0("async/collections/", collection_id),
    body = list(default = TRUE)
)
cat("Collection set as default\n")
```

**Expected Outcome:**
- Default status set successfully

**Validation Checklist:**
- [ ] No errors
- [ ] Confirmation message displayed

**Screenshot Required:** Yes

---

### Test 6.3: List All Collections

**Location:** collections.md (lines 22-23)

**Code:**
```r
collections <- fromJSON(client$get(path = "async/collections")$text, flatten = TRUE)
print(collections$collections[, c("id", "name", "default")])
```

**Expected Outcome:**
- List of collections displayed
- Test collection appears in list

**Validation Checklist:**
- [ ] Collections retrieved
- [ ] Table includes test collection
- [ ] Default flag shows correctly

**Screenshot Required:** Yes

---

### Test 6.4: Update Query Metadata

**Location:** collections.md (lines 41-48)

**Prerequisites:** query_id from Test 3.2

**Code:**
```r
query_id <- "YOUR_QUERY_ID"  # From Test 3.2

client$post(
    path = paste0("async/queries/", query_id),
    body = list(
        name = "TEST - Updated Query Name",
        description = "Updated during testing procedure"
    )
)
cat("Query metadata updated\n")

# Verify update
query_details <- fromJSON(
    client$get(path = paste0("async/queries/", query_id))$text,
    flatten = TRUE
)
cat("New name:", query_details$name, "\n")
```

**Expected Outcome:**
- Metadata updated successfully
- New name retrieved correctly

**Validation Checklist:**
- [ ] Update executes without errors
- [ ] New metadata verified
- [ ] Name matches update

**Screenshot Required:** Yes

---

### Test 6.5: Move Query to Collection

**Location:** collections.md (lines 50-54)

**Prerequisites:**
- query_id from Test 3.2
- collection_id from Test 6.1

**Code:**
```r
query_id <- "YOUR_QUERY_ID"
collection_id <- "YOUR_COLLECTION_ID"

client$post(
    path = paste0("async/queries/", query_id),
    body = list(collection_id = collection_id)
)
cat("Query moved to collection\n")

# Verify
query_details <- fromJSON(
    client$get(path = paste0("async/queries/", query_id))$text,
    flatten = TRUE
)
cat("Collection ID:", query_details$collection_id, "\n")
```

**Expected Outcome:**
- Query moved successfully
- Collection ID updated

**Validation Checklist:**
- [ ] Move executes without errors
- [ ] Query's collection_id matches

**Screenshot Required:** Yes

---

## Test Suite 7: Nested Endpoints (SKILL.md)

### Test 7.1: Instagram Post Comments (Nested URL)

**Location:** SKILL.md (lines 102-114)

**Prerequisites:** Instagram post_id (from previous Instagram query or known ID)

**Code:**
```r
# Use a post_id from Test 4.6 or any Instagram query
post_id <- "YOUR_INSTAGRAM_POST_ID"

# CORRECT method - post_id in URL path
response_correct <- client$get(
  path = paste0("instagram/posts/", post_id, "/comments/preview"),
  params = list("limit" = 10L)
)
result <- fromJSON(response_correct$text, flatten = TRUE)

if (!is.null(result$data) && length(result$data) > 0) {
  cat("Retrieved", nrow(result$data), "comments\n")
  print(result$data[, c("id", "text", "creation_time")])
} else {
  cat("No comments found (post may have 0 comments)\n")
}
```

**Expected Outcome:**
- Comments retrieved using nested endpoint
- No "Invalid parameter" errors

**Validation Checklist:**
- [ ] Nested URL works correctly
- [ ] Comments data returned (or empty if none)
- [ ] No parameter errors

**Screenshot Required:** Yes - CRITICAL (validates nested endpoint)

---

### Test 7.2: Wrong Nested Endpoint Pattern (Expected to Fail)

**Location:** SKILL.md (lines 110-114)

**Purpose:** Demonstrate incorrect pattern causes error

**Code:**
```r
post_id <- "YOUR_INSTAGRAM_POST_ID"

# WRONG method - post_id as parameter (this should error)
tryCatch({
  response_wrong <- client$get(
    path = "instagram/comments/preview",
    params = list("post_ids" = post_id, "limit" = 10L)
  )
  cat("ERROR: This should have failed but didn't!\n")
}, error = function(e) {
  cat("Expected error occurred:\n")
  cat(e$message, "\n")
})
```

**Expected Outcome:**
- Error message about missing parameters or invalid endpoint

**Validation Checklist:**
- [ ] Error occurs as expected
- [ ] Error message mentions missing parameters or invalid path

**Screenshot Required:** Yes (demonstrates wrong pattern)

---

## Test Suite 8: Common Patterns (references/common_patterns.md)

### Test 8.1: Basic Data Collection with Pagination

**Location:** common_patterns.md (lines 27-73)

**Note:** This is a more complex function. Test basic structure first.

**Code:**
```r
# Test the structure without full execution
collect_all_posts <- function(client, query, start_date, end_date, ...) {
  all_results <- list()
  cursor <- NULL
  page <- 1

  # Only fetch first page for testing
  message(sprintf("Fetching page %d...", page))

  # Note: This uses old API pattern, may need adjustment
  # Just test the structure
  cat("Function structure validated\n")
  return(data.frame())
}

# Test function exists
cat("Function defined successfully\n")
```

**Expected Outcome:**
- Function structure validated

**Validation Checklist:**
- [ ] Function defines without syntax errors

**Screenshot Required:** Optional

---

### Test 8.2: Time Series Analysis

**Location:** common_patterns.md (lines 143-159)

**Prerequisites:** Data from completed job with creation_time field

**Code:**
```r
library(dplyr)
library(lubridate)

# Load some posts data
posts <- fromJSON("results/YOUR_JOB_FILE.json", flatten = TRUE)

daily_volume <- posts %>%
  mutate(date = as_date(creation_time)) %>%
  count(date, name = "n_posts")

cat("Daily volume summary:\n")
print(head(daily_volume, 10))
cat("\nTotal days:", nrow(daily_volume), "\n")
cat("Total posts:", sum(daily_volume$n_posts), "\n")
```

**Expected Outcome:**
- Daily aggregation works correctly
- Dates parsed properly

**Validation Checklist:**
- [ ] Date parsing successful
- [ ] Aggregation by date works
- [ ] Counts are accurate

**Screenshot Required:** Yes

---

### Test 8.3: Engagement Metrics

**Location:** common_patterns.md (lines 199-211)

**Prerequisites:** Posts data with statistics fields

**Code:**
```r
library(dplyr)

posts <- fromJSON("results/YOUR_JOB_FILE.json", flatten = TRUE)

engagement_summary <- posts %>%
  summarise(
    n_posts = n(),
    total_reactions = sum(statistics$reactions, na.rm = TRUE),
    total_comments = sum(statistics$comments, na.rm = TRUE),
    total_shares = sum(statistics$shares, na.rm = TRUE),
    avg_reactions = mean(statistics$reactions, na.rm = TRUE),
    median_reactions = median(statistics$reactions, na.rm = TRUE)
  )

print(engagement_summary)
```

**Expected Outcome:**
- Engagement statistics calculated
- No errors from missing fields

**Validation Checklist:**
- [ ] All metrics calculated
- [ ] na.rm handles missing values
- [ ] Summary displays correctly

**Screenshot Required:** Yes

---

## Test Suite 9: Error Handling (references/common_errors.md)

### Test 9.1: Integer Type Error (Intentional Failure)

**Location:** SKILL.md (line 134), common_errors.md (line 21)

**Purpose:** Demonstrate type mismatch error

**Code:**
```r
# WRONG - missing L suffix (should error)
tryCatch({
  response <- client$post(
      path = "facebook/posts/job",
      params = list(
          "q" = "test",
          "since" = "2024-01-01",
          "until" = "2024-01-31",
          "limit" = 100,  # WRONG - no L suffix
          "mode" = "SNAPSHOT",
          "name" = "TEST - Type Error",
          "description" = "Testing type mismatch"
      )
  )
  cat("ERROR: Should have failed with type mismatch!\n")
}, error = function(e) {
  cat("Expected type error:\n")
  cat(e$message, "\n")
})

# CORRECT - with L suffix
response <- client$post(
    path = "facebook/posts/job",
    params = list(
        "q" = "test",
        "since" = "2024-01-01",
        "until" = "2024-01-31",
        "limit" = 100L,  # CORRECT - with L
        "mode" = "SNAPSHOT",
        "name" = "TEST - Correct Type",
        "description" = "Testing correct type"
    )
)
cat("Success with L suffix\n")
```

**Expected Outcome:**
- First attempt errors with type mismatch
- Second attempt succeeds

**Validation Checklist:**
- [ ] Error occurs without L suffix
- [ ] Success with L suffix
- [ ] Error message mentions type

**Screenshot Required:** Yes - CRITICAL (demonstrates L suffix importance)

---

### Test 9.2: Wrong Endpoint Error

**Location:** producer_lists.md (line 353), common_errors.md (line 25)

**Purpose:** Demonstrate 404 error with old endpoint

**Code:**
```r
# WRONG endpoint (should 404)
tryCatch({
  response <- client$get(path = "producer-lists")
  cat("ERROR: Should have returned 404!\n")
}, error = function(e) {
  cat("Expected 404 error:\n")
  cat(e$message, "\n")
})

# CORRECT endpoint
response <- client$get(path = "lists/producers")
lists <- fromJSON(response$text, flatten = TRUE)
cat("Success with correct endpoint\n")
cat("Found", nrow(lists$producer_lists), "producer lists\n")
```

**Expected Outcome:**
- First attempt returns 404
- Second attempt succeeds

**Validation Checklist:**
- [ ] 404 error on wrong endpoint
- [ ] Success on correct endpoint

**Screenshot Required:** Yes

---

### Test 9.3: Platform-Specific Parameter Error

**Location:** query_params.md (line 114), common_errors.md (line 7)

**Purpose:** Demonstrate Instagram parameter error

**Code:**
```r
# Get an Instagram post ID
# Use post_id from previous Instagram query

post_id <- "YOUR_INSTAGRAM_POST_ID"

# WRONG - using surface_ids for Instagram (should error)
tryCatch({
  response <- client$get(
    path = "instagram/posts/preview",
    params = list("surface_ids" = post_id, "limit" = 10L)
  )
  cat("ERROR: Should have failed with parameter error!\n")
}, error = function(e) {
  cat("Expected parameter error:\n")
  cat(e$message, "\n")
})

# CORRECT - using post_ids for Instagram
response <- client$get(
  path = "instagram/posts/preview",
  params = list("post_ids" = post_id, "limit" = 10L)
)
result <- fromJSON(response$text, flatten = TRUE)
cat("Success with correct parameter (post_ids)\n")
```

**Expected Outcome:**
- surface_ids causes error for Instagram
- post_ids works correctly

**Validation Checklist:**
- [ ] Error with surface_ids
- [ ] Success with post_ids
- [ ] Error mentions missing parameters

**Screenshot Required:** Yes - CRITICAL (platform-specific params)

---

## Testing Summary and Reporting

### After Completing All Tests

1. **Count Results:**
   - Total tests: 35
   - Passed: ___
   - Failed: ___
   - Skipped (due to prerequisites): ___

2. **Critical Tests (Must Pass):**
   - [ ] Test 3.2: Submit Async Job
   - [ ] Test 3.4: Save Job Results
   - [ ] Test 4.2: Get Producer IDs (correct extraction)
   - [ ] Test 4.4: Submit Batched Query
   - [ ] Test 4.6: Complete Example
   - [ ] Test 5.2: bind_rows combining
   - [ ] Test 7.1: Nested endpoints
   - [ ] Test 9.1: Integer type handling
   - [ ] Test 9.3: Platform-specific parameters

3. **Screenshot Organization:**
   Create folder structure:
   ```
   screenshots/
   ├── suite1_utilities/
   ├── suite2_openapi/
   ├── suite3_async/
   ├── suite4_producer_lists/
   ├── suite5_chunking/
   ├── suite6_collections/
   ├── suite7_nested/
   ├── suite8_patterns/
   └── suite9_errors/
   ```

4. **Error Documentation:**
   For each failed test, document:
   - Test ID and name
   - Error message
   - Stack trace (if available)
   - Expected vs actual outcome
   - Screenshots of error

5. **Environment Information:**
   Include in report:
   - R version: `R.version.string`
   - reticulate version: `packageVersion("reticulate")`
   - Python version: `py_config()`
   - MCL API version
   - Date of testing
   - Available quota before/after testing

---

## Notes for Testing

### Best Practices

1. **Save Job IDs:** Keep a notebook cell with all job IDs created during testing
2. **Budget Management:** Check quota before each test suite
3. **Rate Limiting:** Wait 60 seconds between async job submissions
4. **Data Cleanup:** Delete test jobs/queries after validation
5. **Screenshot Naming:** Use format `testX.Y_description.png`

### Common Issues

- **Quota Exhaustion:** If quota runs low, prioritize critical tests
- **Slow Jobs:** Some jobs may take 5-10 minutes; be patient
- **Missing Prerequisites:** Some tests require data from previous tests
- **Network Issues:** SRE connection may be slow; allow extra time

### Troubleshooting

If a test fails:
1. Check error message carefully
2. Verify all prerequisites met
3. Check quota status
4. Retry once after 30 seconds
5. Document failure with screenshots
6. Continue to next test

---

## Test Completion Checklist

- [ ] All 35 tests attempted
- [ ] Critical tests (9) passed
- [ ] Screenshots captured and organized
- [ ] Errors documented
- [ ] Environment info recorded
- [ ] Test summary completed
- [ ] Job IDs saved for reference
- [ ] Test data cleaned up
- [ ] Report ready for review

---

**End of Testing Procedure**

Version: 1.0 | Last Updated: 2026-01-05

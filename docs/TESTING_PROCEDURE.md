# MCL API R Skill - Code Testing Procedure

> **Version:** 1.2
> **Last Updated:** 2026-08-18
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

**Location:** SKILL.md § "Setup"

```r
library(reticulate)
library(jsonlite)
library(dplyr)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
async_utils <- import("metacontentlibraryapi")$MetaContentLibraryAPIAsyncUtils
client$set_default_version(client$LATEST_VERSION)

# ID-safe parsing helper - required by every test below.
# Paste the definitions of MCL_ID_PATTERN, mcl_fix_ids() and mcl_fromJSON()
# from SKILL.md § "ID Handling (Always Load IDs as Character)".
# SKILL.md is the single canonical copy; do not maintain a second one here.
```

**Expected Outcome:**
- No errors
- Client object created successfully
- Version set to LATEST_VERSION
- `mcl_fromJSON` and `mcl_fix_ids` defined (used in place of `fromJSON` throughout)

**Screenshot Required:** Yes - showing successful library loading

---

## Test Suite 1: Utilities (references/utilities.md)

### Test 1.1: Check Quota Status

**Location:** utilities.md § "Check Quota Status"

**Purpose:** Verify quota checking functionality

**Code:**
```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "budgets")
budgets <- mcl_fromJSON(response$text)

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

**Location:** utilities.md § "Install R Packages"

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

**Location:** utilities.md § "Retrieve Completed Job Data"

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
  job_data <- mcl_fromJSON(filepath)

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

**Location:** utilities.md § "Get Job Metadata"

**Prerequisites:** Existing job ID

**Code:**
```r
job_id <- "YOUR_ACTUAL_JOB_ID"  # Replace with real job ID

job_response <- client$get(path = paste0("async/jobs/", job_id))
job_metadata <- mcl_fromJSON(job_response$text)

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

**Location:** utilities.md § "List All Jobs"

**Code:**
```r
jobs_response <- client$get(path = "async/jobs")
jobs_data <- mcl_fromJSON(jobs_response$text)

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

**Location:** SKILL.md § "OpenAPI Spec"

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

**Location:** SKILL.md § "OpenAPI Spec"

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

**Location:** SKILL.md § "Async Query Template" (step 1)

**Code:**
```r
estimate_response <- client$get(
    path = "facebook/posts/estimate",
    params = list("q" = "climate change", "since" = "2024-01-01", "until" = "2024-12-31")
)
estimate <- mcl_fromJSON(estimate_response$text)
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

**Location:** SKILL.md § "Async Query Template" (step 2)

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
job_data <- mcl_fromJSON(response$text)
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

**Location:** SKILL.md § "Async Query Template" (step 3)

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

**Location:** SKILL.md § "Async Query Template" (step 4)

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
    data <- mcl_fromJSON("results/climate_test.json")
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

**Location:** SKILL.md § "Rerun a Query"

**Prerequisites:** query_id from Test 3.2

**Code:**
```r
query_id <- "YOUR_QUERY_ID_FROM_TEST_3.2"  # Replace with actual query ID

rerun_response <- client$post(
    path = paste0("async/queries/", query_id, "/job"),
    body = list(mode = "SNAPSHOT")
)
new_job_id <- mcl_fromJSON(rerun_response$text)$id
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

**Location:** producer_lists.md § "List All Producer Lists"

**Code:**
```r
library(reticulate)
library(jsonlite)

client <- import("metacontentlibraryapi")$MetaContentLibraryAPIClient
client$set_default_version(client$LATEST_VERSION)

response <- client$get(path = "lists/producers")
lists <- mcl_fromJSON(response$text)

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

**Location:** producer_lists.md § "Get Producer List Details"

**Prerequisites:** list_id from Test 4.1

**Code:**
```r
list_id <- "YOUR_ACTUAL_LIST_ID"  # Replace with real list ID

response <- client$get(path = paste0("lists/producers/", list_id))
list_data <- mcl_fromJSON(response$text)

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

**Location:** producer_lists.md § "Batching Large Producer Lists"

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

**Location:** producer_lists.md § "Query Posts from Producer List"

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
  params[["account_ids"]] <- as.list(batch_ids)
  endpoint <- "instagram/posts/job"
} else {
  params[["surface_ids"]] <- as.list(batch_ids)
  endpoint <- "facebook/posts/job"
}

cat("Endpoint:", endpoint, "\n")
cat("Parameter name:", ifelse(platform == "instagram", "account_ids", "surface_ids"), "\n")

response <- client$post(path = endpoint, params = params)
job_data <- mcl_fromJSON(response$text)
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

**Location:** producer_lists.md § "Query Account/Page Information"

**Prerequisites:** Instagram producer_ids from Test 4.2

**Code:**
```r
# Use first 5 IDs for testing
test_ids <- head(producer_ids, 5)

params <- list(
  "account_ids" = as.list(test_ids),
  "limit" = 1000L
)

response <- client$get(
  path = "instagram/accounts/preview",
  params = params
)
result <- mcl_fromJSON(response$text)

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

**Location:** producer_lists.md § "Cross-Platform Account Matching"

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
list_data <- mcl_fromJSON(list_response$text)

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
  params[["account_ids"]] <- as.list(producer_ids)
  endpoint <- "instagram/posts/job"
} else {
  params[["surface_ids"]] <- as.list(producer_ids)
  endpoint <- "facebook/posts/job"
}

response <- client$post(path = endpoint, params = params)
job_id <- mcl_fromJSON(response$text)$id
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
posts_data <- mcl_fromJSON(file.path("results", paste0(job_id, ".json")))
cat("Retrieved", nrow(posts_data), "posts\n")

# Get comments for first post (Instagram only)
if (platform == "instagram" && nrow(posts_data) > 0) {
  post_id <- posts_data$id[1]
  cat("Getting comments for post:", post_id, "\n")

  response <- client$get(
    path = paste0("instagram/posts/", post_id, "/comments/preview"),
    params = list("limit" = 10L)
  )
  result <- mcl_fromJSON(response$text)

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

**Location:** chunking.md § "Automatic Date Chunking"

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

**Location:** chunking.md § "Combining Chunked Results" and common_patterns.md § "Combining Results with Mismatched Columns"

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
    data <- mcl_fromJSON(filepath)
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

**Location:** collections.md § "Collections (Folders)"

**Code:**
```r
response <- client$post(
    path = "async/collections",
    body = list(
        name = "TEST - Code Validation Collection",
        description = "Collection created during testing procedure"
    )
)
collection_id <- mcl_fromJSON(response$text)$id
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

**Location:** collections.md § "Collections (Folders)"

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

**Location:** collections.md § "Collections (Folders)"

**Code:**
```r
collections <- mcl_fromJSON(client$get(path = "async/collections")$text)
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

**Location:** collections.md § "Query Management"

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
query_details <- mcl_fromJSON(
    client$get(path = paste0("async/queries/", query_id))$text
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

**Location:** collections.md § "Query Management"

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
query_details <- mcl_fromJSON(
    client$get(path = paste0("async/queries/", query_id))$text
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

**Location:** SKILL.md § "Nested Endpoints"

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
result <- mcl_fromJSON(response_correct$text)

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

**Location:** SKILL.md § "Nested Endpoints"

**Purpose:** Demonstrate incorrect pattern causes error

**Code:**
```r
post_id <- "YOUR_INSTAGRAM_POST_ID"

# WRONG method - post_id as parameter (this should error)
tryCatch({
  response_wrong <- client$get(
    path = "instagram/comments/preview",
    params = list("post_ids" = as.list(post_id), "limit" = 10L)
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

### Test 8.2: Time Series Analysis

**Location:** common_patterns.md § "Time Series Analysis"

**Prerequisites:** Data from completed job with creation_time field

**Code:**
```r
library(dplyr)
library(lubridate)

# Load some posts data
posts <- mcl_fromJSON("results/YOUR_JOB_FILE.json")

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

**Location:** common_patterns.md § "Engagement Analysis"

**Prerequisites:** Posts data with statistics fields

**Code:**
```r
library(dplyr)

posts <- mcl_fromJSON("results/YOUR_JOB_FILE.json")

engagement_summary <- posts %>%
  summarise(
    n_posts = n(),
    total_reactions = sum(statistics.reactions, na.rm = TRUE),
    total_comments = sum(statistics.comments, na.rm = TRUE),
    total_shares = sum(statistics.shares, na.rm = TRUE),
    avg_reactions = mean(statistics.reactions, na.rm = TRUE),
    median_reactions = median(statistics.reactions, na.rm = TRUE)
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

**Location:** SKILL.md § "Common Errors" and common_errors.md § "General Errors"

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

**Location:** producer_lists.md § "Critical: Endpoint Path" and common_errors.md § "Producer List Errors"

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
lists <- mcl_fromJSON(response$text)
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

**Location:** query_params.md § "Platform-Specific ID Parameters" and common_errors.md § "Instagram Errors"

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
    params = list("surface_ids" = as.list(post_id), "limit" = 10L)
  )
  cat("ERROR: Should have failed with parameter error!\n")
}, error = function(e) {
  cat("Expected parameter error:\n")
  cat(e$message, "\n")
})

# CORRECT - using post_ids for Instagram
response <- client$get(
  path = "instagram/posts/preview",
  params = list("post_ids" = as.list(post_id), "limit" = 10L)
)
result <- mcl_fromJSON(response$text)
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

## Test Suite 10: ID Handling (SKILL.md § ID Handling)

### Test 10.1: Helper Unit Test (Offline — No API Calls, No Budget)

**Location:** SKILL.md § "ID Handling (Always Load IDs as Character)"

**Purpose:** Verify `mcl_fromJSON()` on a fixture covering every failure mode: an ID above 2^53, an ID below it, a JSON `null` ID, a nested (flattened) ID, a list-column of IDs, a boolean `is_invalid_id` flag, empty result sets, and two "chunks" that must bind together.

**Run this first**, before any test that spends budget: it needs no API call, and it fails loudly if the environment's `jsonlite` is too old to honour `bigint_as_char`.

**Code:**
```r
chunk_big <- '{"id":"17800000000000001","data":[
  {"id":17841400000000123, "post_id":963780196442228, "parent_id":null,
   "author":{"id":122098765432101234,"name":"a"},
   "reply_ids":[963780196442228, 17841400000000123],
   "is_invalid_id":true, "like_count":5, "text":"hi"}]}'

chunk_small <- '{"id":"17800000000000002","data":[
  {"id":963780196442229, "post_id":963780196442228, "parent_id":963780196442230,
   "author":{"id":9637801964422281,"name":"b"}, "reply_ids":[],
   "is_invalid_id":false, "like_count":7, "text":"ho"}]}'

a <- mcl_fromJSON(chunk_big)$data
b <- mcl_fromJSON(chunk_small)$data

stopifnot(
  identical(a$id, "17841400000000123"),   # no precision loss above 2^53
  identical(b$id, "963780196442229"),     # no scientific notation below 2^53
  is.character(a$author.id),              # flattened nested ID
  is.na(a$parent_id) && !identical(a$parent_id, "NA"),  # null stays NA
  is.character(a$reply_ids[[1]]),         # list-column of IDs
  isTRUE(a$is_invalid_id),                # *_id flags stay logical, not "1"
  is.integer(a$like_count)                # non-ID numerics untouched
)

# Empty / null result sets must parse without error
stopifnot(length(mcl_fromJSON('{"data":[]}')$data) == 0,
          is.null(mcl_fromJSON('{"data":null}')$data))

combined <- bind_rows(a, b)               # would fail with plain fromJSON()
stopifnot(is.character(combined$id))
print(combined[, c("id", "post_id", "parent_id", "author.id")])

# Contrast: what plain fromJSON() does
fromJSON(chunk_big, flatten = TRUE)$data$id   # 1.78414e+16, last digits already wrong
```

**Expected Outcome:**
- All `stopifnot()` checks pass silently
- Printed IDs show full digits, no `e+15`/`e+16`, `parent_id` shows `<NA>` (not `"NA"`)
- `is_invalid_id` remains `logical`, and empty/null `data` parses without error
- The final contrast line prints `1.78414e+16`, demonstrating the bug being prevented

**Validation Checklist:**
- [ ] No `stopifnot` failure
- [ ] `bind_rows()` across chunks succeeds
- [ ] Big ID preserved exactly as `17841400000000123`
- [ ] `parent_id` is `NA`, not the string `"NA"`
- [ ] `is_invalid_id` is `TRUE`/`FALSE`, not `"1"`/`"0"`
- [ ] Empty and null `data` payloads parse without error

**Screenshot Required:** Yes - CRITICAL

---

### Test 10.2: ID Types on Live Data

**Location:** references/utilities.md § "Verify IDs Loaded as Character"

**Prerequisites:** Any data.frame from a previous test (e.g. `job_data` from Test 1.3, producers from Test 4.2, or a `preview` response)

**Code:**
```r
resp <- client$get(path = "facebook/pages/preview", params = list("q" = "news", "limit" = 10L))
pages <- mcl_fromJSON(resp$text)$data

str(pages[grep(MCL_ID_PATTERN, names(pages))])   # all chr
check_ids(pages)                                  # helper from utilities.md

# Round-trip an ID back into a request (the 3790088 trap)
pid <- pages$id[1]
stopifnot(is.character(pid), !grepl("e\\+", pid))
resp2 <- client$get(path = "facebook/pages/preview",
                    params = list("surface_ids" = as.list(pid), "limit" = 5L))
mcl_fromJSON(resp2$text)$data[, c("id", "name")]
```

**Expected Outcome:**
- Every ID column reports as `chr`
- `check_ids()` prints the OK line and does not stop
- The `surface_ids` round-trip returns the same page, no "Invalid Meta Content Library ID" (subcode 3790088)

**Validation Checklist:**
- [ ] All ID columns character
- [ ] No scientific notation anywhere in ID values
- [ ] Round-trip query succeeds with the returned `id`

**Screenshot Required:** Yes - CRITICAL

---

## Test Suite 11: New Surfaces (references/surfaces.md)

Everything in `references/surfaces.md` is transcribed from Meta's guides and has
**never been run**. This suite is what turns it into verified behavior. All five
tests are sync `preview` calls, so they cost no async budget — run them first
when quota is tight, and record the actual field names you see, not just
pass/fail.

### Test 11.1: Facebook Channel Search

**Location:** references/surfaces.md § "Facebook Channels"

**Code:**
```r
resp <- client$get(
  path   = "facebook/channels/preview",
  params = list("q" = "news", "member_count_min" = 1000L, "limit" = 10L)
)
result <- mcl_fromJSON(resp$text)

if (!is.null(result$data) && is.data.frame(result$data) && nrow(result$data) > 0) {
  cat("Channels:", nrow(result$data), "\n")
  print(names(result$data))                       # compare against the documented field list
  print(result$data[, c("id", "name", "member_count")])
  cat("id is character:", is.character(result$data$id), "\n")
} else {
  cat("No channels returned\n")
}
```

**Expected Outcome:**
- Rows returned with `id`, `name`, `description`, `creation_time`,
  `is_admin_verified`, `member_count`, `admin.id`, `admin.type`,
  `admin.username`, `admin.name`
- `member_count_min` accepted (no "Invalid parameter")
- `id` is character

**Validation Checklist:**
- [ ] Endpoint path correct (not a 404)
- [ ] `member_count_min` / `member_count_max` accepted
- [ ] Field names match `surfaces.md`; record any that differ
- [ ] `q` alone works, and `admin_ids` alone works

**Screenshot Required:** Yes - CRITICAL (first test of an untested surface)

---

### Test 11.2: Facebook Channel Messages (Sync and Async Paths)

**Location:** references/surfaces.md § "Channel Messages and Updates"

**Prerequisites:** a `channel_id` from Test 11.1

**Code:**
```r
channel_id <- "PASTE_ID_FROM_TEST_11_1"   # quoted!

# Sync: hangs off the channel node
sync_resp <- client$get(
  path   = paste0("facebook/channels/", channel_id, "/messages/preview"),
  params = list("limit" = 50L)
)
print(names(mcl_fromJSON(sync_resp$text)$data))

# Async: hyphenated resource at the platform root
async_resp <- client$post(
  path   = "facebook/channel-messages/job",
  params = list(
    "channel_ids" = as.list(channel_id),
    "mode"        = "LIVE",
    "name"        = "TEST 11.2 channel messages",
    "description" = "Skill test - delete after"
  )
)
print(mcl_fromJSON(async_resp$text))
```

**Expected Outcome:**
- Both paths resolve; `facebook/channels/job` would 404
- `limit = 50L` accepted; `limit = 100L` rejected or silently capped — record which
- Async response returns `id` and `query_id`

**Validation Checklist:**
- [ ] Sync nested path works
- [ ] Async hyphenated path works
- [ ] `limit` ceiling confirmed (documented as 0-50)
- [ ] `mode` accepted as `"LIVE"` uppercase — try lowercase `"live"` and record
- [ ] Record the literal string `job$get_status()` returns (`COMPLETE` or
      `complete`) — SKILL.md's monitor loop compares against `"COMPLETE"` and would
      spin forever if the 2025-11-10 lowercasing reached job status
- [ ] Job deleted after the test

**Screenshot Required:** Yes - CRITICAL (validates the hyphenated async path)

---

### Test 11.3: WhatsApp Channels and Updates

**Location:** references/surfaces.md § "WhatsApp Channels"

**Code:**
```r
resp <- client$get(
  path   = "whatsapp/channels/preview",
  params = list("q" = "news", "follower_count_min" = 10000L, "limit" = 50L)
)
chan <- mcl_fromJSON(resp$text)$data
print(names(chan))
cat("is_verified present:", "is_verified" %in% names(chan), "\n")

updates <- client$get(
  path   = paste0("whatsapp/channels/", chan$id[1], "/updates/preview"),
  params = list("limit" = 50L)
)
print(names(mcl_fromJSON(updates$text)$data))
```

**Expected Outcome:**
- Channel fields: `id`, `name`, `description`, `creation_time`, `categories`,
  `is_verified`, `follower_count`
- The *filter* is `is_channel_verified` while the *field* is `is_verified` —
  confirm this asymmetry is real
- Updates limited to the last 30 days

**Validation Checklist:**
- [ ] `whatsapp/channels/preview` resolves
- [ ] `is_channel_verified` accepted as a filter
- [ ] Nested `/updates/preview` works
- [ ] 30-day window confirmed against `creation_time` range

**Screenshot Required:** Yes - CRITICAL (newest surface, added 2026-04-30)

---

### Test 11.4: Marketplace Listings and the Price Filter Constraint

**Location:** references/surfaces.md § "Facebook Marketplace Listings"

**Code:**
```r
# Should work: price bounds with a single country
ok <- client$get(
  path   = "facebook/marketplace-listings/preview",
  params = list("q" = "bicycle", "listing_countries" = as.list("IT"),
                "price_min" = 50L, "price_max" = 500L, "limit" = 10L)
)
print(mcl_fromJSON(ok$text)$data)

# Should fail: price bounds across multiple countries
bad <- tryCatch(
  client$get(
    path   = "facebook/marketplace-listings/preview",
    params = list("q" = "bicycle", "listing_countries" = as.list(c("IT", "FR")),
                  "price_min" = 50L, "limit" = 10L)
  ),
  error = function(e) e
)
print(bad)
```

**Expected Outcome:**
- Single-country call returns listings with `listing_details.*` flat columns
- Multi-country call with a price bound is rejected

**Validation Checklist:**
- [ ] `facebook/marketplace-listings/preview` resolves (not `facebook/marketplace/preview`)
- [ ] `listing_details.price.amount` / `.currency` present
- [ ] Price + multi-country constraint confirmed

**Screenshot Required:** Yes

---

### Test 11.5: Fundraisers and Donations

**Location:** references/surfaces.md § "Fundraisers and Donations"

**Code:**
```r
fr <- mcl_fromJSON(client$get(
  path   = "facebook/fundraisers/preview",
  params = list("q" = "children", "limit" = 10L)
)$text)$data
print(names(fr))

don <- mcl_fromJSON(client$get(
  path = paste0("facebook/fundraisers/", fr$id[1], "/donations/preview")
)$text)$data
print(names(don))
cat("rows:", nrow(don), "vs donor_count:", fr$statistics.donor_count[1], "\n")
```

**Expected Outcome:**
- Fundraiser fields include `fundraiser_type`, `goal_amount`, `amount_raised`,
  `currency`, `statistics.donor_count`
- Donation rows carry `owner.type` (with `private` for anonymous donors) and are
  **fewer** than `statistics.donor_count` — only public donations are returned
- `instagram/fundraisers/preview` also resolves, with
  `most_to_least_donations` rather than Facebook's `most_to_least_donors`

**Validation Checklist:**
- [ ] Both fundraiser endpoints resolve
- [ ] Nested donations path resolves
- [ ] Donor-count discrepancy confirmed (documents why the two must not be reconciled)
- [ ] Sort enum difference between platforms confirmed

**Screenshot Required:** Yes

---

## Testing Summary and Reporting

### After Completing All Tests

1. **Count Results:**
   - Total tests: 34
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
   - [ ] Test 10.1: ID handling helper (offline)
   - [ ] Test 10.2: ID types on live data

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
   ├── suite9_errors/
   └── suite10_ids/
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

- [ ] All 39 tests attempted
- [ ] Critical tests (14) passed
- [ ] Screenshots captured and organized
- [ ] Errors documented
- [ ] Environment info recorded
- [ ] Test summary completed
- [ ] Job IDs saved for reference
- [ ] Test data cleaned up
- [ ] Report ready for review

---

**End of Testing Procedure**

Version: 1.3 | Last Updated: 2026-08-21

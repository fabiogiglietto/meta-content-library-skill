# Support ticket draft — ML models in the research environment

Drafted 2026-08-22 from the Phase A/B findings in `ML_MODELS_OPEN_QUESTIONS.md`.
The blocking question is #11 DeBERTaV3, which probing cannot settle because a
`400` cannot distinguish "wrong id" from "not approved". Record the reply here
when it arrives.

---

**Subject:** Approved ML model list — which DeBERTaV3 repository is approved? (plus three documentation issues)

Hello,

I'm using the pre-trained ML model download feature in the Secure Research
Environment (`fbri.package_managers.huggingface`). I have one question I can't
resolve myself, and three small documentation issues I ran into along the way.

All of this was observed on 2026-08-22 from a GPU notebook server. I only used
repository *listing* calls — nothing unapproved was downloaded.

## Question: which DeBERTaV3 repository is the approved one?

The ML models page lists "Hugging Face DeBERTaV3: Improving DeBERTa using
ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing", but I
could not find a repository ID that resolves:

- `microsoft/deberta-v3-base` → 400 Bad Request
- `microsoft/deberta-v3-large` → 400 Bad Request
- `microsoft/mdeberta-v3-base` → works (this is the separate mDeBERTa entry)

Because `microsoft/mdeberta-v3-base` works under the same `microsoft/`
organization, the organization prefix looks correct and the difference seems to
be per-model. Could you tell me the exact repository ID for the approved
DeBERTaV3 model, or confirm whether it is currently unavailable despite being
listed?

## Three documentation issues

**1. The model list omits the Hugging Face organization prefix, and the bare
names do not work.**

| Name as listed | Repository that actually works |
|---|---|
| `t5-base`, `t5-small` | `google-t5/t5-base`, `google-t5/t5-small` |
| `bert-base-uncased` | `google-bert/bert-base-uncased` |
| `distilbert-base-uncased-finetuned-sst-2-english` | `distilbert/distilbert-base-uncased-finetuned-sst-2-english` |
| `xlm-roberta-large` | `FacebookAI/xlm-roberta-large` |
| `all-MiniLM-L6-v2` (owner given as "UKP Lab") | `sentence-transformers/all-MiniLM-L6-v2` |

Hugging Face redirects the bare names to their canonical organization-qualified
repositories, but the proxy at `HF_ENDPOINT` does not follow those redirects.
Since the page prints the bare form in its parentheticals, copying the
documentation directly produces an error. Listing the full repository IDs would
remove the guesswork.

**2. An unapproved model and a mistyped repository ID return the identical
error.** Both give `400 Client Error: Bad Request`, with nothing indicating
approval status — for example `gpt2` (a real, public model that is simply not on
the list) and a repository ID that does not exist anywhere produce the same
response. A researcher cannot tell whether they mistyped the organization prefix
or chose an unapproved model.

Notably, the endpoint **already makes this distinction for revisions**: a
nonexistent revision returns `404`, cleanly separable from the repository-level
`400`. A distinct status or message for "not on the approved list" would bring
repository errors up to the same standard.

**3. Two small issues in `fbri/package_managers/huggingface.py`:**

- `hf_download_repo` and `hf_download_file` are both annotated `-> None` and
  neither has a `return` statement, but both docstrings say
  "Returns: str: The path to the downloaded …". Following the docstring gets you
  `None`.
- `hf_download_file` sets
  `total_size = int(response.headers.get("content-length", 0))` and then divides
  by `total_size` when printing progress. If a response arrives without a
  `content-length` header this raises `ZeroDivisionError` after the first chunk
  has already been written. Because the file is opened before the loop and there
  is no cleanup on failure, that would leave a truncated file at the final path,
  which then fails later inside `from_pretrained()` rather than at download time.

## One request

Would you consider adding `sentence-transformers` to the environment? Two of the
approved models (`all-MiniLM-L6-v2` and
`paraphrase-multilingual-MiniLM-L12-v2`) are Sentence-Transformers models, but
the library is not installed, so they cannot be loaded with the standard
`SentenceTransformer()` API and have to be driven through `transformers` with
manual pooling.

Thank you,
Fabio Giglietto

# Support ticket — ML models in the SRE

> Filed under the name `SUPPORT_TICKET_DRAFT.md`; renamed once the ticket was
> filed and answered. Older CHANGELOG entries use the old name.

Drafted 2026-08-22 from the Phase A/B findings in `ML_MODELS_OPEN_QUESTIONS.md`.
The blocking question was #11 DeBERTaV3, which probing could not settle because a
`400` cannot distinguish "wrong id" from "not approved".

**Status 2026-08-26: filed, answered, follow-up sent.** #11 is
`microsoft/mdeberta-v3-base` — the entry was mis-titled, not missing. Capturing the
screenshot Meta asked for also revealed that the page's **hrefs carry the canonical
repo ids**, which shrinks documentation issue 1 to a one-line fix and exposed a
wrong id in this skill's own #12. The three documentation issues and the
`sentence-transformers` request remain open, now awaiting Meta's response to the
follow-up. See § "Reply" at the end.

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

---

## Reply — Meta Support Community, 2026-08-26

> Hi Fabio,
>
> Thank you for your patience! We can confirm that the approved repository is
> `microsoft/mdeberta-v3-base`. Can you please provide us with the link & a
> screenshot of the documentation you were using? This will help us investigate
> this further.
>
> We will be sure to let you know once we have answers to your remaining
> documentation issues.
>
> Best Regards,
>
> Meta Support Community

**What it settles.** Entry #11's repository is `microsoft/mdeberta-v3-base` — and
the page's own href for that entry says the same, so support was consistent with
Meta's documentation all along. `microsoft/deberta-v3-base` / `-large` are not
approved; their 400 was the allow-list.

**What collecting the screenshot turned up.** Opening the page to capture it
showed that **every entry links to its Hugging Face repository**, even though the
visible text prints a bare name. Two consequences:

1. **Entry #11 is mis-titled.** It carries the DeBERTaV3 paper title over a link to
   mDeBERTa. That mis-titling is what sent us to `microsoft/deberta-v3-base` and
   produced this ticket. There is no duplicate entry and no missing model.
2. **This skill's entry #12 was wrong** — recorded as `microsoft/mdeberta-v3-base`,
   actually `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`, since
   verified to list (13 files). Ours to fix, not Meta's; corrected in
   `references/ml_models_approved.md`. **Nothing here needs raising with Meta** —
   the entry links correctly and the repo is genuinely approved.

Thirteen entries, thirteen repositories. The earlier "twelve" reading is withdrawn.

**What it leaves open.**

| Open item | State |
|---|---|
| Doc issue 1 — bare names as visible text | deferred: "we will let you know" |
| Doc issue 2 — unapproved and mistyped both return `400` | deferred |
| Doc issue 3 — `huggingface.py` return annotations / `ZeroDivisionError` | deferred |
| Request — install `sentence-transformers` | not acknowledged |
| Does `MoritzLaurer/…-xnli-multilingual-nli-2mil7` pass the allow-list? | **yes — verified 2026-08-26, 13 files.** Closed, and no fourth issue for Meta |

**Evidence sent:** `docs/evidence/ml-models-page-2026-08-26.png` — the approved
model list as the page renders it, showing the bare parenthetical names and entry
#11's DeBERTaV3 title. Note the screenshot cannot show the hrefs, so the
link-target finding has to be stated in the text of the reply.

---

## Follow-up — rewritten and **sent 2026-08-26**

An earlier draft of this section asked whether #11 and #12 were duplicates. That
question was false on both branches and was withdrawn before sending, once the
page's link targets were read.

> Hi,
>
> Thank you — that resolves it. I can confirm `microsoft/mdeberta-v3-base` works.
>
> The documentation I was using is Meta's own public page for the Secure Research
> Environment, not a third-party source:
>
> <https://developers.facebook.com/docs/researcher-platform/features/ml-models>
>
> A screenshot of the approved-model list as it appears there is attached.
>
> Having looked at that page again, I can be more precise about what caused my
> original question, and I think it points at a small fix that would help.
>
> **1. The entry is titled after a different model than it links to.** The eleventh
> item reads "Hugging Face DeBERTaV3: Improving DeBERTa using ELECTRA-Style
> Pre-Training with Gradient-Disentangled Embedding Sharing" — the title of the
> DeBERTaV3 paper — but its link points to
> `huggingface.co/microsoft/mdeberta-v3-base`, which is mDeBERTa. Reading the
> entry's name, I tried `microsoft/deberta-v3-base` and `microsoft/deberta-v3-large`
> and got 400 from both, which is what prompted my ticket. Renaming that entry to
> match the model it actually links to would prevent this. It may also be worth
> saying explicitly that the English-only DeBERTaV3 is not available, since the
> current title implies it is.
>
> **2. Your page already contains the exact repository IDs I asked for — in the
> links.** Every one of the thirteen entries links to its Hugging Face repository,
> and those link targets are the canonical, organization-qualified IDs. The visible
> text is the bare name, which does not work: the proxy at `HF_ENDPOINT` does not
> follow Hugging Face's rename redirects, so `t5-base`, `bert-base-uncased`,
> `xlm-roberta-large` and the rest return 400, while `google-t5/t5-base`,
> `google-bert/bert-base-uncased` and `FacebookAI/xlm-roberta-large` work.
>
> So documentation issue 1 from my original message is smaller than I thought:
> the information is already on the page, just not visible. Printing each entry's
> link target as text beside its name — or simply using the repository ID as the
> link text — would resolve it completely, with no new information needed.
>
> The remaining items from my original message are still open whenever you have
> news: documentation issue 2 (an unapproved model and a mistyped repository ID
> both return an indistinguishable `400`, while a bad *revision* correctly returns
> `404`), documentation issue 3 (the two `fbri/package_managers/huggingface.py`
> issues — docstrings promising a return value from functions annotated `-> None`,
> and the `ZeroDivisionError` when a response has no `content-length`), and the
> request to add `sentence-transformers` to the environment.
>
> Best regards,
> Fabio Giglietto

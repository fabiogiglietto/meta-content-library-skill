# Approved ML models in the SRE — snapshot

**This file exists to be diffed.** It records Meta's approved-model list exactly
as fetched, so a later fetch that differs is a detectable event rather than a
silent drift. Do not edit it to be prettier — edit it only to match the page.

- **Source:** https://developers.facebook.com/docs/researcher-platform/features/ml-models
- **First fetched:** 2026-08-21
- **Last confirmed unchanged:** 2026-08-22 (superseded — see change below)
- **Last change detected:** 2026-08-22
- **Checked by:** monthly scheduled agent (see `docs/ML_MODELS_OPEN_QUESTIONS.md`
  § "Tracking Meta's model list for drift")

The prose table in `references/utilities.md` § "Download Machine Learning Models"
groups these by use and is the reader-facing version. This file is the raw
record. When they disagree, this file is right and `utilities.md` is stale.

## The list, as the page presents it

Names are **as written on the page** — Meta lists owners and model names, not
Hugging Face repo ids. Where a full repo id appears verbatim it is marked ✓; the
rest must have their org prefix read off the page before use, since the prefix is
part of the download path.

| # | As listed by Meta | Full repo id |
|---|-------------------|--------------|
| 1 | Facebook No Language Left Behind (nllb-200-3.3B) | not given verbatim |
| 2 | Facebook No Language Left Behind (nllb-200-distilled-600M) | not given verbatim |
| 3 | Google Text-to-Text Transfer Transformer (T5) | not given verbatim |
| 4 | Google Text-to-Text Transfer Transformer (T5-small) | not given verbatim |
| 5 | Google BERT Base Model (Uncased) | not given verbatim |
| 6 | Facebook mBART-50 | not given verbatim |
| 7 | Facebook mBART Many-to-Many Multilingual Machine Translation | `facebook/mbart-large-50-many-to-many-mmt` ✓ |
| 8 | UKP Lab Sentence-BERT (all-MiniLM-L6-v2) | not given verbatim |
| 9 | Hugging Face DistilBERT (distilbert-base-uncased-finetuned-sst-2-english) | not given verbatim |
| 10 | Hugging Face XLM-RoBERTa (large-sized model) | not given verbatim |
| 11 | Hugging Face DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing | not given verbatim |
| 12 | Hugging Face mDeBERTa v3 multilingual | not given verbatim |
| 13 | Hugging Face Sentence-Transformers (paraphrase-multilingual-MiniLM-L12-v2) | not given verbatim |

**Count at last fetch: 13.**

Only #7 appears as a complete repo id, in the page's own download and
translation examples. That is why `docs/TESTING_PROCEDURE.md` Test 1.6 and the
Phase B probe both use #7 — it is the only id we can pass without guessing.

### Correction 2026-08-22 — not drift at Meta, a bad transcription here

The first drift check flagged entry #11 as changed and its commit message
attributed the change to Meta. **That attribution is almost certainly wrong, and
is corrected here.**

The count held at 13, no entry was added or removed, and the license rule,
support-ticket process and GPU note were unchanged. The only difference was
entry #11's wording: this file recorded "Hugging Face DeBERTaV3", while the page
reads "Hugging Face DeBERTaV3: Improving DeBERTa using ELECTRA-Style
Pre-Training with Gradient-Disentangled Embedding Sharing" — the paper's title,
appended after a colon.

The likelier explanation by far is that the **2026-08-21 transcription
abbreviated it**: that snapshot was built from a summarising page fetch, which
shortens long titles as a matter of course, and Meta appending a paper subtitle
to exactly one entry overnight is a far stranger event than a summary dropping
one. Entry #11's name is now the page's, in full.

**This is the check working, not failing.** A verbatim-record file that was not
actually verbatim would have reported "changed!" every single month until a
human looked at it. Better found on run one. The lesson is in this file's own
header — *do not edit it to be prettier* — and it applies as much to writing the
first snapshot as to maintaining it.

## Other constraints stated alongside the list

- Only **text-based models with open-source licenses** qualify for approval.
- **No internet access** for downloading unapproved models.
- Models not on the list require a **support ticket with use-case
  justification**.
- **GPU machines** give faster inference (see `utilities.md` § "CPU or GPU Server").

## What a drift check does

1. Fetch the page.
2. Compare the model list against the table above.
3. **Unchanged** → bump "Last confirmed unchanged" and stop.
4. **Changed** → update this table and the count, update the grouped table in
   `utilities.md`, and note the arrival in `CHANGELOG.md` the way
   `references/surfaces.md` notes new surfaces.

A changed **count** is the cheapest signal; a renamed entry with the same count
is the one a careless check misses.

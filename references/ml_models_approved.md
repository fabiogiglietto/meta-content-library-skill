# Approved ML models in the SRE — snapshot

**This file exists to be diffed.** It records Meta's approved-model list exactly
as fetched, so a later fetch that differs is a detectable event rather than a
silent drift. Do not edit it to be prettier — edit it only to match the page.

- **Source:** https://developers.facebook.com/docs/researcher-platform/features/ml-models
- **First fetched:** 2026-08-21
- **Last confirmed unchanged:** 2026-08-22 (superseded — see change below)
- **Last change detected:** 2026-08-22
- **Last fetched verbatim:** 2026-08-26, **read off the live DOM** — 13 entries,
  and each entry's **link target** extracted. That mapping is now the baseline;
  it is strictly better evidence than any prose summary of the page.
- **Repo ids last corrected:** 2026-08-26 — **entry #12 was wrong here** (see
  § "Correction 2026-08-26" below); entry #11 confirmed against the page's own href.
- **Screenshot of the page as of 2026-08-26:** `docs/evidence/ml-models-page-2026-08-26.png`
- **Checked by:** monthly scheduled agent (see `docs/ML_MODELS_OPEN_QUESTIONS.md`
  § "Tracking Meta's model list for drift")
- **What the drift check must diff:** the **link targets**, not just the entry
  count or the visible names. A repo id can change under an unchanged title, and
  in 2026-08 an entry's title and its href named two different models. The href
  table in § "Correction 2026-08-26" is the baseline to compare against.

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
| 1 | Facebook No Language Left Behind (nllb-200-3.3B) | `facebook/nllb-200-3.3B` ✔ 12 files |
| 2 | Facebook No Language Left Behind (nllb-200-distilled-600M) | `facebook/nllb-200-distilled-600M` — **[verified by listing 2026-08-22]** |
| 3 | Google Text-to-Text Transfer Transformer (T5) | `google-t5/t5-base` ✔ 11 files — **not** `t5-base` |
| 4 | Google Text-to-Text Transfer Transformer (T5-small) | `google-t5/t5-small` ✔ 20 files — **not** `t5-small` |
| 5 | Google BERT Base Model (Uncased) | `google-bert/bert-base-uncased` ✔ 16 files — **not** `bert-base-uncased` |
| 6 | Facebook mBART-50 | `facebook/mbart-large-50` ✔ 9 files |
| 7 | Facebook mBART Many-to-Many Multilingual Machine Translation | `facebook/mbart-large-50-many-to-many-mmt` ✓ |
| 8 | UKP Lab Sentence-BERT (all-MiniLM-L6-v2) | `sentence-transformers/all-MiniLM-L6-v2` — **[verified by listing 2026-08-22]** (note: NOT `ukp-lab/…`) |
| 9 | Hugging Face DistilBERT (distilbert-base-uncased-finetuned-sst-2-english) | `distilbert/distilbert-base-uncased-finetuned-sst-2-english` ✔ 17 files — **not** the bare name Meta prints |
| 10 | Hugging Face XLM-RoBERTa (large-sized model) | `FacebookAI/xlm-roberta-large` ✔ 17 files — **not** `xlm-roberta-large` |
| 11 | Hugging Face DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing | `microsoft/mdeberta-v3-base` ✔ 9 files — **[link target read from the page 2026-08-26; independently stated by Meta Support the same day]**. The entry's *title* is the DeBERTaV3 paper; its *link* is mDeBERTa. `microsoft/deberta-v3-base` / `-large` are not approved |
| 12 | Hugging Face mDeBERTa v3 multilingual | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` ✔ 13 files — **[link target read from the page 2026-08-26; verified by listing 2026-08-26]**. An XNLI-finetuned zero-shot classifier, *not* a base model, and **not** `microsoft/mdeberta-v3-base` as this file previously claimed |
| 13 | Hugging Face Sentence-Transformers (paraphrase-multilingual-MiniLM-L12-v2) | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` ✔ 28 files |

**Count at last fetch: 13 entries over 13 distinct repositories** — one repo per
entry, established from the page's own link targets on 2026-08-26, and **all
thirteen now confirmed downloadable by listing**. An earlier reading of this file
claimed twelve; that was wrong, and § "Correction 2026-08-26" records why.

✔ = **[verified by listing 2026-08-22]** — `hf_list_files(repo, "main")` returned
that many files. Only #7 appears as a complete repo id on Meta's page itself; the
other eleven were resolved by probing, at zero cost with nothing downloaded.

### The org prefix is mandatory, and Meta's page does not give it

**[verified 2026-08-22]** Every bare legacy alias tested returned
`400 Client Error`, while its org-qualified form listed fine:

| Fails (400) | Works |
|-------------|-------|
| `t5-base` | `google-t5/t5-base` |
| `t5-small` | `google-t5/t5-small` |
| `bert-base-uncased` | `google-bert/bert-base-uncased` |
| `distilbert-base-uncased-finetuned-sst-2-english` | `distilbert/distilbert-base-uncased-finetuned-sst-2-english` |
| `xlm-roberta-large` | `FacebookAI/xlm-roberta-large` |

Hugging Face redirects these legacy names to their canonical org-qualified
repos; **Meta's proxy does not follow that redirect.** The bare name is a 400 —
the same 400 that means "not approved".

This is a trap, because the bare names are exactly what the page prints in its
parentheticals (#9 is listed as
"(distilbert-base-uncased-finetuned-sst-2-english)") and exactly what every
tutorial uses. A researcher copying the page's own text gets a 400 with no clue
why. Use the middle column of the table above.

Note too that #8's owner is listed as "UKP Lab" while its repo lives under
`sentence-transformers/`. **Owner names on the page are not org prefixes.**

### Correction 2026-08-26 — #11 answered, and #12 was wrong here

Two things happened on 2026-08-26: Meta Support answered the #11 question, and
reading the page's **link targets** showed that this file's #12 was wrong.

**The page carries the canonical repo ids — in its hrefs.** Every one of the
thirteen entries links to its Hugging Face repo. The visible text is a bare model
name; the org-qualified id is in the link. Read off the live DOM:

| # | Link target |
|---|---|
| 1 | `facebook/nllb-200-3.3B` |
| 2 | `facebook/nllb-200-distilled-600M` |
| 3 | `google-t5/t5-base` |
| 4 | `google-t5/t5-small` |
| 5 | `google-bert/bert-base-uncased` |
| 6 | `facebook/mbart-large-50` |
| 7 | `facebook/mbart-large-50-many-to-many-mmt` |
| 8 | `sentence-transformers/all-MiniLM-L6-v2` |
| 9 | `distilbert/distilbert-base-uncased-finetuned-sst-2-english` |
| 10 | `FacebookAI/xlm-roberta-large` |
| 11 | `microsoft/mdeberta-v3-base` |
| 12 | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` |
| 13 | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` |

**This mapping is the baseline.** It is the page's own machine-readable answer,
and it beats any prose summary — including the 2026-08-26 WebFetch that was
demoted for mixing sources, and including probing, which can only confirm that a
guessed id resolves, never that it is the id Meta meant.

#### #11: the title is a different model from the link

**[link target 2026-08-26]** Entry #11 is *titled* with the DeBERTaV3 paper —
"Improving DeBERTa using ELECTRA-Style Pre-Training…" — and *links to*
`microsoft/mdeberta-v3-base`. Meta Support, asked separately, gave the same repo:

> "We can confirm that the approved repository is `microsoft/mdeberta-v3-base`."

So support was consistent with Meta's own page all along. **There was never a
duplicate entry to infer**, and the earlier reading here — that #11 had no repo of
its own and thirteen entries collapsed to twelve — was wrong, built on this file's
own incorrect #12 rather than on the page.

The real defect is narrower and is Meta's: **#11 is mis-titled.** A researcher
reading "DeBERTaV3" reasonably tries `microsoft/deberta-v3-base`, which is not
approved and returns 400. That is exactly the path that produced the support
ticket. The English-only DeBERTaV3 is not available at all; the entry that appears
to offer it actually offers mDeBERTa.

#### #12: this file had the wrong repo, and the right one is untested

**[link target 2026-08-26]** Entry #12 links to
`MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`. This file previously
recorded `microsoft/mdeberta-v3-base` and marked it "✔ 9 files".

**How the error survived a probe.** The id was guessed from the entry's *name*
("mDeBERTa v3 multilingual"), and the guess resolved — so the checkmark was
earned by a repo that happens to exist and be approved, not by the repo Meta
links. A successful `hf_list_files` says "this id is downloadable"; it never says
"this is the id for that row." Only the href does.

**What this cost, and the risk it leaves.** A researcher following this file for
"mDeBERTa v3 multilingual" got `microsoft/mdeberta-v3-base` — a *base* model,
where Meta's row points at an **XNLI-finetuned zero-shot classifier**. Those are
different tools: the classifier carries an NLI head and is what you would want for
zero-shot topic labelling, while the base model needs a head trained before it
classifies anything. Both are plausible in an MCL pipeline, which is what made the
substitution silent.

**[verified by listing 2026-08-26]** `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7`
lists **13 files** — it passes the allow-list. That was worth checking rather than
assuming: it is the only third-party repo here (every other entry sits under
`facebook/`, `google-*/`, `microsoft/`, `distilbert/`, `FacebookAI/` or
`sentence-transformers/`), and being linked from Meta's page is not in itself
evidence that the proxy accepts an id. It does.

**So the list is now fully resolved: 13 entries, 13 repositories, all verified
against Meta's own link targets and all confirmed downloadable.**

**The lesson worth keeping.** This file's job is to be diffed against Meta's page,
and for #12 it was diffed against a *guess about* Meta's page. When the source
carries the fact in a structured form — an href, a spec, an enum — read that,
rather than reconstructing it from prose and checking the reconstruction resolves.

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

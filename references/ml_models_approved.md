# Approved ML models in the SRE — snapshot

**This file exists to be diffed.** It records Meta's approved-model list exactly
as fetched, so a later fetch that differs is a detectable event rather than a
silent drift. Do not edit it to be prettier — edit it only to match the page.

- **Source:** https://developers.facebook.com/docs/researcher-platform/features/ml-models
- **First fetched:** 2026-08-21
- **Last change detected:** 2026-10-21 — **six multimedia models added** (announced
  on both Meta changelogs as of **2026-10-12**), entries retitled, and the page
  now prints every repo id as visible text. See § "Change 2026-10-12" below.
- **Last fetched verbatim:** 2026-10-21, from the server-rendered HTML — **19
  entries in two groups**, each entry's visible repo id and **link target**
  extracted and found identical for all nineteen. That mapping is the baseline.
- **Last confirmed unchanged:** 2026-10-21 (fetched as the new baseline)
- **Previous baseline:** 2026-08-26, 13 entries, read off the live DOM —
  screenshot `docs/evidence/ml-models-page-2026-08-26.png`. The 2026-08 history
  below refers to entries by **that** page's numbering, not the current one.
- **Checked by:** monthly scheduled agent (see `docs/ML_MODELS_OPEN_QUESTIONS.md`
  § "Tracking Meta's model list for drift")
- **What the drift check must diff:** the **repo ids** (visible text *and* link
  target), not just the entry count or the titles. A repo id can change under an
  unchanged title, and in 2026-08 an entry's title and its href named two
  different models. The table below is the baseline to compare against.

The prose table in `references/utilities.md` § "Download Machine Learning Models"
groups these by use and is the reader-facing version. This file is the raw
record. When they disagree, this file is right and `utilities.md` is stale.

## The list, as the page presents it

**[fetched 2026-10-21]** The page now says *"Use each repository ID as shown"* and
prints each entry as `Title: org/repo`. Titles below are verbatim; the repo id is
the page's own visible text, and it matches the entry's href in all 19 cases.

The list is split into **two groups**, and the split matters:

### All Secure Research Environment environments

| # | Title as listed by Meta | Repo id (as printed = href) | Probe |
|---|-------------------------|-----------------------------|-------|
| 1 | Facebook No Language Left Behind 3.3B | `facebook/nllb-200-3.3B` | ✔ 12 files |
| 2 | Facebook No Language Left Behind distilled 600M | `facebook/nllb-200-distilled-600M` | ✔ |
| 3 | Google T5 base | `google-t5/t5-base` | ✔ 11 files |
| 4 | Google T5 small | `google-t5/t5-small` | ✔ 20 files |
| 5 | Google BERT base (uncased) | `google-bert/bert-base-uncased` | ✔ 16 files |
| 6 | Facebook mBART-50 | `facebook/mbart-large-50` | ✔ 9 files |
| 7 | Facebook mBART-50 many-to-many translation | `facebook/mbart-large-50-many-to-many-mmt` | ✔ |
| 8 | Sentence-Transformers all-MiniLM-L6-v2 | `sentence-transformers/all-MiniLM-L6-v2` | ✔ 30 files |
| 9 | Sentence-Transformers paraphrase-multilingual-MiniLM-L12-v2 | `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | ✔ 28 files |
| 10 | DistilBERT SST-2 sentiment | `distilbert/distilbert-base-uncased-finetuned-sst-2-english` | ✔ 17 files |
| 11 | XLM-RoBERTa large | `FacebookAI/xlm-roberta-large` | ✔ 17 files |
| 12 | Microsoft mDeBERTa V3 base (multilingual) | `microsoft/mdeberta-v3-base` | ✔ 9 files |
| 13 | mDeBERTa V3 base XNLI multilingual NLI | `MoritzLaurer/mDeBERTa-v3-base-xnli-multilingual-nli-2mil7` | ✔ 13 files |

### Meta Content Library API environments only — new 2026-10-12

| # | Title as listed by Meta | Repo id (as printed = href) | Probe |
|---|-------------------------|-----------------------------|-------|
| 14 | OpenAI Whisper large v3 (speech transcription) | `openai/whisper-large-v3` | **[open]** |
| 15 | OpenAI CLIP ViT-L/14 (image and text similarity) | `openai/clip-vit-large-patch14` | **[open]** |
| 16 | Meta DINOv2 large (image embeddings) | `facebook/dinov2-large` | **[open]** |
| 17 | Meta SAM 2.1 Hiera large (image and video segmentation) | `facebook/sam2.1-hiera-large` | **[open]** |
| 18 | Meta DETR ResNet-50 (object detection) | `facebook/detr-resnet-50` | **[open]** |
| 19 | Meta wav2vec 2.0 base 960h (speech recognition and audio embeddings) | `facebook/wav2vec2-base-960h` | **[open]** |

**Count at last fetch: 19 entries over 19 distinct repositories** — 13 available
in every SRE environment, 6 only where the environment is a Meta Content Library
API one.

✔ = `hf_list_files(repo, "main")` through the SRE proxy returned that many files
(2026-08-22, #13 on 2026-08-26). The thirteen ids are unchanged since then, so the
probes still stand. **[open]** = listed by Meta, not yet probed from inside the
SRE; one free `hf_list_files()` call per repo settles it.

## Change 2026-10-12 — multimedia models, and the page fixed its own traps

Announced on **both** changelogs dated **2026-10-12** — Researcher Platform
("New multimedia machine learning models": *"Six new multimedia models are now
available in Meta Content Library API environments for transcription, image
analysis and audio analysis"*) and Content Library and API ("…available for
download from the Hugging Face® Hub when you use Meta Content Library API in
Secure Research Environment"). Picked up here on 2026-10-21.

**1. Six models added, none of them text-only.** Speech (#14 Whisper, #19
wav2vec 2.0), image–text (#15 CLIP), image embeddings (#16 DINOv2), segmentation
(#17 SAM 2.1, image *and* video) and object detection (#18 DETR). The 2026-08 page
said only **text-based** models qualified for approval; that sentence is gone.

**2. The new six are scoped.** They sit under *"Meta Content Library API
environments only"*; the original thirteen under *"All Secure Research Environment
environments"*. **[inferred]** An SRE provisioned for a different Meta dataset
does not get the multimedia models; a researcher using MCL in the SRE does. The
page does not say whether third-party cleanrooms (SOMAR VDE) receive them —
they do not use the `fbri` helper at all.

**3. Every entry was retitled.** No repo id changed among the original thirteen,
but the page now lists them in a different **order** (the multilingual MiniLM
moved from 13th to 9th) and with short, functional titles. Two consequences:

- **The 2026-08 "mis-titled #11" defect is fixed.** The entry that carried the
  DeBERTaV3 *paper* title while linking to `microsoft/mdeberta-v3-base` is now
  titled "Microsoft mDeBERTa V3 base (multilingual)". The English
  `microsoft/deberta-v3-base` remains unapproved.
- **The "owner name ≠ org prefix" trap is gone from the page.** "UKP Lab
  Sentence-BERT" is now "Sentence-Transformers all-MiniLM-L6-v2".

**4. The page prints the full repo id.** Each entry is `Title: org/repo`, under
the instruction *"Use each repository ID as shown"*. Documentation issue 1 of
`docs/SUPPORT_TICKET_ML_MODELS.md` — bare names that 400 — is resolved on Meta's
side. The proxy behaviour behind it is unchanged as far as anyone knows, so
bare legacy aliases copied from tutorials still fail; see below.

**5. The approval rule changed.** Old: text-based models with open-source
licenses. New: *"Only models available in the Hugging Face Hub under an open
source license can be considered."* The page also now says a model approved on
request *"will then be made available to all researchers, not exclusively to the
researcher who requested it"*, and that the request should describe the use case
*"as it relates to your approved research agenda"*.

**What did not change:** the helper functions, their signatures, the default
path `~/huggingface/<REPO_NAME>/<REVISION>`, the mBART example, the GPU note.

**Practical facts about the new six** — size, required files, offline traps — are
in `references/utilities.md` § "Multimedia models (MCL API environments)". The
headline: **`openai/whisper-large-v3` is 24.7 GB as a whole repository**, more than
the ~13 GB free in `/home/jovyan` (2026-10-22), so `hf_download_repo()` on it will fill the
disk.

### The org prefix is mandatory

> **2026-10-12:** Meta's page now prints the org-qualified id for every entry, so
> copying from the page is safe. The trap below survives in tutorials, model
> cards and older notes, which still use the bare legacy names.

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

This was a trap, because the bare names were exactly what the page printed in
its parentheticals until 2026-10 (#9 was listed as
"(distilbert-base-uncased-finetuned-sst-2-english)") and are still exactly what
every tutorial uses. A researcher copying the page's own text gets a 400 with no clue
why. Use the middle column of the table above.

Until 2026-10, #8's owner was listed as "UKP Lab" while its repo lives under
`sentence-transformers/`. **Owner names are not org prefixes.**

### History: the 2026-08 page and this file's corrections to it

The sections below are kept as a record. **Entry numbers in them are the
2026-08-26 page's**, where #9 was DistilBERT, #11 the mis-titled mDeBERTa base,
#12 the XNLI classifier and #13 the multilingual MiniLM.

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

- Only models on the Hugging Face Hub **under an open-source license** can be
  considered. *(Until 2026-10 this read "text-based models with open-source
  licenses"; the text-only condition is gone.)*
- **No internet access** for downloading unapproved models.
- Models not on the list require a **support ticket** with a link to the model
  and a use case tied to your approved research agenda. A model approved this
  way becomes available to **all** researchers.
- **Six models are MCL-API-environment only** (#14–#19 above).
- **GPU machines** give faster inference (see `utilities.md` § "CPU or GPU Server").

## What a drift check does

1. Fetch the page.
2. Compare the model list — both groups, repo ids and group membership —
   against the tables above.
3. **Unchanged** → bump "Last confirmed unchanged" and stop.
4. **Changed** → update this table and the count, update the grouped table in
   `utilities.md`, and note the arrival in `CHANGELOG.md` the way
   `references/surfaces.md` notes new surfaces.

A changed **count** is the cheapest signal; a renamed entry with the same count
is the one a careless check misses, and an entry **moving between groups** is
the one a check that ignores the group headings misses.

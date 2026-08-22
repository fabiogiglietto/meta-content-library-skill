# What can actually drive the SRE

**Stage 0 recon.** Live session observed 2026-08-21. Status: **answered, with three
gaps named at the end.**

Every claim carries how it was observed:

| Tag | Meaning |
|---|---|
| **[verified]** | Observed directly in the live session, on the date given |
| **[documented]** | Stated by AWS or Meta documentation; not observed here |
| **[inferred]** | Follows from a verified or documented fact; not itself observed |
| **[open]** | Not yet answered |

---

## 0. What the session actually is

**[verified 2026-08-21]** `https://content-library-api.fb-researchtool.com/hub/login`
redirects to `https://<portal-uuid>.workspaces-web.com/?deepLinks=...`. The page's
own accessibility tree names the product (`image "WorkSpaces Secure Browser"`) and
loads attributions from `cdn.workspaces-web.com`. The SRE is **Amazon WorkSpaces
Secure Browser**.

**[verified 2026-08-21]** The streamed session renders into a single cross-origin
iframe:

```
<iframe id="appstream-streaming-session"
        src="https://eu-west-1.content.workspaces-web.com/authenticate?parameters=...">
```

So the transport is **AppStream 2.0**, in **eu-west-1**. The entire local page is
314 elements. There is no `canvas`, `video`, `embed`, or `object` in the top
document — the render surface lives inside that cross-origin iframe.

**[verified 2026-08-21]** The portal has `deepLinkAllowed = Enabled`: the login
URL carried a `?deepLinks=` parameter and the session honoured it.

### The one structural fact everything else follows from

The SRE's automation surface is **not** a property of JupyterLab. It is the
WorkSpaces Secure Browser **`UserSettings` resource** that Meta attached to this
portal. Every ingress and egress channel is an `Enabled | Disabled` string an
administrator chose
([API_UserSettings](https://docs.aws.amazon.com/workspaces-web/latest/APIReference/API_UserSettings.html),
**[documented]**):

| Setting | Controls | Meta's value |
|---|---|---|
| `pasteAllowed` | local → session clipboard | **Enabled [verified]** |
| `copyAllowed` | session → local clipboard | **Offered [verified]**, never exercised |
| `uploadAllowed` | local → session files | [open] |
| `downloadAllowed` | session → local files | [open] |
| `printAllowed` | print to local device | [open] |
| `deepLinkAllowed` | deep links into session | **Enabled [verified]** |

This reframes the whole stage. A negative result here means *Meta disabled a
toggle*, not *the architecture forbids it* — and a toggle can be asked about.

---

## 1. Is there a DOM?

**No — and the boundary is exact. [verified 2026-08-21]**

`read_page` on the live, authenticated session returns **only the streaming
client's own shell**: AWS cookie dialogs, a `progressbar`, and
`menubar "docked toolbar"` with seven items (Windows, Clipboard, Dual monitor,
Full screen, Preferences, Notifications, Profile).

It returns **nothing** from inside the session. Visible on screen but absent
from the accessibility tree: JupyterLab's menu bar, its file browser, its
notebook tabs, every code cell, and the rendered data grid. Same for the
streamed Chrome's own tab strip and address bar.

This confirms by observation what `OPEN_QUESTION_ENUM_CASING.md` asserted from
AWS documentation. It is a same-origin boundary *plus* a pixel stream, so it will
not yield to a newer extension version.

### But a screenshot reads it fine — [verified 2026-08-22]

The empty accessibility tree is **not** the end of the story, and reading § 1
alone would leave you thinking the session is opaque to automation. It is not.

| Channel | Works? |
|---|---|
| `read_page` / `get_page_text` | **No** — returns only the streaming client's shell |
| **Screenshot** | **Yes** — notebook output is legible, including code cells, printed results and the JupyterLab status bar |
| **Click** | **Yes** — the streamed browser's tab strip responds to clicks at their on-screen coordinates |
| **Scroll** | **No** — five `scroll` events across three coordinates and two tab configurations never moved the notebook |

So the working division of labour is: **the human scrolls, Claude reads.** A
whole session of `mcl-api-r` ML testing was run this way on 2026-08-22 — probe
code pasted in by the human (`pasteAllowed` is Enabled), results read back by
screenshot — with no transcription by hand.

Two practical notes. The stream repaints as **`Resizing…`** for several seconds
after a screenshot request, so a capture taken immediately after another action
often catches the splash rather than the page; wait 4–6 seconds. And keystrokes
land wherever the streamed browser's focus happens to be — a stray character
appeared inside a code cell during this session, so **avoid `type` actions
entirely** unless the human confirms what is focused.

This does not soften § 1. There is no DOM, so nothing can be selected, queried or
extracted structurally. What is available is what a person can see.

**Do not spend turns** on `javascript_tool`, `get_page_text`, or `find` against
session content. They will return the shell or nothing. The toolbar, by
contrast, *is* real DOM and is clickable by `ref`.

**On method:** the boundary was characterized from the *outside* only — element
counts and tag names in the top document, and the iframe's `id` and `src`
attributes. No attempt was made to reach through it: no `contentDocument`, no
CDP into the child frame, no shadow-piercing into the stream. Terms §5.b.i
prohibits attempts to circumvent privacy or security protections, and the record
should show this boundary was measured and respected rather than probed.

---

## 2. Does clipboard-in work?

**Yes — and it is the best channel into the session. It costs exactly one human
keystroke.**

**[verified 2026-08-21]** The toolbar's **Clipboard** item opens a panel stating:

> Press (CTRL+ c) to copy content **from** remote clipboard.
> Press (CTRL+ v) to paste content **to** remote clipboard.

Both directions are enabled on this portal, so `pasteAllowed` and `copyAllowed`
are both `Enabled`.

**[verified 2026-08-21] A staged clipboard pastes byte-exact.** A three-line R
block was written to the local clipboard from the page, a notebook cell was
focused, the researcher pressed `Ctrl+V` once, and this landed:

```r
# PASTE-TEST-P1
y <- c("([{", 2L, "]})")
cat("PASTE-OK-P9\n")
```

Identical to what was staged. **No auto-indent, no auto-close corruption** —
paste bypasses CodeMirror's per-character input handlers, so the whitespace
divergence that afflicts typing (Q4) does not occur. The cell then ran from a
toolbar click and printed `PASTE-OK-P9`.

That makes the working ingress:

```
Claude composes R  →  Claude stages it to the local clipboard
                   →  the researcher presses Ctrl+V (one keystroke)
                   →  Claude clicks ▶ and reads the output
```

### The one thing that is not automatable, and why

**[verified 2026-08-21]** The `Ctrl+V` must be a *real* keystroke. Everything
around it was tried and fails:

| Attempt | Result |
|---|---|
| `computer` action `key: ctrl+v` | Inserts a literal `v` — the modifier is stripped (Q3) |
| Synthetic `KeyboardEvent` with `ctrlKey: true`, dispatched at `document`, `window`, and the iframe element | Nothing. Handler ignores untrusted events |
| Synthetic `ClipboardEvent('paste')` carrying a `DataTransfer`, same targets | Nothing |
| Any control inside the Clipboard panel | The panel has **no** `button`, `input`, `textarea` or `contenteditable`. "Content preview" is a read-only display and "Example copied or pasted text" is placeholder markup |
| Opening the Clipboard panel to force a sync | Does not sync. The preview still showed its placeholder while the local clipboard held the marker |

So the local→remote clipboard sync is driven **only** by a trusted `Ctrl+V`
keydown, and everything downstream of it — the remote clipboard, and therefore
any in-session right-click → Paste — is unreachable without one. This is a clean
architectural boundary, not a gap to engineer around.

**Do not read it as a defeat.** One keystroke per cell is a far cheaper human
contribution than typing a query by hand, and it buys exactness that typing
cannot.

### A precondition worth designing around

**[verified 2026-08-21]** `navigator.clipboard.writeText()` throws
`NotAllowedError: Document is not focused` whenever the Chrome **window** is not
the OS-focused window — being the only tab in the group is not enough, and a
synthetic click on the page does not confer focus. `document.execCommand('copy')`
on a hidden textarea fails identically. Two workable patterns:

- Poll `document.hasFocus()` in a `setInterval` and write the moment the window
  comes forward. This is what staged the clipboard in this recon.
- Use a system clipboard tool (`xclip` / `wl-copy`) — neither installed here.

The trap this exposes: **a permission prompt on every browser call makes the
clipboard channel unusable**, because approving the prompt moves focus to the
terminal. In this session `mcp__claude-in-chrome` had to come out of
`permissions.ask` before any of this worked.

## 3. Does synthetic typing reach the session, and does what lands match?

**Characters yes. Modifiers no.** Typing is the autonomous fallback; the stripped
modifier is also why the `Ctrl+V` in Q2's primary channel has to be human.

**[verified 2026-08-21] Modifier keys are stripped in transit.** Sending
`ctrl+v` into a focused JupyterLab cell inserted a literal `v`. Sending `ctrl+a`
then appended a literal `a`, leaving `va` in the cell. The character reaches the
stream; the Ctrl flag does not.

Everything that follows from that:

| Shortcut | Status |
|---|---|
| `Ctrl+V` paste | **Unavailable** — inserts `v` |
| `Ctrl+C` copy | **Unavailable** — inserts `c` |
| `Ctrl+A`, `Ctrl+S`, `Ctrl+Z` | **Unavailable** |
| `Shift+Enter` / `Ctrl+Enter` run cell | **Unavailable** — use the toolbar ▶ button |
| Bare characters, `Enter`, `Backspace`, arrows | **Work** |

**[verified 2026-08-21] Plain typing is delivered accurately.** A six-line R
block typed with the `type` action arrived with every character correct —
capitals, `<-`, `1L`, nested `[[1]]`, and both quote styles intact. Only the
leading whitespace differed (Q4). Four further multi-line cells, including a
147-character regex line, were typed and ran correctly.

**[verified 2026-08-21] Mouse input works, with a focus caveat.** Movement always
reaches the stream (hover states render). The *first* click after the window
gains focus is consumed focusing the iframe and does not activate the element
under it; subsequent clicks act normally. Budget one throwaway click per focus
change, then verify.

### Two mechanics of the streaming client that cost real time

**[verified 2026-08-21]** Screen capture triggers the AppStream client to
renegotiate the stream: the session blanks to a Meta logo and `Resizing...` for
roughly 2–5 seconds, and input during that window is lost. This was first
attributed to `screenshot` alone, with `zoom` believed safe; further observation
showed `zoom` does it too. **Both do.** This inverts the naive
drive-and-screenshot loop, in which the act of verifying is what breaks the
session — see the settle-poll pattern below.

**[verified 2026-08-21] Every screen capture renegotiates the stream.** This is
the most operationally important mechanic found. After a `screenshot` or a `zoom`,
the session area blanks and the client displays `Resizing...` for roughly 2–5
seconds; input delivered during that window is lost. `document.visibilityState`
stays `"visible"` throughout.

An earlier reading of this recon blamed window focus, because the blanking
correlated with the researcher clicking away to approve permission prompts. That
was wrong and is corrected here: `Resizing...` was subsequently observed with
`document.hasFocus() === true`. Focus matters for a different reason (below), but
the blanking is driven by capture, not focus.

The practical loop that works:

```
act  →  poll document.body.innerText until it no longer matches /Resizing|Reconnecting/
     →  wait ~1s more  →  capture  →  read
```

That poll is a `javascript_tool` call against the local shell, which costs
nothing and does *not* itself trigger a renegotiation. Budget one throwaway
click after each renegotiation: **the first click following a resize is
consumed** and does not activate the element under it. This was observed
repeatedly — a `Run` click that left the cell prompt at `[ ]:`, an "insert cell"
click that created no cell — each of which succeeded on an immediate second
click.

**[verified 2026-08-21] Window focus governs the clipboard, not the picture.**
`navigator.clipboard.writeText()` throws unless the Chrome window is OS-focused
(see Q2). Since approving a permission prompt in the terminal steals that focus,
a driver that prompts on every browser call cannot stage a clipboard at all. In
this session the fix was to remove `mcp__claude-in-chrome` from `permissions.ask`;
the structural point is that **prompt-per-action and browser automation of a
streamed session are incompatible**.

**[verified 2026-08-21]** The extension connection itself also dropped twice
during this recon. A driver must treat disconnection as expected, must never
assume a keystroke or click landed, and must be resumable.

---

## 4. Does JupyterLab auto-close-brackets corrupt typed R, and can it be disabled?

**Auto-close does not corrupt balanced code. Auto-indent does alter it, harmlessly.**

**[verified 2026-08-21]** This block was typed character by character:

```r
# MCLRECON-A1 begin
x <- c("([{", 'end', "]})")
f <- function(a = list(1L, 2L)) {
paste0("[", a[[1]], "]")
}
cat(x, f(), "MCLRECON-Z9-end\n")
```

What landed differed on exactly two lines:

```r
f <- function(a = list(1L, 2L)) {
    paste0("[", a[[1]], "]")     # <- 4 spaces added
    }                            # <- 4 spaces added, not dedented
```

- **No auto-close corruption.** Not one doubled `)`, `]`, `}` or quote — including
  the deliberately adversarial `c("([{", 'end', "]})")`. CodeMirror inserts a
  closer, and typing the real closer *types over* it rather than duplicating.
  **Balanced code survives typing.** Unbalanced fragments would not, so a driver
  must send only balanced units.
- **Auto-indent does fire**, adding leading whitespace inside braces and failing
  to dedent the closing `}`. In R this is semantically inert. It does mean
  **sent ≠ landed**, so a verifier must compare on normalised whitespace or it
  will report false divergences on every braced block.

**None of this applies to paste.** A pasted block arrives byte-exact (Q2), with
no auto-indent and no auto-close involvement. **These rules govern the typing
fallback only.**

**[open]** Whether auto-close can be disabled in Settings — now low value, since
it did no damage and the primary channel avoids it entirely.

---

## 5. Is there ingress other than typing?

**Yes — a documented, sanctioned one, for data but not for code.**

**[documented, fetched 2026-08-21]** The Researcher Platform provides an **S3
upload** path
([Upload files to an S3 bucket](https://developers.facebook.com/docs/researcher-platform/features/S3-bucket)):

| Property | Value |
|---|---|
| From a notebook | `user.get_uploads_file_cmd('filename.csv')` |
| From the local machine | `user.prompt_uploads_file('filename.csv')`, then run the emailed command locally |
| Formats | **`.csv` and `.tsv` only** |
| Size | 5 GB per upload |
| Consent | type `Agree` (case-sensitive) at the prompt |
| Access | `user.create_table('TableName', 'file_with_id')`, then SQL via `fbri.public.sql.query` against `public_user_[unique_id]` |

**This does not solve code ingress.** It takes tabular data only, so an `.R`
script cannot be uploaded and `source()`d. Code still enters by paste (Q2) or
typing (Q3). What it *does* solve is the producer-list problem: a researcher's
own list of accounts belongs in an uploaded `.csv`, not typed into a cell.

**[verified 2026-08-21]** The JupyterLab launcher offers a **Terminal** tile, and
kernels for **Python 3, Julia 1.12, R and Stata**. **[inferred]** a shell is
therefore reachable — the Terminal was never opened.

**[open]** The AWS `uploadAllowed` / `downloadAllowed` toggles were not
exercised. Note these are a *different* channel from the S3 path above, which is
Meta's own and works regardless. The absence of a file-transfer control in the
WorkSpaces toolbar is not evidence either way — AWS's documented toolbar item
list does not include one.

**[deferred, not open]** Outbound network from a cell — the `source()`-a-URL
bootstrap — was **deliberately not tested**, because it exercises an import
channel and Terms §4 puts imports under the Import & Export Policy. Given the S3
path exists and is sanctioned, this is now also *less* attractive: there is a
documented way in, so an undocumented one is not worth the risk of being read as
circumvention under §5.b.i.

## 6. Can cell output be read as text, or only OCR'd from a screenshot?

**Only from the image. [verified 2026-08-21]**

The hope recorded earlier in this file — that `copyAllowed = Enabled` would let
output be copied out and read as text — **does not survive Q3**. Copying requires
`Ctrl+C`, and the Ctrl modifier does not reach the stream. The channel exists for
the researcher's hands and not for the agent's.

Note the asymmetry with Q2. Ingress is solved by one human keystroke because the
agent controls what goes *in*: it stages the clipboard, and the human's `Ctrl+V`
merely releases it. Egress cannot be solved the same way — a human `Ctrl+C` puts
session content on the *local* clipboard, which the agent can then read in full.
That is a channel for exporting Meta Data, so the constraint on it is
contractual (§5.b.ii), not technical. **Do not build it.**

So output reaches the agent only by **reading the rendered pixels** — `zoom` on
the output region and transcribing. That is vision transcription, not text
extraction, and it can misread. Consequences for the driver:

- Transcribe **verbatim**, never normalise, and say so when a glyph is ambiguous
  rather than guessing. This matters most for exactly the questions worth asking
  — `COMPLETE` vs `complete` is a casing question read off an image.
- Prefer output the agent does not have to read precisely: have the notebook
  print a small, well-separated aggregate rather than a wide table.
- Long identifiers (15-digit job ids) are the worst case. Have the notebook
  `cat()` them in delimiters, one per line, at default zoom.

### Egress: what Meta actually permits

**[documented, fetched 2026-08-21]** Two statements settle this, and both are
tighter than this file's earlier draft assumed.

**Clipboard egress is explicitly forbidden.** The SRE FAQ:

> Copying data and pasting it outside of the Jupyter environment is not allowed.
> — [Secure Research Environment FAQ](https://developers.facebook.com/docs/researcher-platform/support/general-faq/)

So `copyAllowed = Enabled` on the AWS side is an *affordance the platform did not
disable*, not a permission. The agent cannot use it anyway (`Ctrl+C` is stripped),
and the researcher must not.

**The sanctioned export carries code, not results.**
[Export notebooks](https://developers.facebook.com/docs/researcher-platform/features/notebook-export)
is automated with **no review step**, delivered as an emailed download link, and
rate-limited. What it strips:

> Cell outputs (except for images), including `html`, `stdout`, and `stderr`

plus all raw cell data. Code, markdown and **images** survive.

That last word is the whole design consequence: **a number leaves the enclave
either as an image or by being read off the screen and retyped.** There is no
sanctioned text channel for results. Anything the driver reports in a chat
message got there by transcription, outside any platform control — which is why
`mcl-agent/references/egress_policy.md` has to carry that weight itself, and why
it was rewritten on 2026-08-21 to say so.

Practical consequence for the driver: when a result matters and should be
durable, **render it as a plot inside the notebook and export the notebook**.
When it just needs to be reported, transcribe the aggregate.

## Free rider — enum casing: `mode` settled, `status` still open

**Run 2026-08-21, zero budget spent.** Full result in
`OPEN_QUESTION_ENUM_CASING.md`; the short version:

- **`mode` is UPPERCASE, authoritatively.** The OpenAPI spec (512,717 characters,
  fetched via `client$openapi_spec()`) declares
  `"mode": {"type": "string", "enum": ["LIVE", "SNAPSHOT"], ...}` — five
  occurrences, every one an `enum` list. **No code changes needed:** every
  example in `mcl-api-r` already passes `"SNAPSHOT"`.
- **The spec does not declare job status at all.** `status` is a bare
  `{"type": "string", "description": "Execution status of the async job, i.e. in
  progress, completed, failed, etc."}` — prose, no `enum`. Of the 12 enums in the
  spec, none is a status vocabulary.
- **No live job was available to ask.** `GET async/jobs` returned zero rows in
  this workspace, so the wrapper's `get_status()` could not be observed. Doing so
  requires submitting a job, which costs budget and is out of scope for Stage 0.

That last point relocates the question rather than leaving it hanging: **the
status casing is now a Stage 3 item**, to be recorded from the first real run's
job, not a recon item.

The prose description is a trap worth naming. It reads "in progress, completed,
failed" in lowercase, and `mode`'s description likewise says "live mode or
snapshot mode" in lowercase while its `enum` says `["LIVE", "SNAPSHOT"]`. **Prose
casing in this spec does not predict enum casing** — it is demonstrably the
opposite for `mode`. Anyone tempted to infer `status` casing from that
description should not.

One correction to `OPEN_QUESTION_ENUM_CASING.md` from this recon: its Prompt B
tells Claude to "establish whether you can send keystrokes and confirm from a
screenshot", then offers drive-vs-dictate. The answer is now known and is
**neither** cleanly — typing works, shortcuts do not, and screenshots disturb the
stream. Rewrite that prompt against § "The verdict" below before reusing it.

---

## The permission question the toggles do not answer

Stage 0 asked what the platform *can* do. Reading Meta's
[Research Tools Terms and Conditions](https://transparency.meta.com/researchtools/product-terms-meta-research)
(updated 8 Dec 2025, fetched 2026-08-21) shows that what the platform *permits*
is the tighter constraint, and it cuts against parts of the Stage 2 design.

**[documented]** Three clauses bear directly:

- **§5.b.ii** — You will not "make any attempt to export or download Meta Data
  from a Research Tool outside the Meta-approved environment in which the Meta
  Data is accessed, unless otherwise allowed by Meta." A clipboard copy-out of
  raw post text is such an attempt. `copyAllowed = Enabled` is a *platform*
  affordance; it is not a *permission*.
- **§7.b** — Meta Data and the Research Tools "and the information contained
  therein" are Confidential Information, not to be disclosed to any entity that
  lacks a need to know and a signed NDA.
- **§6.c** — "You will ensure access to any Research Tool is limited only to
  You, and You will not share access with any third-party."

**[inferred]** Every screenshot of the streamed session is transmitted to
Anthropic for processing. Under §7.b that is a disclosure of Confidential
Information to a third party; under §6.c it is arguably shared access. This is
not a hypothetical of the driver design — it is what Stage 0 recon *itself* did,
including screenshots that showed producer names, follower counts and profile
descriptions in an open CSV.

**§4** incorporates a **Meta Research Tools Import & Export Policy** by
reference and gives it control over "all import and export matters." **[verified
2026-08-21]** That document is not resolvable at
`transparency.meta.com/researchtools/import-export-policy` (404) and did not
surface in a web search; it appears to live behind the researcher platform
login. **The document itself has still not been read.**

**Substantially mitigated 2026-08-21, after a second search.** The formal policy
is still unlocated, but Meta's Researcher Platform documentation states the
operative rules for both directions, and they are the ones a driver actually
needs:

| Direction | Rule | Source |
|---|---|---|
| Import | `.csv`/`.tsv` via S3 upload, 5 GB/upload, per-researcher database | [S3 bucket](https://developers.facebook.com/docs/researcher-platform/features/S3-bucket) |
| Export | Notebook export, automated, no review, rate-limited; **strips all outputs except images** | [Export notebooks](https://developers.facebook.com/docs/researcher-platform/features/notebook-export) |
| Clipboard out | "Copying data and pasting it outside of the Jupyter environment is not allowed" | [SRE FAQ](https://developers.facebook.com/docs/researcher-platform/support/general-faq/) |

What remains genuinely unknown is narrow: whether the formal policy adds
constraints beyond these — for instance on transcription, which is what a driver
does every time it reads a number off the screen and reports it, and which none
of the three sources above addresses.

**To retrieve it:** not from `transparency.meta.com`. Terms incorporated by
reference for approved researchers normally sit in the **Research Tools
Manager** / application portal. That is a one-line ask of the researcher, not a
session task.

This gap blocks **Stage 2 driver sign-off**. It does not block Stage 0, whose
job is to record what the surface is and where the gaps are.

### What this does to the egress policy

`mcl-agent`'s `references/egress_policy.md` treats in-notebook aggregation as a
prudent default and raw-text egress as something a researcher may approve
per-instance. One half of that needs correcting and the other does not.

**Export is governed, not categorically forbidden.** §5.b.ii ends "unless
otherwise allowed by Meta"; §4 hands control to the Import & Export Policy; and
Meta did enable CSV export of certain widely-known-figure content in the
Content Library UI in 2024. So the question is not *whether* data may leave but
*what* may leave and *by which channel* — and the document that answers it is
the one that could not be read.

**Until it is read, the conservative posture is aggregates-only.** What does
survive regardless of the I&E Policy's contents is the ownership of the
restriction: §5.b.ii is an obligation the researcher owes Meta, so a
researcher's in-the-moment approval is not the thing that authorises an export.
Only Research Outputs (§2.q — findings, tables, charts, statistics, free of
Confidential Information and Personal Data) are described anywhere in the Terms
as exportable.

That sharpens the existing policy rather than contradicting it: keep
aggregates-only, and change the justification from prudence to an unread
controlling document.

---

## The verdict — what Stage 2 can be

Stage 0 was framed around three possible products. The first is wrong, the second
is right with a caveat nobody anticipated, and the third is too pessimistic.

| Framing in `STATUS.md` | Actual |
|---|---|
| Real DOM → ordinary Playwright | **No.** Cross-origin iframe, AppStream 2.0 pixel stream |
| Pixel stream, clipboard-in works → paste blocks | **Yes — but the `Ctrl+V` must be human.** Everything else about it works, and the paste is byte-exact |
| Pixel stream, no clipboard → dictate, human types | **Too pessimistic.** Typing works as a fallback, and clicking works outright |

### The design: stage-and-paste

```
compose R locally         (mcl-api-r rules, as now)
  → stage it to the local clipboard      needs the Chrome window OS-focused
  → researcher presses Ctrl+V            one keystroke, the only manual step
  → click the toolbar ▶ button           Shift+Enter is unavailable
  → poll until the stream settles, then zoom the output region
  → transcribe verbatim
```

The human contribution is **one keystroke per cell**. That is qualitatively
different from "the researcher types the query", which is what this project
feared it would be reduced to. And the paste is exact, so the composed code is
what executes.

**Typing is the fallback**, for when no human is at the keyboard. It works and is
accurate, but it invokes auto-indent (Q4), so sent ≠ landed and every verification
must normalise whitespace. Prefer paste whenever a human is present.

### Rules any driver must respect

All **[verified 2026-08-21]**:

1. **No modifier keys reach the stream.** Every shortcut becomes a toolbar click.
   Enumerate the targets once (Run, Save, Insert Below, Interrupt, Restart).
   `Enter`, `Backspace` and arrows work — `Enter` is how you get a selected cell
   from Command into Edit mode without a click.
2. **Stage the clipboard only while Chrome is OS-focused.** Poll
   `document.hasFocus()` and write on the transition.
3. **Never prompt for permission mid-run.** Approving a prompt steals window
   focus and breaks both the clipboard and the pending action.
4. **Settle before every capture.** Both `screenshot` and `zoom` renegotiate the
   stream, blanking it 2–5 seconds and losing input. Poll the local shell's text
   for `Resizing|Reconnecting` until clear, wait ~1s, then capture. Prefer `zoom`:
   it crops, so less of the screen is transmitted.
5. **Budget one throwaway click** after any renegotiation — the first click
   following one is swallowed.
6. **Assume disconnection.** The extension dropped twice during this recon. Be
   resumable; never assume a keystroke or click landed.
7. **Never capture while Meta Data is on screen** — see the permission section
   above. Clear the workspace first; a scratch notebook is safe.
8. **Trust no prior observation.** Two characters (`")`) *verified present* at the
   end of a typed cell were absent at a later observation, with no delete sent in
   between and no explanation found. **Re-verify immediately before running**,
   every time. A driver that types once, verifies once, and runs later will
   eventually execute something the researcher never wrote. Paste reduces this
   exposure — one atomic insertion instead of hundreds of keystrokes — but does
   not remove the need to verify.
9. **Typing-only rules** (skip when pasting): send balanced units, one complete
   statement at a time; compare on normalised whitespace.

### What this does not settle

- The **Import & Export Policy** (§4) is still unlocated as a document, though
  Meta's platform docs now supply the operative import and export rules (see the
  permission section). The narrow gap left is **transcription** — an agent
  reading a result off the screen and reporting it in a chat is not addressed by
  any source found. Treat that as the open question, not "no rules known."
- **Outbound network from a cell** was deliberately deferred and is now also less
  attractive: a sanctioned import path exists (S3), so probing an undocumented
  one risks being read as circumvention under §5.b.i.
- **Job status casing** is unresolved and has moved to Stage 3: the spec declares
  no `enum` for it and this workspace had no jobs to observe. `mode` *was*
  settled — `["LIVE", "SNAPSHOT"]`, uppercase.
- **Whether `uploadAllowed` / `downloadAllowed` are enabled** was not determined.
  The absence of a file-transfer toolbar control is not evidence either way.

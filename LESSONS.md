# LESSONS — Operational Notes

Observations from running this workspace on real papers. The theme is the same throughout: keep extraction and interpretation separate, and keep the parent context small.

---

## [tags: architecture, evidence, separation] Scripts Extract, Agents Interpret

- The most damaging failure was a generator that produced plausible paragraphs and sample equations for every paper. It made notes look complete while destroying trust in them.
- The current contract is narrow on purpose: `.raw/<slug>/paper.json`, `fulltext.md`, `figures/manifest.json`, and `papers/assets/<slug>/` only. No review text is generated.
- When a note looks thin, the fix is better evidence or an honest `原文未提供`, not a more fluent template.
- If the evidence pack and the note disagree about figure origin, the manifest wins.

## [tags: figures, browser-first, resolution] Browser First, PDF Second

- Publisher thumbnails (`/w400/`, `/lw685/`, `.medium.gif`) are often what appears in the initial DOM. Rewrite to `/full/`, `/w1200/`, or `.large.jpg` before downloading.
- A rendered page is the best source for figure order, captions, and panel structure. PDF embedded images often split a multi-panel figure or lose the caption entirely.
- For a PDF with a DOI, the pipeline still opens the publisher page. PDF figures are only a fallback, and `paper.json.method` must reflect that.
- Direct image URLs may return 403 even when the page is accessible. Fetching in the page context works because the browser supplies the session and referer.
- Never describe a PDF bitmap as a "high-resolution publisher figure".

## [tags: access, cloudflare, ethics] Access Is Not Bypass

- Reusing the user's Chrome session is about rendering and figure access, not circumventing paywalls.
- Cloudflare and similar checks are interactive. Wait, complete them manually if needed, then retry with `--browser existing`.
- Batch jobs run sequentially. Parallel crawls against one publisher are both fragile and impolite.
- Open-access PDFs (OpenAlex, arXiv, bioRxiv, PMC) are preferable for text. Use the paywalled page only for what the session can already see.

## [tags: captions, manifest, honesty] Captions Are Evidence

- Caption extraction is the weakest link. A figure may have no `figcaption`, a caption shared across panels, or a caption far from the image.
- The manifest records what was found. The note must not upgrade an empty caption into a confident title.
- When `is_body_figure` is false or uncertain, check the image manually before using it. Page chrome and inline icons sometimes survive filtering.
- If a figure is missing, say which figure and why (paywall, 403, viewer), instead of silently dropping it.

## [tags: context, token-budget, agent-loop] Context Pressure

- A full paper can be 15k–30k words. Dumping it into the parent conversation invites compaction and loses the thread.
- Read `fulltext.md` in sections, or delegate one paper per subagent. Keep only the structured conclusions in the parent.
- Persist intermediate findings to the note or a scratch file instead of repeating them in chat.
- For a batch, process one paper at a time: extract → write → QA → index. Do not extract all papers first and then try to hold them all in context.

## [tags: qa, vscode, images] Preview Failures Are Usually Workspace Roots

- Notes live in `papers/`; images live in `papers/assets/<slug>/`. The only correct link is `assets/<slug>/fig_XX.png`.
- VS Code's Markdown preview restricts local images to the workspace folder. A project-root `assets/` breaks whenever the user opens `papers/` or a single file, while editor hover still works because it resolves the file differently. That mismatch produced a long false trail before the root cause was clear.
- Keep the figure library inside `papers/` so every plausible workspace root contains it.
- `--check-note --fix` catches missing files, zero-byte files, invalid magic bytes, legacy root assets, and non-standard relative paths, and migrates legacy figures.
- A zero-byte or HTML file with a `.png` extension is worse than a missing figure because it looks present. Validate magic bytes.
- Do not "fix" a report by deleting figures. Fix the path or report the missing evidence.

## [tags: katex, math, vscode] Formulas

- VS Code renders KaTeX natively; no Node.js or SVG conversion.
- Only reproduce equations present in the source. Sample equations are a tell that the note was templated.
- Keep display math balanced; an odd number of `$$` breaks the rest of the preview.
- Use `\$` for literal currency.

## [tags: markdown, vscode, callouts] Callouts

- VS Code's built-in Markdown preview does not render GitHub alert syntax (`> [!NOTE]`, `> [!WARNING]`); it prints the marker as plain text. Use a blockquote with a bold label instead:
  ```markdown
  > **一句话结论**
  >
  > The claim and its boundary conditions.
  ```
- Keep the label on its own quoted line and leave a quoted blank line before the body, otherwise the bold label and the paragraph collapse into one line.
- `--check-note` now treats the marker as an error and `--fix` rewrites it to `> **要点**`. The label is a guess; reword it to the real function rather than shipping "要点" everywhere.

## [tags: contract, preflight, agent-behavior] A Request Is Not a Gate

- "Read `AGENTS.md` before doing anything" is advisory. An agent under context pressure will run `--doi` first and read later, then reconstruct the contract from the flags. Documentation alone cannot make a session start correctly.
- The first fix was to separate the durable rules (`MEMORY.md`) from the failure stories (`LESSONS.md`) and add `--preflight`, which checks the three documents, the environment, the profile and the workspace role, then writes a 24-hour, version-bound marker.
- Literature commands require that marker and exit 2 without it. The point is not to punish the agent; it is to make "skipped the check" a visible failure instead of a silent downgrade.
- The marker cannot prove a document was read. Do not pretend otherwise: the honest claim is "the check ran", and the contract forbids fabricating the marker.
- The escape hatch (`--no-preflight`, `GEO_READER_SKIP_PREFLIGHT=1`) matters. A gate with no override gets disabled entirely the first time it misfires, usually offline. Require explicit user consent and say what was skipped.
- Onboarding also needed a spoken component: confirm the OS, Python, packages, browser and editor; then walk the tree. Printing seven commands is not teaching.
- The last structural fix was separating a *code repository* (no profile, notes or packs) from a *test workspace* (all of them). `--preflight` prints the role, and the data paths are git-ignored, so publishing cannot silently include a user's library.

## [tags: references, citation-network, classic-papers] A Classic Paper Is a Position, Not a PDF

- The first version of the note template only asked for "文献定位" in three bullets. The result was a competent summary that never said who the paper was arguing with. That is a book report, not a classic-paper read.
- What changed the quality was forcing three things: a citation table with 年份 / 工作 / 核心贡献 / 与本文的关系; an explicit **竞争解释** paragraph; and an explicit **后续检验** paragraph.
- Counts are a floor, not a goal. 10 external works for a deep read, 6 for standard, 3 for brief, 15 for a review. Only entries under `## 参考文献` count; the anchor is excluded.
- The failure mode the count creates is padding: adding plausible titles that were never read. The check cannot detect that, so the template says it out loud — if the literature is missing, say which part, do not fill the gap.
- Give every external work a DOI. A citation you cannot resolve is a liability in a note that is supposed to be reusable years later.

## [tags: tone, objectivity] Academic Neutrality

- Ban `颠覆一切`, `彻底终结`, `完美解决`, `前所未有`, and similar phrasing.
- Distinguish the authors' claims, the data, and your inference. A note that merges all three is not useful for later citation.
- Put boundary conditions and sample limitations in a `> **边界条件与未解问题**` blockquote, not in a closing flourish.

## [tags: subagent, delegation, batch] Subagent Delegation

- Delegate one paper per subagent when the batch is larger than two or three papers.
- Give each subagent: the slug, the evidence-pack paths, the note template, the QA commands, and the instruction not to invent content.
- The parent should receive the note path, a 3–5 sentence summary, figure count and origin, QA status, and any unresolved warnings.
- Review at least one subagent-produced note yourself before trusting the batch; template drift is contagious.

## [tags: updates, data-safety, versioning] Updates Replace Code, Never Evidence

- A paper workspace holds two kinds of files with opposite lifecycles: code (replaceable) and notes/packs/preferences (not replaceable). Mixing them in one updater is how people lose months of work.
- The updater's allowlist is the safety boundary. `papers/`, `.raw/`, `.geo-reader/` and `input_pdfs/` are never in it; a git checkout is fast-forwarded only when the tracked tree is clean.
- Refusing to update a dirty tree is the correct behaviour, not a bug. A silent `reset --hard` would "fix" the error by deleting the user's work.
- Version checks must be cheap and offline-safe: a six-hour cache, a short timeout, exit code 0 on failure. An update check that fails a reading task trains users to disable it.
- Patch-first versioning (`0.3.0 → 0.3.1`) keeps release numbering legible for a user who only wants to know whether their copy is current.

## [tags: discovery, journals, workflow] “Find New Papers” Opens the User's Pages, Not a Topic Search

- First failure: asked to “找新文献”, the agent searched OpenAlex by topics inferred from existing notes and produced a curated reading list. It looked helpful and was the wrong contract. The user had asked for the journals' own new-article lists, and wanted to choose before any reading.
- Second failure: the two-stage fix still shipped its own 30-journal Crossref list. That was not the user's list. Their list is a set of publisher pages — Nature research-articles, Science First Release / Current, EPSL volumes, AGU journals, Geology current / early, GJI, PNAS Earth — 17 sections in all. Rebuilt from that list (reference workspace read-only).
- The contract: `--new-literature` opens each configured page in Chrome/CDP, parses the entries the page lists, writes a numbered candidate list, and stops. Only after the user names numbers or DOIs does extraction start.
- Topic inference is the bug, not a feature. Even a good guess removes the user's choice and hides which journals were actually covered.
- No keyword filter. A broad journal will list non-geoscience papers; that is the user's chosen scope. Never narrow it from the conversation.
- The page decides what “latest” means. A research-articles page covers weeks; a volume page covers an issue. `--days 0` is the default so the page is shown as-is.
- Cloudflare is a hand-off, not a retry loop. Wait, report, ask the user to finish the check, rerun the same command.
- Crossref is convenient but not equivalent: it returns what was deposited, not what the page currently lists. Issue dates can sit months ahead, and section choices (AGU Recently Published, PNAS Recent articles, Geology early publication) are lost.
- A Chinese title is part of the list, but it is a reading aid, not bibliographic data. Translate with a real service (Bing `ttranslatev3`, since Google is blocked and MyMemory runs out after ~1000 words), label it “机译，仅供检索”, keep the English title authoritative, and cache by English title so a 300-item scan costs three new requests on rerun, not three hundred.
- Translate the *clean* title. Escaped inline markup (`NH&lt;sub&gt;4&lt;/sub&gt;`, `<i>P</i>-Wave`) must be unescaped before tags are stripped, or the cache key differs from the displayed title and a handful of entries silently show “暂缺”.
- Store raw machine output and post-edit on read. A glossary (`fugacity→逸度`, `sub-arc→弧下`, `large igneous province→大火成岩省`) can then improve every cached entry without retranslation, and a bad rule is a one-line fix rather than a cache purge.
- Never hand-write a missing translation. “暂缺” plus a rerun instruction is honest; a plausible-looking invented title is not.

## [tags: windows, encoding, qa, console] The Console Is Part of the Contract

- First failure: on Windows 11 the QA gate died with `UnicodeEncodeError: 'gbk' codec can't encode character '\U0001f4dd'` at `print("\n\U0001f4dd {}".format(note))`. The note was fine; the report never printed. A check that crashes before it reports is indistinguishable from a check that found nothing.
- A Chinese Windows console encodes a **pipe** with cp936/GBK, not UTF-8. Redirected output — which is exactly how an agent reads a command — therefore arrives as GBK bytes and decodes as mojibake (`֤�ݰ�…`). The files on disk were never affected: every write already used `encoding="utf-8"`.
- Fix both halves. Force UTF-8 on stdout/stderr at the entry point (`sys.stdout.reconfigure(encoding="utf-8", errors="replace")`), and stop printing emoji: the console markers are ASCII (`[OK]`, `[FAIL]`, `[WARN]`). A static test now fails the build if a GBK-unsafe character reappears in any `.py` file.
- Also pin `encoding="utf-8"` on every `subprocess.run(..., text=True)`. `text=True` decodes with the *locale* encoding, so a UTF-8 JSON payload from `doctor.py` would be misread by `preflight.py` on the same machine.
- Exit code **49** with no output means the Microsoft Store alias stub (`AppData\Local\Microsoft\WindowsApps\python3.exe`), not a project bug. It is a zero-byte reparse point that never starts Python. Detect it by path, and say so; the fix is `uv sync` + `uv run`, or a python.org install with "Add Python to PATH".
- `uv init` in an existing checkout fails by design ("Project is already initialized"). `uv sync` is the command that belongs there.

## [tags: review, crossref, evidence, workflow] A Thematic Review Is an Anchor Plus a Network, Not a Longer Summary

- Two review routes exist and they answer different questions. The journal scan lists what a set of pages currently publishes; a thematic review asks what the evidence says about a question. The earlier failure mode — inferring a topic from the conversation and returning a curated list — was exactly what the journal scan had already been corrected for. Reusing it for a thematic review re-opens the same wound.
- An anchor paper changes what a review is. Without one, the note degenerates into a topic digest that any search engine could have written. With one, the work becomes: what did this paper claim, which rivals does it argue against, what tested it later.
- Verification is a separate layer from discovery. Crossref topic search finds candidates; Crossref per-DOI lookup confirms title, authors, year, journal and abstract. OpenAlex is used only to *find* forward citations — every candidate it returns still has to pass through Crossref before it may be cited. A verification failure must stay visible as “待核验”, never silently become a claim.
- Predecessors come from the anchor's Crossref reference list, and that list is only as complete as the publisher's deposit. An empty list means “not deposited”, not “no predecessors” — say so in the note rather than pretending the field is empty.
- Evidence tiers are what keep a review honest: 【直证】direct from the source, 【转述】second-hand, 【推断】inference, 【评估】the writer's assessment, 【未核实】unverified. A review that does not label its claims is a review that quietly mixes a paper's finding with the writer's guess.
- The human fact-check sheet is not paperwork. Automation can confirm that a DOI resolves to a title; only a person can confirm that the title, the year, the figure and the sentence in the note are the ones the paper actually says. Generate the sheet so the checking is a checklist, not a blank page.
- “系统综述” is a claim about method. Without a recorded search string, database, date window and inclusion/exclusion rules, the phrase is a promise the note cannot keep.

## [tags: environment, onboarding, python, windows] A Fresh Clone Is the Install

- A second Windows test run cloned the repository, said `开始使用`, and got a working session with **no installer at all**: the agent read the contract, found `python` exiting with code 49, located `uv`, ran `uv sync`, onboarded the user, extracted a paper and delivered a note that passed QA. The install scripts were never needed.
- That is the real product surface. A script that asks the user to run something before the agent can work is a step *backwards* from an agent that can just do it. The scripts stay as a convenience for people who prefer them; the contract should never require them.
- The environment question generalises: `uv` is one answer, not the answer. The workspace now scans **uv → conda → venv → plain Python** and prints the winner on the `Env:` line of `--preflight`. An agent that hard-codes `uv run` breaks a user who manages Python with conda; an agent that guesses breaks everyone.
- Prefer the environment the user is already in. If a conda env or a venv is activated and the dependencies import there, `python main.py …` is the right command — building a second environment on top of a working one is busywork the user did not ask for.
- The scan must never install anything by itself. It reports a command (`uv sync`, `python -m pip install -r requirements.txt`); the agent decides whether to run it. A detector that also mutates the machine is a setup wizard wearing a detector's clothes.

## [tags: verification, crossref, doi, hallucination] A DOI That Resolves Is Not a DOI You Meant

- Field failure: an agent produced `10.5194/egusphere-egu25-12628` for a paper it claimed was a 2020 review. The DOI resolves — to a real conference abstract on a related topic, with a plausible year. It survives every "does the link work?" check and would have been cited for years.
- The lesson generalises: **resolution is not identity**. A wrong DOI and a right DOI are both real; only the title distinguishes them. Verification that stops at "HTTP 200" verifies nothing.
- So verification now compares the resolved title with the title the note is about to claim (`--refs "doi|expected title"`). A mismatch keeps the entry out of the reference list and says what came back instead.
- Distinguish the failure kinds, because they demand different responses: `not_found` (the DOI does not exist — retrying is pointless), `temporarily_unavailable` (the API was busy — rerun), `title_mismatch` (it points at a different paper — change the DOI or change what you cite).
- Never let a failed lookup become an invented one. A fabricated DOI is indistinguishable from a real one in a reference list until somebody tries to cite it.
- Rate-limited APIs need patience, not luck: retry 429 and 5xx with a backoff, honour `Retry-After`, never retry a 404, report a non-JSON body as a failure instead of letting a decoder traceback escape, and leave a gap between calls. The old code turned a throttled response into an opaque `Expecting value: line 1 column 1` and the agent filled the gap with a guess.

## [tags: style, writing, tutorial, neutrality] Plain, Logical, Tutorial — Without Losing Restraint

- A note that only a specialist can read is not reusable by the person who most needs it: someone who just entered the subfield. The user's correction on the 0.6.0 draft was exactly this — "不能写得太晦涩，要兼具学术的平实性，又要有研究的逻辑性，甚至带有一点教程性质，把这个专业刚入门的讲懂，但是不能失去平实克制".
- The four words pull against each other, and that tension is the design. Tutorial patience becomes padding; plainness becomes vagueness; restraint becomes timidity. The resolution is **explain more, claim less**: a paragraph may be long if it is doing work, never long because it is hedging.
- Turn the adjectives into habits you can check, because "write better" is not a contract. Define a term the first time it appears; make numbers carry units and conditions; replace adjectives with measurements; tell the reader how to read a figure *and what that figure cannot settle*; give one "换句话说……" sentence after a dense result; label the strength of each link; calibrate the verbs (表明 / 提示 / 作者认为 / 我判断).
- Tutorial means the reader is never lost, not that everything is re-derived. If the paper's framing is already clear, paraphrasing it a second time is noise, not helpfulness.
- A note has two readers at once — the colleague who knows the field and the student who entered it last month. Writing for the second one does not dilute the first; it is the same prose with the jargon expanded once.
- The mechanical half stays with `--check-note` (no hype words, a labelled opening takeaway, balanced `$$`). The other half cannot be automated: a note can be technically correct, pass every check, and still be impossible to follow.

---
name: review-paper
description: Review a scientific paper (LaTeX source) against the CompLING house style for writing and math typesetting. Usage: /review-paper [path] [additional instructions]
---

Review a scientific paper against the CompLING house-style rules below. The argument is optional: it may be a path to a LaTeX file or a directory of `.tex` files, optionally followed by additional instructions.

Parse the argument string:
- If the argument is empty, use the current working directory as the project root; everything counts as additional instructions (empty here).
- Otherwise, the first token is the path; everything after is additional instructions (may be empty). If the first token does not look like a path (does not exist as a file or directory), treat the entire argument as additional instructions and use the current working directory as the project root.

## Steps

1. **Locate source files.** If the path is a directory (including the current working directory when no argument was given), find all `.tex` files in it, then identify the main file (the one containing `\documentclass` and `\begin{document}`) and follow `\input{...}` / `\include{...}` references from there. If the path is a file, start from that file and follow `\input{...}` references to any other `.tex` files in the project.
2. **Scan each file** for violations of the rules in the sections below. For each violation, record:
   - File and line number (use `file.tex:LINE` format).
   - A short description of the issue.
   - The suggested fix.
3. **Group the findings** by category (Writing, Typesetting, Citations, Math, etc.) and present them to the user as a summary.
4. **Annotate the source with TODO notes.** For each identified content issue, insert a `\fredaauto{...}` comment at or just before the offending location in the `.tex` file (see "Inline annotations" below for setup). Keep the comment text short — one sentence stating the issue and the suggested fix.
5. If additional instructions were provided in the argument, follow them after the review.
6. **Verify citations (last step).** If the project has any `.bib` file(s), run the reference checker from this skill's `scripts/` directory: `uv run <skill-dir>/scripts/check_reference.py <bib-path-or-project-dir>`. The script queries CrossRef, Semantic Scholar, and OpenAlex and emits a grouped report (`verified` / `suspicious` / `not_found` / `skipped`). Add its findings under the Citations category of the summary: cite `bibfile.bib:LINE` for each flagged entry and note the specific reason (author divergence, year mismatch, generic title, malformed DOI, etc.). Do not insert `\fredaauto{...}` annotations on `.bib` files — bib findings belong in the summary report only. If the script cannot reach the network (all three APIs fail), re-run with `--no-network` to still report local red flags, and explicitly note that the existence check was skipped.

## Inline annotations

Annotations use the `todonotes` package. Before inserting any `\fredaauto{...}` calls, verify the main file's preamble contains the required setup. If any of it is missing, add it to the preamble (right after other `\usepackage{...}` lines).

Required preamble:

```latex
\usepackage{todonotes}
\usepackage{multirow}
\usepackage{array}
\usepackage{tcolorbox}
\newcommand{\note}[4][]{\todo[author=#2,color=#3,size=\scriptsize,fancyline,caption={},#1]{#4}}
\definecolor{tticblue}{RGB}{0, 94, 184}
\newcommand{\fredaauto}[2][]{\note[#1]{Freda via Erich Review Bot}{tticblue!20}{#2}}
\newcommand{\Fredaauto}[2][]{\fredaauto[inline,#1]{#2}\noindent}
```

Rules for inserting annotations:

- Always use the color `tticblue!20` (which `\fredaauto{...}` already does — do not invent other colors).
- Use `\fredaauto{...}` for short margin notes. Use `\Fredaauto{...}` for longer inline notes that would not fit in a margin.
- Place the annotation directly before or inside the problem location so it renders near the issue. Do not reflow or otherwise edit the surrounding text.
- Do not add `\fredaauto{...}` for issues that cannot be localized to a specific line (e.g., overall structure comments) — leave those in the summary report only.
- Inside floating environments (`figure`, `table`, `figure*`, `table*`), annotations are allowed but must go *outside* `\caption{...}`. Use `\Fredaauto{...}` placed elsewhere in the float (e.g., just before `\caption{...}` or before `\end{figure}` / `\end{table}`) to flag caption-wording issues. Never insert `\fredaauto{...}` or `\Fredaauto{...}` inside the `\caption{...}` argument itself.
- If a `\fredaauto` / `\Fredaauto` macro is already defined in the preamble with a different color or author, leave it alone and use it as-is.

Only flag issues you are confident about. If a rule has judgment-call edge cases (e.g., tense, voice), note the ambiguity instead of insisting on one option.

## Rules to check

### Structure and project setup

- **Hierarchical organization.** The main file should split long papers into per-section files included via `\input{...}`. Flag papers with one giant `.tex` file only if it is unwieldy (~500+ lines).
- **Macros.** Recurring strings (model names, method names, dataset names) should use `\newcommand`. Flag repeated literal occurrences (3+ times) of the same model/method name that could be a macro.
- **Booktabs tables.** Tables should use `\usepackage{booktabs}` with `\toprule`, `\midrule`, `\bottomrule`. Flag any `\hline` in tables. Flag vertical lines in tables (e.g., `|` in `tabular` column specs like `{l|cc}`).
- **Figures.** Flag `\includegraphics` calls loading raster formats (`.png`, `.jpg`, `.jpeg`) unless a vectorized alternative is clearly unavailable (e.g., photographs). PDF/SVG is preferred.
- **Caption placement.** In ACL-style papers, captions belong below figures and tables (i.e., `\caption{...}` should appear after `\includegraphics` or after the `tabular` environment, still inside the float). Flag captions placed above.
- **Cross-references.** Prefer `\cref{...}` (from `cleveref`) over manual `Figure~\ref{...}` / `Table~\ref{...}`. Flag inconsistent or manual reference styles.

### Writing style

- **Tense.** Prefer present tense. Past tense is acceptable for dataset construction or experimental procedures. Flag gratuitous past tense in introductions, related work, and analysis.
- **Simpler paraphrases.** Flag these words and suggest replacements:
  - *utilize*, *leverage* → *use*
  - *in order to* → *to*
  - *due to the fact that* → *because*
  - *a large number of* → *many*
- **Passive voice.** Flag passive voice that exists solely to avoid *we* (e.g., *it was observed that* → *we observe that*). Passive voice is fine when the agent is genuinely unimportant.
- **Contractions.** Flag any contractions in the prose: *don't* → *do not*, *we're* → *we are*, *it's* → *it is*, *can't* → *cannot*, etc.
- **Possessive *'s*** on inanimate nouns is often awkward. Flag *the system's implementation* → *the implementation of the system* (but do not be dogmatic — short possessives like *the model's output* are usually fine).
- **Title capitalization.** In `\title{...}` and section titles (`\section{...}`, `\subsection{...}`), capitalize every word except articles (*a*, *an*, *the*), prepositions, and coordinating conjunctions (*and*, *or*, *but*). Always capitalize the first and last word.
- **Main-text capitalization.** In the body, only capitalize named entities and non-obvious abbreviations. Flag title-case phrases like *Natural Language Processing* in body text (should be *natural language processing*). Do NOT flag established named architectures like *Transformer*.
- **Common expressions.**
  - Flag *e.g.* and *i.e.* not followed by a comma: *e.g.,* and *i.e.,* (two commas).
  - Flag *etc.* used for people (should be *et al.*) and *et al.* used for things (should be *etc.*).
  - Flag *state-of-the-art* used as a noun or *state of the art* used as an adjective.
  - *a priori* is an adjective phrase; flag noun usage.
- **Uncountable nouns.** Flag *many works* → *much work*; *researches* (as a noun) → *research*; *literatures* → *literature*; *evidences* → *evidence*.
- **Quotation marks.** Flag straight double quotes `"..."` in LaTeX source — LaTeX needs `` `` ``...'' `` (two backticks, then two single quotes).
- **Dashes.** Flag single hyphens (`-`) used to connect clauses or names that should use en dash (`--`) or em dash (`---`). Examples: *Kullback-Leibler* should be *Kullback--Leibler*; a clause break like *something - something else* should be *something---something else* (no spaces) or *something -- something else* (with spaces). Do NOT flag hyphens inside compound words (*state-of-the-art*, *end-to-end*).
- **Period inside closing quote** when a sentence ends with a quotation: *"...world."* not *"...world".*
- **Footnote placement.** `\footnote{...}` should follow periods, commas, or closing parentheses with no space. Flag footnotes placed before the punctuation.
- **a vs. an.** Check by the sound of the following word, not the letter. *A university*, *an LSTM*, *an MLP*, *a unique*. Flag obvious mismatches.

### Citations and bibliography

- **natbib + cleveref.** The preamble should include `\usepackage{natbib}` (or the conference-provided equivalent) and `\usepackage{cleveref}`. Flag absence.
- **Citation commands.** Flag `\cite{...}` when `\citep{...}` or `\citet{...}` would be more appropriate in context.
- **Venue acronyms.** In BibTeX entries for papers from the following venues, the `booktitle` or `journal` field should use the acronym, not the full name: ACL, EMNLP, NAACL, EACL, AACL, COLING, TACL, CL, CVPR, ICCV, ECCV, ICLR, ICML, NeurIPS, AAAI, IJCAI, AISTATS, COLT, UAI, TMLR, JAIR, TPAMI, CogSci. Flag full-name usage for these.
- **Capitalization protection in bib.** In BibTeX `title` fields, words that must stay capitalized (model names, proper nouns, acronyms) should be wrapped in braces: `{BERT}`, `{Grad-CAM}`. Flag unwrapped proper nouns/acronyms in titles.
- **Citation correctness.** Spot-check a few entries for obviously wrong year or venue if possible, but do not fabricate corrections — just flag suspicious entries.
- **Hallucinated citations.** Every `.bib` entry should resolve to a real work in CrossRef, Semantic Scholar, or OpenAlex. Step 6 runs `check_reference.py` to perform this verification; surface any `not_found` or `suspicious` results in the Citations section of the summary.

### Math typesetting

- **Equation environments.** Flag `\begin{equation}` and `\begin{eqnarray}`. Prefer `align` or `align*`. Only numbered equations should use `align`; unreferenced equations should use `align*`.
- **Multi-character sub/superscripts.** Flag `$p_{surface}$` style — should be `$p_\textit{surface}$` (or similar text wrapper). Single-letter subscripts are fine.
- **Ellipsis.** Flag `...` inside math mode; prefer `\ldots` for lists (`$x_1, \ldots, x_n$`) and `\cdots` for operation sequences (`$x_1 + \cdots + x_n$`).
- **Punctuation in display math.** Displayed equations that are part of a sentence should have a comma or period. Flag display equations in the middle of a sentence that end with nothing.
- **Variable conventions:**
  - Scalars: lowercase Latin letters (`a, b, c`; integers `i, j, k, \ell, m, n`; RV values `x, y, z`). Flag use of `l` (lowercase L) as an index — prefer `\ell`.
  - Structured values (sequences, trees): lowercase `\boldsymbol{...}`.
  - Vectors: `\mathbf{...}` for Latin, `\boldsymbol{...}` for Greek.
  - Matrices: capital `\mathbf{...}` for Latin, `\boldsymbol{...}` for Greek.
  - Vector/matrix elements: scalar typeface (e.g., `h_i`, `w_{i,j}`).
  - Sets of structured values: capital `\mathcal{...}`.
  - Sets of numbers: capital `\mathbb{...}` (e.g., `\mathbb{R}`).
  - Random variables: capital `X, Y, Z`; vector-valued RVs: `\boldsymbol{X}`.
  Flag clear violations (e.g., a weight matrix typeset as `W` instead of `\mathbf{W}`), but do not be overzealous on short inline uses.
- **Tuples.** Flag `<x, y>` for ordered pairs; use `(x, y)` or `\langle x, y \rangle`.
- **Probability:**
  - Conditional bars: flag `|` in conditional probability; use `\mid` (e.g., `p(y \mid x)`).
  - Sums/products: flag `\Sigma` and `\Pi` used as sum/product operators; use `\sum` and `\prod`.
  - Expectations: prefer `\mathbb{E}`.
- **Named operations.** Flag bare text like `softmax(x)` — should be `\mathrm{softmax}(x)`. Built-in operators like `\log`, `\exp`, `\sin`, `\max`, `\min` should use their macros, not `\mathrm{...}` or plain text.
- **Function names.** Functions like *score(x)* should be `\textit{score}(x)`, not `score(x)` (which renders as `s·c·o·r·e`).

## Output format

Present the review as a grouped list. For each finding:

```
[category] file.tex:LINE — <issue>
  fix: <suggested replacement>
```

End with a short summary: how many issues in each category, and a one-line overall impression.

## Rules while reviewing

- The only edits allowed are (a) inserting `\fredaauto{...}` / `\Fredaauto{...}` annotations at issue sites, and (b) adding the required `todonotes` preamble setup if missing. Do not reflow prose, rename macros, or "fix" anything else without explicit user permission.
- Do not commit anything.
- If the paper uses a conference style file (e.g., `acl.sty`, `neurips.sty`) that overrides some of these defaults, defer to the conference style.
- If a rule's application is ambiguous in context, note the ambiguity rather than forcing a fix.

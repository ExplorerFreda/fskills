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
6. **Verify citations.** If the project has any `.bib` file(s), run the reference checker from this skill's `scripts/` directory: `uv run <skill-dir>/scripts/check_reference.py <bib-path-or-project-dir>`. The script queries CrossRef, Semantic Scholar, and OpenAlex and emits a grouped report (`verified` / `suspicious` / `not_found` / `skipped`). Add its findings under the Citations category of the summary: cite `bibfile.bib:LINE` for each flagged entry and note the specific reason (author divergence, year mismatch, generic title, malformed DOI, etc.). Do not insert `\fredaauto{...}` annotations on `.bib` files — bib findings belong in the summary report only. If the script cannot reach the network (all three APIs fail), re-run with `--no-network` to still report local red flags, and explicitly note that the existence check was skipped.
7. **Check logical consistency and clarity.** After all format, typesetting, and citation checks are complete, do a dedicated pass over the prose focused on content-level problems. Look for:
   - **Contradictions.** Statements in the paper that disagree on facts, numbers, model sizes, dataset sizes, hyperparameters, baselines, results, or claims (e.g., the abstract reports +2.3 points but Table 2 shows +1.9; Section 3 says "we use 5 seeds" but Section 4 reports "averaged over 3 runs"; the introduction claims "first to do X" but related work cites a prior X).
   - **Terminology drift.** The same concept referred to by different names without explanation (e.g., *our model*, *the proposed method*, *the framework*, *our system* used interchangeably; *token*, *word*, *subword* mixed within one paragraph). Flag only when the drift is likely to confuse the reader.
   - **Ambiguous referents.** Pronouns (*it*, *this*, *they*, *that*, *these*) whose antecedent is unclear, or demonstratives without a clear noun (*this approach*, *these issues*) when multiple candidates are in scope.
   - **Unclear or underspecified claims.** Vague quantifiers (*significantly*, *substantially*, *many*, *often*, *generally*) used where a concrete number, dataset, or condition should appear; load-bearing passive constructions that hide the agent (*it was shown that*) when specifying the agent matters; undefined symbols or terms introduced without a prior definition.
   - **Dangling references.** `\ref{...}` / `\cref{...}` / `\cite{...}` targets that do not resolve (missing `\label{...}`, typos, stale labels), references to sections/figures/tables/equations that do not exist or were renumbered, and phrases like "as we will see in Section 4" when the referenced section does not cover that material.
   - **Internal inconsistency in procedures / experiments.** Method descriptions whose steps, equations, or dependencies do not line up (e.g., a variable used in Eq. 3 but introduced only in Eq. 5; an algorithm that reads an input never defined; a training recipe whose hyperparameters conflict with Table 1).
   - **Abstract / introduction / conclusion misalignment.** Contributions listed in one place but absent in another; the conclusion claims a result the experiments section does not actually report; the abstract over- or under-sells what the paper delivers.
   - **Figure / table ↔ text mismatch.** The text describes a trend that the figure or table does not show (wrong direction, wrong column, wrong condition); a table caption describes different columns than the table has; a figure is cited from the text but never appears, or appears but is never cited.
   For each finding, record `file.tex:LINE` (or `file.tex:LINE-LINE` for a span), a one-sentence description of the problem, and a concrete suggested fix (or two options if the correct resolution depends on author intent). If a finding can be localized to a specific line, insert a `\fredaauto{...}` annotation following the same rules as in "Inline annotations" above (including the compile-verification step). If the issue spans the whole paper or cannot be localized (e.g., a claim in the abstract contradicting a result in Section 5), leave it in the summary report only. Add these under a **Consistency & clarity** category in the final report. Where the correct fix depends on author intent you cannot infer from the text alone, mark the item as **needs author input** instead of proposing a specific rewrite.
8. **Save the issue report (final step).** The skill must always end by writing a consolidated issue report to `review-report.md` at the project root (the directory resolved in the argument-parsing step), in the format described in "Output format" below, even if no issues were found (in which case, write an empty report with a one-line "no issues found" summary). Overwrite any existing `review-report.md` at that path. After saving, point the user to the file. This is the skill's primary deliverable — do not end the turn without it.

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
- **Verify compilation after each annotation.** After inserting each `\fredaauto{...}` or `\Fredaauto{...}` annotation (including the very first one, which also exercises any preamble additions), run `pdflatex -interaction=nonstopmode -halt-on-error <main.tex>` from the project root to confirm the document still compiles. If the compile fails, revert that specific annotation (and, for the first-insertion case, any preamble changes that caused the failure) so the file returns to its previous state, then skip that site. Record each skipped annotation in the final report under a **Skipped annotations** section with `file.tex:LINE`, the intended note text, and a one-line summary of the compile error. Do not proceed to further annotations until the file is back in a compiling state.

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

Write the review to `review-report.md` at the project root as a grouped list. For each finding:

```
[category] file.tex:LINE — <issue>
  fix: <suggested replacement>
```

If any annotations were reverted because `pdflatex` failed to compile (see "Verify compilation after each annotation"), include a **Skipped annotations** section listing each one with `file.tex:LINE`, the intended note text, and a brief compile-error summary.

End with a short summary: how many issues in each category, and a one-line overall impression.

## Rules while reviewing

- The only edits allowed are (a) inserting `\fredaauto{...}` / `\Fredaauto{...}` annotations at issue sites, and (b) adding the required `todonotes` preamble setup if missing. Do not reflow prose, rename macros, or "fix" anything else without explicit user permission.
- Do not commit anything.
- If the paper uses a conference style file (e.g., `acl.sty`, `neurips.sty`) that overrides some of these defaults, defer to the conference style.
- If a rule's application is ambiguous in context, note the ambiguity rather than forcing a fix.

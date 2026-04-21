---
name: expand-writing
description: Expand a rough draft into polished technical prose, calibrated to a described audience. Usage: /expand-writing --out <path> --audience "<desc>" <input-path-or-inline-text>
---

Turn a rough draft ("verbal vomit") into polished technical prose, calibrated to the audience the user describes. The skill applies a vendored style ruleset (`rules.md` in this skill's directory) and a jargon-density dial based on the audience.

## Parse the argument

The argument string must contain:

- `--out <path>` (**required**) — destination file. Detect the output format from the extension:
  - `.tex` → LaTeX
  - `.md` / `.markdown` → Markdown
  - Any other extension → stop and ask the user which format to produce.
- `--audience "<description>"` (**required**) — free-form description of the intended reader. Must be quoted (single or double) so it can contain spaces.
- Everything remaining (after `--out <path>` and `--audience "..."` are removed) is the **input**. Strip surrounding whitespace, then:
  - If the remainder, treated as a path, resolves to an existing file, read it as the input.
  - Otherwise, treat the literal remainder as inline prose to expand.

Stop and ask the user if:

- `--out` is missing.
- `--audience` is missing.
- The remainder is empty (no input to expand).
- The `--out` extension is neither `.tex` nor `.md` / `.markdown`.
- The `--out` path already exists (confirm before overwriting; do not auto-overwrite).

## Steps

1. **Resolve inputs.** Parse the flags. Read the input (file contents or inline text). Detect the input format: `.tex` source, `.md` source, or plain prose (neither → treat as plain).

2. **Characterize the audience.** From the free-form `--audience` description, infer three internal tags:
   - **Background**: one of *domain-expert*, *adjacent-field*, *informed-layperson*, *general-public*.
   - **Register**: one of *formal*, *semi-formal*, *conversational*.
   - **Jargon tolerance**: one of *keep-as-is*, *gloss-on-first-use*, *replace-with-plain-term*.

   Record these three tags in one short sentence at the top of the change log so the user can sanity-check the calibration.

3. **Load the rules.** Read `rules.md` from this skill's directory. Apply every rule during the rewrite; cite rule IDs (R01, R03, R04, R06, R08, R11, R12, RA, RB, RF, RH, RI) in the change log.

4. **Draft the rewrite.** Produce a polished version of the input that:
   - Applies every rule in `rules.md`.
   - Calibrates vocabulary to the jargon-tolerance tag from step 2 (see "Jargon calibration" below).
   - Preserves all factual content. No fabricated numbers, citations, or claims. If the draft is vague, flag the gap in the change log instead of inventing specifics.
   - When the input is LaTeX, preserves macros, `\cite{...}`, `\ref{...}`, `\label{...}`, `\includegraphics{...}`, and all math environments (`equation`, `align`, `align*`, `\[...\]`, inline `$...$`). Do not rewrite inside any of these.
   - Matches the output format:
     - Markdown input → LaTeX output: headings → `\section{...}` / `\subsection{...}`, `-` lists → `itemize`, `1.` lists → `enumerate`, inline `` `code` `` → `\texttt{...}`, fenced code blocks → `verbatim`. Escape special LaTeX characters (`& % _ # $ ~ ^ \`) outside verbatim.
     - LaTeX input → Markdown output: strip conservative macros (`\emph{x}` → `*x*`, `\textbf{x}` → `**x**`, `\texttt{x}` → `` `x` ``, `\section{x}` → `## x`). For anything without a clean Markdown equivalent (custom macros, `\cite{}`, complex floats), leave the LaTeX as-is and warn in the change log.
     - Same-format pass-through: keep structural markup as-is; rewrite only the prose.

5. **Write the rewrite** to the `--out` path. Never touch the input file. If the output file exists, confirm before overwriting.

6. **Print a change log to the chat** (not to disk), structured as:

   ```
   Audience calibration: <background> / <register> / <jargon-tolerance>.

   Notable edits:
     [R04] "in order to evaluate" → "to evaluate"
     [R06] "leverage" → "use"
     [RF]  acronym "RAG" defined on first use as "retrieval-augmented generation"
     [R11] reordered sentence to place "23% lower error" at the end
     [R03] vague "several datasets" — flagged; input did not name them
     ... (up to ~10)

   Gaps flagged but not filled:
     - <input did not specify the training-set size>
     - <"prior work shows" used without a citation — R.H>

   Style rules adapted from The Elements of Agent Style
   (https://github.com/yzhao062/agent-style), CC BY 4.0.
   ```

   Keep the change log short. If no edits were needed, say so in one line and include only the calibration and attribution.

## Jargon calibration

The upstream ruleset tells the agent to name the reader (R01) but does not specify *how* to tune vocabulary once a reader is named. Use this dial:

- **domain-expert** → *keep-as-is*. Use field-standard jargon freely. Define only novel or niche terms introduced by the draft itself.
- **adjacent-field** → *gloss-on-first-use* (selective). Define field-specific acronyms and methods on first use. Keep well-known shared vocabulary (*gradient*, *regression*, *REST API*) without gloss.
- **informed-layperson** → *gloss-on-first-use* (aggressive). On first use of any technical concept, add a one-clause gloss: *fine-tuning — further training a model on task-specific data*. Prefer the plain term in follow-up mentions when it reads naturally.
- **general-public** → *replace-with-plain-term*. Default to plain English. Use a technical term only when no plain equivalent exists, and always gloss it. Drop internal-jargon shorthand even if it is "one word shorter."

Hard rules regardless of dial:

- Never strip a term that is load-bearing for correctness. If the plain-English replacement would mislead, keep the term and gloss it instead.
- Never invent a gloss. If you are not confident about the definition, flag the term in the change log and leave it unchanged.
- Do not add glosses to terms that already appear with a gloss elsewhere in the same document — track first-mention state across the rewrite.

## Rules while running

- Never modify the input file.
- Never overwrite the output file without user confirmation.
- Do not fabricate citations, numbers, or claims that are not present in the input.
- Preserve the author's voice and intent. This skill rewrites; it does not co-author.
- If the input already meets the style bar for the stated audience, say so in the change log and pass it through largely unchanged.
- Do not commit anything.
- The attribution line in the change log must always be present; removing it violates the CC BY 4.0 terms on the vendored rules.

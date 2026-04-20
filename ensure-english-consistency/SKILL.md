---
name: ensure-english-consistency
description: Ensure all text and code files in the repository follow a single region's English convention (US, CA, or UK). Usage: /ensure-english-consistency <US|us|CA|ca|UK|uk> [additional instructions]
---

Ensure that all natural-language text in the current repository uses a single region's English spelling convention. The argument selects the target region. Everything after the first token is additional instructions (may be empty).

## Parse the argument

1. The first token must be one of `US`, `us`, `CA`, `ca`, `UK`, `uk`. Normalize case-insensitively to one of three targets:
   - `US` → American English (e.g., *color*, *behavior*, *analyze*, *center*, *organize*)
   - `UK` → British English (e.g., *colour*, *behaviour*, *analyse*, *centre*, *organise*)
   - `CA` → Canadian English: British spellings for *-our* (*colour*, *behaviour*), *-re* (*centre*, *metre*), and doubled consonants (*travelled*, *labelled*); American `-ize` endings (*organize*, *recognize*); mixed for a few items (see "Canadian specifics" below).
2. If the first token is missing or not one of the accepted values, stop and ask the user to re-invoke the skill with a valid argument.
3. Remaining tokens are additional instructions to follow after the main scan.

## Steps

1. **Collect candidate files.** From the repository root (current working directory), list files tracked by git via `git ls-files`. If the directory is not a git repo, fall back to a recursive walk that skips `.git/`, `node_modules/`, `.venv/`, `venv/`, `dist/`, `build/`, `__pycache__/`, and any path listed in `.gitignore`.
2. **Filter by type.** Keep files with natural-language content:
   - Text / docs: `.md`, `.markdown`, `.txt`, `.rst`, `.tex`, `.bib`, `.typ`, `.org`, `.adoc`
   - Code (only prose inside comments, docstrings, and user-facing string literals): `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.go`, `.rs`, `.java`, `.c`, `.cpp`, `.h`, `.hpp`, `.rb`, `.sh`, `.zsh`, `.bash`, `.lua`, `.swift`, `.kt`, `.scala`, `.r`, `.jl`, `.php`, `.html`, `.css`, `.scss`, `.vue`, `.svelte`, `.yaml`, `.yml`, `.toml`, `.json` (only `description` / `readme` style fields)
   - Skip: binary files, lock files (`*.lock`, `package-lock.json`, `uv.lock`, `Cargo.lock`, `poetry.lock`, `yarn.lock`), minified assets (`*.min.js`, `*.min.css`), images, archives, PDFs, and generated files.
3. **Scan for region mismatches.** For each candidate file, look for words whose spelling disagrees with the target region. Use the word lists in "Common variants" below as the primary signal, plus the morphological patterns in "Patterns." Match whole words only, case-insensitively, but preserve the original case when proposing a fix (e.g., *Colour* → *Color*, *COLOUR* → *COLOR*).
4. **Apply context rules (critical — see "Do not flag" below).** Identifiers, API names, URLs, file paths, code keywords, import targets, and proper nouns must not be rewritten even when they contain a region-specific spelling. A CSS `color:` property, a Python `argparse` `metavar`, a variable named `analyze_data`, a package called `colorama`, or a quoted path like `/etc/color.conf` all stay as-is.
5. **Group findings** by file with `file:LINE` locations. For each finding include: the matched word, the proposed replacement, and a short reason (e.g., "US→UK: -or → -our").
6. **Confirm before editing.** Present the grouped report to the user and ask whether to apply all fixes, apply a subset, or stop. Do not edit until the user confirms. If the report is empty, state that and stop.
7. **Apply the approved edits** using exact-string replacements that preserve surrounding whitespace and case. Re-scan the edited files once to make sure no new mismatches were introduced (e.g., from cascaded replacements inside longer words).
8. **Return a final report** summarizing files changed, files skipped, and any ambiguous cases the user needs to resolve manually. If additional instructions were provided in the argument, follow them after the scan.

## Common variants

Use these as the baseline list (non-exhaustive — extend when obvious analogues appear). For each entry, the left column is the US form and the right column is the UK form. Canadian English follows the UK column for `-our` / `-re` / doubled-consonant forms and the US column for `-ize` / `-yze` forms unless noted.

| US | UK |
| --- | --- |
| color | colour |
| behavior | behaviour |
| favor | favour |
| honor | honour |
| labor | labour |
| neighbor | neighbour |
| flavor | flavour |
| humor | humour |
| rumor | rumour |
| vapor | vapour |
| center | centre |
| meter | metre (length unit only; *meter* = measuring device stays) |
| liter | litre |
| fiber | fibre |
| theater | theatre |
| organize | organise |
| recognize | recognise |
| analyze | analyse |
| paralyze | paralyse |
| catalog | catalogue |
| dialog | dialogue (except UI `dialog` elements in code) |
| defense | defence |
| offense | offence |
| license (noun+verb) | licence (noun) / license (verb) |
| practice (noun+verb) | practice (noun) / practise (verb) |
| program | programme (non-computing) / program (computing) |
| gray | grey |
| traveled / traveling | travelled / travelling |
| labeled / labeling | labelled / labelling |
| modeled / modeling | modelled / modelling |
| canceled / canceling | cancelled / cancelling |

### Canadian specifics

- Canadian English uses **UK** `-our`, `-re`, and doubled-consonant forms (*colour*, *centre*, *travelled*).
- Canadian English uses **US** `-ize` / `-yze` endings (*organize*, *analyze*, *recognize*).
- `program` (not *programme*) is standard in Canadian usage.
- `defence` / `offence` (UK forms) are standard in Canadian usage.
- `cheque` (financial) is UK/CA; `check` (verify) is universal. Do not flip *check* when it means "verify."

## Patterns

When a word is not in the table, morphological patterns can still decide:

- `-or` ↔ `-our` on common roots (color/colour, honor/honour) — but **not** on Latin/Greek roots like *error*, *tenor*, *author*, *horror*, *major*, *mirror*. Only flag when a reliable US/UK pair exists.
- `-er` ↔ `-re` on specific roots (*centre*, *metre*, *litre*, *fibre*, *theatre*, *calibre*). Do **not** flag generic `-er` words.
- `-ize` ↔ `-ise` only on verbs where both spellings are documented (*organize/organise*, *recognize/recognise*, *realize/realise*, *summarize/summarise*). Do **not** flag *size*, *surprise*, *exercise*, *advertise*, *compromise*, *despise*, *comprise*, which are always `-ise` in both regions.
- `-yze` ↔ `-yse` on a short list (*analyze*, *paralyze*, *catalyze*, *dialyze*).
- Single vs. doubled consonant before suffix on unstressed final syllables (*traveled* ↔ *travelled*, *labeled* ↔ *labelled*). Stressed-syllable cases (*controlled*, *referred*, *occurred*) are the same in both regions.

## Do not flag

- Identifiers in code: variable names, function names, class names, parameter names, field names, enum values, SQL column names. Example: `def analyze_data(...)` or `color: #fff` in CSS stays.
- Import targets, package names, module paths: `from colorama import ...`, `require('color')`, `<link rel="stylesheet" href="theme-color.css">`.
- URL paths, file paths, environment variable names: `https://example.com/color/`, `/etc/defense.conf`, `DEFENSE_MODE=1`.
- Language / library keywords and canonical API names that use a specific spelling: CSS `color`, SVG `fill-color`, HTML `<dialog>`, PyTorch `nn.BatchNorm`, `matplotlib.colors`, `argparse`'s `metavar`, JSON Schema `format`.
- Proper nouns: *World Health Organization*, *Labour Party*, *Pearl Harbor*, *Centre Pompidou*, personal names.
- Direct quotations, epigraphs, and citations — these must preserve the source's original spelling.
- Bibliography entry titles (`title = {...}` in `.bib`) — preserve as published.
- Code inside fenced code blocks in Markdown / reST when the code is meant to be executable or illustrative of an API (treat its identifiers like live code). Prose comments inside such blocks are still fair game.
- Words that are ambiguous between a flaggable variant and a different lexeme (e.g., *meter* as a measuring device in US/UK both) — note as ambiguous instead of rewriting.

## Output format

For the pre-edit report, group by file:

```
<file:LINE> <original> → <replacement>   (<short reason>)
```

End with counts per category (US→target, UK→target, CA-specific adjustments) and an ambiguous-cases section if any.

After edits, print a one-line summary per changed file (e.g., `README.md: 4 replacements`) and a final total.

## Rules while running

- Never change identifiers, import paths, URLs, or file paths — only prose.
- Preserve case (*Colour* → *Color*, *COLOUR* → *COLOR*, *colour* → *color*).
- Preserve surrounding whitespace and punctuation exactly.
- Do not reflow paragraphs, rewrap lines, or make any edits beyond the approved spelling substitutions.
- Do not commit anything.
- If the repo contains a style config (e.g., `.editorconfig`, `CONTRIBUTING.md`, a `STYLE.md`, or a Vale / `cspell` config) that declares a different region than the argument, surface the conflict to the user before editing and let them resolve it.

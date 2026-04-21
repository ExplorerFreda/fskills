---
name: generate-report
description: Generate a styled HTML report from experiment results following the house design system. Usage: /generate-report --results <path> --out <folder> [additional instructions]
---

Generate a styled, self-contained HTML report (`index.html`) summarizing a set of experiment results. The skill inspects the results, drafts a report using the house design system (see `template.html` in this skill's directory), writes it to the requested folder, and then iterates on the draft in response to user refinement instructions.

## Parse the argument

The argument string must contain:

- `--results <path>` (**required**) — a file or folder containing the experiment output. May be a single file (JSONL / JSON / Parquet / HDF5 / CSV / TSV / log), a directory, or a HuggingFace dataset id.
- `--out <folder>` (**required**) — destination folder. The report is written as `<folder>/index.html`. Images and other supporting files referenced by the report live in this same folder (relative paths only).
- Everything remaining is free-form **additional instructions** (may be empty) — e.g. "group by model", "highlight the GPT-4o row", "add a latency section".

Stop and ask the user if:

- `--results` is missing, or the path does not exist (unless it looks like a HuggingFace dataset id).
- `--out` is missing.
- `<folder>/index.html` already exists — confirm before overwriting.

## Steps

1. **Resolve inputs.** Parse the flags. If the `--out` folder does not exist, create it. If `<folder>/index.html` already exists, ask before overwriting (preserve other files in the folder — only `index.html` and files the skill explicitly generates may be written).

2. **Inspect the results.** Use `/inspect-data` (the `inspect-data` skill) on the `--results` target to understand the structure. If `--results` is a directory, inspect the most informative file(s) in it (typical candidates: `results.jsonl`, `metrics.json`, `summary.csv`, `eval.parquet`) — if several look relevant, inspect each. Summarize the fields, row counts, and any categorical dimensions (model, dataset, split, seed, condition) internally so the report can group by them.

3. **Identify or generate image assets.** If the `--results` folder already contains plots (`.png`, `.jpg`, `.svg`, `.pdf`), note their relative paths and copy or symlink them into `<folder>/` so that `<img src="foo.png">` works. If the results are raw numbers with no plots, or the existing plots do not fit the story, **generate new plots** following the "Plot generation" section below. Do not embed base64 — prefer sibling files.

4. **Draft the report.** Read `template.html` from this skill's directory and use it as the scaffold. Keep every CSS variable, font link, cache-control meta, and class name from the template — the design system is non-negotiable. Populate the template with:
   - A gradient header (`<div class="header">`) with the report title and a meta subtitle (date, dataset name, model, or other top-level identifier).
   - A **TL;DR / key findings** card near the top with a `<div class="summary">` banner stating the main takeaways in 2–4 bullet points.
   - One `<div class="card">` per major section, each with an `<h2><span class="num">N</span> Title</h2>` numbered heading.
   - Data tables (with `class="best"` on the best cell per comparison), code blocks for commands / config snippets, and image tags for plots.
   - A `.warning` banner for caveats (small sample sizes, known failures, incomplete runs).
   - `.mtag` pill badges for model / category labels where useful.

5. **Write the report** to `<folder>/index.html`. Use relative paths (`./plot1.png`, not absolute) for every asset. Do not inline external CSS or JS beyond what `template.html` already specifies.

6. **Report back to the user.** Print a short summary:
   - Path to `index.html`.
   - Section list (by number and title).
   - Any gaps you left (e.g., "no per-seed variance in the data — omitted the variance section") or banners added (`.warning` about small N).
   - A one-line invitation to request refinements.

7. **Iterate on refinements.** When the user sends follow-up instructions ("add a latency table", "drop Section 3", "re-color the best column"), edit `<folder>/index.html` in place. Preserve the design system: do not change CSS variables, fonts, class names, or the overall card structure unless explicitly asked. Re-run step 6's summary after each edit so the user knows what changed.

## Environment

All Python execution for this skill — data loading, plot generation, anything — runs via `uv` with inline script metadata. No system Python, no activated venv, no `pip install`. The standard dependency set is:

```python
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
#   "seaborn",
#   "pandas",
# ]
# ///
```

(`json` is stdlib — do not list it.) Add further deps (e.g. `pyarrow` for Parquet, `numpy`) only when the data actually requires them.

Invoke every script with `uv run <path-to-script>`. Never `python`, never `python3`.

## Plot generation

When plots are needed, write a one-off script in the output folder — e.g. `<out>/make_plots.py` — with the uv header above, generate the PNGs with `savefig`, then run it via `uv run <out>/make_plots.py`. The script **must**:

1. Start with the uv inline metadata block from the Environment section.
2. Load data from the `--results` path (JSON, JSONL, CSV, Parquet as appropriate).
3. Apply the house plot style from `scripts/style.py` in this skill's directory. The simplest pattern:

   ```python
   import sys
   sys.path.insert(0, "<absolute path to generate-report/scripts>")
   from style import PALETTE, apply_style, CATEGORICAL
   apply_style()
   ```

   `apply_style()` configures matplotlib + seaborn to match the HTML palette (teal axes, rose accents, Source Sans Pro font, no top/right spines, light grid). Use `PALETTE["primary"]`, `PALETTE["accent"]`, etc. when a specific color is needed; use `CATEGORICAL` as the per-series cycle.

4. Save every figure into the `--out` folder with `fig.savefig("<out>/<name>.png")`. Filenames should match the `<img src="...">` references in `index.html`.

Run the plot script once after writing it (`uv run <out>/make_plots.py`), confirm the PNGs exist, then reference them from `index.html` with relative paths. Keep the `make_plots.py` in the output folder so the user can re-run or tweak it themselves.

For refinement iterations that change plots (new columns, different grouping, color swaps), edit `<out>/make_plots.py` and re-run with `uv run`. Do not hand-edit generated PNGs.

## Design system (baked into `template.html`)

These values are the spec — do not change them without explicit user instruction.

### Color palette
```
primary/teal      #225573
accent/rose       #b6274e
green             #547b5b
olive             #6d8436
amber             #d4880f
light-teal        #4a7a94
gray/neutral      #7d99b1
```

### CSS variables (must appear in `:root`)
```css
--bg:          #f5fbf7;
--card:        #ffffff;
--text:        #225573;
--text-light:  #4a7a94;
--accent:      #b6274e;
--green:       #547b5b;
--green-light: #6d8436;
--border:      #d5e3ec;
--border-light:#e8f0f5;
--tag-bg:      #eef5f0;
--shadow:      0 1px 3px rgba(34,85,115,.08), 0 4px 14px rgba(34,85,115,.05);
--shadow-lg:   0 2px 6px rgba(34,85,115,.10), 0 8px 24px rgba(34,85,115,.08);
--radius:      10px;
--max-w:       1440px;
```

### Required `<head>` elements
- `<meta charset="utf-8">`
- `<meta name="viewport" content="width=device-width, initial-scale=1">`
- Cache-Control / Pragma / Expires no-cache headers (all three)
- Google Fonts link for Source Sans Pro weights 400/600/700

### Structural conventions
1. `<div class="page">` wraps all content; max width 1440px.
2. `<div class="header">` — gradient banner (teal → green) with `<h1>` and `<div class="meta">`.
3. `<div class="card">` — one per section. Each has an `<h2><span class="num">N</span> …</h2>` numbered heading.
4. `<div class="summary">` — teal-green gradient, left-bordered in `--green`, for TL;DRs and key findings.
5. `<div class="warning">` — amber-bordered (`#d4880f`), for caveats.
6. Tables: `border-collapse: separate`, rounded corners via `overflow: hidden` on the outer `<table>`. Use `td.best` (rose, bold) for winner cells.
7. Code: dark (`#1e2d3a` bg, `#c8dce6` text) for `<pre>`; light tag-bg (`--tag-bg`) with green text for inline `<code>`.
8. Links: green default, rose on hover with underline.
9. Images: bordered, rounded (8px), soft shadow, 1em top/bottom margin.
10. `.mtag` pills: colored rounded rectangles for model/category tags.

## Rules while running

- Never modify the `--results` source.
- Never write outside the `--out` folder. The folder may contain `index.html`, generated PNGs, `make_plots.py`, and copied/symlinked assets — nothing else.
- Do not invent numbers, model names, or claims not present in the results. If a field is missing, flag the gap in a `.warning` banner or leave the section out and note it in the summary.
- Do not add JavaScript. The report is static HTML + CSS. (Exception: only if the user explicitly asks for interactivity.)
- Do not commit anything.
- Preserve the design system across refinement iterations. New sections use the same card / heading / banner pattern as the existing ones.

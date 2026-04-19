---
name: inspect-data
description: Inspect a data file (JSONL, JSON, Parquet, or HDF5) to understand its structure. Usage: /inspect-data <file_path> [additional instructions]
---

Inspect a data file to understand its structure. The argument is a file path, optionally followed by additional instructions.

Parse the argument string: the first token is the file path; everything after is additional instructions (may be empty).

**Preliminary step — check file size:**
Before inspecting, run `ls -l` on the file to get its size. If the file is **larger than 100 MB**, set a `large_file` flag and pass `--large` to the inspection script (which reads only a small sample instead of the full file).

The inspection scripts live in `scripts/` next to this skill:
- `scripts/json_inspector.py`
- `scripts/parquet_inspector.py`
- `scripts/hdf5_inspector.py`

Each script accepts `<path>` and an optional `--large` flag, and uses `uv`'s inline script metadata to pull its own dependencies. Run them with `uv run <script> <path> [--large]` (note: **no** `python` — inline metadata is only applied when the script itself is the entry point).

Steps based on file extension:

**For `.jsonl` files:**
1. Read only the first line of the file (use the Read tool with `limit: 1`, or `head -n 1` — never load the entire file).
2. Parse it as JSON.
3. Report the keys found in that first entry.

**For `.json` files:**
Run `uv run scripts/json_inspector.py <path> [--large]` and show the output to the user. The script prints the top-level type, length/keys, and a preview of the first entries (truncated to 200 chars).

**For `.parquet` files:**
Run `uv run scripts/parquet_inspector.py <path> [--large]` and show the output. The script prints row/column counts, per-column dtypes with sample values, the first 3 rows, and the first row as a dict (values truncated to 200 chars). In `--large` mode it uses `pyarrow` metadata + the first row group only.

**For `.h5` / `.hdf5` files:**
Run `uv run scripts/hdf5_inspector.py <path> [--large]` and show the output. The script walks all groups and datasets, prints shapes/dtypes/attrs, and for each dataset previews the first item (or `[:3]` / `[0]` slice in `--large` mode). String values are truncated to 200 chars.

After the inspection, summarize what you found in plain language (structure, field names, example values).

If additional instructions were provided, follow them after completing the inspection above.

Rules:
- Do not modify the data file.
- Do not commit anything.
- Use `uv run` to execute Python code, not bare `python` or `python3`.

---
name: inspect-data
description: Inspect a data file (JSONL, JSON, Parquet, or HDF5) or a HuggingFace dataset to understand its structure. Usage: /inspect-data <file_path_or_dataset_id> [additional instructions]
---

Inspect a data file or a HuggingFace dataset to understand its structure. The argument is either a local file path or a HuggingFace dataset identifier, optionally followed by additional instructions.

Parse the argument string: the first token is the path or dataset id; everything after is additional instructions (may be empty).

**First — decide whether the target is a local file or a HuggingFace dataset:**
- If the argument looks like a dataset id (no file extension and either (a) contains `/` like `allenai/c4`, or (b) is a bare name like `squad` that does not exist as a local path), treat it as a HuggingFace dataset and follow the HuggingFace section below.
- Otherwise, treat it as a local file and follow the per-extension steps.

**Preliminary step for local files — check file size:**
Before inspecting, run `ls -l` on the file to get its size. If the file is **larger than 100 MB**, set a `large_file` flag and pass `--large` to the inspection script (which reads only a small sample instead of the full file).

The inspection scripts live in `scripts/` next to this skill:
- `scripts/json_inspector.py`
- `scripts/parquet_inspector.py`
- `scripts/hdf5_inspector.py`
- `scripts/hf_inspector.py`

Each script uses `uv`'s inline script metadata to pull its own dependencies. Run them with `uv run <script> ...` (note: **no** `python` — inline metadata is only applied when the script itself is the entry point).

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

**For HuggingFace datasets:**
Run `uv run scripts/hf_inspector.py <dataset_id> [--config CONFIG] [--split SPLIT] [-n N]` and show the output. The script uses `load_dataset_builder` to read metadata without downloading (description, homepage, license, splits with example counts, feature schema) and then streams the first N examples (default 3) from the chosen split. It never downloads the full dataset, so the `--large` flag is not used.

Guidance for HuggingFace inspection:
- The `--large` flag does **not** apply here.
- If the dataset has multiple configs, run the script first without `--config` to see the list, then re-run with one of them.
- If the user didn't specify a split, let the script default (it prefers `train`, then `validation`, then `test`).
- If streaming fails (some datasets don't support it), report the error to the user rather than retrying with a full download.

After the inspection, summarize what you found in plain language (structure, field names, example values).

If additional instructions were provided, follow them after completing the inspection above.

Rules:
- Do not modify the data file.
- Do not commit anything.
- Use `uv run` to execute Python code, not bare `python` or `python3`.

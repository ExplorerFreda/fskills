---
name: fix-precommit
description: Run pre-commit hooks and fix any errors they report
---

Run the pre-commit hooks and fix any errors they report.

Steps:
1. Run `uv run pre-commit run --all-files` and capture the output.
2. Read the output carefully. Identify every file and error flagged.
3. For each error, open the relevant file(s) and apply the necessary fixes:
   - Flake8 violations: fix the specific line(s) reported (line length, unused imports, whitespace, etc.)
   - Formatter changes (e.g. ruff-format, black): apply the formatting the hook expects
   - Any other hook failures: follow the specific guidance in the hook output
4. After fixing all issues, re-run `uv run pre-commit run --all-files` to verify all hooks pass.
5. If new errors appear in the re-run, repeat the fix-and-verify cycle until the run is fully clean.

Important rules while fixing:
- Follow the project style: single quotes for string literals, double quotes only for docstrings.
- Do not add unnecessary changes beyond what the hooks require.
- Do not commit anything.

# /// script
# requires-python = ">=3.10"
# dependencies = ["pandas", "pyarrow"]
# ///
"""Inspect a Parquet file.

Usage: uv run parquet_inspector.py <path> [--large]
"""

import argparse
import sys
from typing import Any

TRUNC = 200


def truncate(s: str, limit: int = TRUNC) -> str:
    """Truncate a string to at most ``limit`` characters, appending an ellipsis.

    Args:
        s: The string to truncate.
        limit: Maximum length before truncation.

    Returns:
        The original string if short enough, otherwise a truncated copy.
    """
    return s if len(s) <= limit else s[:limit] + '...'


def describe_columns(df: Any) -> None:
    """Print each column's dtype and a small sample of non-null values.

    Args:
        df: A pandas ``DataFrame``.
    """
    print('columns:')
    for col in df.columns:
        dtype = df[col].dtype
        sample = df[col].dropna().head(3).tolist()
        sample_repr = truncate(repr(sample))
        print(f'  - {col} ({dtype}): sample={sample_repr}')


def print_first_row_dict(df: Any) -> None:
    """Print the first row of a dataframe as a dict of truncated reprs.

    Args:
        df: A pandas ``DataFrame``.
    """
    if df.empty:
        print('(no rows)')
        return
    print('first row (as dict):')
    row = df.iloc[0].to_dict()
    for k, v in row.items():
        print(f'  {k!r}: {truncate(repr(v))}')


def inspect_normal(path: str) -> None:
    """Load a Parquet file fully and print a summary.

    Args:
        path: Path to the Parquet file.
    """
    import pandas as pd

    df = pd.read_parquet(path)
    print(f'rows: {len(df)}')
    print(f'cols: {len(df.columns)}')
    describe_columns(df)
    print('\nfirst 3 rows:')
    print(df.head(3).to_string())
    print()
    print_first_row_dict(df)


def inspect_large(path: str) -> None:
    """Summarize a large Parquet file using pyarrow metadata only.

    Args:
        path: Path to the Parquet file.
    """
    import pyarrow.parquet as pq

    print('(file too large to load fully; using pyarrow metadata + first row group)')

    meta = pq.read_metadata(path)
    schema = pq.read_schema(path)
    print(f'rows: {meta.num_rows}')
    print(f'row groups: {meta.num_row_groups}')
    print(f'cols: {len(schema.names)}')
    print('columns:')
    for name, field in zip(schema.names, schema):
        print(f'  - {name} ({field.type})')

    pf = pq.ParquetFile(path)
    if meta.num_row_groups == 0:
        print('(no row groups)')
        return
    df = pf.read_row_group(0).to_pandas().head(3)
    print('\nfirst 3 rows (from first row group):')
    print(df.to_string())
    print()
    print_first_row_dict(df)


def main() -> int:
    """Parse arguments and dispatch to the normal or large inspector.

    Returns:
        Process exit code.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--large', action='store_true',
                    help='avoid loading full file; read metadata + first row group only')
    args = ap.parse_args()

    if args.large:
        inspect_large(args.path)
    else:
        inspect_normal(args.path)
    return 0


if __name__ == '__main__':
    sys.exit(main())

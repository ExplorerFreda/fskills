# /// script
# requires-python = ">=3.10"
# dependencies = ["ijson"]
# ///
"""Inspect a JSON file.

Usage: uv run json_inspector.py <path> [--large]
"""

import argparse
import json
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


def preview_value(v: Any) -> str:
    """Return a truncated repr of a value for inline preview.

    Args:
        v: The value to preview.

    Returns:
        A truncated ``repr`` of ``v``.
    """
    return truncate(repr(v))


def inspect_normal(path: str) -> None:
    """Load the full JSON file and print a summary of its structure.

    Args:
        path: Path to the JSON file.
    """
    with open(path) as f:
        data = json.load(f)

    if isinstance(data, list):
        print('type: list')
        print(f'length: {len(data)}')
        if data:
            print('first entry:')
            print(json.dumps(data[0], indent=2, default=str))
    elif isinstance(data, dict):
        print('type: dict')
        print(f'keys: {list(data.keys())}')
        for k, v in data.items():
            print(f'  {k!r}: {preview_value(v)}')
    else:
        print(f'type: {type(data).__name__}')
        print(f'value: {preview_value(data)}')


def inspect_large(path: str) -> None:
    """Stream a large JSON file with ijson and print a summary.

    Args:
        path: Path to the JSON file.
    """
    import ijson

    print('(file too large to load fully; streaming with ijson)')

    with open(path, 'rb') as f:
        parser = ijson.parse(f)
        try:
            _, event, _ = next(parser)
        except StopIteration:
            print('empty file')
            return

    if event == 'start_array':
        print('type: list')
        with open(path, 'rb') as f:
            items = ijson.items(f, 'item')
            first = []
            for i, item in enumerate(items):
                if i >= 3:
                    break
                first.append(item)
        print(f'first {len(first)} entries:')
        for i, item in enumerate(first):
            print(f'[{i}]: {truncate(json.dumps(item, default=str))}')
    elif event == 'start_map':
        print('type: dict')
        with open(path, 'rb') as f:
            kvs = ijson.kvitems(f, '')
            first = []
            for i, (k, v) in enumerate(kvs):
                if i >= 3:
                    break
                first.append((k, v))
        print(f'first {len(first)} key-value pairs:')
        for k, v in first:
            print(f'  {k!r}: {truncate(json.dumps(v, default=str))}')
    else:
        print(f'top-level is a scalar (event={event!r}); reading fully')
        inspect_normal(path)


def main() -> int:
    """Parse arguments and dispatch to the normal or streaming inspector.

    Returns:
        Process exit code.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--large', action='store_true',
                    help='stream the file instead of loading it fully')
    args = ap.parse_args()

    if args.large:
        inspect_large(args.path)
    else:
        inspect_normal(args.path)
    return 0


if __name__ == '__main__':
    sys.exit(main())

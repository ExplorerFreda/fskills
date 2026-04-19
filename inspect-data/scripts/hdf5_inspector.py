# /// script
# requires-python = ">=3.10"
# dependencies = ["h5py"]
# ///
"""Inspect an HDF5 file.

Usage: uv run hdf5_inspector.py <path> [--large]
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


def decode_if_bytes(v: Any) -> Any:
    """Decode bytes values to UTF-8 strings; pass through other values.

    Args:
        v: Value to decode if it is bytes.

    Returns:
        Decoded string, ``repr`` of bytes on failure, or ``v`` unchanged.
    """
    if isinstance(v, bytes):
        try:
            return v.decode('utf-8', errors='replace')
        except Exception:
            return repr(v)
    return v


def format_value(v: Any) -> str:
    """Return a truncated repr suitable for printing a value.

    Args:
        v: The value to format.

    Returns:
        A truncated ``repr`` of ``v``.
    """
    return truncate(repr(decode_if_bytes(v)))


def print_attrs(obj: Any, indent: str = '  ') -> None:
    """Print HDF5 attributes of a group or dataset, if any.

    Args:
        obj: An h5py object with an ``attrs`` mapping.
        indent: Indentation string for output.
    """
    if not obj.attrs:
        return
    print(f'{indent}attrs:')
    for k, v in obj.attrs.items():
        print(f'{indent}  {k!r}: {format_value(v)}')


def inspect_dataset(name: str, ds: Any, large: bool) -> None:
    """Print shape, dtype, and a preview of an HDF5 dataset.

    Args:
        name: Full dataset path within the HDF5 file.
        ds: The h5py ``Dataset`` object.
        large: Whether the file is too large for full reads.
    """
    print(f'\ndataset: {name}')
    print(f'  shape: {ds.shape}')
    print(f'  dtype: {ds.dtype}')
    print_attrs(ds)

    shape = ds.shape
    dtype = ds.dtype

    # scalar / 0-d
    if shape == () or shape == (0,):
        if shape == ():
            val = ds[()]
            print(f'  value: {format_value(val)}')
        else:
            print('  value: (empty)')
        return

    # compound dtype (dict-like)
    if dtype.names is not None:
        print(f'  compound fields: {list(dtype.names)}')
        if large:
            row = ds[0]
        else:
            row = ds[0]
        print('  first record:')
        for name_ in dtype.names:
            print(f'    {name_!r}: {format_value(row[name_])}')
        return

    # 1-d
    if len(shape) == 1:
        n = shape[0]
        print(f'  length: {n}')
        if large:
            preview = ds[: min(3, n)]
            print(f'  first {len(preview)} items:')
            for i, v in enumerate(preview):
                print(f'    [{i}]: {format_value(v)}')
        else:
            first = ds[0]
            print(f'  first item: {format_value(first)}')
        return

    # multi-dimensional
    first = ds[0]
    print(f'  first element along axis 0 shape: {getattr(first, "shape", None)}')
    # Preview a flat sample to avoid massive prints.
    try:
        flat = first.reshape(-1) if hasattr(first, 'reshape') else first
        sample = flat[:5] if hasattr(flat, '__len__') else flat
        print(f'  sample: {format_value(sample)}')
    except Exception as e:
        print(f'  (could not preview: {e})')


def walk(h5file: Any, large: bool) -> None:
    """Walk an HDF5 file, printing groups and dataset previews.

    Args:
        h5file: An open h5py ``File`` object.
        large: Whether the file is too large for full reads.
    """
    import h5py

    print(f'file: {h5file.filename}')
    print_attrs(h5file, indent='')

    groups: list[str] = []
    datasets: list[tuple[str, h5py.Dataset]] = []

    def visitor(name: str, obj: Any) -> None:
        if isinstance(obj, h5py.Group):
            groups.append(name)
        elif isinstance(obj, h5py.Dataset):
            datasets.append((name, obj))

    h5file.visititems(visitor)

    print(f'\ngroups ({len(groups)}):')
    for g in groups:
        keys = list(h5file[g].keys())
        print(f'  - {g}  children={keys}')
        print_attrs(h5file[g], indent='    ')

    print(f'\ndatasets ({len(datasets)}):')
    for name, ds in datasets:
        inspect_dataset(name, ds, large=large)


def main() -> int:
    """Parse arguments and dispatch to the HDF5 walker.

    Returns:
        Process exit code.
    """
    import h5py

    ap = argparse.ArgumentParser()
    ap.add_argument('path')
    ap.add_argument('--large', action='store_true',
                    help='read only small slices instead of full datasets')
    args = ap.parse_args()

    if args.large:
        print('(file too large to load fully; reading small slices only)')

    with h5py.File(args.path, 'r') as f:
        walk(f, large=args.large)

    return 0


if __name__ == '__main__':
    sys.exit(main())

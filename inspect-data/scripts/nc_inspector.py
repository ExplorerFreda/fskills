# /// script
# requires-python = ">=3.10"
# dependencies = ["xarray", "numpy", "netcdf4"]
# ///
"""Inspect a NetCDF (.nc) file and report its structure and data content."""

import argparse

import numpy as np
import xarray as xr

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


def _print_dimensions(ds: xr.Dataset) -> None:
    print(f'dimensions: {dict(ds.sizes)}')


def _print_coordinates(ds: xr.Dataset) -> None:
    print(f'\ncoordinates ({len(ds.coords)}):')
    for name, coord in ds.coords.items():
        attrs = coord.attrs
        units = attrs.get('units', '')
        dtype = str(coord.dtype)
        shape = coord.shape
        vals = coord.values

        if vals.ndim == 0:
            preview = f'scalar={vals.item()}'
        elif vals.ndim == 1 and np.issubdtype(vals.dtype, np.datetime64):
            preview = f'range=[{str(vals[0])[:19]}, {str(vals[-1])[:19]}]'
            if len(vals) > 1:
                step_ns = int(
                    (vals[1].astype('datetime64[ns]') - vals[0].astype('datetime64[ns]'))
                    .astype(np.int64)
                )
                step_h = step_ns / 3_600_000_000_000
                preview += f', step={step_h:.4g}h'
        elif vals.ndim == 1 and np.issubdtype(vals.dtype, np.number):
            if len(vals) > 1:
                step = float(vals[1] - vals[0])
                preview = (
                    f'range=[{float(vals.min()):.6g}, {float(vals.max()):.6g}]'
                    f', step={step:.6g}'
                )
            else:
                preview = f'value={float(vals[0]):.6g}'
        else:
            preview = truncate(repr(vals.flat[0]) if vals.size else '(empty)')

        units_str = f', units={units!r}' if units else ''
        print(f'  {name}: dtype={dtype}, shape={shape}{units_str} -- {preview}')


def _print_global_attrs(ds: xr.Dataset) -> None:
    if not ds.attrs:
        return
    print('\nglobal attributes:')
    for k, v in ds.attrs.items():
        print(f'  {k}: {truncate(str(v))}')


def _print_variable_header(name: str, var: xr.DataArray) -> None:
    attrs = var.attrs
    units = attrs.get('units', '')
    long_name = attrs.get('long_name', '')
    print(f'  {name}: dtype={var.dtype}, shape={var.shape}, dims={var.dims}')
    if units:
        print(f'    units: {units}')
    if long_name:
        print(f'    long_name: {long_name}')


def _variable_stats_full(var: xr.DataArray) -> None:
    arr = var.values.astype(np.float64)
    nan_count = int(np.isnan(arr).sum())
    finite = arr[np.isfinite(arr)]
    if finite.size:
        print(
            f'    range: [{float(finite.min()):.6g}, {float(finite.max()):.6g}]'
            f', mean={float(finite.mean()):.6g}, NaN={nan_count}'
        )
    else:
        print(f'    (all values are non-finite, NaN={nan_count})')


def _variable_stats_sample(var: xr.DataArray) -> None:
    time_dim = next(
        (d for d in ('valid_time', 'time') if d in var.dims),
        None,
    )
    if time_dim is None:
        return
    try:
        sample = var.isel({time_dim: 0}).values.astype(np.float64)
        finite = sample[np.isfinite(sample)]
        if finite.size:
            print(
                f'    sample (t=0): range=[{float(finite.min()):.6g},'
                f' {float(finite.max()):.6g}], mean={float(finite.mean()):.6g}'
            )
    except Exception as exc:
        print(f'    (sample read failed: {exc})')


def inspect_normal(path: str) -> None:
    """Load a NetCDF file fully and print dimensions, coordinates, and variable stats.

    Args:
        path: Path to the .nc file.
    """
    ds = xr.open_dataset(path)
    _print_dimensions(ds)
    _print_coordinates(ds)
    print(f'\ndata variables ({len(ds.data_vars)}):')
    for name, var in ds.data_vars.items():
        _print_variable_header(name, var)
        _variable_stats_full(var)
    _print_global_attrs(ds)
    ds.close()


def inspect_large(path: str) -> None:
    """Summarize a large NetCDF file using a single-timestep sample per variable.

    Args:
        path: Path to the .nc file.
    """
    ds = xr.open_dataset(path)
    _print_dimensions(ds)
    _print_coordinates(ds)
    print(f'\ndata variables ({len(ds.data_vars)}):')
    for name, var in ds.data_vars.items():
        _print_variable_header(name, var)
        _variable_stats_sample(var)
    _print_global_attrs(ds)
    ds.close()


def main() -> None:
    """Parse arguments and dispatch to the normal or large inspector."""
    parser = argparse.ArgumentParser(
        description='Inspect a NetCDF (.nc) file.',
    )
    parser.add_argument('path', help='Path to the .nc file.')
    parser.add_argument(
        '--large',
        action='store_true',
        help='Large-file mode: skip full data load, show a single-timestep sample.',
    )
    args = parser.parse_args()

    if args.large:
        inspect_large(args.path)
    else:
        inspect_normal(args.path)


if __name__ == '__main__':
    main()

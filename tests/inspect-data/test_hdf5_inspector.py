"""Tests for inspect-data/scripts/hdf5_inspector.py."""

import sys
from pathlib import Path

import hdf5_inspector
import pytest


def test_decode_if_bytes_decodes_bytes() -> None:
    """Bytes input is decoded to UTF-8 string."""
    assert hdf5_inspector.decode_if_bytes(b'hello') == 'hello'


def test_decode_if_bytes_passes_through_non_bytes() -> None:
    """Non-bytes values are returned unchanged."""
    assert hdf5_inspector.decode_if_bytes(42) == 42
    assert hdf5_inspector.decode_if_bytes('x') == 'x'


def test_format_value_truncates_long_repr() -> None:
    """Values with long reprs are truncated with '...'."""
    out = hdf5_inspector.format_value('x' * 500)
    assert out.endswith('...')


def test_main_walks_file(
    sample_h5_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() walks the file and lists groups and datasets.

    Args:
        sample_h5_path: Fixture path to a small HDF5 file.
        monkeypatch: pytest monkeypatch fixture.
        capsys: pytest stdout/stderr capture fixture.
    """
    monkeypatch.setattr(sys, 'argv', ['hdf5_inspector', str(sample_h5_path)])
    assert hdf5_inspector.main() == 0
    out = capsys.readouterr().out
    assert 'group_a' in out
    assert 'numbers' in out
    assert "'note'" in out


def test_main_large_flag_runs(
    sample_h5_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--large mode uses small slices and completes.

    Args:
        sample_h5_path: Fixture path to a small HDF5 file.
        monkeypatch: pytest monkeypatch fixture.
        capsys: pytest stdout/stderr capture fixture.
    """
    monkeypatch.setattr(
        sys, 'argv', ['hdf5_inspector', str(sample_h5_path), '--large']
    )
    assert hdf5_inspector.main() == 0
    out = capsys.readouterr().out
    assert 'group_a' in out
    assert 'numbers' in out

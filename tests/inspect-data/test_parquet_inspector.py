"""Tests for inspect-data/scripts/parquet_inspector.py."""

import sys
from pathlib import Path

import parquet_inspector
import pytest


def test_describe_columns_emits_column_lines(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """describe_columns prints one line per column with dtype and sample.

    Args:
        capsys: pytest stdout/stderr capture fixture.
    """
    import pandas as pd

    df = pd.DataFrame({'id': [1, 2], 'name': ['a', 'b']})
    parquet_inspector.describe_columns(df)
    out = capsys.readouterr().out
    assert 'columns:' in out
    assert '- id' in out
    assert '- name' in out


def test_print_first_row_dict_on_empty_df(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """An empty dataframe prints '(no rows)'.

    Args:
        capsys: pytest stdout/stderr capture fixture.
    """
    import pandas as pd

    parquet_inspector.print_first_row_dict(pd.DataFrame({'id': []}))
    assert '(no rows)' in capsys.readouterr().out


def test_print_first_row_dict_truncates_long_values(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Values longer than TRUNC get the '...' suffix.

    Args:
        capsys: pytest stdout/stderr capture fixture.
    """
    import pandas as pd

    df = pd.DataFrame({'blob': ['x' * 500]})
    parquet_inspector.print_first_row_dict(df)
    out = capsys.readouterr().out
    assert '...' in out


def test_main_reports_rows_and_columns(
    sample_parquet_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() in normal mode reports row and column counts.

    Args:
        sample_parquet_path: Fixture path to a small Parquet file.
        monkeypatch: pytest monkeypatch fixture.
        capsys: pytest stdout/stderr capture fixture.
    """
    monkeypatch.setattr(
        sys, 'argv', ['parquet_inspector', str(sample_parquet_path)]
    )
    assert parquet_inspector.main() == 0
    out = capsys.readouterr().out
    assert 'rows: 3' in out
    assert 'cols: 2' in out


def test_main_large_flag_runs(
    sample_parquet_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--large mode reads metadata and completes.

    Args:
        sample_parquet_path: Fixture path to a small Parquet file.
        monkeypatch: pytest monkeypatch fixture.
        capsys: pytest stdout/stderr capture fixture.
    """
    monkeypatch.setattr(
        sys, 'argv', ['parquet_inspector', str(sample_parquet_path), '--large']
    )
    assert parquet_inspector.main() == 0
    out = capsys.readouterr().out
    assert 'rows: 3' in out

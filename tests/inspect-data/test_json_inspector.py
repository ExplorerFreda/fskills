"""Tests for inspect-data/scripts/json_inspector.py."""

import sys
from pathlib import Path

import json_inspector
import pytest


def test_truncate_short_string_passthrough() -> None:
    """Short inputs are returned unchanged."""
    assert json_inspector.truncate('hi', 10) == 'hi'


def test_truncate_long_string_appends_ellipsis() -> None:
    """Strings longer than the limit are truncated with a trailing '...'."""
    out = json_inspector.truncate('x' * 300, 200)
    assert out.endswith('...')
    assert len(out) == 203


def test_preview_value_wraps_repr() -> None:
    """preview_value returns the repr of its argument (when short)."""
    assert json_inspector.preview_value({'a': 1}) == "{'a': 1}"


def test_main_prints_top_level_keys_for_dict(
    sample_json_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """main() on a dict-valued JSON file reports type and keys.

    Args:
        sample_json_path: Fixture path to a small JSON file.
        monkeypatch: pytest monkeypatch fixture.
        capsys: pytest stdout/stderr capture fixture.
    """
    monkeypatch.setattr(sys, 'argv', ['json_inspector', str(sample_json_path)])
    assert json_inspector.main() == 0
    out = capsys.readouterr().out
    assert 'type: dict' in out
    assert "'name'" in out
    assert "'items'" in out


def test_main_large_flag_runs(
    sample_json_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """--large mode runs against a small dict file and completes.

    Args:
        sample_json_path: Fixture path to a small JSON file.
        monkeypatch: pytest monkeypatch fixture.
        capsys: pytest stdout/stderr capture fixture.
    """
    monkeypatch.setattr(
        sys, 'argv', ['json_inspector', str(sample_json_path), '--large']
    )
    assert json_inspector.main() == 0
    out = capsys.readouterr().out
    assert 'type: dict' in out

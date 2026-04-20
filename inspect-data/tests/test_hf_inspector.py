# /// script
# requires-python = ">=3.10"
# dependencies = ["pytest"]
# ///
"""Tests for hf_inspector.

Run as a script:
    uv run tests/test_hf_inspector.py
Or with pytest directly (once pytest is installed):
    pytest tests/test_hf_inspector.py -v
"""

import sys
import types
from pathlib import Path
from types import SimpleNamespace

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / 'scripts'
sys.path.insert(0, str(SCRIPTS_DIR))

import hf_inspector  # noqa: E402


# --- helpers ---------------------------------------------------------------

def _split(num: int | None) -> SimpleNamespace:
    """Build a fake ``SplitInfo`` with just ``num_examples``."""
    return SimpleNamespace(num_examples=num)


def _install_fake_datasets(
    monkeypatch: pytest.MonkeyPatch,
    *,
    configs: list[str] | None = None,
    configs_error: Exception | None = None,
    builder_info: SimpleNamespace | None = None,
    builder_error: Exception | None = None,
    stream_items: list | None = None,
    stream_error: Exception | None = None,
    iter_error: Exception | None = None,
) -> list[dict]:
    """Install a fake ``datasets`` module into ``sys.modules``.

    Returns a list that records calls to ``load_dataset`` (one dict per call)
    so tests can assert the right args were passed through.
    """
    calls: list[dict] = []

    def fake_get_dataset_config_names(dataset_id: str) -> list[str]:
        if configs_error is not None:
            raise configs_error
        return list(configs or [])

    def fake_load_dataset_builder(dataset_id: str, name: str | None = None):
        if builder_error is not None:
            raise builder_error
        return SimpleNamespace(info=builder_info)

    def fake_load_dataset(dataset_id, name=None, split=None, streaming=False):
        calls.append({
            'dataset_id': dataset_id,
            'name': name,
            'split': split,
            'streaming': streaming,
        })
        if stream_error is not None:
            raise stream_error

        items = list(stream_items or [])

        def gen():
            for item in items:
                yield item
            if iter_error is not None:
                raise iter_error

        return gen()

    mod = types.ModuleType('datasets')
    mod.get_dataset_config_names = fake_get_dataset_config_names
    mod.load_dataset_builder = fake_load_dataset_builder
    mod.load_dataset = fake_load_dataset
    monkeypatch.setitem(sys.modules, 'datasets', mod)
    return calls


# --- truncate --------------------------------------------------------------

class TestTruncate:
    def test_short_string_unchanged(self):
        assert hf_inspector.truncate('hi') == 'hi'

    def test_at_limit_unchanged(self):
        s = 'x' * hf_inspector.TRUNC
        assert hf_inspector.truncate(s) == s

    def test_over_limit_truncated(self):
        s = 'x' * (hf_inspector.TRUNC + 10)
        out = hf_inspector.truncate(s)
        assert out.endswith('...')
        assert len(out) == hf_inspector.TRUNC + 3

    def test_custom_limit(self):
        assert hf_inspector.truncate('abcdef', limit=3) == 'abc...'


# --- pick_split ------------------------------------------------------------

class TestPickSplit:
    def test_requested_wins(self):
        assert hf_inspector.pick_split('custom', {'train': None}) == 'custom'

    def test_none_splits(self):
        assert hf_inspector.pick_split(None, None) is None

    def test_empty_splits(self):
        assert hf_inspector.pick_split(None, {}) is None

    def test_prefers_train(self):
        splits = {'test': None, 'validation': None, 'train': None}
        assert hf_inspector.pick_split(None, splits) == 'train'

    def test_falls_back_to_validation(self):
        splits = {'test': None, 'validation': None}
        assert hf_inspector.pick_split(None, splits) == 'validation'

    def test_falls_back_to_test(self):
        assert hf_inspector.pick_split(None, {'test': None}) == 'test'

    def test_unusual_split_name(self):
        assert hf_inspector.pick_split(None, {'dev': None}) == 'dev'


# --- print_splits ----------------------------------------------------------

class TestPrintSplits:
    def test_none(self, capsys):
        hf_inspector.print_splits(None)
        assert '(none declared)' in capsys.readouterr().out

    def test_empty(self, capsys):
        hf_inspector.print_splits({})
        assert '(none declared)' in capsys.readouterr().out

    def test_formats_counts_with_commas(self, capsys):
        hf_inspector.print_splits({'train': _split(12345), 'test': _split(7)})
        out = capsys.readouterr().out
        assert '- train: 12,345 examples' in out
        assert '- test: 7 examples' in out

    def test_unknown_num_examples(self, capsys):
        hf_inspector.print_splits({'train': _split(None)})
        assert '- train: unknown examples' in capsys.readouterr().out


# --- print_features --------------------------------------------------------

class TestPrintFeatures:
    def test_none(self, capsys):
        hf_inspector.print_features(None)
        assert 'unknown' in capsys.readouterr().out

    def test_prints_each_feature(self, capsys):
        hf_inspector.print_features({'text': 'Value(string)', 'label': 'ClassLabel'})
        out = capsys.readouterr().out
        assert '- text: Value(string)' in out
        assert '- label: ClassLabel' in out


# --- stream_examples -------------------------------------------------------

class TestStreamExamples:
    def test_prints_dict_examples(self, capsys, monkeypatch):
        calls = _install_fake_datasets(
            monkeypatch,
            stream_items=[{'text': 'hello', 'label': 0}, {'text': 'world', 'label': 1}],
        )
        hf_inspector.stream_examples('fake/ds', None, 'train', n=2)
        out = capsys.readouterr().out
        assert "'text': 'hello'" in out
        assert "'label': 0" in out
        assert "'text': 'world'" in out
        assert calls == [{
            'dataset_id': 'fake/ds',
            'name': None,
            'split': 'train',
            'streaming': True,
        }]

    def test_respects_n(self, capsys, monkeypatch):
        _install_fake_datasets(
            monkeypatch,
            stream_items=[{'x': i} for i in range(10)],
        )
        hf_inspector.stream_examples('fake/ds', None, 'train', n=2)
        out = capsys.readouterr().out
        assert '[0]:' in out
        assert '[1]:' in out
        assert '[2]:' not in out

    def test_passes_config_through(self, monkeypatch):
        calls = _install_fake_datasets(monkeypatch, stream_items=[])
        hf_inspector.stream_examples('fake/ds', 'en', 'validation', n=3)
        assert calls[0]['name'] == 'en'
        assert calls[0]['split'] == 'validation'

    def test_scalar_examples(self, capsys, monkeypatch):
        _install_fake_datasets(monkeypatch, stream_items=['abc', 'def'])
        hf_inspector.stream_examples('fake/ds', None, 'train', n=2)
        out = capsys.readouterr().out
        assert "'abc'" in out and "'def'" in out

    def test_values_are_truncated(self, capsys, monkeypatch):
        long = 'x' * (hf_inspector.TRUNC + 50)
        _install_fake_datasets(monkeypatch, stream_items=[{'text': long}])
        hf_inspector.stream_examples('fake/ds', None, 'train', n=1)
        out = capsys.readouterr().out
        assert '...' in out
        # full string must not be present
        assert ('x' * (hf_inspector.TRUNC + 10)) not in out

    def test_load_failure_reported(self, capsys, monkeypatch):
        _install_fake_datasets(monkeypatch, stream_error=RuntimeError('nope'))
        hf_inspector.stream_examples('fake/ds', None, 'train', n=3)
        out = capsys.readouterr().out
        assert 'streaming failed' in out
        assert 'RuntimeError' in out and 'nope' in out

    def test_iteration_failure_reported(self, capsys, monkeypatch):
        _install_fake_datasets(
            monkeypatch,
            stream_items=[{'x': 1}],
            iter_error=RuntimeError('mid-stream'),
        )
        hf_inspector.stream_examples('fake/ds', None, 'train', n=5)
        out = capsys.readouterr().out
        assert "'x': 1" in out
        assert 'iteration stopped' in out
        assert 'mid-stream' in out

    def test_no_examples_message(self, capsys, monkeypatch):
        _install_fake_datasets(monkeypatch, stream_items=[])
        hf_inspector.stream_examples('fake/ds', None, 'train', n=3)
        assert '(no examples returned)' in capsys.readouterr().out


# --- inspect ---------------------------------------------------------------

def _info(**kw) -> SimpleNamespace:
    """Build a fake builder.info with sensible defaults."""
    return SimpleNamespace(
        description=kw.get('description', ''),
        citation=kw.get('citation', ''),
        homepage=kw.get('homepage', ''),
        license=kw.get('license', ''),
        splits=kw.get('splits', {'train': _split(100)}),
        features=kw.get('features', {'text': 'Value(string)'}),
    )


class TestInspect:
    def test_happy_path(self, capsys, monkeypatch):
        _install_fake_datasets(
            monkeypatch,
            configs=['default'],
            builder_info=_info(
                description='   A test dataset.  ',
                homepage='https://example.com',
                license='MIT',
                splits={'train': _split(500), 'test': _split(100)},
                features={'text': 'Value(string)', 'label': 'ClassLabel'},
            ),
            stream_items=[{'text': 'hi', 'label': 0}],
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'dataset: fake/ds' in out
        assert "available configs: ['default']" in out
        assert 'description: A test dataset.' in out
        assert 'homepage: https://example.com' in out
        assert 'license: MIT' in out
        assert '- train: 500 examples' in out
        assert '- text: Value(string)' in out
        assert "'text': 'hi'" in out

    def test_picks_first_config_when_multiple_and_none_requested(self, capsys, monkeypatch):
        calls = _install_fake_datasets(
            monkeypatch,
            configs=['en', 'fr', 'de'],
            builder_info=_info(),
            stream_items=[],
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'multiple configs available' in out
        assert "using 'en'" in out
        assert 'config: en' in out
        # the streaming call should have used the auto-picked config
        assert calls and calls[0]['name'] == 'en'

    def test_explicit_config_skips_auto_pick(self, capsys, monkeypatch):
        calls = _install_fake_datasets(
            monkeypatch,
            configs=['en', 'fr'],
            builder_info=_info(),
            stream_items=[],
        )
        hf_inspector.inspect('fake/ds', config='fr', split=None, n=1)
        out = capsys.readouterr().out
        assert 'multiple configs available' not in out
        assert 'config: fr' in out
        assert calls[0]['name'] == 'fr'

    def test_default_config_single_is_not_announced(self, capsys, monkeypatch):
        _install_fake_datasets(
            monkeypatch,
            configs=['default'],
            builder_info=_info(),
            stream_items=[],
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'multiple configs available' not in out

    def test_builder_failure_is_reported(self, capsys, monkeypatch):
        _install_fake_datasets(
            monkeypatch,
            configs=[],
            builder_error=RuntimeError('offline'),
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'load_dataset_builder failed' in out
        assert 'offline' in out

    def test_configs_listing_failure_is_tolerated(self, capsys, monkeypatch):
        _install_fake_datasets(
            monkeypatch,
            configs_error=RuntimeError('no network'),
            builder_info=_info(splits={}),
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'could not list configs' in out
        # should still proceed to builder / splits sections
        assert 'splits: (none declared)' in out

    def test_no_splits_skips_streaming(self, capsys, monkeypatch):
        calls = _install_fake_datasets(
            monkeypatch,
            configs=['default'],
            builder_info=_info(splits={}),
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'no split available to stream' in out
        assert calls == []  # load_dataset must not be called

    def test_explicit_split_is_used(self, capsys, monkeypatch):
        calls = _install_fake_datasets(
            monkeypatch,
            configs=['default'],
            builder_info=_info(splits={'train': _split(10), 'test': _split(5)}),
            stream_items=[],
        )
        hf_inspector.inspect('fake/ds', config=None, split='test', n=1)
        assert calls[0]['split'] == 'test'


if __name__ == '__main__':
    sys.exit(pytest.main([__file__, '-v']))

"""Tests for hf_inspector."""

import sys
import types
from collections.abc import Iterator
from types import SimpleNamespace

import hf_inspector
import pytest


def _split(num: int | None) -> SimpleNamespace:
    """Build a fake ``SplitInfo`` with just ``num_examples``.

    Args:
        num: Number of examples for the split, or ``None``.

    Returns:
        A ``SimpleNamespace`` with a ``num_examples`` attribute.
    """
    return SimpleNamespace(num_examples=num)


def _info(
    description: str = '',
    citation: str = '',
    homepage: str = '',
    license_: str = '',
    splits: dict | None = None,
    features: dict | None = None,
) -> SimpleNamespace:
    """Build a fake ``builder.info`` with sensible defaults.

    Args:
        description: Dataset description text.
        citation: Citation text.
        homepage: Homepage URL.
        license_: License string (named ``license_`` to avoid the builtin).
        splits: Mapping from split name to ``SplitInfo``.
        features: Feature schema mapping.

    Returns:
        A ``SimpleNamespace`` that mimics ``datasets.DatasetInfo``.
    """
    return SimpleNamespace(
        description=description,
        citation=citation,
        homepage=homepage,
        license=license_,
        splits={'train': _split(100)} if splits is None else splits,
        features={'text': 'Value(string)'} if features is None else features,
    )


def _install_fake_datasets(
    monkeypatch: pytest.MonkeyPatch,
    configs: list[str] | None = None,
    configs_error: Exception | None = None,
    builder_info: SimpleNamespace | None = None,
    builder_error: Exception | None = None,
    stream_items: list | None = None,
    stream_error: Exception | None = None,
    iter_error: Exception | None = None,
) -> list[dict]:
    """Install a fake ``datasets`` module into ``sys.modules``.

    Args:
        monkeypatch: The pytest ``monkeypatch`` fixture.
        configs: Configs to return from ``get_dataset_config_names``.
        configs_error: Exception to raise from ``get_dataset_config_names``.
        builder_info: Info namespace returned by ``load_dataset_builder``.
        builder_error: Exception to raise from ``load_dataset_builder``.
        stream_items: Items the fake ``load_dataset`` generator yields.
        stream_error: Exception to raise from ``load_dataset`` at call time.
        iter_error: Exception to raise from the generator after yielding.

    Returns:
        A list that records each call to ``load_dataset`` as a dict, so tests
        can assert that the expected args were forwarded.
    """
    calls: list[dict] = []

    def fake_get_dataset_config_names(dataset_id: str) -> list[str]:
        """Fake ``datasets.get_dataset_config_names``.

        Args:
            dataset_id: Dataset identifier (ignored).

        Returns:
            The configured list of config names.

        Raises:
            configs_error: The exception supplied via the outer call.
        """
        if configs_error is not None:
            raise configs_error
        return list(configs or [])

    def fake_load_dataset_builder(
        dataset_id: str,
        name: str | None = None,
    ) -> SimpleNamespace:
        """Fake ``datasets.load_dataset_builder``.

        Args:
            dataset_id: Dataset identifier (ignored).
            name: Config name (ignored).

        Returns:
            A namespace with an ``info`` attribute set to ``builder_info``.

        Raises:
            builder_error: The exception supplied via the outer call.
        """
        if builder_error is not None:
            raise builder_error
        return SimpleNamespace(info=builder_info)

    def fake_load_dataset(
        dataset_id: str,
        name: str | None = None,
        split: str | None = None,
        streaming: bool = False,
    ) -> Iterator:
        """Fake ``datasets.load_dataset``.

        Args:
            dataset_id: Dataset identifier.
            name: Config name.
            split: Split name.
            streaming: Whether streaming was requested.

        Returns:
            A generator that yields ``stream_items`` then optionally raises.

        Raises:
            stream_error: The exception supplied via the outer call.
        """
        calls.append({
            'dataset_id': dataset_id,
            'name': name,
            'split': split,
            'streaming': streaming,
        })
        if stream_error is not None:
            raise stream_error

        items = list(stream_items or [])

        def gen() -> Iterator:
            """Yield the recorded items, then optionally raise.

            Yields:
                The next item from ``stream_items``.

            Raises:
                iter_error: The exception supplied via the outer call.
            """
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


class TestTruncate:
    """Tests for ``hf_inspector.truncate``."""

    def test_short_string_unchanged(self) -> None:
        """Short strings pass through unchanged."""
        assert hf_inspector.truncate('hi') == 'hi'

    def test_at_limit_unchanged(self) -> None:
        """A string exactly at the limit is not truncated."""
        s = 'x' * hf_inspector.TRUNC
        assert hf_inspector.truncate(s) == s

    def test_over_limit_truncated(self) -> None:
        """Strings above the limit get the ellipsis suffix."""
        s = 'x' * (hf_inspector.TRUNC + 10)
        out = hf_inspector.truncate(s)
        assert out.endswith('...')
        assert len(out) == hf_inspector.TRUNC + 3

    def test_custom_limit(self) -> None:
        """The ``limit`` argument overrides the default."""
        assert hf_inspector.truncate('abcdef', limit=3) == 'abc...'


class TestPickSplit:
    """Tests for ``hf_inspector.pick_split``."""

    def test_requested_wins(self) -> None:
        """An explicit request always wins, even over ``train``."""
        assert hf_inspector.pick_split('custom', {'train': None}) == 'custom'

    def test_none_splits(self) -> None:
        """``None`` splits returns ``None``."""
        assert hf_inspector.pick_split(None, None) is None

    def test_empty_splits(self) -> None:
        """An empty splits mapping returns ``None``."""
        assert hf_inspector.pick_split(None, {}) is None

    def test_prefers_train(self) -> None:
        """``train`` is preferred when all three canonical splits exist."""
        splits = {'test': None, 'validation': None, 'train': None}
        assert hf_inspector.pick_split(None, splits) == 'train'

    def test_falls_back_to_validation(self) -> None:
        """``validation`` wins when ``train`` is absent."""
        splits = {'test': None, 'validation': None}
        assert hf_inspector.pick_split(None, splits) == 'validation'

    def test_falls_back_to_test(self) -> None:
        """``test`` wins when neither ``train`` nor ``validation`` exists."""
        assert hf_inspector.pick_split(None, {'test': None}) == 'test'

    def test_unusual_split_name(self) -> None:
        """Any other split name is picked when it's the only option."""
        assert hf_inspector.pick_split(None, {'dev': None}) == 'dev'


class TestPrintSplits:
    """Tests for ``hf_inspector.print_splits``."""

    def test_none(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``None`` prints a ``(none declared)`` notice.

        Args:
            capsys: Captures stdout/stderr.
        """
        hf_inspector.print_splits(None)
        assert '(none declared)' in capsys.readouterr().out

    def test_empty(self, capsys: pytest.CaptureFixture[str]) -> None:
        """An empty mapping prints a ``(none declared)`` notice.

        Args:
            capsys: Captures stdout/stderr.
        """
        hf_inspector.print_splits({})
        assert '(none declared)' in capsys.readouterr().out

    def test_formats_counts_with_commas(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Large example counts use comma grouping.

        Args:
            capsys: Captures stdout/stderr.
        """
        hf_inspector.print_splits({'train': _split(12345), 'test': _split(7)})
        out = capsys.readouterr().out
        assert '- train: 12,345 examples' in out
        assert '- test: 7 examples' in out

    def test_unknown_num_examples(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Splits without a known count show ``unknown``.

        Args:
            capsys: Captures stdout/stderr.
        """
        hf_inspector.print_splits({'train': _split(None)})
        assert '- train: unknown examples' in capsys.readouterr().out


class TestPrintFeatures:
    """Tests for ``hf_inspector.print_features``."""

    def test_none(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``None`` prints the ``unknown`` notice.

        Args:
            capsys: Captures stdout/stderr.
        """
        hf_inspector.print_features(None)
        assert 'unknown' in capsys.readouterr().out

    def test_prints_each_feature(
        self,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Every feature name and type appears in the output.

        Args:
            capsys: Captures stdout/stderr.
        """
        hf_inspector.print_features(
            {'text': 'Value(string)', 'label': 'ClassLabel'},
        )
        out = capsys.readouterr().out
        assert '- text: Value(string)' in out
        assert '- label: ClassLabel' in out


class TestStreamExamples:
    """Tests for ``hf_inspector.stream_examples``."""

    def test_prints_dict_examples(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Dict examples print their keys and truncated values.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        calls = _install_fake_datasets(
            monkeypatch,
            stream_items=[
                {'text': 'hello', 'label': 0},
                {'text': 'world', 'label': 1},
            ],
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

    def test_respects_n(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Only the first ``n`` items are printed.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        _install_fake_datasets(
            monkeypatch,
            stream_items=[{'x': i} for i in range(10)],
        )
        hf_inspector.stream_examples('fake/ds', None, 'train', n=2)
        out = capsys.readouterr().out
        assert '[0]:' in out
        assert '[1]:' in out
        assert '[2]:' not in out

    def test_passes_config_through(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Config and split are forwarded to ``load_dataset``.

        Args:
            monkeypatch: The pytest monkeypatch fixture.
        """
        calls = _install_fake_datasets(monkeypatch, stream_items=[])
        hf_inspector.stream_examples('fake/ds', 'en', 'validation', n=3)
        assert calls[0]['name'] == 'en'
        assert calls[0]['split'] == 'validation'

    def test_scalar_examples(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Non-dict examples are printed via ``repr``.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        _install_fake_datasets(monkeypatch, stream_items=['abc', 'def'])
        hf_inspector.stream_examples('fake/ds', None, 'train', n=2)
        out = capsys.readouterr().out
        assert "'abc'" in out and "'def'" in out

    def test_values_are_truncated(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Long values are truncated in the output.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        long = 'x' * (hf_inspector.TRUNC + 50)
        _install_fake_datasets(monkeypatch, stream_items=[{'text': long}])
        hf_inspector.stream_examples('fake/ds', None, 'train', n=1)
        out = capsys.readouterr().out
        assert '...' in out
        assert ('x' * (hf_inspector.TRUNC + 10)) not in out

    def test_load_failure_reported(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A ``load_dataset`` error is caught and reported.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        _install_fake_datasets(monkeypatch, stream_error=RuntimeError('nope'))
        hf_inspector.stream_examples('fake/ds', None, 'train', n=3)
        out = capsys.readouterr().out
        assert 'streaming failed' in out
        assert 'RuntimeError' in out and 'nope' in out

    def test_iteration_failure_reported(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A mid-stream error is caught after partial output.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
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

    def test_no_examples_message(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Empty streams print the ``no examples returned`` message.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        _install_fake_datasets(monkeypatch, stream_items=[])
        hf_inspector.stream_examples('fake/ds', None, 'train', n=3)
        assert '(no examples returned)' in capsys.readouterr().out


class TestInspect:
    """Tests for ``hf_inspector.inspect``."""

    def test_happy_path(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """All major sections appear when builder info is fully populated.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        _install_fake_datasets(
            monkeypatch,
            configs=['default'],
            builder_info=_info(
                description='   A test dataset.  ',
                homepage='https://example.com',
                license_='MIT',
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

    def test_picks_first_config_when_multiple_and_none_requested(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """When multiple non-``default`` configs exist, the first is used.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
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
        assert calls and calls[0]['name'] == 'en'

    def test_explicit_config_skips_auto_pick(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An explicit ``--config`` suppresses the auto-pick notice.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
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

    def test_default_config_single_is_not_announced(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A single ``default`` config does not trigger the multi notice.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        _install_fake_datasets(
            monkeypatch,
            configs=['default'],
            builder_info=_info(),
            stream_items=[],
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'multiple configs available' not in out

    def test_builder_failure_is_reported(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Builder errors are caught and surfaced to the user.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        _install_fake_datasets(
            monkeypatch,
            configs=[],
            builder_error=RuntimeError('offline'),
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'load_dataset_builder failed' in out
        assert 'offline' in out

    def test_configs_listing_failure_is_tolerated(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """A failure listing configs does not abort the inspection.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        _install_fake_datasets(
            monkeypatch,
            configs_error=RuntimeError('no network'),
            builder_info=_info(splits={}),
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'could not list configs' in out
        assert 'splits: (none declared)' in out

    def test_no_splits_skips_streaming(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """If the builder reports no splits, streaming is skipped.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        calls = _install_fake_datasets(
            monkeypatch,
            configs=['default'],
            builder_info=_info(splits={}),
        )
        hf_inspector.inspect('fake/ds', config=None, split=None, n=1)
        out = capsys.readouterr().out
        assert 'no split available to stream' in out
        assert calls == []

    def test_explicit_split_is_used(
        self,
        capsys: pytest.CaptureFixture[str],
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """An explicit ``--split`` is forwarded to the streaming call.

        Args:
            capsys: Captures stdout/stderr.
            monkeypatch: The pytest monkeypatch fixture.
        """
        calls = _install_fake_datasets(
            monkeypatch,
            configs=['default'],
            builder_info=_info(
                splits={'train': _split(10), 'test': _split(5)},
            ),
            stream_items=[],
        )
        hf_inspector.inspect('fake/ds', config=None, split='test', n=1)
        assert calls[0]['split'] == 'test'

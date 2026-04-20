# /// script
# requires-python = ">=3.10"
# dependencies = ["datasets"]
# ///
"""Inspect a HuggingFace dataset without downloading it fully.

Usage: uv run hf_inspector.py <dataset_id> [--config CONFIG] [--split SPLIT] [-n N]

Examples:
    uv run hf_inspector.py squad
    uv run hf_inspector.py allenai/c4 --config en --split train
    uv run hf_inspector.py glue --config sst2 -n 5
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


def print_features(features: Any) -> None:
    """Print the feature schema of a dataset.

    Args:
        features: A ``datasets.Features`` mapping, or ``None``.
    """
    if features is None:
        print('features: (unknown — not declared in builder info)')
        return
    print('features:')
    for name, feat in features.items():
        print(f'  - {name}: {feat}')


def print_splits(splits: Any) -> None:
    """Print the available splits and their example counts.

    Args:
        splits: A mapping from split name to ``SplitInfo``, or ``None``.
    """
    if not splits:
        print('splits: (none declared)')
        return
    print('splits:')
    for name, info in splits.items():
        num = getattr(info, 'num_examples', None)
        num_str = f'{num:,}' if isinstance(num, int) else 'unknown'
        print(f'  - {name}: {num_str} examples')


def pick_split(requested: str | None, splits: Any) -> str | None:
    """Choose which split to stream samples from.

    Args:
        requested: Split name provided by the user, if any.
        splits: The builder's declared splits mapping.

    Returns:
        A split name to stream, or ``None`` if nothing is available.
    """
    if requested:
        return requested
    if not splits:
        return None
    for preferred in ('train', 'validation', 'test'):
        if preferred in splits:
            return preferred
    return next(iter(splits))


def stream_examples(
    dataset_id: str,
    config: str | None,
    split: str,
    n: int,
) -> None:
    """Stream and print the first ``n`` examples from a dataset split.

    Args:
        dataset_id: HuggingFace dataset identifier (e.g. ``"squad"``).
        config: Optional config/subset name.
        split: Split to stream from.
        n: Number of examples to print.
    """
    from datasets import load_dataset

    print(f'\nfirst {n} example(s) from split={split!r} (streaming):')
    try:
        ds = load_dataset(
            dataset_id,
            name=config,
            split=split,
            streaming=True,
        )
    except Exception as e:
        print(f'  (streaming failed: {type(e).__name__}: {e})')
        return

    shown = 0
    try:
        for i, ex in enumerate(ds):
            if i >= n:
                break
            print(f'[{i}]:')
            if isinstance(ex, dict):
                for k, v in ex.items():
                    print(f'  {k!r}: {truncate(repr(v))}')
            else:
                print(f'  {truncate(repr(ex))}')
            shown += 1
    except Exception as e:
        print(f'  (iteration stopped: {type(e).__name__}: {e})')

    if shown == 0:
        print('  (no examples returned)')


def inspect(dataset_id: str, config: str | None, split: str | None, n: int) -> None:
    """Print metadata and a small sample of a HuggingFace dataset.

    Args:
        dataset_id: HuggingFace dataset identifier.
        config: Optional config/subset name.
        split: Optional split to stream from; chosen heuristically if omitted.
        n: Number of streaming examples to preview.
    """
    from datasets import get_dataset_config_names, load_dataset_builder

    print(f'dataset: {dataset_id}')

    if config is None:
        try:
            configs = get_dataset_config_names(dataset_id)
        except Exception as e:
            configs = []
            print(f'(could not list configs: {type(e).__name__}: {e})')
        if configs:
            print(f'available configs: {configs}')
            if len(configs) > 1 and 'default' not in configs:
                print('(multiple configs available; pass --config to pick one; '
                      f'using {configs[0]!r} for metadata)')
                config = configs[0]

    try:
        builder = load_dataset_builder(dataset_id, name=config)
    except Exception as e:
        print(f'load_dataset_builder failed: {type(e).__name__}: {e}')
        return

    info = builder.info
    if config is not None:
        print(f'config: {config}')
    if info.description:
        print(f'description: {truncate(info.description.strip())}')
    if info.citation:
        print(f'citation: {truncate(info.citation.strip())}')
    if info.homepage:
        print(f'homepage: {info.homepage}')
    if info.license:
        print(f'license: {info.license}')

    print_splits(info.splits)
    print_features(info.features)

    chosen = pick_split(split, info.splits)
    if chosen is None:
        print('\n(no split available to stream examples from)')
        return
    stream_examples(dataset_id, config, chosen, n)


def main() -> int:
    """Parse arguments and run the inspector.

    Returns:
        Process exit code.
    """
    ap = argparse.ArgumentParser()
    ap.add_argument('dataset_id',
                    help='HuggingFace dataset id, e.g. "squad" or "allenai/c4"')
    ap.add_argument('--config', default=None,
                    help='dataset config/subset name (if the dataset has configs)')
    ap.add_argument('--split', default=None,
                    help='split to stream examples from (default: train/validation/test)')
    ap.add_argument('-n', type=int, default=3,
                    help='number of streaming examples to preview (default: 3)')
    args = ap.parse_args()

    inspect(args.dataset_id, args.config, args.split, args.n)
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""Fixtures for the inspect-data script tests."""

import json
from pathlib import Path

import pytest


@pytest.fixture(scope='session')
def sample_json_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a small dict-valued JSON file and return its path.

    Args:
        tmp_path_factory: pytest's session-scoped tmp path factory.

    Returns:
        Path to the generated ``sample.json`` file.
    """
    path = tmp_path_factory.mktemp('inspect-data-json') / 'sample.json'
    path.write_text(json.dumps({'name': 'alice', 'items': [1, 2, 3]}))
    return path


@pytest.fixture(scope='session')
def sample_parquet_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a 3-row Parquet file and return its path.

    Args:
        tmp_path_factory: pytest's session-scoped tmp path factory.

    Returns:
        Path to the generated ``sample.parquet`` file.
    """
    import pandas as pd

    df = pd.DataFrame({'id': [1, 2, 3], 'name': ['a', 'b', 'c']})
    path = tmp_path_factory.mktemp('inspect-data-parquet') / 'sample.parquet'
    df.to_parquet(path, engine='pyarrow')
    return path


@pytest.fixture(scope='session')
def sample_h5_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Create a small HDF5 file with one group, dataset, and attribute.

    Args:
        tmp_path_factory: pytest's session-scoped tmp path factory.

    Returns:
        Path to the generated ``sample.h5`` file.
    """
    import h5py
    import numpy as np

    path = tmp_path_factory.mktemp('inspect-data-h5') / 'sample.h5'
    with h5py.File(path, 'w') as f:
        grp = f.create_group('group_a')
        ds = grp.create_dataset('numbers', data=np.array([10, 20, 30]))
        ds.attrs['note'] = 'small test dataset'
    return path

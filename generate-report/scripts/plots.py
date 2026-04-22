# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
#   "seaborn",
#   "pandas",
#   "numpy",
# ]
# ///
"""Plot helpers for generate-report.

Importable functions that produce matplotlib Figures styled with the
house palette (see ``style.py``). All functions accept a pandas
DataFrame as their primary input and return a ``Figure`` — call
``save_svg(fig, path)`` to write it out.

The house style is applied on module import, so ad-hoc scripts can just
``from plots import bar, line, scatter, heatmap, save_svg`` and go.
"""

from __future__ import annotations

from typing import Any, Sequence

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.axes import Axes
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.figure import Figure
from style import CATEGORICAL, PALETTE, apply_style, save_svg

__all__ = [
    'bar', 'line', 'scatter', 'heatmap',
    'save_svg', 'apply_style', 'PALETTE', 'CATEGORICAL',
]

apply_style()


def _hue_colors(levels: Sequence[Any]) -> dict:
    return {lvl: CATEGORICAL[i % len(CATEGORICAL)] for i, lvl in enumerate(levels)}


def _finish(
    ax: Axes,
    *,
    title: str | None,
    xlabel: str | None,
    ylabel: str | None,
) -> None:
    if title is not None:
        ax.set_title(title)
    if xlabel is not None:
        ax.set_xlabel(xlabel)
    if ylabel is not None:
        ax.set_ylabel(ylabel)


def bar(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    hue: str | None = None,
    err: str | None = None,
    orientation: str = 'v',
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure:
    """Bar / grouped-bar plot.

    Args:
        df: Source DataFrame.
        x: Column name for the categorical axis.
        y: Column name for the numeric axis.
        hue: Optional column name to group bars by; each level gets its
            own color.
        err: Optional column name holding symmetric error-bar magnitudes.
        orientation: ``'v'`` for vertical bars (default) or ``'h'`` for
            horizontal.
        title: Optional axes title.
        xlabel: Optional x-axis label.
        ylabel: Optional y-axis label.
        figsize: Figure size in inches.

    Returns:
        The matplotlib ``Figure`` containing the plot.
    """
    fig, ax = plt.subplots(figsize=figsize)

    if hue is None:
        cats = list(df[x])
        vals = df[y].to_numpy()
        errs = df[err].to_numpy() if err else None
        color = CATEGORICAL[0]
        if orientation == 'h':
            ax.barh(cats, vals, xerr=errs, color=color, edgecolor='white')
            ax.invert_yaxis()
        else:
            ax.bar(cats, vals, yerr=errs, color=color, edgecolor='white')
    else:
        cats = list(dict.fromkeys(df[x]))
        hues = list(dict.fromkeys(df[hue]))
        colors = _hue_colors(hues)
        n = len(hues)
        width = 0.8 / max(n, 1)
        positions = np.arange(len(cats))
        for i, h in enumerate(hues):
            sub = df[df[hue] == h].set_index(x).reindex(cats)
            vals = sub[y].to_numpy()
            errs = sub[err].to_numpy() if err else None
            offset = (i - (n - 1) / 2) * width
            if orientation == 'h':
                ax.barh(positions + offset, vals, height=width, xerr=errs,
                        color=colors[h], edgecolor='white', label=str(h))
            else:
                ax.bar(positions + offset, vals, width=width, yerr=errs,
                       color=colors[h], edgecolor='white', label=str(h))
        if orientation == 'h':
            ax.set_yticks(positions, cats)
            ax.invert_yaxis()
        else:
            ax.set_xticks(positions, cats)
        ax.legend(frameon=False, title=hue)

    _finish(ax, title=title, xlabel=xlabel, ylabel=ylabel)
    fig.tight_layout()
    return fig


def line(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    hue: str | None = None,
    err: str | None = None,
    markers: bool = False,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    figsize: tuple[float, float] = (8, 5),
) -> Figure:
    """Line plot with optional multiple series and shaded confidence band.

    Args:
        df: Source DataFrame.
        x: Column name for the horizontal axis.
        y: Column name for the vertical axis.
        hue: Optional column name; each level is plotted as its own line.
        err: Optional column name with symmetric error magnitudes; drawn
            as a shaded band around the line.
        markers: Whether to draw point markers at each data point.
        title: Optional axes title.
        xlabel: Optional x-axis label.
        ylabel: Optional y-axis label.
        figsize: Figure size in inches.

    Returns:
        The matplotlib ``Figure`` containing the plot.
    """
    fig, ax = plt.subplots(figsize=figsize)

    series = [(None, df)] if hue is None else [
        (h, df[df[hue] == h]) for h in dict.fromkeys(df[hue])
    ]
    colors = _hue_colors([s[0] for s in series]) if hue else None
    marker = 'o' if markers else None

    for label, sub in series:
        sub = sub.sort_values(x)
        xs = sub[x].to_numpy()
        ys = sub[y].to_numpy()
        color = colors[label] if colors else CATEGORICAL[0]
        ax.plot(xs, ys, color=color, linewidth=2, marker=marker,
                label=str(label) if label is not None else None)
        if err:
            es = sub[err].to_numpy()
            ax.fill_between(xs, ys - es, ys + es, color=color, alpha=0.18,
                            linewidth=0)

    if hue is not None:
        ax.legend(frameon=False, title=hue)
    _finish(ax, title=title, xlabel=xlabel, ylabel=ylabel)
    fig.tight_layout()
    return fig


def scatter(
    df: pd.DataFrame,
    *,
    x: str,
    y: str,
    hue: str | None = None,
    size: str | None = None,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    figsize: tuple[float, float] = (7, 6),
) -> Figure:
    """Scatter plot with optional hue (color) and size mapping.

    Args:
        df: Source DataFrame.
        x: Column name for the horizontal axis.
        y: Column name for the vertical axis.
        hue: Optional column name; each level gets its own color.
        size: Optional column name; numeric values map to marker area.
        title: Optional axes title.
        xlabel: Optional x-axis label.
        ylabel: Optional y-axis label.
        figsize: Figure size in inches.

    Returns:
        The matplotlib ``Figure`` containing the plot.
    """
    fig, ax = plt.subplots(figsize=figsize)

    if size is not None:
        raw = df[size].to_numpy(dtype=float)
        lo, hi = np.nanmin(raw), np.nanmax(raw)
        span = (hi - lo) if hi > lo else 1.0
        sizes = 30 + 220 * (raw - lo) / span
    else:
        sizes = 48

    if hue is None:
        ax.scatter(df[x], df[y], s=sizes, color=CATEGORICAL[0],
                   alpha=0.82, edgecolor='white', linewidth=0.7)
    else:
        hues = list(dict.fromkeys(df[hue]))
        colors = _hue_colors(hues)
        for h in hues:
            mask = df[hue] == h
            s = sizes[mask.to_numpy()] if isinstance(sizes, np.ndarray) else sizes
            ax.scatter(df.loc[mask, x], df.loc[mask, y], s=s,
                       color=colors[h], alpha=0.82, edgecolor='white',
                       linewidth=0.7, label=str(h))
        ax.legend(frameon=False, title=hue)

    _finish(ax, title=title, xlabel=xlabel, ylabel=ylabel)
    fig.tight_layout()
    return fig


def heatmap(
    matrix: pd.DataFrame | np.ndarray,
    *,
    row_labels: Sequence[str] | None = None,
    col_labels: Sequence[str] | None = None,
    annot: bool = True,
    fmt: str = '.2f',
    cmap: Any = None,
    title: str | None = None,
    xlabel: str | None = None,
    ylabel: str | None = None,
    figsize: tuple[float, float] = (7, 6),
) -> Figure:
    """Heatmap for confusion matrices, ablation grids, etc.

    Args:
        matrix: The 2D data to display. A pandas DataFrame contributes
            its index and columns as default labels; a numpy array uses
            ``row_labels`` / ``col_labels`` if given.
        row_labels: Optional row tick labels (overrides DataFrame index).
        col_labels: Optional column tick labels (overrides DataFrame columns).
        annot: Whether to write the numeric value in each cell.
        fmt: Format string used for cell annotations (e.g. ``'.2f'``,
            ``'d'``). Only meaningful when ``annot=True``.
        cmap: Matplotlib colormap or name. Defaults to a teal→white→rose
            diverging map built from the house palette.
        title: Optional axes title.
        xlabel: Optional x-axis label.
        ylabel: Optional y-axis label.
        figsize: Figure size in inches.

    Returns:
        The matplotlib ``Figure`` containing the heatmap.
    """
    if isinstance(matrix, pd.DataFrame):
        if row_labels is None:
            row_labels = list(matrix.index)
        if col_labels is None:
            col_labels = list(matrix.columns)
        raw = matrix.to_numpy()
    else:
        raw = np.asarray(matrix)
    data = raw.astype(float, copy=False)

    if cmap is None:
        cmap = LinearSegmentedColormap.from_list(
            'house_div',
            [PALETTE['primary'], '#ffffff', PALETTE['accent']],
        )

    fig, ax = plt.subplots(figsize=figsize)
    im = ax.imshow(data, cmap=cmap, aspect='auto')
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)

    if col_labels is not None:
        ax.set_xticks(range(len(col_labels)), col_labels, rotation=30, ha='right')
    if row_labels is not None:
        ax.set_yticks(range(len(row_labels)), row_labels)

    ax.grid(False)

    if annot:
        finite = data[np.isfinite(data)]
        mid = (np.nanmin(finite) + np.nanmax(finite)) / 2 if finite.size else 0.0
        for i in range(data.shape[0]):
            for j in range(data.shape[1]):
                v = data[i, j]
                if not np.isfinite(v):
                    continue
                color = 'white' if abs(v - mid) > (np.nanmax(finite) - mid) * 0.6 else PALETTE['primary']
                ax.text(j, i, format(raw[i, j], fmt), ha='center', va='center',
                        color=color, fontsize=9)

    _finish(ax, title=title, xlabel=xlabel, ylabel=ylabel)
    fig.tight_layout()
    return fig

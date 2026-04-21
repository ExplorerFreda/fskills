# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "matplotlib",
#   "seaborn",
#   "pandas",
# ]
# ///
"""House plot style for generate-report.

Import from an ad-hoc plotting script, or run directly to emit a
`style-preview.png` showing the palette.

Usage from a plot script (inside the report folder):

    # /// script
    # requires-python = ">=3.10"
    # dependencies = ["matplotlib", "seaborn", "pandas"]
    # ///
    import sys
    sys.path.insert(0, "<absolute path to generate-report/scripts>")
    from style import PALETTE, apply_style
    apply_style()
    ...

The palette mirrors the CSS variables in template.html so plots and
HTML share the same visual language.
"""

from __future__ import annotations

PALETTE = {
    'primary':    '#225573',  # teal — primary text / headers
    'accent':     '#b6274e',  # rose — highlights, best values
    'green':      '#547b5b',  # green — links, positive
    'olive':      '#6d8436',  # olive — secondary green
    'amber':      '#d4880f',  # amber — warnings
    'light_teal': '#4a7a94',  # secondary text
    'neutral':    '#7d99b1',  # gray
    'bg':         '#f5fbf7',  # page background
    'card':       '#ffffff',
}

CATEGORICAL = [
    PALETTE['primary'],
    PALETTE['accent'],
    PALETTE['green'],
    PALETTE['amber'],
    PALETTE['olive'],
    PALETTE['light_teal'],
    PALETTE['neutral'],
]


def apply_style() -> None:
    """Set matplotlib + seaborn defaults to match the HTML theme."""
    import matplotlib as mpl
    import seaborn as sns

    sns.set_theme(style='whitegrid', context='notebook')
    sns.set_palette(CATEGORICAL)

    mpl.rcParams.update({
        'font.family':       ['Source Sans Pro', 'DejaVu Sans', 'sans-serif'],
        'font.size':         11,
        'axes.titlesize':    13,
        'axes.titleweight':  'bold',
        'axes.labelsize':    11,
        'axes.labelcolor':   PALETTE['primary'],
        'axes.edgecolor':    PALETTE['neutral'],
        'axes.titlecolor':   PALETTE['primary'],
        'axes.spines.top':   False,
        'axes.spines.right': False,
        'xtick.color':       PALETTE['light_teal'],
        'ytick.color':       PALETTE['light_teal'],
        'grid.color':        '#e8f0f5',
        'grid.linewidth':    0.8,
        'figure.facecolor':  'white',
        'axes.facecolor':    'white',
        'savefig.dpi':       160,
        'savefig.bbox':      'tight',
        'savefig.facecolor': 'white',
    })


def _preview() -> None:
    """Emit style-preview.png showing the palette and a sample plot."""
    import matplotlib.pyplot as plt
    import numpy as np

    apply_style()
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4))

    names = list(PALETTE.keys())
    ax1.barh(names, [1] * len(names), color=[PALETTE[n] for n in names])
    ax1.set_title('Palette')
    ax1.set_xticks([])
    ax1.invert_yaxis()

    x = np.linspace(0, 10, 100)
    for i, label in enumerate(['model-a', 'model-b', 'model-c', 'baseline']):
        ax2.plot(x, np.sin(x + i * 0.6) + i * 0.3, label=label, linewidth=2)
    ax2.set_title('Sample lines')
    ax2.legend(frameon=False)

    fig.tight_layout()
    fig.savefig('style-preview.png')
    print('wrote style-preview.png')


if __name__ == '__main__':
    _preview()

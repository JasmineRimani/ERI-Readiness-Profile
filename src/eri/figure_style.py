"""One visual language for every exported PNG: palette, typography, footnotes.

Colour carries exactly one job per figure. Case identity uses two fixed hues;
ordered stages use one blue ramp; evidence states use the reserved status
scale with a text label in every cell, so nothing depends on colour alone.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.colors import to_rgb

CASES = ('HLS_SORTIE', 'HUMANS')
NAMES = {'HLS_SORTIE': 'Lander · 4 crew, 4-day sortie', 'HUMANS': 'HUMANS · 2 crew, 14-day campaign'}
SHORT = {'HLS_SORTIE': 'Lander', 'HUMANS': 'HUMANS'}
CASE_COLOUR = {'HLS_SORTIE': '#2a78d6', 'HUMANS': '#eb6834'}
CANDIDATE = {'open': 'Open support', 'integrated': 'Integrated air loop', 'distributed': 'Distributed air chain'}
CANDIDATE_COLOUR = {'integrated': '#4a3aa7', 'distributed': '#1baf7a', 'open': '#898781',
                    'DEFER_OR_RESTRUCTURE': '#898781'}
TECH = {'T-AR-001': 'LiOH CO₂ removal', 'T-AR-002': 'O₂ storage', 'T-AR-003': 'Humidity control',
        'T-AR-004': 'Trace-contaminant control', 'T-AR-006': 'Thermal-amine CO₂ removal',
        'T-AR-007': 'Water electrolysis', 'T-AR-008': 'Sabatier CO₂ reduction',
        'T-AR-014': 'ACLS-class integrated air loop', 'T-EM-001': 'Atmosphere monitoring',
        'T-WR-001': 'Water storage', 'T-WR-006': 'Water polishing', 'T-WR-009': 'Membrane water recovery'}
FUNCTION = {'co2_removal': 'CO₂ removal', 'o2_generation': 'O₂ generation', 'co2_reduction': 'CO₂ reduction',
            'water_processing': 'Water processing', 'water_polishing': 'Water polishing',
            'humidity_control': 'Humidity control', 'tccs': 'Trace-contaminant control',
            'monitoring_atmosphere': 'Atmosphere monitoring', 'o2_storage': 'O₂ storage',
            'water_storage': 'Water storage', 'monitoring_trace_gas': 'Trace-gas monitoring',
            'water_disinfection': 'Water disinfection'}
SERIES = ['#2a78d6', '#eb6834', '#1baf7a', '#eda100', '#e87ba4', '#008300', '#4a3aa7', '#e34948']
BLUES = ['#cde2fb', '#b7d3f6', '#9ec5f4', '#86b6ef', '#6da7ec', '#5598e7', '#3987e5',
         '#2a78d6', '#256abf', '#1c5cab', '#184f95', '#104281', '#0d366b']
STATUS = {'good': '#0ca30c', 'warning': '#fab219', 'serious': '#ec835a', 'critical': '#d03b3b'}
INK, INK2, MUTED = '#0b0b0b', '#52514e', '#898781'
GRID, AXIS, NEUTRAL, SURFACE = '#e1e0d9', '#c3c2b7', '#f0efec', '#ffffff'


def tint(colour, amount):
    """Mix a colour towards white; amount 0 keeps it, 1 gives white."""
    r, g, b = to_rgb(colour)
    return (r + (1 - r) * amount, g + (1 - g) * amount, b + (1 - b) * amount)


def apply_style():
    plt.rcParams.update({
        'font.size': 9.5, 'font.family': 'sans-serif',
        'axes.titlesize': 10.5, 'axes.titleweight': 'medium', 'axes.labelsize': 9.5,
        'axes.edgecolor': AXIS, 'axes.labelcolor': INK2, 'axes.spines.top': False, 'axes.spines.right': False,
        'axes.grid': False, 'grid.color': GRID, 'grid.linewidth': 0.8, 'grid.linestyle': '-',
        'xtick.color': INK2, 'ytick.color': INK2, 'xtick.labelsize': 9, 'ytick.labelsize': 9,
        'xtick.major.size': 3, 'ytick.major.size': 3, 'xtick.color': AXIS, 'ytick.color': AXIS,
        'xtick.labelcolor': INK2, 'ytick.labelcolor': INK2,
        'legend.frameon': False, 'legend.fontsize': 8.5,
        'figure.facecolor': SURFACE, 'axes.facecolor': SURFACE, 'savefig.facecolor': SURFACE,
        'text.color': INK,
    })


def grid(ax, axis='x'):
    ax.grid(True, axis=axis, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)


def finish(fig, path, note=None, dpi=220, bottom=0.10):
    """Footnote in secondary ink, then a tight export."""
    if note:
        fig.text(0.5, 0.012, note, ha='center', va='bottom', fontsize=8.3, color=INK2, linespacing=1.4)
    fig.savefig(path, dpi=dpi, bbox_inches='tight', facecolor=SURFACE)
    plt.close(fig)


def label_bar_end(ax, x, y, text, colour=INK2, pad=0.0, **kw):
    ax.text(x + pad, y, text, va='center', ha='left', fontsize=8.5, color=colour, **kw)


def humanise(name):
    return name.replace('_', ' ').strip().capitalize()

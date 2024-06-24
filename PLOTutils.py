import numpy as np

import matplotlib.pyplot as plt
import mplhep as hep

from typing import Optional
import matplotlib as mpl



FONTSIZE  = 22
FIGSIZE   = (10, 8)

CMS_PALETTE_1 = ["#5790fc", "#f89c20", "#e42536", "#964a8b", "#9c9ca1", "#7a21dd"]
CMS_PALETTE_2 = ["#3f90da", "#ffa90e", "#bd1f01", "#94a4a2", "#832db6", "#a96b59", "#e76300", "#b9ac70", "#717581", "#92dadd"]


def restore_minor_ticks_log_plot(
    ax: Optional[plt.Axes] = None, n_subticks=9
) -> None:
    """For axes with a logrithmic scale where the span (max-min) exceeds
    10 orders of magnitude, matplotlib will not set logarithmic minor ticks.
    If you don't like this, call this function to restore minor ticks.

    Args:
        ax:
        n_subticks: Number of Should be either 4 or 9.

    Returns:
        None
    """
    if ax is None:
        ax = plt.gca()

    locmaj = mpl.ticker.LogLocator(base=10, numticks=1000)
    ax.yaxis.set_major_locator(locmaj)
    locmin = mpl.ticker.LogLocator(
        base=10.0, subs=np.linspace(0, 1.0, n_subticks + 2)[1:-1], numticks=1000
    )
    ax.yaxis.set_minor_locator(locmin)
    ax.yaxis.set_minor_formatter(mpl.ticker.NullFormatter())
    
    

def set_label_font(ax: plt.Axes, fontsize: int = 28):
    """
    Set the font size of the x and y axis labels of a matplotlib Axes object.
    
    Parameters:
    ax (matplotlib.pyplot.Axes): The Axes object to modify.
    fontsize (int): The font size to set the labels to. Default is 28.
    """
    ax.set_xlabel(ax.get_xlabel(), fontsize = fontsize)
    ax.set_ylabel(ax.get_ylabel(), fontsize = fontsize)
    
    
def set_tick_font(ax: plt.Axes, fontsize: int = 28):
    """
    Set the font size of the tick labels for the given Axes object.
    
    Parameters:
    -----------
    ax : matplotlib.axes.Axes
        The Axes object for which to set the tick font size.
    fontsize : int, optional
        The font size to use for the tick labels. Default is 28.
    """
    ax.tick_params(axis = "x", labelsize = fontsize, which = "major")
    ax.tick_params(axis = "y", labelsize = fontsize, which = "major")
    
    
def draw_grid(ax: plt.Axes):
    """
    Draw a grid on the given matplotlib Axes object.
    
    Parameters:
    -----------
    ax: plt.Axes
        The matplotlib Axes object on which to draw the grid.
    """
    ax.grid(True, which="major", axis="both", alpha=0.5, color="gray")
    ax.set_axisbelow(True)
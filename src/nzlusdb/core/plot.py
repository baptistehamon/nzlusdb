"""Plotting functions for NZLUSDB."""

import matplotlib as mpl


def plt_robustness_categories(da, ax):
    r"""
    Plot robustness categories.

    The function overlays hatching patterns on a map to represent different robustness categories from
    `xclim.ensemble.robutness_categories` computed based on `xclim.ensemble.robutness_fractions`
    'ipcc-ar6-c' approach. A 'xxx' hatching pattern indicates conflicting signals, while a '\\\\\' pattern
    indicates no change or no signal. Robust signals are left unhatched.

    Parameters
    ----------
    da : xarray.DataArray
        DataArray containing robustness categories (`xclim.ensemble.robutness_categories` output).
    ax : matplotlib.axes.Axes
        The axis on which to plot the robustness categories.
    """
    for val, ha in zip(da.flag_values, [None, "\\\\\\", "xxx"], strict=False):
        ax.pcolor(
            da.lon,
            da.lat,
            da.where(da == val),
            hatch=ha,
            cmap=mpl.colors.ListedColormap(["none"]),
        )

"""Plotting functions for NZLUSDB."""

import matplotlib as mpl
import matplotlib.pyplot as plt


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


def robustness_categories_lgd(ax, **kwargs):
    r"""
    Add a legend for robustness categories.

    The robustness categories are represented by different hatching patterns:
    - No hatching: Robust signal
    - '\\\\\': No change or no signal
    - 'xxx': Conflicting signal

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axis on which to add the legend.
    **kwargs : dict
        Additional keyword arguments to pass to `matplotlib.pyplot.legend()`.
    """
    handles = [
        mpl.patches.Rectangle((0, 0), 2, 2, fill=False, hatch=h, label=lbl)
        for h, lbl in zip(
            ["", "\\\\\\", "xxx"], ["Robust signal", "No change or no signal", "Conflicting signal"], strict=False
        )
    ]
    ax.legend(handles=handles, **kwargs)


def _plt_map(data, ax, title, **kwargs):
    data.plot(ax=ax, add_colorbar=False, **kwargs)
    ax.set_title(title)
    ax.axis("off")


def plt_scenario_maps(
    ds,
    axs,
    scenario,
    variable: str | None = None,
    hist_var: str | None = None,
    proj_var: str | None = None,
    scenario_label: str | None = None,
    hist_kw: dict | None = None,
    proj_kw: dict | None = None,
    robustness: bool = False,
    **kwargs,
):
    """
    Plot maps for historical and projected periods for a given scenario.

    The function creates four side-by-side (horizontal) maps on the provided axes, the first one corresponding to
    the historical period (1980-2009) and the next three to future periods (2010-2039, 2040-2069, 2070-2099) for the
    specified scenario. The name of the scenario is displayed vertically on the left side of the plots. Optionally,
    robustness categories can be overlaid on the projected period maps.

    Parameters
    ----------
    ds : xarray.Dataset
        Dataset containing the data to be plotted, with a multi-index time dimension ('scenario', 'period').
        Scenario name should correspond to 'historical' for the 1980-2009 period.
    axs : array-like of matplotlib.axes.Axes
        Array of four axes where the maps will be plotted.
    scenario : str
        The scenario name for the projected periods.
    variable : str, optional
        The variable name to be plotted for all periods. If not provided, both `hist_var` and `proj_var` must
        be specified.
    hist_var : str, optional
        The variable name to be plotted for the historical period (1980-2009). Required if `variable` is not provided.
    proj_var : str, optional
        The variable name to be plotted for the projected periods. Required if `variable` is not provided.
    scenario_label : str, optional
        Label to display for the scenario on the left side of the plots. Defaults to the uppercase scenario name.
    hist_kw : dict, optional
        Additional keyword arguments to pass to `_plt_map` for the historical period map.
    proj_kw : dict, optional
        Additional keyword arguments to pass to `_plt_map` for the projected period maps.
    robustness : bool, optional
        If True, overlays robustness categories on the projected period maps using `plt_robustness_categories`.
    **kwargs : dict
        Additional keyword arguments to pass to `_plt_map` for all maps.
    """
    if hist_var is None:
        hist_var = variable
    if proj_var is None:
        proj_var = variable
    if scenario_label is None:
        scenario_label = scenario.upper()
    if variable is None and (hist_var is None or proj_var is None):
        raise ValueError("Either variable or both hist_var and proj_var must be provided.")
    elif hist_var is None:
        hist_var = variable
    elif proj_var is None:
        proj_var = variable

    plt.text(
        -0.1,
        0.5,
        scenario_label,
        ha="center",
        va="center",
        transform=axs[0].transAxes,
        rotation="vertical",
        fontweight="bold",
    )
    _plt_map(ds.sel(time=("historical", "1980-2009"))[hist_var], axs[0], "", **hist_kw, **kwargs)
    _plt_map(ds.sel(time=(scenario, "2010-2039"))[proj_var], axs[1], "", **proj_kw, **kwargs)
    _plt_map(ds.sel(time=(scenario, "2040-2069"))[proj_var], axs[2], "", **proj_kw, **kwargs)
    _plt_map(ds.sel(time=(scenario, "2070-2099"))[proj_var], axs[3], "", **proj_kw, **kwargs)
    if robustness:
        plt_robustness_categories(ds.sel(time=(scenario, "2010-2039")).robustness_categories, axs[1])
        plt_robustness_categories(ds.sel(time=(scenario, "2040-2069")).robustness_categories, axs[2])
        plt_robustness_categories(ds.sel(time=(scenario, "2070-2099")).robustness_categories, axs[3])


def plt_timeline(ax, color="black"):
    """
    Create a timeline plot indicating historical and projected periods.

    The function draws a horizontal timeline with labeled segments for the historical period (1980-2009)
    and three projected periods (2010-2039, 2040-2069, 2070-2099).

    Parameters
    ----------
    ax : matplotlib.axes.Axes
        The axis on which to draw the timeline.
    color : str, optional
        Color of the timeline and text. Default is "black".
    """
    ax.plot([0, 1], [0.5, 0.5], color=color, linewidth=2)
    ax.text(
        0.125,
        0.5,
        "Historical",
        ha="center",
        va="center",
        transform=ax.transAxes,
        bbox=dict(facecolor="white", edgecolor="none", pad=5),
        color=color,
        fontweight="bold",
        fontstyle="italic",
    )
    ax.text(
        0.625,
        0.5,
        "Projected Suitability",
        ha="center",
        va="center",
        transform=ax.transAxes,
        bbox=dict(facecolor="white", edgecolor="none", pad=5),
        color=color,
        fontweight="bold",
        fontstyle="italic",
    )
    ax.text(0.125, 0.3, "1980-2009", ha="center", va="center", transform=ax.transAxes, color=color, fontweight="bold")
    ax.text(0.375, 0.3, "2010-2039", ha="center", va="center", transform=ax.transAxes, color=color, fontweight="bold")
    ax.text(0.625, 0.3, "2040-2069", ha="center", va="center", transform=ax.transAxes, color=color, fontweight="bold")
    ax.text(0.875, 0.3, "2070-2099", ha="center", va="center", transform=ax.transAxes, color=color, fontweight="bold")
    ax.plot([0, 0], [0.45, 0.55], color=color, linewidth=2)
    ax.plot([0.25, 0.25], [0.45, 0.55], color=color, linewidth=2)
    ax.plot([1, 1], [0.45, 0.55], color=color, linewidth=2)
    ax.set_xlim(-0.01, 1.01)
    ax.set_ylim(0.25, 0.75)
    ax.axis("off")

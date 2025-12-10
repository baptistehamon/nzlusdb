"""Climate indices module."""

from __future__ import annotations

from typing import Callable

import numpy as np
import xarray as xr
from xclim.core.calendar import get_calendar, select_time
from xclim.core.units import Quantified, convert_units_to, declare_units
from xclim.indices.generic import domain_count, to_agg_units


@declare_units(tasmax="[temperature]")
def day_full_bloom(
    tasmax: xr.DataArray,
    freq: str = "YS",
) -> xr.DataArray:
    """
    Day of full bloom for apple.

    The day of full bloom is computed as a function of the mean maximum temperature
    in August and September following the formula from Hall et al. (2018):

    Parameters
    ----------
    tasmax : xr.DataArray
        Maximum temperature.
    freq : str, optional
        Resampling frequency.

    Returns
    -------
    xr.DataArray
        Day of the year of full bloom.

    Warnings
    --------
    This indices is specific to apple grown in New Zealand.

    References
    ----------
    Hall, A.; Stanley, J.; Müller, K.; van den Dijssel, C. Criteria for Defining Climatic Suitability
    of Horticultural Crops; Client Report for the Ministry for Primary Industries; Plant & Food Research:
    Auckland, New Zealand, 2018.

    """
    tasmax = select_time(convert_units_to(tasmax, "degC"), month=[8, 9])
    tasmax = tasmax.resample(time=freq).mean()
    out = (367 - 5.5 * tasmax).round()
    out = out.assign_attrs(units="", is_dayofyear=np.int32(1), get_calendar=get_calendar(tasmax))
    return out


@declare_units(tas="[temperature]")
def day_budbreak(
    tas: xr.DataArray,
    freq: str = "YS",
) -> xr.DataArray:
    """
    Day of budbreak for kiwifruit.

    The day of budbreak is computed as a function of the mean temperature
    from May to July following the formula from Vetharaniam et al. (2022):

    Parameters
    ----------
    tas : xr.DataArray
        Mean temperature.
    freq : str, optional
        Resampling frequency.

    Returns
    -------
    xr.DataArray
        Day of the year of budbreak.

    Warnings
    --------
    This indices is specific to kiwifruit grown in New Zealand.

    References
    ----------
    Vetharaniam, I., Müller, K., Stanley, J., Van den Dijssel, C., Timar, L., & Cummins, M. (2021).
    Modelling the effect of climate change on land suitability for growing perennial crops (p. 362).
    A Plant & Food Research report prepared for: Ministry for Primary Industries. Milestone No. 87023 & 73685.
    Contract  No. 34671. Job code: P/405421/01. PFR SPTS No. 20712.
    """
    tas = select_time(convert_units_to(tas, "degC"), month=[5, 6, 7]).resample(time=freq).mean()
    out = np.minimum(335, 225 + np.exp(0.267 * tas)).round()
    out = out.assign_attrs(units="", is_dayofyear=np.int32(1), get_calendar=get_calendar(tas))
    return out


@declare_units(tasmin="[temperature]")
def frost_survival(
    tasmin: xr.DataArray,
    weights: xr.DataArray | int | float = 1,
    func: Callable | None = None,
    fparams: dict | None = None,
    freq: str = "YS",
):
    """
    Frost survival computed as a function of minimum temperature.

    Parameters
    ----------
    tasmin : xr.DataArray
        Minimum temperature.
    weights : xr.DataArray, optional
        Weights to apply to daily survival probabilities. Default is 1 (no weighting).
    func : Callable, optional
        Function to compute daily survival probabilities.
    fparams : dict, optional
        Parameters to pass to `func`.
    freq : str, optional
        Resampling frequency. Default is "YS".

    Returns
    -------
    xr.DataArray
        Frost survival.

    References
    ----------
    Vetharaniam, I., Müller, K., Stanley, C. J., van den Dijssel, C., Timar, L., & Clothier, B. (2022).
    Modelling Continuous Location Suitability Scores and Spatial Footprint of Apple and Kiwifruit in New Zealand.
    Land, 11(9), Article 9. https://doi.org/10.3390/land11091528
    """
    tasmin = convert_units_to(tasmin, "degC")

    out = xr.apply_ufunc(
        func,
        tasmin,
        kwargs=fparams,
        dask="parallelized",
    )

    out = (1 - (1 - out) * weights).resample(time=freq).prod("time")
    out = out.assign_attrs(units="")
    return out


@declare_units(tasmax="[temperature]")
def tasmax_survival(
    tasmax: xr.DataArray,
    weights: xr.DataArray | int | float = 1,
    func: Callable | None = None,
    fparams: dict | None = None,
    freq: str = "YS",
):
    """
    Survival rate computed as a function of daily maximum temperature.

    Parameters
    ----------
    tasmax : xr.DataArray
        Maximum temperature.
    weights : xr.DataArray, optional
        Weights to apply to daily survival probabilities. Default is 1 (no weighting).
    func : Callable, optional
        Function to compute daily survival probabilities.
    fparams : dict, optional
        Parameters to pass to `func`.
    freq : str, optional
        Resampling frequency. Default is "YS".

    Returns
    -------
    xr.DataArray
        Survival rate.

    References
    ----------
    Vetharaniam, I., Müller, K., Stanley, C. J., van den Dijssel, C., Timar, L., & Clothier, B. (2022).
    Modelling Continuous Location Suitability Scores and Spatial Footprint of Apple and Kiwifruit in New Zealand.
    Land, 11(9), Article 9. https://doi.org/10.3390/land11091528
    """
    tasmax = convert_units_to(tasmax, "degC")

    out = xr.apply_ufunc(
        func,
        tasmax,
        kwargs=fparams,
        dask="parallelized",
    )

    out = (1 - (1 - out) * weights).resample(time=freq).prod("time")
    out = out.assign_attrs(units="")
    return out


@declare_units(tas="[temperature]", low="[temperature]", high="[temperature]")
def chilling_hours(
    tas: xr.DataArray, low: Quantified = "-1E3 degC", high: Quantified = "7 degC", freq: str = "YS"
) -> xr.DataArray:
    r"""
    Chilling hours.

    Number of hours where the hourly temperature is within low and high thresholds.

    Parameters
    ----------
    tas : xarray.DataArray
        Mean hourly temperature.
    low : Quantified
        Lower temperature threshold.
    high : Quantified
        Upper temperature threshold.
    freq : str
        Resampling frequency.

    Returns
    -------
    xarray.DataArray, [time]
        Chilling hours.
    """
    low = convert_units_to(low, tas)
    high = convert_units_to(high, tas)
    out = domain_count(tas, low, high, freq)
    return to_agg_units(out, tas, "count")


@declare_units(hurs="[]")
def cracking_survival(
    hurs: xr.DataArray,
    weights: xr.DataArray | int | float = 1,
    func: Callable | None = None,
    fparams: dict | None = None,
    freq: str = "YS",
):
    """
    Cracking survival computed as a function of daily relative humidity.

    Parameters
    ----------
    hurs : xr.DataArray
        Relative humidity.
    weights : xr.DataArray, optional
        Weights to apply to daily survival probabilities. Default is 1 (no weighting).
    func : Callable, optional
        Function to compute daily survival probabilities.
    fparams : dict, optional
        Parameters to pass to `func`.
    freq : str, optional
        Resampling frequency. Default is "YS".

    Returns
    -------
    xr.DataArray
        Cracking survival.

    References
    ----------
    Vetharaniam, I., Müller, K., Stanley, J., Van den Dijssel, C., Timar, L., & Cummins, M. (2021).
    Modelling the effect of climate change on land suitability for growing perennial crops (p. 362).
    A Plant & Food Research report prepared for: Ministry for Primary Industries. Milestone No. 87023 & 73685.
    Contract  No. 34671. Job code: P/405421/01. PFR SPTS No. 20712.
    """
    tasmax = convert_units_to(hurs, "%")

    out = xr.apply_ufunc(
        func,
        tasmax,
        kwargs=fparams,
        dask="parallelized",
    )

    out = (1 - (1 - out) * weights).resample(time=freq).prod("time")
    out = out.assign_attrs(units="")
    return out

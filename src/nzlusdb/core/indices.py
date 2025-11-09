"""Climate indices module."""

from __future__ import annotations

import lsapy.standardize as lstd
import numpy as np
import xarray as xr
from xclim.core.calendar import get_calendar, select_time
from xclim.core.units import convert_units_to, declare_units


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


@declare_units(tasmin="[temperature]")
def frost_survival(
    tasmin: xr.DataArray,
    weights: xr.DataArray | int | float = 1,
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
        lstd.vetharaniam2022_eq3,
        tasmin,
        kwargs={"a": 1, "b": -3},
        dask="parallelized",
    )

    out = (1 - (1 - out) * weights).resample(time=freq).prod("time")
    out = out.assign_attrs(units="")
    return out


@declare_units(tasmax="[temperature]")
def sunburn_survival(
    tasmax: xr.DataArray,
    weights: xr.DataArray | int | float = 1,
    freq: str = "YS",
):
    """
    Sunburn survival computed as a function of daily maximum temperature.

    Parameters
    ----------
    tasmax : xr.DataArray
        Maximum temperature.
    weights : xr.DataArray, optional
        Weights to apply to daily survival probabilities. Default is 1 (no weighting).
    freq : str, optional
        Resampling frequency. Default is "YS".

    Returns
    -------
    xr.DataArray
        Sunburn survival.

    References
    ----------
    Vetharaniam, I., Müller, K., Stanley, C. J., van den Dijssel, C., Timar, L., & Clothier, B. (2022).
    Modelling Continuous Location Suitability Scores and Spatial Footprint of Apple and Kiwifruit in New Zealand.
    Land, 11(9), Article 9. https://doi.org/10.3390/land11091528
    """
    tasmax = convert_units_to(tasmax, "degC")

    out = xr.apply_ufunc(
        lstd.logistic,
        tasmax,
        kwargs={"a": -0.52, "b": 37.5},
        dask="parallelized",
    )

    out = (1 - (1 - out) * weights).resample(time=freq).prod("time")
    out = out.assign_attrs(units="")
    return out

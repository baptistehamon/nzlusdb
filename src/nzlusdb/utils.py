"""Utility functions for NZLUSDB."""

from pathlib import Path

import numpy as np
import xarray as xr
from dask.diagnostics import ProgressBar
from xclim.core.calendar import select_time


def write_netcdf(data: xr.DataArray | xr.Dataset, filepath: Path, progressbar=False, verbose=False, **kwargs):
    """
    Write xarray DataArray or Dataset to a NetCDF file.

    Parameters
    ----------
    data : xr.DataArray | xr.Dataset
        The xarray DataArray or Dataset to write.
    filepath : Path
        The path to the output NetCDF file.
    progressbar : bool, optional
        Whether to display a progress bar during the write operation. Default is True.
    **kwargs
        Additional keyword arguments to pass to the `to_netcdf` method.
    """
    if verbose:
        print(filepath)
    if progressbar:
        with ProgressBar():
            data.to_netcdf(path=filepath, **kwargs)
    else:
        data.to_netcdf(path=filepath, **kwargs)


def downweight(
    weight: xr.DataArray,
    period_type: str,
    period: tuple,
    downweight_from: int | float | None = None,
    downweight_to: int | float | None = None,
    include_bounds: tuple[bool] = (False, False),
    interp_method: str | None = "linear",
):
    """
    Downweight values in a DataArray over a specified period.

    Parameters
    ----------
    weight : xr.DataArray
        The input weights DataArray to be downweighted.
    period_type : str
        The type of period to select time (see xclim.core.calendar.select_time for options).
    period : tuple
        A tuple specifying the start and end of the period.
    downweight_from : int | float | None, optional
        The value to downweight from at the start of the period. Default is None.
    downweight_to : int | float | None, optional
        The value to downweight to at the end of the period. Default is None.
    include_bounds : tuple[bool], optional
        Whether to include the bounds of the period when selecting time. Default is (False, False).
    interp_method : str | None, optional
        The interpolation method to use for filling NaN values. If None, no interpolation is performed.
        Default is 'linear'.

    Returns
    -------
    xr.DataArray
        The downweighted weights DataArray.
    """
    out = weight.copy()

    if len(period) != 2:
        raise ValueError("length of period must be 2")
    if downweight_from is None and downweight_to is None:
        raise ValueError("at least one of 'downweight_from' or 'downweight_to' must be provided")
    elif downweight_from is not None and downweight_to is not None:
        raise ValueError("only one of 'downweight_from' or 'downweight_to' must be provided")

    _start, _end = period
    mask = select_time(out, **{period_type: period}, include_bounds=include_bounds)
    out = xr.where(mask.notnull(), np.nan, out)

    if downweight_from is not None:
        dw_value = downweight_from
        mask = select_time(out, **{period_type: (_start, _start)})
    if downweight_to is not None:
        dw_value = downweight_to
        mask = select_time(out, **{period_type: (_end, _end)})
    out = xr.where(mask.notnull(), dw_value, out).chunk({"time": -1})

    if interp_method is not None:
        interp = out.interpolate_na("time", method=interp_method, use_coordinate=False)
        out = xr.where(weight.notnull(), interp, np.nan)

    return out


def downweight_season(
    weight: xr.DataArray,
    period_type: str | tuple[str],
    periods: dict[str, tuple[xr.DataArray | int, xr.DataArray | int]],
    values: list[int | float] | int | float = 0,
    interp_method: str = "linear",
    include_bounds: tuple[tuple[bool]] = ((False, False), (False, False)),
) -> xr.DataArray:
    """
    Downweight weights for the start and end of a season.

    Parameters
    ----------
    weight : xr.DataArray
        The input weights DataArray to be downweighted.
    period_type : str | tuple[str]
        The type of period to select time (see xclim.core.calendar.select_time for options).
    periods : dict[str, tuple[xr.DataArray | int, xr.DataArray | int]]
        A dictionary specifying the start and end periods with keys 'start' and 'end'.
    values : list[int | float] | int | float, optional
        The values to downweight to for the start and end periods. Default is 0.
    interp_method : str, optional
        The interpolation method to use for filling NaN values. Default is 'linear'.
    include_bounds : tuple[tuple[bool]], optional
        A tuple specifying whether to include the bounds of the start and end periods when selecting time.
        Does not include bounds by default.

    Returns
    -------
    xr.DataArray
        The downweighted weights DataArray.

    Notes
    -----
    Consider using 'downweight' function to downweight only the start or end of a season.
    """
    if isinstance(period_type, str):
        period_type = [period_type] * 2
    if len(periods) != 2:
        raise ValueError("length of periods must be 2")
    if any([k not in ["start", "end"] for k in periods.keys()]):
        raise ValueError("periods keys must be 'start' and 'end'")
    if isinstance(values, (int, float)):
        values = [values] * 2
    if len(values) != 2:
        raise ValueError("length of 'values' must be 2")
    if len(include_bounds) != 2:
        raise ValueError("length of 'include_bounds' must be 2")

    out = weight.copy()
    for params in zip(period_type, periods.keys(), periods.values(), values, include_bounds):
        ptype, period, prange, dw, inc_bnd = params
        if period == "start":
            dw = {"downweight_from": dw}
        if period == "end":
            dw = {"downweight_to": dw}
        out = downweight(out, ptype, prange, **dw, include_bounds=inc_bnd, interp_method=None)
    interp = out.interpolate_na("time", method=interp_method, use_coordinate=False)
    return xr.where(weight.notnull(), interp, np.nan)

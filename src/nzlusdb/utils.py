"""Utility functions for NZLUSDB."""

from pathlib import Path

import xarray as xr
from dask.diagnostics import ProgressBar


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

"""Utility functions for NZLUSDB indicator computation."""

from collections.abc import Callable

import pandas as pd
import xarray as xr

from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf


class LoopOverYears:
    """
    Class to loop over years in a dataset and apply a function to each year's data.

    Parameters
    ----------
    data : xarray.Dataset
        The input dataset to loop over.
    func : callable
        The function to apply to each year's data.
    freq : str
        The frequency string to resample the data by year (e.g., "YS" for year start).
    filename : str, optional
        The filename pattern for temporary files, with "<YEAR>" as a placeholder for the year.
    skip_existing : bool, optional
        If True, skip processing for years where the output file already exists.
    """

    def __init__(
        self,
        data: xr.DataArray,
        func: Callable,
        freq: str,
        filename: str = "tmp_<YEAR>.nc",
        skip_existing: bool = False,
    ):
        self.data = data
        self.func = func
        self.freq = freq
        self.filename = filename
        self.skip_existing = skip_existing
        self.files = []
        self.skipped = []

    def __call__(self, tmp_files=True, year_break=None, *args, **kwds):
        """
        Apply the function to each year's data, optionally saving to temporary files.

        Parameters
        ----------
        tmp_files : bool, optional
            If True, save each year's output to a temporary file. If False, return the concatenated result.
        year_break : int, optional
            If provided, stop processing after this many years. Should be used for testing with small datasets.
        """
        out = []
        for year_index, (base_time, indexes) in enumerate(self.data.resample(time=self.freq).groups.items()):
            if year_break is not None and year_index > year_break:
                break
            year = base_time.year if hasattr(base_time, "year") else pd.Timestamp(base_time).year
            data_yr = self.data.isel(time=indexes)
            fname = INDICATORPATH / self.filename.replace("<YEAR>", str(year))

            if self.skip_existing and fname.exists():
                self.skipped.append(fname)
            else:
                _out = self.func(data_yr, *args, **kwds)
                if tmp_files:
                    self.files.append(fname)
                    write_netcdf(_out, fname, progressbar=True, verbose=False)
                else:
                    out.append(_out)

        if tmp_files:
            out = xr.open_mfdataset(self.files, combine="by_coords").load()
        else:
            out = xr.concat(out, dim="time")
        return out

    def cleanup(self, ds):
        """Close the dataset and remove temporary files."""
        ds.close()
        for f in self.files + self.skipped:
            if f.exists():
                f.unlink()

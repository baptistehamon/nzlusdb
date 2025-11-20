"""Blueberry suitability climate indicators."""

import argparse

import lsapy.standardize as lstd
import numpy as np
import xarray as xr
from xclim.indicators import atmos
from xclim.indices.helpers import make_hourly_temperature

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf


@climdata
def chilling_hours(data, res):
    """Chilling hours between May 1 and Aug 31."""
    if "latitude" in data.coords:  # rename dims for 1km climate data
        data = data.rename({"latitude": "lat", "longitude": "lon"})
        data = data.chunk({"time": 365})

    # loop over years to avoid memory issues
    years = np.unique(data.time.dt.year.values)
    out = []
    for y in years[:-1]:
        _data = data.sel(time=slice(f"{y}-05-01", f"{y}-08-31")).convert_calendar("noleap")
        tas = make_hourly_temperature(_data["tasmin"], _data["tasmax"])
        ch = indicators.chilling_hours(tas, thresh="7 degC", date_bounds=("05-01", "08-31"), freq="YS-MAY")
        if res == "5km":
            fname = INDICATORPATH / f"tmp_chilling-hours_{y}_5km.nc"
            write_netcdf(ch, INDICATORPATH / f"tmp_chilling-hours_{y}_5km.nc", progressbar=True, verbose=False)
            out.append(fname)
        else:
            out.append(ch)

    if res == "25km":
        out = xr.concat(out, dim="time")
    if res == "5km":
        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["chilling_hours"]
        for f in fp:
            f.unlink()
    return out


@climdata
def frost_survival(data, res):
    """Frost survival from Sept 1 to Oct 31."""
    if res == "25km":
        data = data.chunk({"realization": 3})
        return indicators.frost_survival(
            data,
            func=lstd.vetharaniam2022_eq3,
            fparams={"a": 1.1, "b": -4.5},
            freq="YS-JUL",
            date_bounds=("09-01", "10-31"),
        )

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-04-30"))
            fs = indicators.frost_survival(
                data_yr,
                func=lstd.vetharaniam2022_eq3,
                fparams={"a": 1.1, "b": -4.5},
                freq="YS-JUL",
                date_bounds=("09-01", "10-31"),
            )
            fname = INDICATORPATH / f"tmp_frost_survival_{y}_5km.nc"
            write_netcdf(fs, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["frost_survival"]
        for f in fp:
            f.unlink()
        return out


@climdata
def growing_degree_days(data):
    """Growing degree days between Oct 1 and Apr 30."""
    return atmos.growing_degree_days(data, thresh="10 degC", freq="YS-JUL", date_bounds=("10-01", "04-30"))


def compute(resolution="5km"):
    """Compute and save all blueberry indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(
                climDS, scen, ["tas", "tasmax", "tasmin"], ens_kwargs={"calendar": "noleap"}
            )

            # Chilling Hours
            fname = f"ch7_0501-0831_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                ch = chilling_hours(
                    climDS, ["tasmin", "tasmax"], period=tperiod, freq="YS-MAY", offset={"months": 2}, res=climDS.res
                )
                write_netcdf(ch, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Frost Survival during Flowering
            fname = f"blueberry_frost-survival_0901-1031_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fsg = frost_survival(
                    climDS,
                    "tasmin",
                    period=tperiod,
                    units="",
                    res=climDS.res,
                )
                write_netcdf(fsg, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Growing Degree Days
            fname = f"gdd10_1001-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                gdd = growing_degree_days(climDS, "tas", period=tperiod, units="degC d")
                write_netcdf(gdd, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all blueberry climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

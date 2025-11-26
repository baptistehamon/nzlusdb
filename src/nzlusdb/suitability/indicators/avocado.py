"""Avocado suitability climate indicators."""

import argparse

import lsapy.standardize as lstd
import numpy as np
import xarray as xr
from xclim.indicators import atmos

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf


@climdata
def frost_survival(data, res):
    """Annual frost survival."""
    if res == "25km":
        data = data.chunk({"realization": 3})
        return indicators.frost_survival(
            data,
            func=lstd.vetharaniam2022_eq3,
            fparams={"a": 1.3, "b": -3},
            freq="YS-JUL",
        )

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            fs = indicators.frost_survival(
                data_yr,
                func=lstd.vetharaniam2022_eq3,
                fparams={"a": 1.3, "b": -3},
                freq="YS-JUL",
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
def tg_mean(data):
    """Mean annual temperature."""
    return atmos.tg_mean(data, freq="YS-JUL")


def compute(resolution="5km"):
    """Compute and save all avocado indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(climDS, scen, ["tas", "tasmin"], ens_kwargs={"calendar": "noleap"})

            # Frost Survival during Flowering
            fname = f"avocado_frost-survival_annual_{scen}_{climDS.res}.nc"
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

            # Mean Annual Temperature
            fname = f"tgm_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                tgm = tg_mean(climDS, "tas", period=tperiod, units="degC")
                write_netcdf(tgm, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all avocado climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

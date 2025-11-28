"""Kiwifruit suitability climate indicators."""

import argparse

import lsapy.standardize as lstd
import numpy as np
import xarray as xr
from xclim.core.calendar import select_time
from xclim.indicators import atmos

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import downweight_season, write_netcdf


# Define indicators
@climdata
def day_budbreak(data):
    """Day of budbreak."""
    return indicators.day_budbreak(data, freq="YS-MAY")


@climdata
def tg_mean(data):
    """Mean annual temperature between May 1 and Jul 31."""
    return atmos.tg_mean(data, freq="YS-MAY", date_bounds=("05-01", "07-31"))


@climdata
def growing_degree_days(data):
    """Growing degree days between Oct 1 and Apr 30."""
    return atmos.growing_degree_days(data, thresh="10 degC", freq="YS-JUL", date_bounds=("10-01", "04-30"))


@climdata
def frost_survival(data, dbb, res):
    """Frost survival during growing period (Aug 13 to Jun 30)."""

    def _downweight(data, start, end):
        weights = select_time(xr.where(data.notnull(), 1, np.nan), doy_bounds=(225, 181))
        weights = weights.rename("weight")
        weights["time"] = weights.indexes["time"].to_datetimeindex()
        weights = xr.where(weights.time.dt.dayofyear == 74, 0.5, weights)  # noqa: PLR2004
        weights = downweight_season(
            weights,
            "doy_bounds",
            {"start": (start, end), "end": (74, 181)},
            values=0,
            interp_method="linear",
            include_bounds=((True, False), (False, False)),
        )
        return weights

    if res == "25km":
        data = data.chunk({"realization": 3})
        weights = _downweight(data, 225, dbb)
        weights["time"] = data["time"]
        return indicators.frost_survival(
            data,
            weights,
            func=lstd.vetharaniam2022_eq3,
            fparams={"a": 1, "b": -2},
            freq="YS-JUL",
            doy_bounds=(dbb, 181),
        )

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            dbb_yr = dbb.sel(time=f"{y}-07-01")
            weights = _downweight(data_yr, 225, dbb_yr)
            weights["time"] = data_yr["time"]
            fs = indicators.frost_survival(
                data_yr,
                weights,
                func=lstd.vetharaniam2022_eq3,
                fparams={"a": 1, "b": -2},
                freq="YS-JUL",
                doy_bounds=(dbb_yr, 181),
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
def tn_min(data):
    """Minimum annual temperature."""
    return atmos.tn_min(data, freq="YS-JUL")


def compute(resolution="5km"):
    """Compute and save all kiwifruit climate indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(climDS, scen, ["tas", "tasmin"], ens_kwargs={"calendar": "noleap"})

            # Day of budbreak
            fname = f"kiwifruit_day_budbreak_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                dbb = day_budbreak(climDS, "tas", period=tperiod, units="", freq="YS-MAY", offset={"months": 2})
                write_netcdf(dbb, INDICATORPATH / fname, progressbar=True, verbose=True)
            dbb = xr.open_dataarray(INDICATORPATH / fname)

            # Mean Temperature
            fname = f"tgm_0501-0731_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                tgm = tg_mean(climDS, "tas", period=tperiod, units="degC", freq="YS-MAY", offset={"months": 2})
                write_netcdf(tgm, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Growing Degree Days
            fname = f"gdd10_1001-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                gdd = growing_degree_days(climDS, "tas", period=tperiod, units="degC d")
                write_netcdf(gdd, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Frost Survival during Growth
            fname = f"kiwifruit_frost_survival_225-181_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fsg = frost_survival(climDS, "tasmin", dbb=dbb, period=tperiod, units="", res=climDS.res)
                write_netcdf(fsg, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Minimum Temperature
            fname = f"tnn_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                tnm = tn_min(climDS, "tasmin", period=tperiod, units="degC", freq="YS-JUL")
                write_netcdf(tnm, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all kiwifruit climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

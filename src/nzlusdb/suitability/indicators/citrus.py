"""Citrus suitability climate indicators."""

import argparse

import xarray as xr
from xclim.indicators import atmos
from xclim.indices.generic import compare, count_occurrences

from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf


# Define indicators
@climdata
def prcptot(data):
    """Total annual precipitation."""
    return atmos.precip_accumulation(data, freq="YS-JUL")


@climdata
def tn_mean(data):
    """Mean minimum temperature between Aug 15 and Oct 15."""
    return atmos.tn_mean(data, freq="YS-JUL", date_bounds=("08-15", "10-15"))


@climdata
def tg_mean(data):
    """Mean annual temperature between Sep 15 and Nov 15."""
    return atmos.tg_mean(data, freq="YS-JUL", date_bounds=("09-15", "11-15"))


@climdata
def tx_mean(data):
    """Mean maximum temperature between Jan 1 and Feb 15."""
    return atmos.tx_mean(data, freq="YS-JUL", date_bounds=("01-01", "02-15"))


@climdata
def year_with_hot_week(data):
    """Number of years with at least one hot week (3 days over 35C in a 7-day period) between Dec 1 and Feb 28."""
    hd = atmos.hot_days(data, thresh="35 degC", freq="7D", date_bounds=("12-01", "02-28"))
    out = compare(hd, ">=", 3).assign_attrs(units="")
    out = count_occurrences(out, threshold="0", op=">", freq="YS-JUL")
    out = count_occurrences(out, threshold="1 week", op=">=", freq="YS-JUL")
    out = out.rename("year_with_hot_week")
    return out.where(data.isel(time=0).notnull())


def compute(resolution="5km"):
    """Compute and save all citrus climate indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(
                climDS, scen, ["pr", "tas", "tasmax", "tasmin"], ens_kwargs={"calendar": "noleap"}
            )

            # Total Precip
            fname = f"prcptot_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                prcptot_ds = prcptot(climDS, "pr", period=tperiod, units="mm/day")
                write_netcdf(prcptot_ds, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Mean Min Temperature
            fname = f"tnm_0815-1015_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                tnm = tn_mean(climDS, "tasmin", period=tperiod, units="degC", freq="YS-JUL")
                write_netcdf(tnm, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Mean Annual Temperature
            fname = f"tgm_0915-1115_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                tgm = tg_mean(climDS, "tas", period=tperiod, units="degC")
                write_netcdf(tgm, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Mean Max Temperature
            fname = f"txm_0101-0215_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                txm = tx_mean(climDS, "tasmax", period=tperiod, units="degC")
                write_netcdf(txm, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Years with Hot Week
            fname = f"years-7days-3txge35_1201-0228_10yr_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                yhw = year_with_hot_week(climDS, "tasmax", period=tperiod, freq="YS-JUL")
                # work around to handle historical and projection transition for rolling sum
                if scen != "historical":
                    histfile = f"years-7days-3txge35_1201-0228_10yr_annual_historical_{climDS.res}.nc"
                    hist = xr.open_dataarray(INDICATORPATH / histfile)
                    hist = hist.isel(time=slice(-9, None))
                    projtime = yhw.time.values
                    yhw = xr.concat([hist, yhw], dim="time")
                yhw = yhw.chunk({"time": -1}).rolling(time=10).sum()  # 10-yr rolling sum
                if scen != "historical":
                    yhw = yhw.sel(time=projtime)
                write_netcdf(yhw, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all citrus climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

"""Manuka suitability climate indicators."""

import argparse

from xclim.indicators import atmos

from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf


# Define indicators
@climdata
def tx_mean(data):
    """Mean maximum temperature between Oct 15 and Jan 31."""
    return atmos.tx_mean(data, freq="YS-JUL", date_bounds=("10-15", "01-31"))


@climdata
def tn_mean(data):
    """Mean minimum temperature between Jun 22 and Sep 22."""
    return atmos.tn_mean(data, freq="YS-JUN", date_bounds=("06-22", "09-22"))


def compute(resolution="5km"):
    """Compute and save all manuka climate indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(climDS, scen, ["tasmax", "tasmin"], ens_kwargs={"calendar": "noleap"})

            # Mean Max Temperature
            fname = f"txm_1015-0131_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
                continue
            else:
                txm = tx_mean(climDS, "tasmax", period=tperiod, units="degC")
                write_netcdf(txm, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Mean Min Temperature
            fname = f"tnm_0622-0922_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
                continue
            else:
                tnm = tn_mean(climDS, "tasmin", period=tperiod, units="degC", freq="YS-JUN", offset={"months": 1})
                write_netcdf(tnm, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all manuka climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

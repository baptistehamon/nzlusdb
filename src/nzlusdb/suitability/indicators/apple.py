"""Apple suitability climate indicators."""

import argparse

import lsapy.standardize as lstd
import numpy as np
import xarray as xr
import xclim
from xclim.compute.helpers import make_hourly_temperature
from xclim.core.calendar import days_since_to_doy, doy_to_days_since, select_time
from xclim.indicators import atmos

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH, LoopOverYearsWithPath
from nzlusdb.utils import downweight, downweight_season, write_netcdf

xclim.set_options(as_dataset=False)


# Define indicators
@climdata
def day_full_bloom(data):
    """Day of full bloom."""
    return indicators.day_full_bloom(data, freq="YS-JUL")


@climdata
def chill_units(data, tmp_files=True, year_break=None):
    """Chill units between May 1 and Aug 31."""

    def _yearly_chill_units(data):
        # keep only relevant time period to compute hourly temperature
        data = select_time(data, date_bounds=("05-01", "08-31"), drop=True)
        tas = make_hourly_temperature(data["tasmin"], data["tasmax"]).astype("float32")
        return atmos.chill_units(tas, date_bounds=("05-01", "08-31"), freq="YS-MAY").astype("float32")

    # rename lat/lon if needed for 5km data
    data = data.rename({"latitude": "lat", "longitude": "lon"}) if "latitude" in data.coords else data

    loop = LoopOverYearsWithPath(data, _yearly_chill_units, freq="YS-MAY", filename="tmp_chill_units_<YEAR>.nc")
    cu = loop(tmp_files=tmp_files, year_break=year_break)
    return cu, loop


@climdata
def growing_degree_days(data):
    """Growing degree days between Oct 1 and Apr 30."""
    return atmos.growing_degree_days(data, thresh="10 degC", freq="YS-JUL", date_bounds=("10-01", "04-30"))


@climdata
def growing_degree_days_dfb(data, dfb, tmp_files=True, year_break=None):
    """Growing degree days between day of full bloom and 50 days after."""

    def _yearly_gdd_dfb(data, dfb, end):
        return atmos.growing_degree_days(data, thresh="10 degC", freq="YS-JUL", doy_bounds=(dfb, end))

    end = days_since_to_doy(doy_to_days_since(dfb) + 50)
    loop = LoopOverYearsWithPath(data, _yearly_gdd_dfb, freq="YS-JUL", filename="tmp_gdd_dfb_<YEAR>.nc")
    gdd_dfb = loop(dfb=dfb, end=end, tmp_files=True, year_break=year_break)
    return gdd_dfb, loop


@climdata
def frost_survival(data, dfb, tmp_files=True, year_break=None):
    """Frost survival during growing period (from 3 weeks before full bloom to end of April)."""

    def _downweight(data, start, end):
        weights = select_time(xr.where(data.notnull(), 1, np.nan), doy_bounds=(start, 120)).astype("float32")
        weights = weights.rename("weight")
        weights = downweight_season(
            weights, "doy_bounds", {"start": (start, end), "end": (91, 120)}, values=0, interp_method="linear"
        )
        return weights

    def _yearly_fsg(data, dfb):
        start = days_since_to_doy(doy_to_days_since(dfb) - 21)
        end = days_since_to_doy(doy_to_days_since(start) + 8)
        weights = _downweight(data, start, end)
        return indicators.frost_survival(
            data,
            weights,
            func=lstd.vetharaniam2022_eq3,
            fparams={"a": 1, "b": -3},
            freq="YS-JUL",
            doy_bounds=(start, 120),
        )

    loop = LoopOverYearsWithPath(data, _yearly_fsg, freq="YS-JUL", filename="tmp_frost_survival_<YEAR>.nc")
    fsg = loop(dfb=dfb, tmp_files=tmp_files, year_break=year_break)
    return fsg, loop


@climdata
def sunburn_survival(data, tmp_files=True, year_break=None):
    """Sunburn survival from Oct 1 to Apr 30."""

    def _downweight(data):
        weights = select_time(xr.where(data.notnull(), 1, np.nan), date_bounds=("10-01", "04-30")).astype("float32")
        weights = weights.rename("weight")
        weights = downweight(weights, "date_bounds", ("04-01", "04-30"), downweight_to=0)
        return weights

    def _yearly_sbs(data):
        weights = _downweight(data)
        return indicators.sunburn_survival(
            data,
            weights,
            func=lstd.logistic,
            fparams={"a": -0.52, "b": 37.5},
            freq="YS-JUL",
            date_bounds=("10-01", "04-30"),
        )

    loop = LoopOverYearsWithPath(data, _yearly_sbs, freq="YS-JUL", filename="tmp_sunburn_survival_<YEAR>.nc")
    sbs = loop(tmp_files=tmp_files, year_break=year_break)
    return sbs, loop


def compute(resolution="5km"):
    """Compute and save all apple climate indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            period = open_climdata_timeserie(
                climDS, scen, ["tas", "tasmax", "tasmin"], ens_kwargs={"calendar": "noleap"}
            )

            # Day of Full Bloom
            fname = f"apple_day_full_bloom_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                chunks = {"latitude": 52, "time": -1} if climDS.res == "5km" else {}
                dfb = day_full_bloom(
                    climDS, scen, "tasmax", units="", open_kwargs={"ens_kwargs": {"calendar": "noleap"}}, chunks=chunks
                )
                write_netcdf(dfb, INDICATORPATH / fname, progressbar=True, verbose=True)
            dfb = xr.open_dataarray(INDICATORPATH / fname)

            # Chill Units
            fname = f"cu_0501-0831_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                cu, loop = chill_units(
                    # climdata decorator params
                    climDS,
                    scen,
                    ["tasmin", "tasmax"],
                    freq="YS-MAY",
                    offset={"months": 2},
                    open_kwargs={"ens_kwargs": {"calendar": "noleap"}},
                    chunks={"time": xr.groupers.TimeResampler("YS-MAY")},
                    # LoopOverYears params
                    tmp_files=True if climDS.res == "5km" else False,
                )
                write_netcdf(cu, INDICATORPATH / fname, progressbar=True, verbose=True)
                loop.cleanup(cu)

            # Growing Degree Days
            fname = f"gdd10_1001-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                gdd = growing_degree_days(
                    climDS, scen, "tas", units="degC d", chunks={"time": xr.groupers.TimeResampler("YS-JUL")}
                )
                write_netcdf(gdd, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Growing Degree Days from Day of Full Bloom
            fname = f"apple_gdd10_dfb-dfb50d_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                gdd_dfb, loop = growing_degree_days_dfb(
                    # climdata decorator params
                    climDS,
                    scen,
                    "tas",
                    dfb=dfb,
                    units="degC d",
                    chunks={"time": xr.groupers.TimeResampler("YS-JUL")},
                    # LoopOverYears params
                    tmp_files=True if climDS.res == "5km" else False,
                )
                gdd_dfb = growing_degree_days_dfb(climDS, "tas", dfb=dfb, period=period, units="degC d", res=climDS.res)
                write_netcdf(gdd_dfb, INDICATORPATH / fname, progressbar=True, verbose=True)
                loop.cleanup(gdd_dfb)

            # Frost Survival during Growth
            fname = f"apple_frost-survival_dfb-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fsg, loop = frost_survival(
                    # climdata decorator params
                    climDS,
                    scen,
                    "tasmin",
                    dfb=dfb,
                    units="",
                    chunks={"time": xr.groupers.TimeResampler("YS-JUL")},
                    # LoopOverYears params
                    tmp_files=True if climDS.res == "5km" else False,
                )
                write_netcdf(fsg, INDICATORPATH / fname, progressbar=True, verbose=True)
                loop.cleanup(fsg)

            # Sunburn Survival
            fname = f"apple_sunburn-survival_1001-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                sbs, loop = sunburn_survival(
                    # climdata decorator params
                    climDS,
                    scen,
                    "tasmax",
                    units="",
                    chunks={"time": xr.groupers.TimeResampler("YS-JUL")},
                    # LoopOverYears params
                    tmp_files=True if climDS.res == "5km" else False,
                    year_break=2,
                )
                write_netcdf(sbs, INDICATORPATH / fname, progressbar=True, verbose=True)
                loop.cleanup(sbs)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all apple climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

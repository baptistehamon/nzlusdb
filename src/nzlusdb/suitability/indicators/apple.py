"""Apple suitability climate indicators."""

import argparse

import numpy as np
import xarray as xr
import xclim.indices as xci
from xclim.core.calendar import days_since_to_doy, doy_to_days_since, select_time
from xclim.indicators import atmos
from xclim.indices.helpers import make_hourly_temperature

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import downweight, downweight_season, write_netcdf


# Define indicators
@climdata
def day_full_bloom(data):
    """Day of full bloom."""
    return indicators.day_full_bloom(data, freq="YS-JUL")


@climdata
def chill_units(data, res):
    """Chill units between May 1 and Aug 31."""
    if "latitude" in data.coords:  # rename dims for 1km climate data
        data = data.rename({"latitude": "lat", "longitude": "lon"})
        data = data.chunk({"time": 365})

    # loop over years to avoid memory issues
    year = np.unique(data.time.dt.year.values)
    out = []
    for y in year[:-1]:
        _data = data.sel(time=slice(f"{y}-05-01", f"{y}-08-31")).convert_calendar("noleap")
        tas = make_hourly_temperature(_data["tasmin"], _data["tasmax"])
        cu = atmos.chill_units(tas, date_bounds=("05-01", "08-31"), freq="YS-MAY")
        if res == "5km":
            fname = INDICATORPATH / f"temp_chill_units_{y}_5km_temp.nc"
            write_netcdf(cu, INDICATORPATH / f"temp_chill_units_{y}_5km_temp.nc", progressbar=True, verbose=False)
            out.append(fname)
        else:
            out.append(cu)

    if res == "25km":
        out = xr.concat(out, dim="time")
    if res == "5km":
        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["cu"]
        for f in fp:
            f.unlink()
    return out


@climdata
def growing_degree_days(data):
    """Growing degree days between Oct 1 and Apr 30."""
    return atmos.growing_degree_days(data, thresh="10 degC", freq="YS-JUL", date_bounds=("10-01", "04-30"))


@climdata
def growing_degree_days_dfb(data, dfb, res):
    """Growing degree days between day of full bloom and 50 days after."""
    end = days_since_to_doy(doy_to_days_since(dfb) + 50)
    if res == "25km":
        return atmos.growing_degree_days(data, thresh="10 degC", freq="YS-JUL", doy_bounds=(dfb, end))
    elif res == "5km":
        # use index to avoid memory issues with indicator health checks
        _data = select_time(data, doy_bounds=(dfb, end))
        out = xci.growing_degree_days(_data, thresh="10 degC", freq="YS-JUL")
        out = out.where(data.isel(time=0).notnull(), np.nan)
        das, params, dsattrs = atmos.growing_degree_days._parse_variables_from_call(
            args=[data], kwds={"thresh": "10 degC", "freq": "YS-JUL"}
        )
        attrs = atmos.growing_degree_days._update_attrs(
            args=params,
            das=das,
            attrs=atmos.growing_degree_days.cf_attrs[0],
            names=atmos.growing_degree_days._cf_names,
            var_id=None,
        )
        out.attrs.update(attrs)
        return out


@climdata
def frost_survival(data, dfb):
    """Frost survival during growth period (from 3 weeks before full bloom to end of April)."""
    data = data.chunk({"realization": 3})
    start = days_since_to_doy(doy_to_days_since(dfb) - 21)
    end = days_since_to_doy(doy_to_days_since(start) + 8)

    weights = select_time(xr.where(data.notnull(), 1, np.nan), doy_bounds=(start, 120))
    weights = weights.rename("weight")
    weights = downweight_season(
        weights, "doy_bounds", {"start": (start, end), "end": (91, 120)}, values=0, interp_method="linear"
    )

    return indicators.frost_survival(data, weights, freq="YS-JUL", doy_bounds=(start, 120))


@climdata
def sunburn_survival(data):
    """Sunburn survival from Oct 1 to Apr 30."""
    data = data.chunk({"realization": 3})
    weights = select_time(xr.where(data.notnull(), 1, np.nan), date_bounds=("10-01", "04-30"))
    weights = weights.rename("weight")
    weights = downweight(weights, "date_bounds", ("04-01", "04-30"), downweight_to=0)

    return indicators.sunburn_survival(data, weights, freq="YS-JUL", date_bounds=("10-01", "04-30"))


def compute(resolution="5km"):
    """Compute and save all apple climate indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(
                climDS, scen, ["tas", "tasmax", "tasmin"], ens_kwargs={"calendar": "noleap"}
            )

            # Day of Full Bloom
            fname = f"apple_day_full_bloom_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                dfb = day_full_bloom(climDS, "tasmax", period=tperiod, units="")
                write_netcdf(dfb, INDICATORPATH / fname, progressbar=True, verbose=True)
            dfb = xr.open_dataarray(INDICATORPATH / fname)

            # Chill Units
            fname = f"cu_0501-0831_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                cu = chill_units(
                    climDS, ["tasmin", "tasmax"], period=tperiod, freq="YS-MAY", offset={"months": 2}, res=climDS.res
                )
                write_netcdf(cu, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Growing Degree Days
            fname = f"gdd10_1001-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                gdd = growing_degree_days(climDS, "tas", period=tperiod, units="degC d")
                write_netcdf(gdd, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Growing Degree Days from Day of Full Bloom
            fname = f"apple_gdd10_dfb-dfb50d_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                gdd_dfb = growing_degree_days_dfb(
                    climDS, "tas", dfb=dfb, period=tperiod, units="degC d", res=climDS.res
                )
                write_netcdf(gdd_dfb, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Frost Survival during Growth
            fname = f"apple_frost-survival_dfb-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fsg = frost_survival(climDS, "tasmin", dfb=dfb, period=tperiod, units="")
                write_netcdf(fsg, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Sunburn Survival
            fname = f"apple_sunburn-survival_1001-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                sbs = sunburn_survival(climDS, "tasmax", period=tperiod, units="")
                write_netcdf(sbs, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all apple climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

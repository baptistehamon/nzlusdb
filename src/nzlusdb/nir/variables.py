"""NIR inputs variables computation."""

import argparse

import xarray as xr
from xclim.core.units import convert_units_to
from xclim.indicators.convert import potential_evapotranspiration as _potential_evapotranspiration
from xclim.indices.helpers import wind_speed_height_conversion as _wind_speed_height_conversion

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf


@climdata
def potential_evapotranspiration(data: xr.Dataset) -> xr.DataArray:
    """Return potential evapotranspiration computed with the Hargreaves method."""
    return _potential_evapotranspiration(ds=data, method="hargreaves85")


@climdata
def daily_effective_precipitation(pr):
    """Daily effective precipitation computed from daily total precipitation."""
    return indicators.daily_effective_precipitation(pr=pr)


@climdata
def minimum_relative_humidity(data: xr.Dataset) -> xr.DataArray:
    """Minimum relative humidity computed from daily minimum and maximum temperature."""
    return indicators.minimum_relative_humidity(tasmin=data["tasmin"], tasmax=data["tasmax"])


@climdata
def wind_speed_height_conversion(wind):
    """Convert wind speed from 10 m to 2 m height."""
    return _wind_speed_height_conversion(wind, "10 m", "2 m")


def compute(resolution="5km"):
    """Compute and save all NIR input variables."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(
                climDS, scen, ["pr", "tasmax", "tasmin", "sfcWind"], ens_kwargs={"calendar": "noleap"}
            )

            # Potential Evapotranspiration
            fname = f"etp_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                etp = potential_evapotranspiration(climDS, ["tasmax", "tasmin"], period=tperiod, freq="YS-JUL")
                etp = convert_units_to(etp, "mm/day", context="hydro")
                write_netcdf(etp, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Effective Precipitation
            fname = f"peff_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                peff = daily_effective_precipitation(climDS, "pr", period=tperiod, freq="YS-JUL")
                write_netcdf(peff, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Minimum Relative Humidity
            fname = f"hursmin_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                hursmin = minimum_relative_humidity(climDS, ["tasmin", "tasmax"], period=tperiod, freq="YS-JUL")
                del hursmin.attrs["standard_name"]
                write_netcdf(hursmin, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Wind Speed Height Conversion
            fname = f"wind_speed_2m_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                windspd = wind_speed_height_conversion(climDS, "sfcWind", period=tperiod, freq="YS-JUL")
                write_netcdf(windspd, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all NIR input variables.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

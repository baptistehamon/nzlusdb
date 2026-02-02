"""Sauvignon blanc suitability climate indicators."""

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


# Define indicators
@climdata
def day_budbreak(data):
    """Day of budbreak."""
    return atmos.degree_days_exceedance_date(
        data,
        thresh="10 degC",
        sum_thresh="59 K days",
        op=">=",
        after_date="07-01",
        never_reached="06-30",
        freq="YS-JUL",
    )


@climdata
def flowering(data):
    """Day of flowering."""
    return atmos.degree_days_exceedance_date(
        data,
        thresh="0 degC",
        sum_thresh="1282 K days",
        op=">=",
        after_date="08-29",
        never_reached="06-30",
        freq="YS-JUL",
    )


@climdata
def veraison(data):
    """Day of veraison."""
    return atmos.degree_days_exceedance_date(
        data,
        thresh="0 degC",
        sum_thresh="2528 K days",
        op=">=",
        after_date="08-29",
        never_reached="06-30",
        freq="YS-JUL",
    )


@climdata
def ripeness(data):
    """Day of ripeness."""
    return atmos.degree_days_exceedance_date(
        data,
        thresh="0 degC",
        sum_thresh="2820 K days",
        op=">=",
        after_date="09-29",
        never_reached="06-30",
        freq="YS-JUL",
    )


@climdata
def chilling_hours(data, res):
    """Chilling hours between Jun 1 and Aug 31."""
    if "latitude" in data.coords:  # rename dims for 1km climate data
        data = data.rename({"latitude": "lat", "longitude": "lon"})
        data = data.chunk({"time": 365})

    # loop over years to avoid memory issues
    years = np.unique(data.time.dt.year.values)
    out = []
    for y in years[:-1]:
        _data = data.sel(time=slice(f"{y}-06-01", f"{y}-08-31")).convert_calendar("noleap")
        tas = make_hourly_temperature(_data["tasmin"], _data["tasmax"])
        ch = indicators.chilling_hours(tas, low="0 degC", high="7 degC", date_bounds=("06-01", "08-31"), freq="YS-JUN")
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
def frost_survival(data, dbb, veraison, res):
    """Frost survival from budbreak to veraison."""
    if res == "25km":
        data = data.chunk({"realization": 3})
        return indicators.frost_survival(
            data, func=lstd.logistic, fparams={"a": 1.099, "b": -1.7}, freq="YS-JUL", doy_bounds=(dbb, veraison)
        )

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            fs = indicators.frost_survival(
                data_yr, func=lstd.logistic, fparams={"a": 1.099, "b": -1.7}, freq="YS-JUL", doy_bounds=(dbb, veraison)
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
def heat_survival(data, veraison, ripeness, res):
    """Heat survival from veraison to ripeness."""
    if res == "25km":
        data = data.chunk({"realization": 3})
        return indicators.heat_survival(
            data, func=lstd.logistic, fparams={"a": -0.3213, "b": 52}, freq="YS-JUL", doy_bounds=(veraison, ripeness)
        )

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            fs = indicators.heat_survival(
                data_yr,
                func=lstd.logistic,
                fparams={"a": -0.3213, "b": 52},
                freq="YS-JUL",
                doy_bounds=(veraison, ripeness),
            )
            fname = INDICATORPATH / f"tmp_heat_survival_{y}_5km.nc"
            write_netcdf(fs, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["heat_survival"]
        for f in fp:
            f.unlink()
        return out


@climdata
def prcptot(data):
    """Total precipitation between Mar 1 and Apr 30."""
    return atmos.precip_accumulation(data, freq="YS-JUL", date_bounds=("03-01", "04-30"))


def compute(resolution="5km"):  # noqa: PLR0912, PLR0914, PLR0915
    """Compute and save all Sauvignon blanc climate indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(
                climDS, scen, ["tas", "tasmax", "tasmin", "pr"], ens_kwargs={"calendar": "noleap"}
            )

            # PHENOLOGY
            # Day of Budbreak
            fname = f"sauvignonblanc_day-budbreak_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                dbb = day_budbreak(climDS, "tas", period=tperiod)
                write_netcdf(dbb, INDICATORPATH / fname, progressbar=True, verbose=True)
            dbb = xr.open_dataarray(INDICATORPATH / fname)

            # Day of Flowering
            fname = f"sauvignonblanc_flowering_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                flow = flowering(climDS, "tas", period=tperiod)
                write_netcdf(flow, INDICATORPATH / fname, progressbar=True, verbose=True)
            flow = xr.open_dataarray(INDICATORPATH / fname)

            # Day of Veraison
            fname = f"sauvignonblanc_veraison_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                ver = veraison(climDS, "tas", period=tperiod)
                write_netcdf(ver, INDICATORPATH / fname, progressbar=True, verbose=True)
            ver = xr.open_dataarray(INDICATORPATH / fname)

            # Day of Ripeness
            fname = f"sauvignonblanc_ripeness_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                rip = ripeness(climDS, "tas", period=tperiod)
                write_netcdf(rip, INDICATORPATH / fname, progressbar=True, verbose=True)
            rip = xr.open_dataarray(INDICATORPATH / fname)

            # CLIMATE INDICATORS
            # Chilling Hours
            fname = f"0ch7_0601-0831_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                ch = chilling_hours(
                    climDS, ["tasmin", "tasmax"], period=tperiod, freq="YS-JUN", offset={"months": 1}, res=climDS.res
                )
                write_netcdf(ch, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Frost Survival from Budbreak to 31 Dec
            fname = f"sauvignonblanc_frost-survival_budbreak-veraison_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fs = frost_survival(climDS, "tasmin", dbb=dbb, veraison=ver, period=tperiod, units="", res=climDS.res)
                write_netcdf(fs, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Heat Survival from Veraison to Ripeness
            fname = f"sauvignonblanc_heat-survival_veraison-ripeness_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                hs = heat_survival(
                    climDS, "tasmax", veraison=ver, ripeness=rip, period=tperiod, units="", res=climDS.res
                )
                write_netcdf(hs, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Total Precipitation Mar-Apr
            fname = f"prcptot_0301-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                prtot = prcptot(climDS, "pr", period=tperiod, units="mm")
                write_netcdf(prtot, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all Sauvignon blanc climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

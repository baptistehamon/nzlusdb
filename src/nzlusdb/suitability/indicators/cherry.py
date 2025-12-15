"""Cherry suitability climate indicators."""

import argparse

import lsapy.standardize as lstd
import numpy as np
import xarray as xr
from xclim.core.calendar import doy_to_days_since
from xclim.indicators import atmos
from xclim.indices.generic import first_occurrence
from xclim.indices.helpers import make_hourly_temperature

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata, open_climdata_timeserie
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf


# Define indicators
@climdata
def difference_cumulative_sum(data, res, weight=None):
    """Annual cumulative sum of daily difference above 4.5 degC."""
    if weight is not None:
        data = (data * weight).assign_attrs(data.attrs)

    if res == "25km":
        out = atmos.growing_degree_days(data, thresh="4.5 degC", freq=None, date_bounds=("07-15", "04-30"))
        out = out.resample(time="YS-JUL").cumsum(dim="time")
        out = out.where(data.notnull(), np.nan)
        fp = None

    elif res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            gdd = atmos.growing_degree_days(data_yr, thresh="4.5 degC", freq=None, date_bounds=("07-15", "04-30"))
            gdd = gdd.resample(time="YS-JUL").cumsum(dim="time")
            gdd = gdd.where(data_yr.notnull(), np.nan)
            fname = INDICATORPATH / f"tmp_diffcumsum4.5_{y}_5km.nc"
            write_netcdf(gdd, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords")["growing_degree_days"]

    return (out, fp)


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
        ch = indicators.chilling_hours(tas, thresh="7 degC", date_bounds=("06-01", "08-31"), freq="YS-JUN")
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
def growing_degree_days_dbb(data, dbb, res):
    """Growing degree days between day of budbreak and Apr 30."""
    if res == "25km":
        out = atmos.growing_degree_days(data, thresh="4.5 degC", freq="YS-JUL", doy_bounds=(dbb, 120))

    elif res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-04-30"))
            gdd = atmos.growing_degree_days(data_yr, thresh="4.5 degC", freq="YS-JUL", doy_bounds=(dbb, 120))
            fname = INDICATORPATH / f"tmp_gdd4.5_{y}_5km.nc"
            write_netcdf(gdd, fname, progressbar=True, verbose=False)
            out.append(fname)
        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["growing_degree_days"]
        for f in fp:
            f.unlink()

    return out


@climdata
def frost_survival(data, weight, res):
    """Frost survival during growing period (from open cluster to ripening)."""
    if res == "25km":
        data = data.chunk({"realization": 3})
        return indicators.frost_survival(
            data, weight, func=lstd.logistic, fparams={"a": 1.099, "b": -3.4}, freq="YS-JUL"
        )

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            weight_yr = weight.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            fs = indicators.frost_survival(
                data_yr, weight_yr, func=lstd.logistic, fparams={"a": 1.099, "b": -3.4}, freq="YS-JUL"
            )
            fname = INDICATORPATH / f"tmp_frost_survival_{y}_5km.nc"
            write_netcdf(fs, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["frost_survival"]
        for f in fp:
            f.unlink()
        return out


def budbreak_to_31dec(day_budbreak):
    """Days from budbreak to 31 Dec."""
    days_31dec = doy_to_days_since(xr.full_like(day_budbreak, 365), "07-01")
    days_budbreak = doy_to_days_since(day_budbreak, "07-01")
    out = (days_31dec - days_budbreak).clip(min=0).rename("days_budbreak_to_31dec").assign_attrs(units="days")
    out = xr.apply_ufunc(
        lstd.logistic,
        out,
        kwargs={"a": 0.2478, "b": 77},
        dask="parallelized",
    ).convert_calendar("standard")
    return out


def frost_cold(frost_survival, days_budbreak_to_31dec):
    """Frost and cold indicator as the product of frost survival and days from budbreak to 31 Dec."""
    return (frost_survival * days_budbreak_to_31dec).rename("frost_cold").assign_attrs(units="")


@climdata
def cracking_survival(data, weight, res):
    """Cracking survival from Nov 1 to ripening."""
    data = data.chunk({"realization": 3})
    if res == "25km":
        return indicators.cracking_survival(
            data,
            weight,
            func=lstd.logistic,
            fparams={"a": -0.1108, "b": 109.9},
            freq="YS-JUL",
            date_bounds=("11-01", "06-30"),
        )

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            weight_yr = weight.sel(time=slice(f"{y}-07-01", f"{y + 1}-06-30"))
            ss = indicators.cracking_survival(
                data_yr,
                weight_yr,
                func=lstd.logistic,
                fparams={"a": -0.1108, "b": 109.9},
                freq="YS-JUL",
                date_bounds=("11-01", "06-30"),
            )
            fname = INDICATORPATH / f"tmp_craking_survival_{y}_5km.nc"
            write_netcdf(ss, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["cracking_survival"]
        for f in fp:
            f.unlink()
        return out


def compute(resolution="5km"):  # noqa: PLR0912, PLR0914, PLR0915
    """Compute and save all cherry climate indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(
                climDS, scen, ["tas", "tasmax", "tasmin", "hurs"], ens_kwargs={"calendar": "noleap"}
            )

            # PHENOLOGY
            # Cumulative Difference Sum above 4.5 degC
            fname = f"cherry_diff-cumsum4.5_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
                fp = None
            else:
                diffcumsum, fp = difference_cumulative_sum(
                    climDS, "tas", period=tperiod, units="degC d", convert_calendar=False, res=climDS.res
                )
                write_netcdf(diffcumsum, INDICATORPATH / fname, progressbar=True, verbose=True)
            diffcumsum = xr.open_dataarray(INDICATORPATH / fname, chunks={"time": 365, "realization": 2})
            if fp is not None:
                for f in fp:
                    f.unlink()

            # Budbreak Probability
            fname = f"cherry_budbreak-probability_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                dbb_prob = (
                    xr.apply_ufunc(
                        lstd.logistic,
                        diffcumsum,
                        kwargs={"a": 0.1446, "b": 174},
                        dask="parallelized",
                    )
                    .rename("budbreak_probability")
                    .assign_attrs(units="1")
                )
                write_netcdf(dbb_prob, INDICATORPATH / fname, progressbar=True, verbose=True)
            dbb_prob = xr.open_dataarray(INDICATORPATH / fname, chunks={"time": 365, "realization": 2})

            # Day of Budbreak
            fname = f"cherry_day_budbreak_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                dbb = first_occurrence(dbb_prob, threshold="0.5", op=">=", freq="YS-JUL").rename("day_budbreak")
                dbb = dbb.assign_attrs(units="", is_dayofyear=np.int32(1))
                write_netcdf(dbb, INDICATORPATH / fname, progressbar=True, verbose=True)
            dbb = xr.open_dataarray(INDICATORPATH / fname)

            # Open-cluster Probability
            fname = f"cherry_open-cluster-probability_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                oc_prob = xr.apply_ufunc(
                    lstd.logistic,
                    diffcumsum,
                    kwargs={"a": 0.1156, "b": 211},
                    dask="parallelized",
                ).rename("open_cluster_probability")
                write_netcdf(oc_prob, INDICATORPATH / fname, progressbar=True, verbose=True)
            oc_prob = xr.open_dataarray(INDICATORPATH / fname, chunks={"time": 365, "realization": 2})

            # Ripening Probability
            fname = f"cherry_ripening-probability_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                weighted_diffcumsum, fp = difference_cumulative_sum(
                    climDS,
                    weight=dbb_prob,
                    variable="tas",
                    period=tperiod,
                    units="degC d",
                    convert_calendar=False,
                    res=climDS.res,
                )
                write_netcdf(
                    weighted_diffcumsum,
                    INDICATORPATH / "tmp_weighted-diffcumsum4.5.nc",
                    progressbar=True,
                    verbose=False,
                )
                weighted_diffcumsum = xr.open_dataarray(
                    INDICATORPATH / "tmp_weighted-diffcumsum4.5.nc", chunks={"time": 365, "realization": 2}
                )
                ripening_prob = xr.apply_ufunc(
                    lstd.vetharaniam2022_eq5,
                    weighted_diffcumsum,
                    kwargs={"a": -0.8482, "b": 839.1},
                    dask="parallelized",
                ).rename("ripening_probability")
                write_netcdf(ripening_prob, INDICATORPATH / fname, progressbar=True, verbose=True)
                weighted_diffcumsum.close()
                (INDICATORPATH / "tmp_weighted-diffcumsum4.5.nc").unlink()
                if fp is not None:
                    for f in fp:
                        f.unlink()
            ripening_prob = xr.open_dataarray(INDICATORPATH / fname, chunks={"time": 365, "realization": 2})

            # Open-cluster to Ripening Probability
            fname = f"cherry_oc-to-ripening-probability_daily_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                oc_to_ripening_prob = (oc_prob * (1 - ripening_prob)).rename("open_cluster_to_ripening_probability")
                write_netcdf(oc_to_ripening_prob, INDICATORPATH / fname, progressbar=True, verbose=True)
            oc_to_ripening_prob = xr.open_dataarray(INDICATORPATH / fname, chunks={"time": 365, "realization": 2})

            # CLIMATE INDICATORS
            # Chilling Hours
            fname = f"ch7_0601-0831_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                ch = chilling_hours(
                    climDS, ["tasmin", "tasmax"], period=tperiod, freq="YS-JUN", offset={"months": 1}, res=climDS.res
                )
                write_netcdf(ch, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Growing Degree Days from Day of Budbreak
            fname = f"cherry_gdd4.5_dbb-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                gdd_dbb = growing_degree_days_dbb(
                    climDS, "tas", dbb=dbb, period=tperiod, units="degC d", res=climDS.res
                )
                write_netcdf(gdd_dbb, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Frost Survival during Growth
            fname = f"cherry_frost-survival_opencluster-ripening_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fsg = frost_survival(
                    climDS, "tasmin", weight=oc_to_ripening_prob, period=tperiod, units="", res=climDS.res
                )
                write_netcdf(fsg, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Time from Budbreak to 31 Dec
            fname = f"cherry_days-budbreak-to-31dec_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                dbb_to_31dec = budbreak_to_31dec(dbb)
                write_netcdf(dbb_to_31dec, INDICATORPATH / fname, progressbar=True, verbose=True)
            dbb_to_31dec = xr.open_dataarray(INDICATORPATH / fname)

            # Frost and Cold
            fname = f"cherry_frost-cold_opencluster-ripening_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fc = frost_cold(fsg, dbb_to_31dec)
                write_netcdf(fc, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Craking Survival
            fname = f"cherry_cracking-survival_1101-ripening_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                cs = cracking_survival(
                    climDS, "hurs", weight=(1 - ripening_prob), period=tperiod, units="", res=climDS.res
                )
                write_netcdf(cs, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all cherry climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

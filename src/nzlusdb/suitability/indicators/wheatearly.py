"""Early wheat suitability climate indicators."""

import argparse

import numpy as np
import pynar as pn
import xarray as xr
from xclim.core.calendar import days_since_to_doy, doy_to_days_since
from xclim.indicators import atmos
from xclim.indices.generic import count_occurrences

from nzlusdb.core.climdataset import TIMEPERIOD, climateDS, climdata, open_climdata_timeserie, select_hist_proj
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf

# Define phenology parameters for wheat
PHENO_PARAMS = {
    "sensiphot": 0,
    "phobase": 6.3,
    "phosat": 20,
    "optimum_temp": 6.5,
    "thermal_sensi": 10,
    "vern_mindays": 7,
    "vern_ndays": 35,
    "tmin_thresh": 0,
    "tmax_thresh": 25,
    "tstop_thresh": 100,
}


# Define indicators
def _rename_latlon(data):
    """Rename latitude and longitude dimensions to lat and lon."""
    if "latitude" in data.coords:  # rename dims for 1km climate data
        data = data.rename({"latitude": "lat", "longitude": "lon"})
    return data


def _select_pheno_climdata(climds, tperiod):
    """
    Select climate data for phenology indicators.

    'climdata' decorator cannot be used here because of how pynar masks data.
    """
    data = climds.data["tas"]
    if tperiod == "historical":
        proj_startdate = "2015-01-01"
    else:
        proj_startdate = "2014-01-01"
    data = select_hist_proj(data, tperiod, TIMEPERIOD[0], TIMEPERIOD[1], proj_startdate, freq="YS")
    return _rename_latlon(data.chunk(climds.chunks))


def emergence(climds, tperiod):
    """Day of crop emergence."""
    data = _select_pheno_climdata(climds, tperiod)

    return pn.phenological_stage(
        data,
        thresh=120,
        params=PHENO_PARAMS,
        is_photoperiod=False,
        is_vernalisation=False,
        start_cycle_doy=105,  # sowing date: Apr 15
        freq="YS-APR",
    )


def ear_1cm(climds, tperiod, s1):
    """Day of ear 1cm."""
    data = _select_pheno_climdata(climds, tperiod)

    return pn.phenological_stage(
        data,
        thresh=210,
        params=PHENO_PARAMS,
        is_photoperiod=True,
        is_vernalisation=True,
        start_cycle_doy=105,  # sowing date: Apr 15
        from_doy=s1,
        freq="YS-APR",
    )


def flag_leaf(climds, tperiod, s2):
    """Day of flag leaf."""
    data = _select_pheno_climdata(climds, tperiod)

    return pn.phenological_stage(
        data,
        thresh=260,
        params=PHENO_PARAMS,
        is_photoperiod=True,
        is_vernalisation=True,
        start_cycle_doy=105,  # sowing date: Apr 15
        from_doy=s2,
        freq="YS-APR",
    )


def anthesis(climds, tperiod, s3):
    """Day of anthesis."""
    data = _select_pheno_climdata(climds, tperiod)

    return pn.phenological_stage(
        data,
        thresh=245,
        params=PHENO_PARAMS,
        is_photoperiod=True,
        is_vernalisation=True,
        start_cycle_doy=105,  # sowing date: Apr 15
        from_doy=s3,
        freq="YS-APR",
    )


def maturity(climds, tperiod, s4):
    """Day of maturity."""
    data = _select_pheno_climdata(climds, tperiod)

    out = pn.phenological_stage(
        data,
        thresh=700,
        params=PHENO_PARAMS,
        is_photoperiod=False,
        is_vernalisation=False,
        start_cycle_doy=105,  # sowing date: Apr 15
        from_doy=s4,
        freq="YS-APR",
    )
    return xr.where(out.notnull(), out, xr.where(data.isel(time=0).notnull(), 90, np.nan), keep_attrs=True)


# Define indicators
@climdata
def prcptot(data):
    """Total annual precipitation."""
    return atmos.precip_accumulation(data, freq="YS-JUL")


def _frost_year(fd):
    """Helper function to compute frost days for a year."""
    out = count_occurrences(fd, threshold="5 days", op=">=", freq="YS-APR")
    return out.where(fd.isel(time=0).notnull())


@climdata
def year_with_winter_frost(data, s1, s2, res):
    """Number of years with at least 5 day below -8°C between crop emergence and ear 1cm."""
    if res == "25km":
        out = atmos.frost_days(data, thresh="-8 degC", freq="YS-APR", doy_bounds=(s1, s2))

    elif res == "5km":
        data = _rename_latlon(data)
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 1}-03-31"))
            fd = atmos.frost_days(data_yr, thresh="-8 degC", freq="YS-APR", doy_bounds=(s1, s2))
            fname = INDICATORPATH / f"tmp_frost-days_{res}_{y}.nc"
            write_netcdf(fd, fname, progressbar=True, verbose=False)
            out.append(fname)
        fp = out
        out = xr.open_mfdataset(out, combine="by_coords", decode_timedelta=False).load()["frost_days"]
        for f in fp:
            f.unlink()
    return _frost_year(fd=out).rename("year_with_winter_frost")


@climdata
def year_with_growth_frost(data, s2, s3, res):
    """Number of years with at least 5 day below -2°C between ear 1cm and flag leaf."""
    if res == "25km":
        out = atmos.frost_days(data, thresh="-2 degC", freq="YS-APR", doy_bounds=(s2, s3))

    elif res == "5km":
        data = _rename_latlon(data)
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 1}-03-31"))
            fd = atmos.frost_days(data_yr, thresh="-2 degC", freq="YS-APR", doy_bounds=(s2, s3))
            fname = INDICATORPATH / f"tmp_frost-days_{res}_{y}.nc"
            write_netcdf(fd, fname, progressbar=True, verbose=False)
            out.append(fname)
        fp = out
        out = xr.open_mfdataset(out, combine="by_coords", decode_timedelta=False).load()["frost_days"]
        for f in fp:
            f.unlink()
    return _frost_year(fd=out).rename("year_with_growth_frost")


@climdata
def year_with_flowering_heat(data, s4, res):
    """Number of years with at least 5 days above 30°C between anthesis +/- 30 days."""

    def _year_heat(hd):
        out = count_occurrences(hd, threshold="5 days", op=">=", freq="YS-APR")
        return out.where(data.isel(time=0).notnull())

    start = days_since_to_doy(doy_to_days_since(s4) - 30)
    end = days_since_to_doy(doy_to_days_since(s4) + 30)

    if res == "25km":
        out = atmos.hot_days(data, thresh="30 degC", freq="YS-APR", doy_bounds=(start, end))

    elif res == "5km":
        data = _rename_latlon(data)
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 1}-03-31"))
            hd = atmos.hot_days(data_yr, thresh="30 degC", freq="YS-APR", doy_bounds=(start, end))
            fname = INDICATORPATH / f"tmp_hot-days_{res}_{y}.nc"
            write_netcdf(hd, fname, progressbar=True, verbose=False)
            out.append(fname)
        fp = out
        out = xr.open_mfdataset(out, combine="by_coords", decode_timedelta=False).load()["hot_days"]
        for f in fp:
            f.unlink()
    return _year_heat(hd=out).rename("year_with_flowering_heat")


def compute(resolution="5km"):  # noqa: PLR0912, PLR0914, PLR0915
    """Compute and save all Pinot noir climate indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            tperiod = open_climdata_timeserie(
                climDS, scen, ["tas", "tasmax", "tasmin", "pr"], ens_kwargs={"calendar": "noleap"}
            )

            # PHENOLOGY
            # Emergence
            fname = f"wheatearly_emergence_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s1 = emergence(climDS, tperiod=tperiod)
                write_netcdf(s1, INDICATORPATH / fname, progressbar=True, verbose=True)
            s1 = xr.open_dataarray(INDICATORPATH / fname)

            # Ear 1cm
            fname = f"wheatearly_ear-1cm_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s2 = ear_1cm(climDS, s1=s1, tperiod=tperiod)
                write_netcdf(s2, INDICATORPATH / fname, progressbar=True, verbose=True)
            s2 = xr.open_dataarray(INDICATORPATH / fname)

            # Flag Leaf
            fname = f"wheatearly_flag-leaf_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s3 = flag_leaf(climDS, s2=s2, tperiod=tperiod)
                write_netcdf(s3, INDICATORPATH / fname, progressbar=True, verbose=True)
            s3 = xr.open_dataarray(INDICATORPATH / fname)

            # Anthesis
            fname = f"wheatearly_anthesis_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s4 = anthesis(climDS, s3=s3, tperiod=tperiod)
                write_netcdf(s4, INDICATORPATH / fname, progressbar=True, verbose=True)
            s4 = xr.open_dataarray(INDICATORPATH / fname)

            # Maturity
            fname = f"wheatearly_maturity_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s5 = maturity(climDS, s4=s4, tperiod=tperiod)
                write_netcdf(s5, INDICATORPATH / fname, progressbar=True, verbose=True)
            s5 = xr.open_dataarray(INDICATORPATH / fname)

            # CLIMATE INDICATORS
            # Total Precipitation
            fname = f"prcptot_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                prtot = prcptot(climDS, "pr", period=tperiod, units="mm")
                write_netcdf(prtot, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Years with Winter Frost
            fname = f"wheatearly_years-5fdm8_emergence-ear1cm_5yr_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                ywf = year_with_winter_frost(
                    climDS, "tasmin", s1=s1, s2=s2, res=climDS.res, period=tperiod, freq="YS-APR", offset={"months": 3}
                )
                # work around to handle historical and projection transition for rolling sum
                if scen == "historical":
                    ywf.to_netcdf(INDICATORPATH / "tmp_wheatearly_winter-frost.nc")
                else:
                    histfile = "tmp_wheatearly_winter-frost.nc"
                    hist = xr.open_dataarray(INDICATORPATH / histfile)
                    hist = hist.isel(time=slice(-4, None))
                    projtime = ywf.time.values
                    ywf = xr.concat([hist, ywf], dim="time")
                ywf = ywf.chunk({"time": -1}).rolling(time=5).sum()  # 5-yr rolling sum

                if scen != "historical":
                    ywf = ywf.sel(time=projtime)
                write_netcdf(ywf, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Years with Growth Frost
            fname = f"wheatearly_years-5fdm2_ear1cm-flagleaf_5yr_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                ygf = year_with_growth_frost(
                    climDS, "tasmin", s2=s2, s3=s3, res=climDS.res, period=tperiod, freq="YS-APR", offset={"months": 3}
                )
                # work around to handle historical and projection transition for rolling sum
                if scen == "historical":
                    ygf.to_netcdf(INDICATORPATH / "tmp_wheatearly_growth-frost.nc")
                else:
                    histfile = "tmp_wheatearly_growth-frost.nc"
                    hist = xr.open_dataarray(INDICATORPATH / histfile)
                    hist = hist.isel(time=slice(-4, None))
                    projtime = ygf.time.values
                    ygf = xr.concat([hist, ygf], dim="time")
                ygf = ygf.chunk({"time": -1}).rolling(time=5).sum()  # 5-yr rolling sum

                if scen != "historical":
                    ygf = ygf.sel(time=projtime)
                write_netcdf(ygf, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Years with Flowering Heat
            fname = f"wheatearly_years-5txge30_30anthesis-anthesis30_5yr_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                yfh = year_with_flowering_heat(
                    climDS, "tasmax", s4=s4, res=climDS.res, period=tperiod, freq="YS-APR", offset={"months": 3}
                )
                # work around to handle historical and projection transition for rolling sum
                if scen == "historical":
                    yfh.to_netcdf(INDICATORPATH / "tmp_wheatearly_flowering-heat.nc")
                else:
                    histfile = "tmp_wheatearly_flowering-heat.nc"
                    hist = xr.open_dataarray(INDICATORPATH / histfile)
                    hist = hist.isel(time=slice(-4, None))
                    projtime = yfh.time.values
                    yfh = xr.concat([hist, yfh], dim="time")
                yfh = yfh.chunk({"time": -1}).rolling(time=5).sum()  # 5-yr rolling sum

                if scen != "historical":
                    yfh = yfh.sel(time=projtime)
                write_netcdf(yfh, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all Pinot noir climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

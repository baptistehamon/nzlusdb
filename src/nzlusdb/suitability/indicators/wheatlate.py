"""Late wheat suitability climate indicators."""

import argparse

import numpy as np
import pynar as pn
import xarray as xr
from xclim.core.calendar import days_since_to_doy, doy_to_days_since
from xclim.indicators import atmos

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
    "vern_ndays": 62,
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


def emergence(climds, tperiod, res):
    """Day of crop emergence."""

    def _compute_emergence(data):
        return pn.phenological_stage(
            data,
            thresh=120,
            params=PHENO_PARAMS,
            is_photoperiod=False,
            is_vernalisation=False,
            start_cycle_doy=105,  # sowing date: Apr 15
            freq="YS-APR",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_emergence(data)

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)[:-1]
        out = []
        for y in years[::5]:
            if y == years[::5][-1] and years[-1] - y < 4:  # noqa: PLR2004
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{years[-1]}-03-31"))
            else:
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 5}-03-31"))
            stage = _compute_emergence(data_yr)
            fname = INDICATORPATH / f"tmp_emergence_{y}_5km.nc"
            write_netcdf(stage, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["dayofyear"]
        for f in fp:
            f.unlink()
        return out


def ear_1cm(climds, tperiod, s1, res):
    """Day of ear 1cm."""

    def _compute_ear_1cm(data, s1):
        return pn.phenological_stage(
            data,
            thresh=275,
            params=PHENO_PARAMS,
            is_photoperiod=True,
            is_vernalisation=True,
            start_cycle_doy=105,  # sowing date: Apr 15
            from_doy=s1,
            freq="YS-APR",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_ear_1cm(data, s1)

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)[:-1]
        out = []
        for y in years[::5]:
            if y == years[::5][-1] and years[-1] - y < 4:  # noqa: PLR2004
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{years[-1]}-03-31"))
                s1_yr = s1.sel(time=slice(f"{y}-04-01", f"{years[-1]}-03-31"))
            else:
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 5}-03-31"))
                s1_yr = s1.sel(time=slice(f"{y}-04-01", f"{y + 5}-03-31"))
            stage = _compute_ear_1cm(data_yr, s1_yr)
            fname = INDICATORPATH / f"tmp_ear-1cm_{y}_5km.nc"
            write_netcdf(stage, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["dayofyear"]
        for f in fp:
            f.unlink()
        return out


def flag_leaf(climds, tperiod, s2, res):
    """Day of flag leaf."""

    def _compute_flag_leaf(data, s2):
        return pn.phenological_stage(
            data,
            thresh=360,
            params=PHENO_PARAMS,
            is_photoperiod=True,
            is_vernalisation=True,
            start_cycle_doy=105,  # sowing date: Apr 15
            from_doy=s2,
            freq="YS-APR",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_flag_leaf(data, s2)

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)[:-1]
        out = []
        for y in years[::5]:
            if y == years[::5][-1] and years[-1] - y < 4:  # noqa: PLR2004
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{years[-1]}-03-31"))
                s2_yr = s2.sel(time=slice(f"{y}-04-01", f"{years[-1]}-03-31"))
            else:
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 5}-03-31"))
                s2_yr = s2.sel(time=slice(f"{y}-04-01", f"{y + 5}-03-31"))
            stage = _compute_flag_leaf(data_yr, s2_yr)
            fname = INDICATORPATH / f"tmp_flag-leaf_{y}_5km.nc"
            write_netcdf(stage, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["dayofyear"]
        for f in fp:
            f.unlink()
        return out


def anthesis(climds, tperiod, s3, res):
    """Day of anthesis."""

    def _compute_anthesis(data, s3):
        return pn.phenological_stage(
            data,
            thresh=205,
            params=PHENO_PARAMS,
            is_photoperiod=True,
            is_vernalisation=True,
            start_cycle_doy=105,  # sowing date: Apr 15
            from_doy=s3,
            freq="YS-APR",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_anthesis(data, s3)

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)[:-1]
        out = []
        for y in years[::5]:
            if y == years[::5][-1] and years[-1] - y < 4:  # noqa: PLR2004
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{years[-1]}-03-31"))
                s3_yr = s3.sel(time=slice(f"{y}-04-01", f"{years[-1]}-03-31"))
            else:
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 5}-03-31"))
                s3_yr = s3.sel(time=slice(f"{y}-04-01", f"{y + 5}-03-31"))
            stage = _compute_anthesis(data_yr, s3_yr)
            fname = INDICATORPATH / f"tmp_anthesis_{y}_5km.nc"
            write_netcdf(stage, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["dayofyear"]
        for f in fp:
            f.unlink()
        return out


def maturity(climds, tperiod, s4, res):
    """Day of maturity."""

    def _compute_maturity(data):
        return pn.phenological_stage(
            data,
            thresh=700,
            params=PHENO_PARAMS,
            is_photoperiod=False,
            is_vernalisation=False,
            start_cycle_doy=105,  # sowing date: Apr 15
            from_doy=s4,
            freq="YS-APR",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_maturity(data)

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)[:-1]
        out = []
        for y in years[::5]:
            if y == years[::5][-1] and years[-1] - y < 4:  # noqa: PLR2004
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{years[-1]}-03-31"))
            else:
                data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 5}-03-31"))
            stage = _compute_maturity(data_yr)
            fname = INDICATORPATH / f"tmp_maturity_{y}_5km.nc"
            write_netcdf(stage, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["dayofyear"]
        for f in fp:
            f.unlink()
        return out


# Define indicators
@climdata
def prcptot(data):
    """Total annual precipitation."""
    return atmos.precip_accumulation(data, freq="YS-JUL")


@climdata
def winter_frost_days(data, s1, s2, res):
    """Number of days below -8°C between crop emergence and ear 1cm."""
    data = _rename_latlon(data)

    if res == "25km":
        return atmos.frost_days(data, thresh="-8 degC", freq="YS-APR", doy_bounds=(s1, s2))

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 1}-03-31"))
            fd = atmos.frost_days(data_yr, thresh="-8 degC", freq="YS-APR", doy_bounds=(s1, s2))
            fname = INDICATORPATH / f"tmp_winter_frost_days_{y}_5km.nc"
            write_netcdf(fd, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["frost_days"]
        for f in fp:
            f.unlink()
        return out


@climdata
def growth_frost_days(data, s2, s3, res):
    """Number of days below -5°C between ear 1cm and flag leaf."""
    data = _rename_latlon(data)

    if res == "25km":
        return atmos.frost_days(data, thresh="-5 degC", freq="YS-APR", doy_bounds=(s2, s3))

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 1}-03-31"))
            fd = atmos.frost_days(data_yr, thresh="-5 degC", freq="YS-APR", doy_bounds=(s2, s3))
            fname = INDICATORPATH / f"tmp_growth_frost_days_{y}_5km.nc"
            write_netcdf(fd, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["frost_days"]
        for f in fp:
            f.unlink()
        return out


@climdata
def flowering_heat_days(data, s4, res):
    """Number of days above 30°C between anthesis +/- 30 days."""
    data = _rename_latlon(data)
    start = days_since_to_doy(doy_to_days_since(s4) - 30)
    end = days_since_to_doy(doy_to_days_since(s4) + 30)

    if res == "25km":
        return atmos.hot_days(data, thresh="30 degC", freq="YS-APR", doy_bounds=(start, end))

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-04-01", f"{y + 1}-03-31"))
            hd = atmos.hot_days(data_yr, thresh="30 degC", freq="YS-APR", doy_bounds=(start, end))
            fname = INDICATORPATH / f"tmp_flowering_heat_days_{y}_5km.nc"
            write_netcdf(hd, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["hot_days"]
        for f in fp:
            f.unlink()
        return out


def compute(resolution="5km"):  # noqa: PLR0912, PLR0914, PLR0915
    """Compute and save all late wheat climate indicators."""
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
            fname = f"wheatlate_emergence_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s1 = emergence(climDS, tperiod=tperiod, res=climDS.res)
                write_netcdf(s1, INDICATORPATH / fname, progressbar=True, verbose=True)
            s1 = xr.open_dataarray(INDICATORPATH / fname)

            # Ear 1cm
            fname = f"wheatlate_ear-1cm_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s2 = ear_1cm(climDS, s1=s1, tperiod=tperiod, res=climDS.res)
                write_netcdf(s2, INDICATORPATH / fname, progressbar=True, verbose=True)
            s2 = xr.open_dataarray(INDICATORPATH / fname)

            # Flag Leaf
            fname = f"wheatlate_flag-leaf_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s3 = flag_leaf(climDS, s2=s2, tperiod=tperiod, res=climDS.res)
                write_netcdf(s3, INDICATORPATH / fname, progressbar=True, verbose=True)
            s3 = xr.open_dataarray(INDICATORPATH / fname)

            # Anthesis
            fname = f"wheatlate_anthesis_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s4 = anthesis(climDS, s3=s3, tperiod=tperiod, res=climDS.res)
                write_netcdf(s4, INDICATORPATH / fname, progressbar=True, verbose=True)
            s4 = xr.open_dataarray(INDICATORPATH / fname)

            # Maturity
            fname = f"wheatlate_maturity_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s5 = maturity(climDS, s4=s4, tperiod=tperiod, res=climDS.res)
                write_netcdf(s5, INDICATORPATH / fname, progressbar=True, verbose=True)
                s5 = xr.open_dataarray(INDICATORPATH / fname)
                # Fill missing values with 90 (end of March) where climate data exists
                s5 = xr.where(
                    s5.notnull(),
                    s5,
                    _rename_latlon(xr.where(climDS.data["tas"].isel(time=0).notnull(), 90, np.nan)),
                    keep_attrs=True,
                )
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

            # Winter Frost Days
            fname = f"wheatlate_fdm8_emergence-ear1cm_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fdm8 = winter_frost_days(
                    climDS, "tasmin", s1=s1, s2=s2, period=tperiod, freq="YS-APR", offset={"months": 3}, res=climDS.res
                )
                write_netcdf(fdm8, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Growth Frost Days
            fname = f"wheatlate_fdm5_ear1cm-flagleaf_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fdm2 = growth_frost_days(
                    climDS, "tasmin", s2=s2, s3=s3, period=tperiod, freq="YS-APR", offset={"months": 3}, res=climDS.res
                )
                write_netcdf(fdm2, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Flowering Heat Days
            fname = f"wheatlate_txge30_30anthesis-anthesis30_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                tx30 = flowering_heat_days(
                    climDS, "tasmax", s4=s4, period=tperiod, freq="YS-APR", offset={"months": 3}, res=climDS.res
                )
                write_netcdf(tx30, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all late wheat climate indicators.")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

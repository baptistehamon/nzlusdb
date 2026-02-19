"""Late maize (volga) suitability climate indicators."""

import argparse

import numpy as np
import pynar as pn
import xarray as xr
from xclim.core.calendar import days_since_to_doy, doy_to_days_since
from xclim.indicators import atmos

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import TIMEPERIOD, climateDS, climdata, open_climdata_timeserie, select_hist_proj
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.utils import write_netcdf

# Define phenology parameters for maize
PHENO_PARAMS = {
    "tmin_thresh": 6,
    "tmax_thresh": 30,
    "tstop_thresh": 40,
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


def _fill_missing_stages(stage, climds, fill_value=304):
    """Fill missing phenological stages with a specified value where climate data exists."""
    return xr.where(
        stage.notnull(),
        stage,
        _rename_latlon(xr.where(climds.data["tas"].isel(time=0).notnull(), fill_value, np.nan)),
        keep_attrs=True,
    )


def _5km_pheno(data, compute_func, *args, **kwargs):
    """Compute phenological stage for 5km data by looping over years to avoid memory issues."""
    years = np.unique(data.time.dt.year.values)
    out = []
    drop_last = False
    for y in years[::5]:
        if drop_last:
            continue
        elif (y == years[::5][-2] and years[-1] - years[::5][-1] < 3) or (y == years[::5][-1] and years[-1] - y < 4):  # noqa: PLR2004
            data_yr = data.sel(time=slice(f"{y}-01-01", f"{years[-1]}-12-31"))
            drop_last = True
        else:
            data_yr = data.sel(time=slice(f"{y}-01-01", f"{y + 5}-12-31"))
        stage = compute_func(data_yr, *args, **kwargs)
        fname = INDICATORPATH / f"tmp_{compute_func.__name__}_{y}_5km.nc"
        write_netcdf(stage, fname, progressbar=True, verbose=False)
        out.append(fname)

    fp = out
    out = xr.open_mfdataset(out, combine="by_coords").load()["dayofyear"]
    for f in fp:
        f.unlink()
    return out


def emergence(climds, tperiod, res):
    """Day of crop emergence."""

    def _compute_emergence(data):
        return pn.phenological_stage(
            data,
            thresh=80,
            params=PHENO_PARAMS,
            cycle_start="11-01",
            freq="YS-NOV",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_emergence(data)

    if res == "5km":
        return _5km_pheno(data, _compute_emergence)


def stem_elongation(climds, tperiod, s1, res):
    """Day of beginning of stem elongation."""

    def _compute_stem_elongation(data, s1):
        return pn.phenological_stage(
            data,
            thresh=288,
            params=PHENO_PARAMS,
            cycle_start="11-01",
            start_from=s1,
            freq="YS-NOV",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_stem_elongation(data, s1)

    if res == "5km":
        return _5km_pheno(data, _compute_stem_elongation, s1)


def meiosis(climds, tperiod, s2, res):
    """Day of meiosis."""

    def _compute_meiosis(data, s2):
        return pn.phenological_stage(
            data,
            thresh=120,
            params=PHENO_PARAMS,
            cycle_start="11-01",
            start_from=s2,
            freq="YS-NOV",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_meiosis(data, s2)

    if res == "5km":
        return _5km_pheno(data, _compute_meiosis, s2)


def anthesis(climds, tperiod, s3, res):
    """Day of anthesis."""

    def _compute_anthesis(data, s3):
        return pn.phenological_stage(
            data,
            thresh=527,
            params=PHENO_PARAMS,
            cycle_start="11-01",
            start_from=s3,
            freq="YS-NOV",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_anthesis(data, s3)

    if res == "5km":
        return _5km_pheno(data, _compute_anthesis, s3)


def dry_matter_32pct(climds, tperiod, s4, res):
    """Day of 32% dry matter."""

    def _compute_dry_matter_32pct(data):
        return pn.phenological_stage(
            data,
            thresh=650,
            params=PHENO_PARAMS,
            cycle_start="11-01",
            start_from=s4,
            freq="YS-NOV",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_dry_matter_32pct(data)

    if res == "5km":
        return _5km_pheno(data, _compute_dry_matter_32pct)


def maturity(climds, tperiod, s5, res):
    """Day of maturity."""

    def _compute_maturity(data):
        return pn.phenological_stage(
            data,
            thresh=65,
            params=PHENO_PARAMS,
            cycle_start="11-01",
            start_from=s5,
            freq="YS-NOV",
        )

    data = _select_pheno_climdata(climds, tperiod)

    if res == "25km":
        return _compute_maturity(data)

    if res == "5km":
        return _5km_pheno(data, _compute_maturity)


# Define indicators
@climdata
def prcptot(data):
    """Total annual precipitation."""
    return atmos.precip_accumulation(data, freq="YS-JUL")


@climdata
def growth_frost_days(data, s1, s2, res):
    """Number of days below -6°C between emergence and beginning of stem elongation."""
    data = _rename_latlon(data)

    if res == "25km":
        return atmos.frost_days(data, thresh="-6 degC", freq="YS-NOV", doy_bounds=(s1, s2))

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-11-01", f"{y + 1}-10-31"))
            fd = atmos.frost_days(data_yr, thresh="-6 degC", freq="YS-NOV", doy_bounds=(s1, s2))
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
    """Frequency of days above 35°C between anthesis +/- 30 days."""
    data = _rename_latlon(data)
    start = days_since_to_doy(doy_to_days_since(s4) - 30)
    end = days_since_to_doy(doy_to_days_since(s4) + 30)

    if res == "25km":
        return indicators.hot_days_frequency(data, bounds=(start, end), thresh="35 degC", freq="YS-NOV")

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-11-01", f"{y + 1}-10-31"))
            hd = indicators.hot_days_frequency(data_yr, bounds=(start, end), thresh="35 degC", freq="YS-NOV")
            fname = INDICATORPATH / f"tmp_flowering_heat_days_freq_{y}_5km.nc"
            write_netcdf(hd, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["hot_days_frequency"]
        for f in fp:
            f.unlink()
        return out


@climdata
def harvest_cold_days(data, s4, s6, res):
    """Frequency of days with mean daily temperature below 10°C between flowering and maturity."""
    data = _rename_latlon(data)

    if res == "25km":
        return indicators.cold_days_frequency(
            data, bounds=(s4, s6), doy_bounds=(s4, s6), thresh="10 degC", freq="YS-NOV"
        )

    if res == "5km":
        # loop over years to avoid memory issues
        years = np.unique(data.time.dt.year.values)
        out = []
        for y in years[:-1]:
            data_yr = data.sel(time=slice(f"{y}-11-01", f"{y + 1}-10-31"))
            cd = indicators.cold_days_frequency(
                data_yr, bounds=(s4, s6), doy_bounds=(s4, s6), thresh="10 degC", freq="YS-NOV"
            )
            fname = INDICATORPATH / f"tmp_harvest_cold_days_freq_{y}_5km.nc"
            write_netcdf(cd, fname, progressbar=True, verbose=False)
            out.append(fname)

        fp = out
        out = xr.open_mfdataset(out, combine="by_coords").load()["cold_days_frequency"]
        for f in fp:
            f.unlink()
        return out


def compute(resolution="5km"):  # noqa: PLR0912, PLR0914, PLR0915
    """Compute and save all late maize climate indicators."""
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
            fname = f"maizelate_emergence_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s1 = emergence(climDS, tperiod=tperiod, res=climDS.res)
                write_netcdf(s1, INDICATORPATH / fname, progressbar=True, verbose=True)
            s1 = xr.open_dataarray(INDICATORPATH / fname)

            # Stem Elongation
            fname = f"maizelate_stem-elongation_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s2 = stem_elongation(climDS, s1=s1, tperiod=tperiod, res=climDS.res)
                write_netcdf(s2, INDICATORPATH / fname, progressbar=True, verbose=True)
            s2 = xr.open_dataarray(INDICATORPATH / fname)

            # Meiosis
            fname = f"maizelate_meiosis_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s3 = meiosis(climDS, s2=s2, tperiod=tperiod, res=climDS.res)
                write_netcdf(s3, INDICATORPATH / fname, progressbar=True, verbose=True)
            s3 = xr.open_dataarray(INDICATORPATH / fname)

            # Anthesis
            fname = f"maizelate_anthesis_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s4 = anthesis(climDS, s3=s3, tperiod=tperiod, res=climDS.res)
                write_netcdf(s4, INDICATORPATH / fname, progressbar=True, verbose=True)
            s4 = xr.open_dataarray(INDICATORPATH / fname)

            # Dry Matter 32%
            fname = f"maizelate_dry-matter-32pct_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s5 = dry_matter_32pct(climDS, s4=s4, tperiod=tperiod, res=climDS.res)
                write_netcdf(s5, INDICATORPATH / fname, progressbar=True, verbose=True)
            s5 = xr.open_dataarray(INDICATORPATH / fname)

            # Maturity
            fname = f"maizelate_maturity_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                s6 = maturity(climDS, s5=s5, tperiod=tperiod, res=climDS.res)
                write_netcdf(s5, INDICATORPATH / fname, progressbar=True, verbose=True)
                s6 = xr.open_dataarray(INDICATORPATH / fname)
                s6 = _fill_missing_stages(s6, climDS, fill_value=304)
                write_netcdf(s6, INDICATORPATH / fname, progressbar=True, verbose=True)
            s6 = xr.open_dataarray(INDICATORPATH / fname)

            # CLIMATE INDICATORS
            # Total Precipitation
            fname = f"prcptot_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                prtot = prcptot(climDS, "pr", period=tperiod, units="mm")
                write_netcdf(prtot, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Growth Frost Days
            fname = f"maizelate_fdm6_emergence-stemelongation_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                fdm6 = growth_frost_days(
                    climDS, "tasmin", s1=s1, s2=s2, period=tperiod, freq="YS-NOV", offset={"months": -4}, res=climDS.res
                )
                write_netcdf(fdm6, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Flowering Heat Days
            fname = f"maizelate_txge35freq_30anthesis-anthesis30_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                txge35 = flowering_heat_days(
                    climDS, "tasmax", s4=s4, period=tperiod, freq="YS-NOV", offset={"months": -4}, res=climDS.res
                )
                write_netcdf(txge35, INDICATORPATH / fname, progressbar=True, verbose=True)

            # Harvest Cold Days
            fname = f"maizelate_tnle10freq_anthesis-maturity_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                print(f"{fname} exists, skipping...")
            else:
                tnle10 = harvest_cold_days(
                    climDS, "tas", s4=s4, s6=s6, period=tperiod, freq="YS-NOV", offset={"months": -4}, res=climDS.res
                )
                write_netcdf(tnle10, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compute and save all late maize climate indicators")
    parser.add_argument("--res", nargs="+", default=["5km", "1km"], help="Resolution(s) to process (e.g. 5km, 1km)")
    args = parser.parse_args()
    compute(args.res)

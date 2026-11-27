"""Blueberry suitability climate indicators."""

import click
import lsapy.standardize as lstd
import xarray as xr
import xclim
from xclim.compute.helpers import make_hourly_temperature
from xclim.core.calendar import select_time
from xclim.indicators import atmos

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata
from nzlusdb.suitability.indicators import INDICATORPATH, LoopOverYearsWithPath
from nzlusdb.utils import write_netcdf

xclim.set_options(as_dataset=False)


@climdata
def chilling_hours(data, tmp_files=True, year_break=None):
    """Chilling hours between May 1 and Aug 31."""

    def _yearly_chilling_hours(data):
        # keep only relevant time period to compute hourly temperature
        data = select_time(data, date_bounds=("05-01", "08-31"), drop=True)
        tas = make_hourly_temperature(data["tasmin"], data["tasmax"]).astype("float32")
        return indicators.chilling_hours(tas, high="7 degC", date_bounds=("05-01", "08-31"), freq="YS-MAY").astype(
            "float32"
        )

    # rename lat/lon if needed for 5km data
    data = data.rename({"latitude": "lat", "longitude": "lon"}) if "latitude" in data.coords else data

    loop = LoopOverYearsWithPath(
        data, _yearly_chilling_hours, freq="YS-MAY", filename="tmp_blueberry_chill_units_<YEAR>.nc"
    )
    ch = loop(tmp_files=tmp_files, year_break=year_break)
    return ch, loop


@climdata
def frost_survival(data, tmp_files=True, year_break=None):
    """Frost survival during flowering period (from Sept 1 to Oct 31)."""

    def _yearly_fsg(data):
        return indicators.frost_survival(
            data,
            func=lstd.vetharaniam2022_eq3,
            fparams={"a": 1.1, "b": -4.5},
            freq="YS-JUL",
            date_bounds=("09-01", "10-31"),
        )

    loop = LoopOverYearsWithPath(data, _yearly_fsg, freq="YS-JUL", filename="tmp_blueberry_frost_survival_<YEAR>.nc")
    fsg = loop(tmp_files=tmp_files, year_break=year_break)
    return fsg, loop


@climdata
def growing_degree_days(data):
    """Growing degree days between Oct 1 and Apr 30."""
    return atmos.growing_degree_days(data, thresh="10 degC", freq="YS-JUL", date_bounds=("10-01", "04-30"))


@click.command()
@click.option(
    "-res",
    "--resolution",
    multiple=True,
    default=("5km", "1km"),
    type=click.Choice(["5km", "1km"]),
    show_default=True,
)
def compute(resolution):
    """Compute and save all blueberry indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            # Chilling Hours
            fname = f"ch7_0501-0831_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                click.echo(f"{fname} exists, skipping...")
            else:
                ch, loop = chilling_hours(
                    # climdata decorator params
                    climDS,
                    scen,
                    ["tasmin", "tasmax"],
                    freq="YS-MAY",
                    offset={"months": 2},
                    chunks={"time": xr.groupers.TimeResampler("YS-MAY")},
                    # LoopOverYears params
                    tmp_files=True if climDS.res == "5km" else False,
                )
                write_netcdf(ch, INDICATORPATH / fname, progressbar=True, verbose=True)
                loop.cleanup(ch)

            # Frost Survival during Flowering
            fname = f"blueberry_frost-survival_0901-1031_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                click.echo(f"{fname} exists, skipping...")
            else:
                fsg, loop = frost_survival(
                    # climdata decorator params
                    climDS,
                    scen,
                    "tasmin",
                    units="",
                    chunks={"time": xr.groupers.TimeResampler("YS-JUL")},
                    # LoopOverYears params
                    tmp_files=True if climDS.res == "5km" else False,
                )
                write_netcdf(fsg, INDICATORPATH / fname, progressbar=True, verbose=True)
                loop.cleanup(fsg)

            # Growing Degree Days
            fname = f"gdd10_1001-0430_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                click.echo(f"{fname} exists, skipping...")
            else:
                gdd = growing_degree_days(
                    climDS, scen, "tas", units="degC d", chunks={"time": xr.groupers.TimeResampler("YS-JUL")}
                )
                write_netcdf(gdd, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    compute()

"""Avocado suitability climate indicators."""

import click
import lsapy.standardize as lstd
import xarray as xr
import xclim
from xclim.indicators import atmos

from nzlusdb.core import indicators
from nzlusdb.core.climdataset import climateDS, climdata
from nzlusdb.suitability.indicators import INDICATORPATH, LoopOverYearsWithPath
from nzlusdb.utils import write_netcdf

xclim.set_options(as_dataset=False)


# Define indictors
@climdata
def frost_survival(data, tmp_files=True, year_break=None):
    """Annual frost survival."""

    def _yearly_fsg(data):
        return indicators.frost_survival(
            data,
            func=lstd.vetharaniam2022_eq3,
            fparams={"a": 1.3, "b": -3},
            freq="YS-JUL",
        )

    loop = LoopOverYearsWithPath(data, _yearly_fsg, freq="YS-JUL", filename="tmp_frost_survival_<YEAR>.nc")
    fsg = loop(tmp_files=tmp_files, year_break=year_break)
    return fsg, loop


@climdata
def tg_mean(data):
    """Mean annual temperature."""
    return atmos.tg_mean(data, freq="YS-JUL")


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
    """Compute and save all avocado indicators."""
    if isinstance(resolution, str):
        resolution = [resolution]

    for res in resolution:
        climDS = climateDS[f"nzlusdb_{res}"]

        for scen in climDS.scenario:
            # Frost Survival during Flowering
            fname = f"avocado_frost-survival_annual_{scen}_{climDS.res}.nc"
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
                    year_break=2,
                )
                write_netcdf(fsg, INDICATORPATH / fname, progressbar=True, verbose=True)
                loop.cleanup(fsg)

            # Mean Annual Temperature
            fname = f"tgm_annual_{scen}_{climDS.res}.nc"
            if (INDICATORPATH / fname).exists():
                click.echo(f"{fname} exists, skipping...")
            else:
                chunks = {"latitude": 52, "time": -1} if climDS.res == "5km" else {}
                tgm = tg_mean(climDS, scen, "tas", units="degC", chunks=chunks)
                write_netcdf(tgm, INDICATORPATH / fname, progressbar=True, verbose=True)


if __name__ == "__main__":
    compute()

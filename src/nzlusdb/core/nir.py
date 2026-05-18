"""Module with functions related to Net Irrigation Requirements (NIR)."""

import numpy as np
import xarray as xr
from xclim.core.calendar import (
    DayOfYearStr,
    _doy_days_since_doys,  # noqa: PLC2701
    doy_from_string,
    get_calendar,
)

from nzlusdb.suitability.indicators import INDICATORPATH


def doys_from_string(
    doy_str: str,
    da: xr.DataArray,
    freq: str | None = None,
) -> xr.DataArray:
    """Get the day-of-year corresponding to the `doy_str` for each period defined by `freq`."""
    if freq is not None:
        da = da.resample(time=freq).first()
        bnds = da.time.resample(time=freq).first()
        years = bnds.time.dt.year.values
    else:
        years = da.time.dt.year.values
    cal = get_calendar(da)
    doys = [doy_from_string(doy_str, year=y, calendar=cal) for y in years]

    return xr.DataArray(doys, coords={"time": da.time if freq is None else bnds.time}, dims=["time"])


def daily_doy_to_days_since(
    da: xr.DataArray,
    start: DayOfYearStr | None = None,
    calendar: str | None = None,
) -> xr.DataArray:
    """Update `xclim.core.calendar.doy_to_days_since` to use daily data."""
    base_calendar = get_calendar(da)
    calendar = calendar or da.attrs.get("calendar", base_calendar)
    dac = da.convert_calendar(calendar)

    _, start_doy, doy_max = _doy_days_since_doys(dac.time, start)

    # 2cases:
    # val is a day in the same year as its index : da - offset
    # val is a day in the next year : da + doy_max - offset
    out = xr.where(dac >= start_doy, dac, dac + doy_max) - start_doy
    out.attrs.update(da.attrs)
    if start is not None:
        out.attrs.update(units=f"days after {start}")
    else:
        starts = np.unique(out.time.dt.strftime("%m-%d"))
        if len(starts) == 1:
            out.attrs.update(units=f"days after {starts[0]}")
        else:
            out.attrs.update(units="days after time coordinate")

    out.attrs.pop("is_dayofyear", None)
    out.attrs.update(calendar=calendar)
    return out.convert_calendar(base_calendar).rename(da.name)


def climate_kc_adjustement(kc, windspd, rhmin, height):
    """Adjust Kc values based on climatic conditions and crop height, following Allen et al. (1998) formula."""
    if height < 0.1:  # similar to grass, no adjustment #  noqa: PLR2004
        return kc
    return kc + (0.04 * (windspd - 2) - 0.004 * (rhmin - 45)) * (height / 3) ** 0.3


class KcCurve:
    """
    Kc crop coefficient class.

    Parameters
    ----------
    start_date : DayOfYearStr
        The day of year corresponding to the start of the growing season.
    stage_values : dict[str, float]
        The Kc values for each stage of the growing season. Keys must be "init", "mid" and "end".
    stage_lengths : dict[str, int]
        The length in days of each stage of the growing season. Keys must be "init", "dev", "mid" and "end".
    height : float | int
        The height of the crop in meters, used for climatic adjustment of Kc values.
    time : xr.DataArray
        The time coordinate of the data for which the Kc curve will built.

    Methods
    -------
    curve(like) -> xr.DataArray
        Build the Kc curve as an `xr.DataArray` with the same coordinates as `like`.
    adjust(windspd, rhmin) -> None
        Adjust `mid ` and `end` Kc values base on climatic conditions.
    """

    def __init__(
        self,
        start_date: DayOfYearStr,
        stage_values: dict[str, float],
        stage_lengths: dict[str, int],
        height: float | int,
        time: xr.DataArray,
    ):
        self.start_date = start_date
        self.stage_values = stage_values
        self.stage_lengths = stage_lengths
        self.height = height
        self._populate_days(time)

    @property
    def start_date(self):
        """The day of year corresponding to the start of the growing season."""
        return self._start_date

    @start_date.setter
    def start_date(self, value):
        self._start_date = value

    @property
    def stage_values(self):
        """The Kc values for each stage of the growing season."""
        return self._stage_values

    @stage_values.setter
    def stage_values(self, value):
        if not all(k in value for k in ["init", "mid", "end"]):
            raise ValueError("stage_values must contain keys 'init', 'mid' and 'end'")
        self._stage_values = value

    @property
    def stage_lengths(self):
        """The length in days of each stage of the growing season."""
        return self._stage_lengths

    @stage_lengths.setter
    def stage_lengths(self, value):
        if not all(k in value for k in ["init", "dev", "mid", "end"]):
            raise ValueError("stage_lengths must contain keys 'init', 'dev', 'mid' and 'end'")
        self._stage_lengths = value

    @property
    def height(self):
        """The height of the crop in meters, used for climatic adjustment of Kc values."""
        return self._height

    @height.setter
    def height(self, value):
        if value < 0:
            raise ValueError("height must be a positive value")
        elif value > 15:  # likely a unit error, as 15m is a very high crop, raise a warning # noqa: PLR2004
            raise UserWarning("height value seems very high, please check the units")
        self._height = value

    def curve(self, like) -> xr.DataArray:
        """Build the Kc curve as an `xr.DataArray` with the same coordinates as `like`."""
        kc = xr.full_like(like, fill_value=np.nan, dtype=float).rename("crop_coefficient")
        kc = xr.where(
            (self.days.dayofyear >= self.days.start_init) & (self.days.dayofyear < self.days.start_dev),
            self.stage_values["init"],
            kc,
        )

        for base_time, indexes in like.time.resample(time="YS-JUL").groups.items():
            grp_time = like.time[indexes]
            grp_kcmid = self.stage_values["mid"]
            if isinstance(grp_kcmid, xr.DataArray):
                grp_kcmid = grp_kcmid.sel(time=base_time)

            grp_kcend = self.stage_values["end"]
            if isinstance(grp_kcend, xr.DataArray):
                grp_kcend = grp_kcend.sel(time=base_time)

            kc = xr.where(
                like.time.isin(grp_time)
                & (self.days.dayofyear >= self.days.start_mid)
                & (self.days.dayofyear < self.days.start_end),
                grp_kcmid,
                kc,
            )
            kc = xr.where(
                like.time.isin(grp_time)
                & (self.days.dayofyear >= self.days.start_dev)
                & (self.days.dayofyear < self.days.start_mid),
                self.stage_values["init"]
                + (grp_kcmid - self.stage_values["init"])
                * (self.days.dayofyear - self.days.start_dev)
                / (self.days.start_mid - self.days.start_dev),
                kc,
            )
            kc = xr.where(like.time.isin(grp_time) & (self.days.dayofyear == self.days.end), grp_kcend, kc)
            kc = xr.where(
                like.time.isin(grp_time)
                & (self.days.dayofyear >= self.days.start_end)
                & (self.days.dayofyear < self.days.end),
                grp_kcmid
                - (grp_kcmid - grp_kcend)
                * (self.days.dayofyear - self.days.start_end)
                / (self.days.end - self.days.start_end),
                kc,
            )
        return kc

    def adjust(self, windspd, rhmin):
        """Adjust `mid ` and `end` Kc values base on climatic conditions."""
        self.stage_values["mid"] = self._adjust_stage("mid", windspd, rhmin)
        # senescence or drydown phase, no adjustment (see Allen et al., 1998)
        if self.stage_values["end"] >= 0.45:  # noqa: PLR2004
            self.stage_values["end"] = self._adjust_stage("end", windspd, rhmin)

    def _adjust_stage(self, stage: str, windspd: xr.DataArray, rhmin: xr.DataArray) -> float | xr.DataArray:
        """Adjust the Kc value of a given stage based on climatic conditions."""
        if stage not in ["mid", "end"]:
            return self.stage_values[stage]
        rhmin_stage = self._stage_mean(rhmin, stage, freq="YS-JUL")
        windspd_stage = self._stage_mean(windspd, stage, freq="YS-JUL")
        return climate_kc_adjustement(self.stage_values[stage], windspd_stage, rhmin_stage, self.height)

    def _stage_mean(self, da: xr.DataArray, stage: str, freq: str) -> xr.DataArray:
        """Calculate the mean of a input variable over the period corresponding to a given stage."""
        _start = {"init": "start_init", "dev": "start_dev", "mid": "start_mid", "end": "start_end"}.get(stage)
        _end = {"init": "start_dev", "dev": "start_mid", "mid": "start_end", "end": "end"}.get(stage)
        out = da.where((self.days.dayofyear >= self.days[_start]) & (self.days.dayofyear < self.days[_end]))
        return out.resample(time=freq).mean()

    def _populate_days(self, time) -> None:
        """Create a dataset with the number of days since the start of the growing season for each stage."""
        self.days = daily_doy_to_days_since(time.dt.dayofyear, start=self.start_date).to_dataset()
        self.days["start_init"] = daily_doy_to_days_since(
            da=doys_from_string(self.start_date, self.days.dayofyear), start=self.start_date
        )
        self.days["start_dev"] = self.days.start_init + self.stage_lengths["init"]
        self.days["start_mid"] = self.days.start_dev + self.stage_lengths["dev"]
        self.days["start_end"] = self.days.start_mid + self.stage_lengths["mid"]
        self.days["end"] = self.days.start_end + self.stage_lengths["end"]


def load_nir_inputs(variable, scenario="historical", resolution="5km"):
    """Load NIR input variables from netCDF files."""
    if variable == "windspd":
        variable = "wind_speed_2m"
    fname = f"{variable}_daily_{scenario}_{resolution}.nc"
    da = xr.open_dataarray(INDICATORPATH / fname)

    # climate data resolution
    if resolution == "25km":
        _chunks = {"realization": 1, "lat": 23, "time": xr.groupers.TimeResampler("YS-JUL")}
    if resolution == "5km":
        _chunks = {"realization": 1, "time": xr.groupers.TimeResampler("YS-JUL")}
        da = da.rename({"latitude": "lat", "longitude": "lon"})
    return da.chunk(_chunks)

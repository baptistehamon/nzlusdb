"""Climate indicators module."""

from __future__ import annotations

from xclim.indicators.atmos._temperature import Temp, TempHourlyWithIndexing, TempWithIndexing

from nzlusdb.core import indices

day_full_bloom = Temp(
    title="Day of full bloom for apple",
    identifier="day_full_bloom",
    units="",
    standard_name="day_of_year",
    long_name="Last day of full bloom for apple",
    description="Last day of full bloom for apple as computed from maximum temperature in August and September.",
    abstract="The day of full bloom is computed as a function of the mean maximum temperature in August and September "
    "following the formula from Hall et al. (2018).",
    compute=indices.day_full_bloom,
)

frost_survival = TempWithIndexing(
    title="Frost survival",
    identifier="frost_survival",
    units="",
    long_name="Frost survival",
    description="Frost survival computed as a function of minimum temperature.",
    abstract="Frost survival is computed as a function of minimum temperature following Vetharaniam et al. (2022).",
    compute=indices.frost_survival,
    cell_methods="time: prod",
)

sunburn_survival = TempWithIndexing(
    title="Sunburn survival",
    identifier="sunburn_survival",
    units="",
    long_name="Sunburn survival",
    description="Sunburn survival computed as a function of maximum temperature.",
    abstract="Sunburn survival is computed as a function of maximum temperature following vetharaniam et al. (2022).",
    compute=indices.sunburn_survival,
    cell_methods="time: prod",
)

chilling_hours = TempHourlyWithIndexing(
    title="Chilling hours",
    identifier="chilling_hours",
    units="",
    long_name="Number of hours where the hourly temperature is below {thresh}",
    description="{freq} number of hours where the hourly temperature is below {thresh}.",
    abstract="Number of hours where the hourly temperature is below a given threshold.",
    cell_methods="time: sum over hours",
    compute=indices.chilling_hours,
)

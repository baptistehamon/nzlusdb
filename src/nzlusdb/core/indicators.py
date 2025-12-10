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

day_budbreak = Temp(
    title="Day of budbreak for kiwifruit",
    identifier="day_budbreak",
    units="",
    standard_name="day_of_year",
    long_name="Day of budbreak for kiwifruit",
    description="Day of budbreak for kiwifruit as computed from mean temperature from May to July.",
    abstract="The day of budbreak is computed as a function of the mean temperature from May to July following the "
    "formula from Vetharaniam et al. (2022).",
    compute=indices.day_budbreak,
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
    abstract="Sunburn survival is computed as a function of maximum temperature following Vetharaniam et al. (2022).",
    compute=indices.tasmax_survival,
    cell_methods="time: prod",
)

chilling_hours = TempHourlyWithIndexing(
    title="Chilling hours",
    identifier="chilling_hours",
    units="hours",
    long_name="Number of hours where the hourly temperature is between {low} and {high}",
    description="{freq} number of hours where the hourly temperature higher than {low} and lower or equal to {high}.",
    abstract="Number of hours with hourly temperature between lower and upper limits.",
    cell_methods="time: sum over hours",
    compute=indices.chilling_hours,
)

sunburn_survival = TempWithIndexing(
    title="Craking survival",
    identifier="cracking_survival",
    units="",
    long_name="Cracking survival",
    description="Cracking survival computed as a function of daily relative humidity.",
    abstract="Cracking survival computed as a function of daily relative humidity following Vetharaniam et al. (2021).",
    compute=indices.cracking_survival,
    cell_methods="time: prod",
)

heat_survival = TempWithIndexing(
    title="Heat survival",
    identifier="heat_survival",
    units="",
    long_name="Heat survival",
    description="Heat survival computed as a function of maximum temperature.",
    abstract="Heat survival is computed as a function of maximum temperature following Vetharaniam et al. (2021).",
    compute=indices.tasmax_survival,
    cell_methods="time: prod",
)

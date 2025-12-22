"""Early wheat LSA Criteria."""

import lsapy.standardize as lstd
import pandas as pd
from lsapy import SuitabilityCriteria
from xclim.core.calendar import doy_to_days_since

__all__ = ["wheatearly_criteria", "wheatearly_criteria_indicators"]

wheatearly_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -10.21, "b": 0.4077},
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=2,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 2.067, "b": 8.029},
    ),
    "drainage_class": SuitabilityCriteria(
        name="drainage_class",
        long_name="Soil Drainage Class",
        weight=1,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={"rules": {0: 0, 1: 0.1, 2: 0.6, 3: 0.9, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}},
    ),
    "potential_total_available_water": SuitabilityCriteria(
        name="potential_total_available_water",
        long_name="Soil Potential Plant Available Water (mm)",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -1.336, "b": 85.19},
    ),
    "annual_rainfall_excess": SuitabilityCriteria(
        name="annual_rainfall_excess",
        long_name="Annual Rainfall Excess: total annual precipitation",
        weight=1,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 0.6759, "b": 1284},
    ),
    "winter_frost_frequency": SuitabilityCriteria(
        name="winter_frost_frequency",
        long_name="Number of years with at least 5 days below -8°C between crop emergence and ear 1cm",
        weight=1.0,
        category="climate",
        func=lstd.logistic,
        fparams={"a": -2.326, "b": 3.143},
    ),
    "growth_frost_frequency": SuitabilityCriteria(
        name="growth_frost_frequency",
        long_name="Number of years with at least 5 days below -2°C between ear 1cm and flag leaf",
        weight=1,
        category="climate",
        func=lstd.logistic,
        fparams={"a": -4.652, "b": 2.572},
    ),
    "flowering_heat_frequency": SuitabilityCriteria(
        name="flowering_heat_frequency",
        long_name="Number of years with at least 5 days above 30°C between anthesis +/- 30 days",
        weight=1,
        category="climate",
        func=lstd.logistic,
        fparams={"a": -2.326, "b": 3.143},
    ),
    "maturity_date": SuitabilityCriteria(
        name="maturity_date",
        long_name="Date of Maturity",
        weight=1,
        category="climate",
        func=lstd.boolean,
        fparams={"op": "<=", "thresh": 364},
    ),
}


def _format_maturity_date(da):
    """
    Format maturity date indicator.

    Convert maturity date from day-of-year to days since April 1st and shift time coordinate
    to July 1st to align with the YS-JUL calendar.
    """
    da = doy_to_days_since(da)
    return da.assign_coords(time=(pd.to_datetime(da.time) + pd.DateOffset(months=3)))  # YS-APR to YS-JUL


wheatearly_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "potential_total_available_water": (
        "New-Zealand-Gridded-Land-Information-Dataset",
        "profile_total_available_water",
    ),
    "annual_rainfall_excess": "prcptot_annual",
    "winter_frost_frequency": "wheatearly_years-5fdm8_emergence-ear1cm_5yr_annual",
    "growth_frost_frequency": "wheatearly_years-5fdm2_ear1cm-flagleaf_5yr_annual",
    "flowering_heat_frequency": "wheatearly_years-5txge30_30anthesis-anthesis30_5yr_annual",
    "maturity_date": "wheatearly_maturity_annual",
    "preprocess": {
        "maturity_date": {"convert_calendar": {"calendar": "standard"}, "func": (_format_maturity_date, {})}
    },
}

"""Early wheat LSA Criteria."""

import lsapy.standardize as lstd
import numpy as np
import pandas as pd
from lsapy import SuitabilityCriteria
from xclim.core.calendar import doy_to_days_since

__all__ = ["wheatearly_criteria", "wheatearly_criteria_indicators"]


def leroux_sigmoid(x, a, b):
    """Le Roux et al. (2024) sigmoid function."""
    return 1 / (1 + np.exp(np.subtract(a, x) / b))


def leroux_exp(x, a, b):
    """Le Roux et al. (2024) modified exponential function."""
    return np.minimum(a * np.exp(b / x), 1)


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
    "winter_frost_days": SuitabilityCriteria(
        name="winter_frost_days",
        long_name="Number of days below -8°C between crop emergence and ear 1cm",
        weight=1,
        category="climate",
        func=leroux_exp,
        fparams={"a": 0.04, "b": 6.0},
    ),
    "growth_frost_days": SuitabilityCriteria(
        name="growth_frost_days",
        long_name="Number of days below -5°C between ear 1cm and flag leaf",
        weight=1,
        category="climate",
        func=leroux_sigmoid,
        fparams={"a": 2.8, "b": -0.5},
    ),
    "flowering_heat_days": SuitabilityCriteria(
        name="flowering_heat_days",
        long_name="Number of days above 30°C between anthesis +/- 30 days",
        weight=1,
        category="climate",
        func=leroux_sigmoid,
        fparams={"a": 2.8, "b": -0.5},
    ),
    "maturity_date": SuitabilityCriteria(
        name="maturity_date",
        long_name="Date of Maturity",
        weight=0.25,
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
    "winter_frost_days": "wheatearly_fdm8_emergence-ear1cm_annual",
    "growth_frost_days": "wheatearly_fdm5_ear1cm-flagleaf_annual",
    "flowering_heat_days": "wheatearly_txge30_30anthesis-anthesis30_annual",
    "maturity_date": "wheatearly_maturity_annual",
    "preprocess": {
        "maturity_date": {"convert_calendar": {"calendar": "standard"}, "func": (_format_maturity_date, {})}
    },
}

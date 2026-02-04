"""Early maize LSA Criteria."""

import lsapy.standardize as lstd
import numpy as np
import pandas as pd
from lsapy import SuitabilityCriteria
from xclim.core.calendar import doy_to_days_since

__all__ = ["maizeearly_criteria", "maizeearly_criteria_indicators"]


def caubel_sigmoid(x, a, b):
    """Caubel et al. (2015) sigmoid function."""
    return 1 / (1 + np.exp(np.subtract(a, x) / b))


def caubel_exp(x, a, b):
    """Caubel et al. (2015) modified exponential function."""
    return np.minimum(a * np.exp(b / x), 1)


maizeearly_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=lstd.logistic,
        fparams={"a": 8.954, "b": 0.5532},
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=2,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 2.067, "b": 8.029},
    ),
    "topsoil_gravel_content": SuitabilityCriteria(
        name="topsoil_gravel_content",
        long_name="Topsoil Gravel Content",
        weight=0.5,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 1.550, "b": 6.214},
    ),
    "salinity": SuitabilityCriteria(
        name="salinity",
        long_name="Salinity",
        weight=0.5,
        category="soilTerrain",
        func=lstd.boolean,
        fparams={"op": "<", "thresh": 0.1},
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
        fparams={"a": 2.719, "b": 1410},
    ),
    "growth_frost_days": SuitabilityCriteria(
        name="growth_frost_days",
        long_name="Number of days below -6°C between emergence and beginning of stem elongation",
        weight=1,
        category="climate",
        func=caubel_exp,
        fparams={"a": 0.1, "b": 3.5},
    ),
    "flowering_heat_days": SuitabilityCriteria(
        name="flowering_heat_days",
        long_name="Frequency of days above 35°C between anthesis +/- 30 days",
        weight=1,
        category="climate",
        func=caubel_sigmoid,
        fparams={"a": 20, "b": -4},
    ),
    "harvest_cold_days": SuitabilityCriteria(
        name="harvest_cold_days",
        long_name="Frequency of days with mean daily temperature below 10°C between flowering and maturity",
        weight=1,
        category="climate",
        func=caubel_sigmoid,
        fparams={"a": 20, "b": -4},
    ),
    "maturity_date": SuitabilityCriteria(
        name="maturity_date",
        long_name="Date of Maturity",
        weight=0.25,
        category="climate",
        func=lstd.boolean,
        fparams={"op": "<=", "thresh": 363},
    ),
}


def _format_maturity_date(da):
    """
    Format maturity date indicator.

    Convert maturity date from day-of-year to days since November 1st and shift time coordinate
    to July 1st to align with the YS-JUL calendar.
    """
    da = doy_to_days_since(da)
    return da.assign_coords(time=(pd.to_datetime(da.time) + pd.DateOffset(months=-4)))  # YS-NOV to YS-JUL


maizeearly_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "topsoil_gravel_content": ("New-Zealand-Gridded-Land-Information-Dataset", "topsoil_gravel_content"),
    "salinity": ("New-Zealand-Gridded-Land-Information-Dataset", "salinity"),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "potential_total_available_water": (
        "New-Zealand-Gridded-Land-Information-Dataset",
        "profile_total_available_water",
    ),
    "annual_rainfall_excess": "prcptot_annual",
    "growth_frost_days": "maizeearly_fdm6_emergence-stemelongation_annual",
    "flowering_heat_days": "maizeearly_txge35freq_30anthesis-anthesis30_annual",
    "harvest_cold_days": "maizeearly_tnle10freq_anthesis-maturity_annual",
    "maturity_date": "maizeearly_maturity_annual",
    "preprocess": {
        "maturity_date": {"convert_calendar": {"calendar": "standard"}, "func": (_format_maturity_date, {})}
    },
}

"""Citrus LSA Criteria."""

import lsapy.standardize as lstd
from lsapy import SuitabilityCriteria

__all__ = ["citrus_criteria", "citrus_criteria_indicators"]

citrus_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -10.27, "b": 0.5506},
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 3.629, "b": 10.70},
    ),
    "topsoil_gravel_content": SuitabilityCriteria(
        name="topsoil_gravel_content",
        long_name="Topsoil Gravel Content",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 0.9353, "b": 39.34},
    ),
    "salinity": SuitabilityCriteria(
        name="salinity",
        long_name="Salinity",
        weight=1,
        category="soilTerrain",
        func=lstd.boolean,
        fparams={"op": "<", "thresh": 0.1},
    ),
    "potential_total_available_water": SuitabilityCriteria(
        name="potential_total_available_water",
        long_name="Soil Potential Plant Available Water (mm)",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -0.6951, "b": 150.1},
    ),
    "drainage_class": SuitabilityCriteria(
        name="drainage_class",
        long_name="Soil Drainage Class",
        weight=1,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={"rules": {0: 1, 1: 1, 2: 0.8, 3: 0.6, 4: 0.4, 5: 0.2, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}},
    ),
    "ph": SuitabilityCriteria(
        name="ph",
        long_name="Soil pH",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2024_eq10,
        fparams={"a": 0.0003683, "b": 5.974, "c": 2.767},
    ),
    "rainfall_excess": SuitabilityCriteria(
        name="rainfall_excess",
        long_name="Rainfall excess: annual total precipitation (mm)",
        weight=1,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 0.5805, "b": 2080},
    ),
    "tn_mean": SuitabilityCriteria(
        name="tn_mean",
        long_name="Mean daily minimum temperature between Aug 15 and Oct 15 (°C)",
        weight=1.5,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -7.315, "b": 2.84},
    ),
    "tg_mean": SuitabilityCriteria(
        name="tg_mean",
        long_name="Mean daily temperature between Sep 15 and Nov 15 (°C)",
        weight=1.5,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -15.14, "b": 10.85},
    ),
    "tx_mean": SuitabilityCriteria(
        name="tx_mean",
        long_name="Mean daily maximum temperature between Jan 1 and Feb 15 (°C)",
        weight=1.5,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -5.576, "b": 14.55},
    ),
    "year_with_hot_week": SuitabilityCriteria(
        name="year_with_hot_week",
        long_name=(
            "Number of years with at least one hot week (3 days over 35C in a 7-day period)"
            " between Dec 1 and Feb 28 (over 10 years)"
        ),
        weight=1.5,
        category="climate",
        func=lstd.vetharaniam2022_eq3,
        fparams={"a": -2.326, "b": 2.143},
    ),
}

citrus_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "topsoil_gravel_content": ("New-Zealand-Gridded-Land-Information-Dataset", "topsoil_gravel_content"),
    "salinity": ("New-Zealand-Gridded-Land-Information-Dataset", "salinity"),
    "potential_total_available_water": (
        "New-Zealand-Gridded-Land-Information-Dataset",
        "profile_total_available_water",
    ),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "ph": ("New-Zealand-Gridded-Land-Information-Dataset", "ph"),
    "rainfall_excess": "prcptot_annual",
    "tn_mean": "tnm_0815-1015_annual",
    "tg_mean": "tgm_0915-1115_annual",
    "tx_mean": "txm_0101-0215_annual",
    "year_with_hot_week": "years-7days-3txge35_1201-0228_10yr_annual",
    "preprocess": {"tn_mean": {"clip": {"min": 0}}},
}

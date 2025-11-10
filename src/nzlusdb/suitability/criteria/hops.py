"""Hops LSA Criteria."""

import lsapy.standardize as lstd
from lsapy import SuitabilityCriteria

__all__ = ["hops_criteria", "hops_criteria_indicators"]

hops_criteria = {
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
        weight=2,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 3.629, "b": 10.70},
    ),
    "topsoil_gravel_content": SuitabilityCriteria(
        name="topsoil_gravel_content",
        long_name="Topsoil Gravel Content",
        weight=0.5,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 0.9353, "b": 39.34},
    ),
    "salinity": SuitabilityCriteria(
        name="salinity",
        long_name="Salinity",
        weight=0.5,
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
        fparams={"a": 2.347, "b": 5.937, "c": 0.8710},
    ),
    "rainfall_excess": SuitabilityCriteria(
        name="rainfall_excess",
        long_name="Rainfall excess: annual total precipitation (mm)",
        weight=0.5,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 1.184, "b": 1632},
    ),
    "chilling_hours": SuitabilityCriteria(
        name="chilling_hours",
        long_name="Chilling hours between May 1 and Aug 30",
        weight=1.5,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -0.425, "b": 340.0},
    ),
    "tn_mean": SuitabilityCriteria(
        name="tn_mean",
        long_name="Mean daily minimum temperature between Aug 15 and Oct 15 (°C)",
        weight=2,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -6.154, "b": 1.826},
    ),
    "tg_mean": SuitabilityCriteria(
        name="tg_mean",
        long_name="Mean daily temperature between Dec 1 and Jan 31 (°C)",
        weight=2,
        category="climate",
        func=lstd.vetharaniam2022_eq3,
        fparams={"a": 0.9693, "b": 7.567},
    ),
    "tx_mean": SuitabilityCriteria(
        name="tx_mean",
        long_name="Mean maximum temperature between Feb 1 and Mar 15 (°C)",
        weight=1.5,
        category="climate",
        func=lstd.vetharaniam2022_eq3,
        fparams={"a": 0.9693, "b": 17.57},
    ),
    "year_with_hot_week": SuitabilityCriteria(
        name="year_with_hot_week",
        long_name=(
            "Number of years with at least one hot week (3 days over 35C in a 7-day period)"
            " between Mar 1 and Apr 20 (over 10 years)"
        ),
        weight=1.5,
        category="climate",
        func=lstd.vetharaniam2022_eq3,
        fparams={"a": -2.326, "b": 2.143},
    ),
}

hops_criteria_indicators = {
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
    "chilling_hours": "ch_0501-0830_annual",
    "tn_mean": "tnm_0815-1015_annual",
    "tg_mean": "tgm_1201-0131_annual",
    "tx_mean": "txm_0201-0315_annual",
    "year_with_hot_week": "years-7days-3txge35_0301-0420_10yr_annual",
    "preprocess": {"tn_mean": {"clip": {"min": 0}}},
}

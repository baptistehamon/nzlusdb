"""Manuka LSA Criteria."""

import xarray as xr
from lsapy import SuitabilityCriteria, SuitabilityFunction

__all__ = ["manuka_criteria", "manuka_criteria_indicators"]

manuka_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=SuitabilityFunction(name="vetharaniam2022_eq5", params={"a": -14.12, "b": 0.2754}),
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=1,
        category="soilTerrain",
        func=SuitabilityFunction(name="vetharaniam2022_eq3", params={"a": -0.1787, "b": 22.34}),
    ),
    "topsoil_gravel_content": SuitabilityCriteria(
        name="topsoil_gravel_content",
        long_name="Topsoil Gravel Content",
        weight=1,
        category="soilTerrain",
        indicator=xr.DataArray(),
        func=SuitabilityFunction(name="vetharaniam2022_eq5", params={"a": 0.9981, "b": 39.46}),
    ),
    "salinity": SuitabilityCriteria(
        name="salinity",
        long_name="Salinity",
        weight=1,
        category="soilTerrain",
        indicator=xr.DataArray(),
        func=SuitabilityFunction(name="boolean", params={"op": "<", "thresh": 0.1}),
    ),
    "potential_total_available_water": SuitabilityCriteria(
        name="potential_total_available_water",
        long_name="Soil Potential Plant Available Water (mm)",
        weight=1,
        category="soilTerrain",
        func=SuitabilityFunction(name="vetharaniam2022_eq5", params={"a": -1.146, "b": 54.65}),
    ),
    "tn_mean": SuitabilityCriteria(
        name="tn_mean",
        long_name="Mean daily minimum temperature between Jun 15 and Sep 15 (°C)",
        weight=2.5,
        category="climate",
        func=SuitabilityFunction(name="vetharaniam2022_eq3", params={"a": 2.333, "b": -2.144}),
    ),
    "tx_mean": SuitabilityCriteria(
        name="tx_mean",
        long_name="Mean daily maximum temperature between Oct 15 and Jan 31 (°C)",
        weight=2.5,
        category="climate",
        func=SuitabilityFunction(name="vetharaniam2022_eq5", params={"a": -7.920, "b": 11.70}),
    ),
}

manuka_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "topsoil_gravel_content": ("New-Zealand-Gridded-Land-Information-Dataset", "topsoil_gravel_content"),
    "salinity": ("New-Zealand-Gridded-Land-Information-Dataset", "salinity"),
    "potential_total_available_water": (
        "New-Zealand-Gridded-Land-Information-Dataset",
        "profile_total_available_water",
    ),
    "tn_mean": "tnm_0622-0922_annual",
    "tx_mean": "txm_1015-0131_annual",
}

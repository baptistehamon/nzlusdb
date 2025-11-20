"""Blueberry LSA Criteria."""

import lsapy.standardize as lstd
from lsapy import SuitabilityCriteria

__all__ = ["blueberry_criteria", "blueberry_criteria_indicators"]

blueberry_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -12.00, "b": 0.3500},
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=0.5,
        category="soilTerrain",
        func=lstd.logistic,
        fparams={"a": -0.500, "b": 12.00},
    ),
    "drainage_class": SuitabilityCriteria(
        name="drainage_class",
        long_name="Soil Drainage Class",
        weight=3,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={"rules": {0: 0, 1: 0.1, 2: 0.3, 3: 0.75, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}},
    ),
    "land_use_capability": SuitabilityCriteria(
        name="land_use_capability",
        long_name="Land Use Capability Class",
        weight=1,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={
            "rules": {0: 1, 1: 0.95, 2: 0.9, 3: 0.8, 4: 0.6, 5: 0.4, 6: 0.2, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}
        },
    ),
    "ph": SuitabilityCriteria(
        name="ph",
        long_name="Soil pH",
        weight=2,
        category="soilTerrain",
        func=lstd.vetharaniam2024_eq10,
        fparams={"a": 150.0, "b": 4.700, "c": 0.2000},
    ),
    "chilling_hours": SuitabilityCriteria(
        name="chilling_hours",
        long_name="Chilling hours between May 1 and Aug 31",
        weight=2,
        category="climate",
        func=lstd.logistic,
        fparams={"a": 0.007350, "b": 550.0},
    ),
    "frost_survival": SuitabilityCriteria(
        name="frost_survival",
        long_name="Frost survival flowering period (from Sept 1 to Oct 31)",
        weight=2,
        category="climate",
        is_computed=True,
    ),
    "growing_degree_days": SuitabilityCriteria(
        name="growing_degree_days",
        long_name="Growing degree days between Oct 1 and Apr 30",
        weight=2,
        category="climate",
        func=lstd.vetharaniam2022_eq3,
        fparams={"a": 0.0110, "b": 700.0},
    ),
}

blueberry_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "land_use_capability": ("New-Zealand-Gridded-Land-Information-Dataset", "land_use_capability"),
    "ph": ("New-Zealand-Gridded-Land-Information-Dataset", "ph"),
    "chilling_hours": "ch7_0501-0831_annual",
    "frost_survival": "blueberry_frost-survival_0901-1031_annual",
    "growing_degree_days": "gdd10_1001-0430_annual",
}

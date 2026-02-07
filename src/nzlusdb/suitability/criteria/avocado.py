"""Avocado LSA Criteria."""

import lsapy.standardize as lstd
from lsapy import SuitabilityCriteria

__all__ = ["avocado_criteria", "avocado_criteria_indicators"]

avocado_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -11.00, "b": 0.6500},
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=0.5,
        category="soilTerrain",
        func=lstd.logistic,
        fparams={"a": -0.500, "b": 19.00},
    ),
    "drainage_class": SuitabilityCriteria(
        name="drainage_class",
        long_name="Soil Drainage Class",
        weight=3,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={"rules": {0: 0, 1: 0.1, 2: 0.4, 3: 0.9, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}},
    ),
    "land_use_capability": SuitabilityCriteria(
        name="land_use_capability",
        long_name="Land Use Capability Class",
        weight=1,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={
            "rules": {0: 1, 1: 0.95, 2: 0.9, 3: 0.8, 4: 0.65, 5: 0.5, 6: 0.05, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}
        },
    ),
    "ph": SuitabilityCriteria(
        name="ph",
        long_name="Soil pH",
        weight=2,
        category="soilTerrain",
        func=lstd.vetharaniam2024_eq10,
        fparams={"a": 0.7400, "b": 6.500, "c": 1.000},
    ),
    "frost_survival": SuitabilityCriteria(
        name="frost_survival",
        long_name="Annual frost survival",
        weight=2,
        category="climate",
        is_computed=True,
    ),
    "tg_mean": SuitabilityCriteria(
        name="tg_mean",
        long_name="Mean annual temperature",
        weight=2,
        category="climate",
        func=lstd.vetharaniam2024_eq8,
        fparams={"a": 2.073e-3, "b": 17.50, "c": 4.000},
    ),
}

avocado_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "land_use_capability": ("New-Zealand-Gridded-Land-Information-Dataset", "land_use_capability"),
    "ph": ("New-Zealand-Gridded-Land-Information-Dataset", "ph"),
    "frost_survival": "avocado_frost-survival_annual",
    "tg_mean": "tgm_annual",
}

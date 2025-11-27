"""Kiwifruit LSA Criteria."""

import lsapy.standardize as lstd
from lsapy import SuitabilityCriteria

__all__ = ["kiwifruit_criteria", "kiwifruit_criteria_indicators"]

kiwifruit_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -10.30, "b": 0.4500},
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=1,
        category="soilTerrain",
        func=lstd.logistic,
        fparams={"a": -0.500, "b": 12.00},
    ),
    "drainage_class": SuitabilityCriteria(
        name="drainage_class",
        long_name="Soil Drainage Class",
        weight=2,
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
    "tg_mean": SuitabilityCriteria(
        name="tg_mean",
        long_name="Mean annual temperature between May 1 and Jul 31",
        weight=1,
        category="climate",
        func=lstd.logistic,
        fparams={"a": -1.200, "b": 12.20},
    ),
    "growing_degree_days": SuitabilityCriteria(
        name="growing_degree_days",
        long_name="Growing degree days between Oct 1 and Apr 30",
        weight=1,
        category="climate",
        func=lstd.logistic,
        fparams={"a": 0.01400, "b": 900.0},
    ),
    "frost_survival": SuitabilityCriteria(
        name="frost_survival",
        long_name="Frost survival during growing period (Aug 13 to Jun 30)",
        weight=1,
        category="climate",
        is_computed=True,
    ),
    "tn_min": SuitabilityCriteria(
        name="tn_min",
        long_name="Minimum annual temperature",
        weight=2,
        category="climate",
        is_computed=True,
    ),
}

kiwifruit_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "land_use_capability": ("New-Zealand-Gridded-Land-Information-Dataset", "land_use_capability"),
    "tg_mean": "tgm_0501-0731_annual",
    "growing_degree_days": "gdd10_1001-0430_annual",
    "frost_survival": "kiwifruit_frost_survival_225-181_annual",
    "tn_min": "tnn_annual",
}

"""Cherry LSA Criteria."""

import lsapy.standardize as lstd
from lsapy import SuitabilityCriteria

__all__ = ["cherry_criteria", "cherry_criteria_indicators"]

cherry_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -12.77, "b": 0.6005},
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=0.5,
        category="soilTerrain",
        func=lstd.logistic,
        fparams={"a": -0.4395, "b": 15.00},
    ),
    "drainage_class": SuitabilityCriteria(
        name="drainage_class",
        long_name="Soil Drainage Class",
        weight=2,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={"rules": {0: 0, 1: 0.2, 2: 0.4, 3: 0.9, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}},
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
    "chilling_hours": SuitabilityCriteria(
        name="chilling_hours",
        long_name="Chilling hours between Jun 1 and Aug 31",
        weight=1,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -0.4457, "b": 897.3},
    ),
    "growing_degree_days": SuitabilityCriteria(
        name="growing_degree_days",
        long_name="Growing degree days between day of budbreak and Apr 30",
        weight=2,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -0.8481, "b": 839.1},
    ),
    "frost_cold": SuitabilityCriteria(
        name="frost_cold",
        long_name="Frost and cold indicator as the product of frost survival and days from budbreak to 31 Dec",
        weight=1,
        category="climate",
        is_computed=True,
    ),
    "cracking_survival": SuitabilityCriteria(
        name="cracking_survival",
        long_name="Craking survival from Nov 1 to ripening",
        weight=0.5,
        category="climate",
        is_computed=True,
    ),
}

cherry_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "land_use_capability": ("New-Zealand-Gridded-Land-Information-Dataset", "land_use_capability"),
    "chilling_hours": "ch7_0601-0831_annual",
    "growing_degree_days": "cherry_gdd4.5_dbb-0430_annual",
    "frost_cold": "cherry_frost-cold_opencluster-ripening_annual",
    "cracking_survival": "cherry_cracking-survival_1101-ripening_annual",
}

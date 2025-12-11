"""Pinot noir LSA Criteria."""

import lsapy.standardize as lstd
from lsapy import SuitabilityCriteria

__all__ = ["pinotnoir_criteria", "pinotnoir_criteria_indicators"]

pinotnoir_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=0.5,
        category="soilTerrain",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -9.333, "b": 0.4000},
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=0.5,
        category="soilTerrain",
        func=lstd.logistic,
        fparams={"a": -0.6278, "b": 12.00},
    ),
    "drainage_class": SuitabilityCriteria(
        name="drainage_class",
        long_name="Soil Drainage Class",
        weight=1,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={"rules": {0: 0, 1: 0.1, 2: 0.4, 3: 0.9, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}},
    ),
    "land_use_capability": SuitabilityCriteria(
        name="land_use_capability",
        long_name="Land Use Capability Class",
        weight=0.25,
        category="soilTerrain",
        func=lstd.discrete,
        fparams={
            "rules": {0: 1, 1: 0.95, 2: 0.9, 3: 0.8, 4: 0.7, 5: 0.65, 6: 0.6, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}
        },
    ),
    "chilling_hours": SuitabilityCriteria(
        name="chilling_hours",
        long_name="Chilling hours between Jun 1 and Aug 31",
        weight=1,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": -0.6727, "b": 145.8},
    ),
    "frost_survival": SuitabilityCriteria(
        name="frost_survival",
        long_name="Frost survival from budbreak to veraison",
        weight=1.25,
        category="climate",
        is_computed=True,
    ),
    "heat_survival": SuitabilityCriteria(
        name="heat_survival",
        long_name="Heat survival from veraison to ripeness",
        weight=1.25,
        category="climate",
        is_computed=True,
    ),
    "botrytis_risk": SuitabilityCriteria(
        name="botrytis_risk",
        long_name="Botrytis risk: total precipitation between Mar 1 and Apr 30",
        weight=3,
        category="climate",
        func=lstd.vetharaniam2022_eq5,
        fparams={"a": 0.9311, "b": 160.0},
    ),
    "ripeness_date": SuitabilityCriteria(
        name="ripeness_date",
        long_name="Date of Ripeness",
        weight=2,
        category="climate",
        func=lstd.boolean,
        fparams={"op": "<=", "thresh": 135},
    ),
}

pinotnoir_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "land_use_capability": ("New-Zealand-Gridded-Land-Information-Dataset", "land_use_capability"),
    "chilling_hours": "0ch7_0601-0831_annual",
    "frost_survival": "pinotnoir_frost-survival_budbreak-veraison_annual",
    "heat_survival": "pinotnoir_heat-survival_veraison-ripeness_annual",
    "botrytis_risk": "prcptot_0301-0430_annual",
    "ripeness_date": "pinotnoir_ripeness_annual",
}

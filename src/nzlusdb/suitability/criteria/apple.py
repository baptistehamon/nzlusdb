"""Apple LSA Criteria."""

from lsapy import SuitabilityCriteria, SuitabilityFunction

__all__ = ["apple_criteria", "apple_criteria_indicators"]

apple_criteria = {
    "potential_rooting_depth": SuitabilityCriteria(
        name="potential_rooting_depth",
        long_name="Potential Rooting Depth",
        weight=1,
        category="soilTerrain",
        func=SuitabilityFunction(name="vetharaniam2022_eq5", params={"a": -10.30, "b": 0.4500}),
    ),
    "slope": SuitabilityCriteria(
        name="slope",
        long_name="Slope",
        weight=0.5,
        category="soilTerrain",
        func=SuitabilityFunction(name="logistic", params={"a": -0.500, "b": 19.00}),
    ),
    "drainage_class": SuitabilityCriteria(
        name="drainage_class",
        long_name="Soil Drainage Class",
        weight=2,
        category="soilTerrain",
        func=SuitabilityFunction(
            name="discrete",
            params={"rules": {0: 0, 1: 0.3, 2: 0.6, 3: 1, 4: 1, 5: 0, 6: 0, 7: 0, 8: 0, 9: 0, 10: 0, 11: 0, 12: 0}},
        ),
    ),
    "land_use_capability": SuitabilityCriteria(
        name="land_use_capability",
        long_name="Land Use Capability Class",
        weight=1,
        category="soilTerrain",
        func=SuitabilityFunction(
            name="discrete",
            params={
                "rules": {
                    0: 1,
                    1: 0.95,
                    2: 0.9,
                    3: 0.8,
                    4: 0.65,
                    5: 0.5,
                    6: 0.05,
                    7: 0,
                    8: 0,
                    9: 0,
                    10: 0,
                    11: 0,
                    12: 0,
                }
            },
        ),
    ),
    "chill_units": SuitabilityCriteria(
        name="chill_units",
        long_name="Chill units between May 1 and Aug 31",
        weight=1,
        category="climate",
        func=SuitabilityFunction(name="logistic", params={"a": 0.005000, "b": 700.0}),
    ),
    "growing_degree_days": SuitabilityCriteria(
        name="growing_degree_days",
        long_name="Growing degree days between Oct 1 and Apr 30",
        weight=1,
        category="climate",
        func=SuitabilityFunction(name="logistic", params={"a": 0.01000, "b": 800.0}),
    ),
    "fruit_size": SuitabilityCriteria(
        name="fruit_size",
        long_name="Growing degree days between day of full bloom and 50 days after",
        weight=1,
        category="climate",
        func=SuitabilityFunction(name="logistic", params={"a": 0.05000, "b": 120.0}),
    ),
    "frost_survival": SuitabilityCriteria(
        name="frost_survival",
        long_name="Frost survival during growth period (from 3 weeks before full bloom to end of April)",
        weight=2,
        category="climate",
        is_computed=True,
    ),
    "sunburn_survival": SuitabilityCriteria(
        name="sunburn_survival",
        long_name="Sunburn survival from Oct 1 to Apr 30",
        weight=0.5,
        category="climate",
        is_computed=True,
    ),
}

apple_criteria_indicators = {
    "potential_rooting_depth": ("New-Zealand-Gridded-Land-Information-Dataset", "potential_rooting_depth"),
    "slope": ("New-Zealand-Gridded-Land-Information-Dataset", "slope"),
    "drainage_class": ("New-Zealand-Gridded-Land-Information-Dataset", "drainage"),
    "land_use_capability": ("New-Zealand-Gridded-Land-Information-Dataset", "land_use_capability"),
    "chill_units": "cu_0501-0831_annual",
    "growing_degree_days": "gdd10_1001-0430_annual",
    "fruit_size": "apple_gdd10_dfb-dfb50d_annual",
    "frost_survival": "apple_frost-survival_dfb-0430_annual",
    "sunburn_survival": "apple_sunburn-survival_1001-0430_annual",
}

"""Wheat NIR Computation Parameters."""

__all__ = ["wheat_kc_params"]

wheat_kc_params = {
    "start_date": "05-15",
    "stage_values": {"init": 0.4, "mid": 1.15, "end": 0.25},
    "stage_lengths": {"init": 30, "dev": 140, "mid": 50, "end": 30},
    "height": 1,
    "freq": "YS-MAY",
}

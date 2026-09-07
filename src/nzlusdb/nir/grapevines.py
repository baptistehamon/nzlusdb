"""Grapevines NIR Computation Parameters."""

__all__ = ["grapevines_kc_params"]

grapevines_kc_params = {
    "start_date": "10-01",
    "stage_values": {"init": 0.3, "mid": 0.7, "end": 0.45},
    "stage_lengths": {"init": 30, "dev": 60, "mid": 40, "end": 80},
    "height": 2,
}

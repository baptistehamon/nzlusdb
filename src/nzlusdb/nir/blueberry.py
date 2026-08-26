"""Blueberry NIR Computation Parameters."""

__all__ = ["blueberry_kc_params"]

blueberry_kc_params = {
    "start_date": "10-01",
    "stage_values": {"init": 0.3, "mid": 1.05, "end": 0.5},
    "stage_lengths": {"init": 25, "dev": 40, "mid": 80, "end": 10},
    "height": 1.5,
}

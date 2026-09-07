"""Citrus NIR Computation Parameters."""

__all__ = ["citrus_kc_params"]

citrus_kc_params = {
    "start_date": "07-01",
    "stage_values": {"init": 0.8, "mid": 0.8, "end": 0.8},
    "stage_lengths": {"init": 60, "dev": 90, "mid": 120, "end": 95},
    "height": 3,
}

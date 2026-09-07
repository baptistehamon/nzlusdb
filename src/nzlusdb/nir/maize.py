"""Maize NIR Computation Parameters."""

__all__ = ["maize_kc_params"]

maize_kc_params = {
    "start_date": "09-01",
    "stage_values": {"init": 0.3, "mid": 1.2, "end": 0.45},
    "stage_lengths": {"init": 30, "dev": 40, "mid": 50, "end": 30},
    "height": 2,
}

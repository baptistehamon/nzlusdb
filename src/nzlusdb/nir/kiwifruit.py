"""Kiwifruit NIR Computation Parameters."""

__all__ = ["kiwifruit_kc_params"]

kiwifruit_kc_params = {
    "start_date": "10-01",
    "stage_values": {"init": 0.4, "mid": 1.05, "end": 1.05},
    "stage_lengths": {"init": 20, "dev": 70, "mid": 90, "end": 30},
    "height": 3,
}

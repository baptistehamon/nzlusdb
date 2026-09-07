"""Apple NIR Computation Parameters."""

__all__ = ["apple_kc_params"]

apple_kc_params = {
    "start_date": "10-15",
    "stage_values": {"init": 0.5, "mid": 1.2, "end": 0.95},
    "stage_lengths": {"init": 20, "dev": 70, "mid": 90, "end": 30},
    "height": 4,
}

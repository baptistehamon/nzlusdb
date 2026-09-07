"""Hops NIR Computation Parameters."""

__all__ = ["hops_kc_params"]

hops_kc_params = {
    "start_date": "10-01",
    "stage_values": {"init": 0.3, "mid": 1.05, "end": 0.85},
    "stage_lengths": {"init": 20, "dev": 40, "mid": 80, "end": 10},
    "height": 5,
}

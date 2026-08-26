"""Avocado NIR Computation Parameters."""

__all__ = ["avocado_kc_params"]

avocado_kc_params = {
    "start_date": "10-01",
    "stage_values": {"init": 0.6, "mid": 0.85, "end": 0.75},
    "stage_lengths": {"init": 20, "dev": 70, "mid": 90, "end": 30},
    "height": 3,
}

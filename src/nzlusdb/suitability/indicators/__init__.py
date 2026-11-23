"""Python Code to compute land use indicators."""

from nzlusdb import db
from nzlusdb.suitability.indicators.utils import LoopOverYears

__all__ = ["LoopOverYearsWithPath"]

INDICATORPATH = db.path / "indicators"


class LoopOverYearsWithPath(LoopOverYears):
    """A child class of LoopOverYears that sets the 'tmp_path' to INDICATORPATH."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs, tmp_path=INDICATORPATH)

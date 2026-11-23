"""Python Code to compute land use indicators."""

from nzlusdb import db
from nzlusdb.suitability.indicators.utils import LoopOverYears as LoopOverYears

INDICATORPATH = db.path / "indicators"

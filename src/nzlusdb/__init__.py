"""Python Code of New Zealand Land Use Database (NZLUSDB)."""

from pathlib import Path

__author__ = "Baptiste Hamon"
__email__ = "baptiste.hamon@pg.canterbury.ac.nz"
__version__ = "0.0-dev5"

__all__ = ["ROOTPATH"]

ROOTPATH = Path(r"R:\DATA\NZLUSDB")
DOCPATH = Path(__file__).parent.parent.parent / "docs"

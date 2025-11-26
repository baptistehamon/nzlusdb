"""Python Code of New Zealand Land Use Suitability Database (NZLUSDB)."""

from pathlib import Path

from nzlusdb.core.database import DataBase

__author__ = "Baptiste Hamon"
__email__ = "baptiste.hamon@pg.canterbury.ac.nz"
__version__ = "1.0-dev7"
release = __version__.split("-", maxsplit=1)[0]

__all__ = ["db", "release"]

db = DataBase(
    name="nzlusdb",
    attrs={
        "title": "New Zealand Land Use Suitability Database (NZLUSDB)",
        "institution": (
            "Department of Civil and Environmental Engineering, University of Canterbury, Christchurch 8140, NZ"
        ),
        "contact": "Baptiste Hamon: baptiste.hamon@pg.canterbury.ac.nz",
        "reference": "https://baptistehamon.github.io/nzlusdb/",
        "version": f"v{release}",
    },
    path=Path(r"R:\DATA"),
)

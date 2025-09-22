"""Python Code of New Zealand Land Use Suitability Database (NZLUSDB)."""

from pathlib import Path

__author__ = "Baptiste Hamon"
__email__ = "baptiste.hamon@pg.canterbury.ac.nz"
__version__ = "0.0-dev6"
release = __version__.split("-", maxsplit=1)[0]

__all__ = ["ROOTPATH", "DOCPATH", "nzlusdb_attrs", "release"]

ROOTPATH = Path(r"R:\DATA\NZLUSDB")
DOCPATH = Path(__file__).parent.parent.parent / "docs"

nzlusdb_attrs = {
    "title": "New Zealand Land Use Suitability Database (NZLUSDB)",
    "institution": "Department of Civil and Environmental Engineering, University of Canterbury, Christchurch 8140, NZ",
    "contact": "Baptiste Hamon: baptiste.hamon@pg.canterbury.ac.nz",
    "reference": "https://baptistehamon.github.io/nzlusdb/",
    "version": f"v{release}",
}

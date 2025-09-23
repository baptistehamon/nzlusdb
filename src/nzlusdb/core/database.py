"""Database class to register land uses."""

from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from nzlusdb.core.landuse import LandUse


class DataBase:
    """
    Database to register land uses.

    Parameters
    ----------
    name : str
        Name of the database.
    attrs : dict
        Global attributes of the database.
    path : Path
        Path to the database folder.
    """

    def __init__(self, name: str, attrs: dict, path: Path):
        self._name = name
        self.attrs = attrs
        self.path = path / self.name.upper()
        self.path.mkdir(parents=True, exist_ok=True)
        self.pathdoc = Path(__file__).parent.parent.parent.parent / "docs"
        self._landuses = {}
        self._lu_names = {}

    @property
    def name(self) -> str:
        """Name of the database."""
        return self._name

    @name.setter
    @staticmethod
    def name(value):
        """Name cannot be changed after initialization."""
        raise AttributeError("Cannot set attribute 'name' after initialization.")

    @property
    def attrs(self) -> dict:
        """Global attributes of the database."""
        return self._attrs

    @attrs.setter
    def attrs(self, value: dict):
        """Set global attributes of the database."""
        if not isinstance(value, dict):
            raise ValueError("attrs must be a dictionary.")
        self._attrs = value

    def register(self, cls_: "LandUse"):
        """Register a land use class in the database."""
        self._lu_names[cls_.name] = cls_.name
        if cls_.name in self._landuses:
            raise ValueError(f"Land use '{cls_.name}' already registered in the database.")
        self._landuses[cls_.name] = cls_

    def __getitem__(self, key) -> "LandUse":
        """Get a land use class from the database."""
        if key not in self._landuses:
            raise KeyError(f"Land use '{key}' not found in the database.")
        return self._landuses[key]

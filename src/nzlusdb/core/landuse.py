"""Land Use class for NZLUSDB."""

from __future__ import annotations

import xarray as xr
from lsapy import LandSuitabilityAnalysis

from nzlusdb import __version__
from nzlusdb.suitability import criteria
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.suitability.lsa import LSAPATH
from nzlusdb.utils import write_netcdf


class LusDb: ...


class LandUse:
    """
    Land Use class for NZLUSDB.

    Parameters
    ----------
    name : str
        Name of the land use.
    description : str, optional
        Description of the land use.
    version : str, optional
        Version of the land use analysis. Default is the current package version.

    Attributes
    ----------
    name : str
        Name of the land use.
    description : str
        Description of the land use.
    version : str
        Version of the land use analysis.
    criteria : dict
        Dictionary of suitability criteria. The `indicator` attribute of each criteria will be populated when
        `run_lsa` is called.
    """

    def __init__(self, name: str, description: str = "", version: str = __version__):
        self.name = name
        self.description = description
        self.version = version
        self._get_criteria_info()

    @property
    def criteria(self):
        """Land Use Criteria."""
        return self._criteria

    @criteria.setter
    def criteria(self, value: dict):
        if not isinstance(value, dict):
            raise ValueError("Criteria must be a dictionary.")
        self._criteria = value

    def run_lsa(self, scenario: str | list[str], resolution: str | list[str], **kwargs) -> xr.Dataset:
        """
        Run land suitability analysis (LSA) for given scenario and resolution.

        Parameters
        ----------
        scenario : str or list of str
            Scenario(s) to use (e.g., 'historical', 'ssp126', 'ssp585').
        resolution : str or list of str
            Resolution(s) to use (e.g., '5km', '1km').
        **kwargs : dict
            Additional keyword arguments to pass to `LandSuitabilityAnalysis.run()`.

        Returns
        -------
        xr.Dataset
            Computed land suitability dataset.
        """
        if isinstance(scenario, str):
            scenario = [scenario]
        if isinstance(resolution, str):
            resolution = [resolution]

        for res in resolution:
            for scen in scenario:
                out = self._run_lsa(scenario=scen, resolution=res, **kwargs)
                out_fp = LSAPATH / f"{self.name}_suitability_{scen}_{res}_{self.version}.nc"
                write_netcdf(out, out_fp, progressbar=True, verbose=True)

    def _run_lsa(self, scenario: str = "historical", resolution: str = "5km", **kwargs) -> xr.Dataset:
        """Internal method to run LSA for a single scenario and resolution."""
        lsa = LandSuitabilityAnalysis(
            land_use=self.name,
            short_name=f"{self.name}_suitability",
            long_name=f"{self.name.capitalize()} Suitability",
            criteria=self._load_criteria_indicators(scenario=scenario, resolution=resolution),
        )
        return lsa.run(**kwargs)

    def _get_criteria_info(self) -> None:
        """Get criteria and criteria indicators from criteria module."""
        crop_criteria = f"{self.name}_criteria"
        crop_criteria_indicators = f"{self.name}_criteria_indicators"
        if hasattr(criteria, crop_criteria):
            self.criteria = getattr(criteria, crop_criteria)
        else:
            raise ValueError(f"Criteria '{crop_criteria}' not found in criteria module.")
        if hasattr(criteria, crop_criteria_indicators):
            self._criteria_indicators = getattr(criteria, crop_criteria_indicators)
        else:
            raise ValueError(f"Criteria indicators '{crop_criteria_indicators}' not found in criteria module.")

    def _load_criteria_indicators(self, scenario, resolution) -> dict:
        """Load criteria indicators based on scenario and resolution."""
        clim_res = {"5km": "25km", "1km": "5km"}.get(resolution, resolution)
        sc = self.criteria
        for key, val in sc.items():
            if key in self._criteria_indicators:
                file = self._criteria_indicators[key]
                if isinstance(file, tuple):
                    file, variable = file
                else:
                    variable = None

                if val.category == "climate":
                    file = f"{file}_{scenario}_{clim_res}.nc"
                elif val.category == "soilTerrain":
                    file = f"{file}_NZ{resolution}.nc"
                else:
                    raise ValueError(f"Unknown category '{val.category}' for criteria '{key}'.")

                val.indicator = self._load_indicator(file, variable)
            else:
                raise ValueError(f"Indicator for criteria '{key}' not found in criteria indicators.")
        sc = self._interpolate_indicator(sc)
        return sc

    @staticmethod
    def _load_indicator(file: str, variable: str | None = None) -> xr.DataArray:
        """Load an indicator from a NetCDF file."""
        ds = xr.open_dataset(INDICATORPATH / file)
        if variable:
            return ds[variable]
        elif len(ds.data_vars) == 1:
            return list(ds.data_vars.values())[0]
        else:
            raise ValueError(f"Multiple variables found in {file}. Please specify a variable.")

    @staticmethod
    def _interpolate_indicator(sc):
        """Interpolate indicators to climate resolution if needed."""
        category = list(set([val.category for val in sc.values()]))
        if len(category) != 1:
            for val in sc.values():
                if val.category == "climate":
                    continue
                else:
                    target = val.indicator
                    break

            for val in sc.values():
                if val.category == "climate":
                    val.indicator = val.indicator.interp_like(target, method="nearest")
        return sc

    def write_data(): ...

    def make_plot(): ...

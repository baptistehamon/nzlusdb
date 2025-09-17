"""Land Use class for NZLUSDB."""

from __future__ import annotations

import xarray as xr
from lsapy import LandSuitabilityAnalysis
from xclim import ensembles as xens

from nzlusdb import __version__
from nzlusdb.core.climdataset import climateDS
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
                out_fp = LSAPATH / self.name
                out_fp.mkdir(parents=True, exist_ok=True)
                out_fp /= f"{self.name}_suitability_{scen}_{res}_v{self.version}.nc"
                write_netcdf(out, out_fp, progressbar=True, verbose=True)

    def open_suitability(self, resolution: str = "5km") -> xr.Dataset:
        """Open suitability dataset for given resolution.

        Parameters
        ----------
        resolution : str
            Resolution of the suitability dataset (e.g., '5km', '1km').

        Returns
        -------
        xr.Dataset
            Suitability dataset.
        """
        fp = LSAPATH / self.name
        files = list(fp.glob("*.nc"))

        hist_scenario = climateDS[f"nzlusdb_{resolution}"].hist_scenario
        proj_scenarios = climateDS[f"nzlusdb_{resolution}"].proj_scenario

        hist = xr.open_dataset([f for f in files if hist_scenario in f.name][0])["suitability"]
        proj = []
        for scen in proj_scenarios:
            file = [f for f in files if scen in f.name][0]
            ds = xr.open_dataset(file)["suitability"].assign_coords(scenario=scen).expand_dims("scenario")
            proj.append(ds)
        return xr.concat([hist, xr.concat(proj, dim="scenario")], dim="time")

    def write_output(self, data: xr.Dataset, resolution: str = "5km") -> None:
        """
        Write suitability data to NetCDF and GeoTIFF files.

        The suitability should correspond to the output of `period_mmm_change_robustness`.

        Parameters
        ----------
        data : xr.Dataset
            Dataset containing suitability data with dimensions including 'time'.
        resolution : str
            Resolution of the suitability dataset (e.g., '5km', '1km').

        Returns
        -------
        None
            Writes NetCDF and GeoTIFF files to the appropriate directory.
        """
        fp = LSAPATH / self.name / f"{self.name}_suitability-MMM-change-robustness_{resolution}_v{self.version}.nc"
        data.to_netcdf(fp)

        data = data.set_index(time=["scenario", "period"])
        self._write_output_as_raster(data, resolution=resolution)

    @staticmethod
    def period_mmm_change_robustness(data: xr.DataArray, delta_method="absolute") -> xr.Dataset:
        """
        Compute multi-model mean, future changes and associated robustness.

        The computation are done using the 1980-2009 period as reference, and three future periods:
        2010-2039 (near term), 2040-2069 (mid-term) and 2070-2099 (long term). The robustness is computed
        following the IPCC AR6 methodology.

        Parameters
        ----------
        data : xr.DataArray
            Input data array with dimensions including 'time', 'scenario', and 'realization'.
        delta_method : str, optional
            Method to compute changes: "absolute" for absolute changes, "relative" for percentage changes.
            Default is "absolute".

        Returns
        -------
        xr.Dataset
            Dataset containing the multi-model mean of the variable for each period and scenario, the computed changes,
            and the robustness categories. A multi-index 'time' dimension combining 'period' and 'scenario' is used.
        """
        data_hist = data.sel(time=slice("1980", "2009"))
        data_near = data.sel(time=slice("2010", "2039"))
        data_mid = data.sel(time=slice("2040", "2069"))
        data_long = data.sel(time=slice("2070", "2099"))

        fractions = xr.concat(
            [
                xens.robustness_fractions(data_near, data_hist, test="ipcc-ar6-c").assign_coords(period="2010-2039"),
                xens.robustness_fractions(data_mid, data_hist, test="ipcc-ar6-c").assign_coords(period="2040-2069"),
                xens.robustness_fractions(data_long, data_hist, test="ipcc-ar6-c").assign_coords(period="2070-2099"),
            ],
            dim="period",
        )

        robustness_cat = xens.robustness_categories(fractions).rename("robustness_categories")

        robustness_coeff = xr.concat(
            [
                xens.robustness_coefficient(data_near, data_hist.mean("realization")).assign_coords(period="2010-2039"),
                xens.robustness_coefficient(data_mid, data_hist.mean("realization")).assign_coords(period="2040-2069"),
                xens.robustness_coefficient(data_long, data_hist.mean("realization")).assign_coords(period="2070-2099"),
            ],
            dim="period",
        ).rename("robustness_coefficient")

        data_hist = data_hist.isel(scenario=0).drop_vars("scenario").mean("time")
        data_proj = xr.concat(
            [
                data_near.assign_coords(period="2010-2039"),
                data_mid.assign_coords(period="2040-2069"),
                data_long.assign_coords(period="2070-2099"),
            ],
            dim="period",
        ).mean("time")

        if delta_method == "absolute":
            delta = (data_proj - data_hist).mean("realization").rename("change")
            if "units" in data.attrs:
                delta.attrs["units"] = data.attrs["units"]
        elif delta_method == "relative":
            delta = ((data_proj - data_hist) / data_hist * 100).mean("realization").rename("change")

        delta = xr.merge(
            [
                delta.stack(time=["period", "scenario"]),
                robustness_cat.stack(time=["period", "scenario"]),
                robustness_coeff.stack(time=["period", "scenario"]),
            ]
        )

        data_hist = data_hist.assign_coords(period="1980-2009", scenario="historical").expand_dims(
            ["period", "scenario"]
        )

        out = xr.concat(
            [data_hist.stack(time=("period", "scenario")), data_proj.stack(time=("period", "scenario"))], dim="time"
        ).mean("realization")

        return xr.merge([out, delta]).reset_index("time")

    def _run_lsa(self, scenario: str = "historical", resolution: str = "5km", **kwargs) -> xr.Dataset:
        """Internal method to run LSA for a single scenario and resolution."""
        lsa = LandSuitabilityAnalysis(
            land_use=self.name,
            short_name=f"{self.name}_suitability",
            long_name=f"{self.name.capitalize()} Suitability",
            criteria=self._load_criteria_indicators(scenario=scenario, resolution=resolution),
        )
        return lsa.run(**kwargs)

    def _write_output_as_raster(self, data: xr.Dataset, resolution: str = "5km") -> None:
        """
        Write suitability data to GeoTIFF files.

        The suitability should correspond to the output of `period_mmm_change_robustness`.

        Parameters
        ----------
        data : xr.Dataset
            Dataset containing suitability data with dimensions including 'time'.

        Returns
        -------
        None
            Writes GeoTIFF files to the appropriate directory.
        """
        vars_dict = {
            "suitability": "suitability",
            "change": "suitability-change",
            "robustness_categories": "suitability-robustness-categories",
            "robustness_coefficient": "suitability-robustness-coefficient",
        }

        for time in data.time.values:
            for var in ["suitability", "change", "robustness_categories", "robustness_coefficient"]:
                if time == ("historical", "1980-2009") and var in [
                    "change",
                    "robustness_categories",
                    "robustness_coefficient",
                ]:
                    continue
                da = data[var].sel(time=time)
                da = da.rio.set_spatial_dims(x_dim="lon", y_dim="lat").rio.write_crs("EPSG:4326")
                fp = LSAPATH / self.name / "tiff"
                fp.mkdir(parents=True, exist_ok=True)
                fp /= f"{self.name}_{vars_dict[var]}_{time[0]}_{time[1]}_{resolution}_v{self.version}.tif"
                da.rio.to_raster(fp)

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

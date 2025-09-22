"""Land Use class for NZLUSDB."""

from __future__ import annotations

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from lsapy import LandSuitabilityAnalysis
from lsapy.stats import spatial_stats_summary, stats_summary
from xclim import ensembles as xens

from nzlusdb import DOCPATH, nzlusdb_attrs, release
from nzlusdb.core.climdataset import climateDS
from nzlusdb.core.plot import change_boundnorm, suitability_boundnorm, summary_figure
from nzlusdb.suitability import criteria
from nzlusdb.suitability.indicators import INDICATORPATH
from nzlusdb.suitability.lsa import LSAPATH
from nzlusdb.utils import write_netcdf


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
    resolution : str
        Resolution of the land use analysis ('1km' or '5km').
    version : str
        Version of the land use analysis.
    criteria : dict
        Dictionary of suitability criteria. The `indicator` attribute of each criteria will be populated when
        `run_lsa` is called.
    """

    def __init__(self, name: str, description: str = "", resolution: str = "5km", version: str = release):
        self.name = name
        self.description = description
        self.resolution = resolution
        self.version = version
        self._get_criteria_info()
        self.path = LSAPATH / self.name
        self._nzlusdb_attrs = nzlusdb_attrs
        if self._nzlusdb_attrs.get("version", None) != f"v{self.version}":
            self._nzlusdb_attrs["version"] = f"v{self.version}"

    @property
    def criteria(self):
        """Land Use Criteria."""
        return self._criteria

    @criteria.setter
    def criteria(self, value: dict):
        if not isinstance(value, dict):
            raise ValueError("Criteria must be a dictionary.")
        self._criteria = value

    @property
    def resolution(self):
        """Resolution of the land use analysis."""
        return self._resolution

    @resolution.setter
    def resolution(self, value: str):
        if value not in ["1km", "5km"]:
            raise ValueError("Resolution must be '1km' or '5km'.")
        self._resolution = value

    def run_workflow(self, resolution: list[str] | str | None = None):
        """
        Run the full land suitability analysis (LSA) workflow.

        This method runs the LSA for the specified resolution(s) and scenarios, computes the multi-model mean
        changes and robustness, writes the outputs to NetCDF and GeoTIFF files, and generates summary figures
        and statistics.

        Parameters
        ----------
        resolution : list of str, str, or None
            Resolution(s) to use for the analysis ('1km' or '5km'). If None, uses the instance's resolution attribute.
            Default is None.
        """
        if resolution is None:
            if self.resolution is None:
                raise ValueError("Resolution must be set before running workflow.")
            resolution = [self.resolution]
        elif isinstance(resolution, str):
            resolution = [resolution]

        for res in resolution:
            self.resolution = res
            self.run_lsa(scenario=["historical", "ssp126", "ssp245", "ssp370", "ssp585"], agg_methods="wgmean")
            data = self.open_suitability()
            ds = self.period_mmm_change_robustness(data, delta_method="absolute").assign_attrs(
                {
                    **self._nzlusdb_attrs,
                    **{
                        "source": f"{climateDS[f'nzlusdb_{self.resolution}'].name}: "
                        + f"{', '.join(climateDS[f'nzlusdb_{self.resolution}'].model)}"
                    },
                }
            )
            self.write_output(ds, variable="suitability")
            self.summary_figs()
            self.stats_summary()

    def run_lsa(self, scenario: str | list[str], **kwargs) -> xr.Dataset:
        """
        Run land suitability analysis (LSA) for given scenario and resolution.

        Parameters
        ----------
        scenario : str or list of str
            Scenario(s) to use (e.g., 'historical', 'ssp126', 'ssp585').
        **kwargs : dict
            Additional keyword arguments to pass to `LandSuitabilityAnalysis.run()`.

        Returns
        -------
        xr.Dataset
            Computed land suitability dataset.
        """
        if isinstance(scenario, str):
            scenario = [scenario]

        for scen in scenario:
            out = self._run_lsa(scenario=scen, **kwargs)
            out.attrs.update({**self._nzlusdb_attrs, **{"source": climateDS[f"nzlusdb_{self.resolution}"].name}})
            out["suitability"].attrs.update({"long_name": "Suitability"})
            self.path.mkdir(parents=True, exist_ok=True)
            fp = self.path / f"{self.name}_suitability_{scen}_{self.resolution}_v{self.version}.nc"
            write_netcdf(out, fp, progressbar=True, verbose=True)

    def open_suitability(self) -> xr.Dataset:
        """
        Open suitability dataset for given resolution.

        Returns
        -------
        xr.Dataset
            Suitability dataset.
        """
        files = list(self.path.glob("*.nc"))

        hist_scenario = climateDS[f"nzlusdb_{self.resolution}"].hist_scenario
        proj_scenarios = climateDS[f"nzlusdb_{self.resolution}"].proj_scenario

        hist = xr.open_dataset([f for f in files if hist_scenario in f.name][0])["suitability"]
        proj = []
        for scen in proj_scenarios:
            file = [f for f in files if scen in f.name][0]
            ds = xr.open_dataset(file)["suitability"].assign_coords(scenario=scen).expand_dims("scenario")
            proj.append(ds)
        return xr.concat([hist, xr.concat(proj, dim="scenario")], dim="time")

    def open_mmm_data(self, variable: str = "suitability") -> xr.Dataset:
        """
        Open multi-model mean change and robustness dataset for given variable and resolution.

        Parameters
        ----------
        variable : str
            Name of the variable data corresponds to (default is 'suitability').

        Returns
        -------
        xr.Dataset
            Multi-model mean change and robustness dataset.
        """
        file = f"{self.name}_{variable}-MMM-change-robustness_{self.resolution}_v{self.version}.nc"
        return xr.open_dataset(self.path / file)

    def write_output(self, data: xr.Dataset, variable: str) -> None:
        """
        Write data to NetCDF and GeoTIFF files.

        The method writes output from `period_mmm_change_robustness` to NetCDF and GeoTIFF files
        for a given variable.

        Parameters
        ----------
        data : xr.Dataset
            Dataset output from `period_mmm_change_robustness`.
        variable : str
            Name of the variable data corresponds to.

        Returns
        -------
        None
            Writes NetCDF and GeoTIFF files to the appropriate directories.
        """
        fp = self.path / f"{self.name}_{variable}-MMM-change-robustness_{self.resolution}_v{self.version}.nc"
        data.to_netcdf(fp)

        data = data.set_index(time=["scenario", "period"])
        self._write_output_as_raster(data, variable)

    def summary_figs(self) -> None:
        """
        Generate and save summary figures.

        Two figure are made. The first shows historical and projected suitability, the second shows
        historical suitability and projected changes with robustness. In each figure, the historical
        period is 1980-2009 and the projected periods are 2010-2039, 2040-2069 and 2070-2099 for the
        SSP245 and SSP585 scenarios. The figures are saved in the `docs/_static/summary_figs` directory.
        """
        data = self.open_mmm_data()
        data = data.set_index(time=["scenario", "period"])

        fp = DOCPATH / "_static/summary_figs"
        fp.mkdir(parents=True, exist_ok=True)

        summary_figure(
            data,
            f"Historical and Projected Suitability for {self.name.capitalize()}",
            hist_kw={"norm": suitability_boundnorm, "cmap": "cividis"},
            proj_kw={"norm": suitability_boundnorm, "cmap": "cividis"},
        )
        fname = f"{self.name}_suitability_SSP245-SSP585_{self.resolution}_v{self.version}.png"
        plt.savefig(fp / fname, dpi=300)
        plt.close()

        summary_figure(
            data,
            f"Historical Suitability and Projected Changes for {self.name.capitalize()}",
            proj_var="change",
            hist_kw={"norm": suitability_boundnorm, "cmap": "cividis"},
            proj_kw={"norm": change_boundnorm, "cmap": "PiYG"},
            legend_labels={"suitability": "Suitability", "change": "Change in Suitability"},
            robustness=True,
        )
        fname = f"{self.name}_suitability_change_SSP245-SSP585_{self.resolution}_v{self.version}.png"
        plt.savefig(fp / fname, dpi=300)
        plt.close()

    def stats_summary(self) -> None:
        """Generate and save national and regional suitability statistics summary."""

        def _add_coords(df, mapping):
            df.insert(1, "period", df["time"].map(mapping["period"]))
            df.insert(2, "scenario", df["time"].map(mapping["scenario"]))
            return df.drop(columns=["time"])

        agmask = self._agriculture_mask()
        regions = gpd.read_file(r"R:\DATA\GIS-NZ\statsnz-regional-council-2022-clipped-generalised").to_crs(epsg=4326)

        data = self.open_mmm_data()
        data = data.where(agmask == 1)

        mapping = {
            "scenario": {time: scenario for time, scenario in zip(data["time"].values, data["scenario"].values)},
            "period": {time: period for time, period in zip(data["time"].values, data["period"].values)},
        }

        cell_area = (int(self.resolution.replace("km", "")) ** 2, "km2")

        args = {
            "on_vars": ["suitability"],
            "on_dims": ["time"],
            "dropna": True,
            "bins": np.linspace(0, 1, 11),
            "cell_area": cell_area,
            "all_bins": True,
        }

        nz_stats = stats_summary(
            data,
            **args,
        )
        nz_stats = _add_coords(nz_stats, mapping)

        reg_stats = spatial_stats_summary(
            data,
            areas=regions,
            name="region",
            mask_kwargs={"names": "REGC2022_1"},
            **args,
        )
        reg_stats = _add_coords(reg_stats, mapping)
        nz_stats.to_csv(
            self.path / f"{self.name}_national_suitability_stats_summary_{self.resolution}_v{self.version}.csv",
            index=False,
        )
        reg_stats.to_csv(
            self.path / f"{self.name}_regional_suitability_stats_summary_{self.resolution}_v{self.version}.csv",
            index=False,
        )

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
            delta.attrs["units"] = "%"
        delta.attrs["long_name"] = "Change"

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

    def _run_lsa(self, scenario: str = "historical", **kwargs) -> xr.Dataset:
        """Internal method to run LSA for a single scenario."""
        lsa = LandSuitabilityAnalysis(
            land_use=self.name,
            short_name=f"{self.name}_suitability",
            long_name=f"{self.name.capitalize()} Suitability",
            criteria=self._load_criteria_indicators(scenario=scenario),
        )
        return lsa.run(**kwargs)

    def _write_output_as_raster(self, data: xr.Dataset, variable: str) -> None:
        """
        Write output data as GeoTIFF files.

        The data should correspond to the output of `period_mmm_change_robustness` with the multi-index
        'time' dimension combining 'period' and 'scenario'.

        Parameters
        ----------
        data : xr.Dataset
            Dataset output from `period_mmm_change_robustness`.
        variable : str
            Name of the variable data corresponds to.

        Returns
        -------
        None
            Writes GeoTIFF files to the appropriate directory.
        """
        vars_dict = {
            variable: variable,
            "change": f"{variable}-change",
            "robustness_categories": f"{variable}-robustness-categories",
            "robustness_coefficient": f"{variable}-robustness-coefficient",
        }
        path = self.path / "tiff"
        path.mkdir(parents=True, exist_ok=True)

        for time in data.time.values:
            for var in [variable, "change", "robustness_categories", "robustness_coefficient"]:
                if time == ("historical", "1980-2009") and var in [
                    "change",
                    "robustness_categories",
                    "robustness_coefficient",
                ]:
                    continue
                da = data[var].sel(time=time)
                da = da.rio.set_spatial_dims(x_dim="lon", y_dim="lat").rio.write_crs("EPSG:4326")
                fp = path / f"{self.name}_{vars_dict[var]}_{time[0]}_{time[1]}_{self.resolution}_v{self.version}.tif"
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

    def _load_criteria_indicators(self, scenario) -> dict:
        """Load criteria indicators based on scenario and resolution."""
        clim_res = {"5km": "25km", "1km": "5km"}.get(self.resolution, None)
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
                    file = f"{file}_NZ{self.resolution}.nc"
                else:
                    raise ValueError(f"Unknown category '{val.category}' for criteria '{key}'.")

                val.indicator = self._load_indicator(file, variable)
            else:
                raise ValueError(f"Indicator for criteria '{key}' not found in criteria indicators.")
        sc = self._interpolate_indicator(sc)
        return sc

    def _agriculture_mask(self) -> xr.DataArray:
        """Create a mask for agricultural land use areas."""
        # conservation land areas
        doc = xr.open_dataarray(
            rf"R:\DATA\GIS-NZ\lds-doc-public-conservation-areas\doc-public-conservation-areas_NZ{self.resolution}.nc"
        )
        doc = doc.sel(lat=slice(-34, -48), lon=slice(166, 180))  # crop to NZ
        doc_mask = xr.where(doc.isnull(), 1, 0)
        # land use map
        lum = xr.open_dataarray(
            rf"R:\DATA\GIS-NZ\mfe-lucas-nz-land-use-map-2020-v003\lucas-nz-land-use-map-2020_NZ{self.resolution}.nc"
        )
        # non-agricultural land use classes
        # Natural forest 71, open water 79, wetland 80, settlement 81, other 82
        # 71=0, 79=8, 80=9, 81=10, 82=11 : see LUM attrs
        lum_mask = xr.where(lum.isin([0, 8, 9, 10, 11]), 0, 1)

        return xr.where((doc_mask + lum_mask) > 0, 1, 0)

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

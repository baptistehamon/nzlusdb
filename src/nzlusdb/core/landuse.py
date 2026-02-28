"""Land Use class for NZLUSDB."""

from __future__ import annotations

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from lsapy import LandSuitabilityAnalysis
from lsapy.aggregate import aggregate
from lsapy.stats import spatial_stats_summary, stats_summary
from xclim import ensembles as xens

import nzlusdb
from nzlusdb.core.climdataset import climateDS
from nzlusdb.core.plot import change_boundnorm, suitability_boundnorm, summary_figure
from nzlusdb.suitability import criteria
from nzlusdb.utils import write_netcdf


class LandUse:
    """
    Land Use class for NZLUSDB.

    Parameters
    ----------
    name : str
        Name of the land use.
    long_name : str, optional
        Long name of the land use.
    version : str, optional
        Version of the land use analysis. Default is the current package version.

    Attributes
    ----------
    name : str
        Name of the land use.
    long_name : str
        Long name of the land use.
    resolution : str
        Resolution of the land use analysis ('1km' or '5km').
    version : str
        Version of the land use analysis.
    criteria : dict
        Dictionary of suitability criteria. The `indicator` attribute of each criteria will be populated when
        `run_lsa` is called.
    """

    def __init__(self, name: str, long_name: str | None = None, resolution: str = "5km", version: str = ""):
        self.name = name
        self.long_name = long_name if long_name else name.capitalize()
        self.resolution = resolution
        self.version = version
        self._get_criteria_info()
        self.path = nzlusdb.db.path / self.resolution / "suitability" / self.name
        self._db_attrs = nzlusdb.db.attrs
        if self._db_attrs.get("version", None) != f"v{nzlusdb.release}":
            self._db_attrs["version"] = f"v{nzlusdb.release}"

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
        self.path = nzlusdb.db.path / self.resolution / "suitability" / self.name

    def run_workflow(self, resolution: list[str] | str | None = None, rerun_lsa=False):
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

        def _mmm_robustness(kwargs=None):
            ds = self.open_suitability(**kwargs if kwargs else {})
            return self.period_mmm_change_robustness(ds, delta_method="absolute")

        def _set_index(ds):
            return ds.set_index(time=["scenario", "period"])

        if resolution is None:
            if self.resolution is None:
                raise ValueError("Resolution must be set before running workflow.")
            resolution = [self.resolution]
        elif isinstance(resolution, str):
            resolution = [resolution]

        for res in resolution:
            self.resolution = res
            self.run_lsa(scenario=["historical", "ssp126", "ssp245", "ssp370", "ssp585"], rerun=rerun_lsa)
            if self.resolution == "5km":
                ds = _mmm_robustness()
            if self.resolution == "1km":
                fp = []
                for s in ["ssp126", "ssp245", "ssp370", "ssp585"]:
                    out = _mmm_robustness(kwargs={"scenario": s})
                    if s == "ssp126":
                        histfname = f"{self.name}_tmp_mmm-change-robustness_historical.nc"
                        write_netcdf(out.isel(time=0), self.path / histfname, progressbar=True, verbose=True)
                    out = out.drop_isel(time=0)
                    fname = f"{self.name}_tmp_mmm-change-robustness_{s}.nc"
                    fp.append(self.path / fname)
                    write_netcdf(out, self.path / fname, progressbar=True, verbose=True)
                ds = xr.concat(
                    [
                        xr.open_dataset(self.path / histfname).assign_coords(
                            {"scenario": "historical", "period": "1980-2009"}
                        ),
                        xr.open_mfdataset(fp, combine="by_coords", preprocess=_set_index).reset_index("time"),
                    ],
                    dim="time",
                )

            ds = ds.assign_attrs(
                {
                    **self._db_attrs,
                    **{
                        "source": f"{climateDS[f'nzlusdb_{self.resolution}'].name}: "
                        + f"{', '.join(climateDS[f'nzlusdb_{self.resolution}'].model)}"
                    },
                }
            )
            self.write_output(ds, variable="suitability")
            self.summary_figs()
            self.stats_summary()
            self.add_to_doc(overwrite=True)

    def run_lsa(self, scenario: str | list[str], model=None, rerun=False, **kwargs) -> None:
        """
        Run land suitability analysis (LSA) for given scenario and resolution.

        Parameters
        ----------
        scenario : str or list of str
            Scenario(s) to use (e.g., 'historical', 'ssp126', 'ssp585').
        model : str, optional
            Climate model to use for the analysis. If None, uses all available models. Default is None.
        **kwargs : dict
            Additional keyword arguments to pass to `LandSuitabilityAnalysis.run()`.
        """

        def _run(scenario, model=None, **kwargs):
            out = self._run_lsa(scenario=scenario, model=model, **kwargs)
            out.attrs.update({**self._db_attrs, **{"source": climateDS[f"nzlusdb_{self.resolution}"].name}})
            out["suitability"].attrs.update({"long_name": "Suitability"})
            return out

        if isinstance(scenario, str):
            scenario = [scenario]

        for scen in scenario:
            self.path.mkdir(parents=True, exist_ok=True)
            if self.resolution == "5km":
                fp = self.path / f"{self.name}_suitability_{scen}_{self.resolution}_v{self.version}.nc"
                if not rerun and fp.exists():
                    continue
                out = _run(scen, **kwargs)
                write_netcdf(out, fp, progressbar=True, verbose=True)
            else:
                for m in climateDS[f"nzlusdb_{self.resolution}"].model:
                    fp = self.path / f"{self.name}_suitability_{scen}_{m}_{self.resolution}_v{self.version}.nc"
                    if not rerun and fp.exists():
                        continue
                    out = _run(scen, model=m, **kwargs)
                    soil_vars = [v for v in out.data_vars if "time" not in out[v].dims]
                    if m == climateDS[f"nzlusdb_{self.resolution}"].model[0] and scen == "historical":
                        fp_hist = (
                            self.path / f"{self.name}_soilTerrain-suitability_{self.resolution}_v{self.version}.nc"
                        )
                        write_netcdf(out[soil_vars], fp_hist, progressbar=True, verbose=True)
                    fp = self.path / f"{self.name}_suitability_{scen}_{m}_{self.resolution}_v{self.version}.nc"
                    write_netcdf(
                        out[[v for v in out.data_vars if v not in soil_vars]], fp, progressbar=True, verbose=True
                    )

    def open_suitability(self, scenario: str | None = None) -> xr.Dataset:
        """
        Open suitability dataset for given resolution.

        Returns
        -------
        xr.Dataset
            Suitability dataset.
        """
        files = list(self.path.glob("*.nc"))

        hist_scenario = climateDS[f"nzlusdb_{self.resolution}"].hist_scenario
        if self.resolution == "5km":
            proj_scenarios = climateDS[f"nzlusdb_{self.resolution}"].proj_scenario
            hist = xr.open_dataset([f for f in files if hist_scenario in f.name][0])["suitability"]
            proj = []
            for scen in proj_scenarios:
                file = [f for f in files if scen in f.name][0]
                ds = xr.open_dataset(file)["suitability"].assign_coords(scenario=scen).expand_dims("scenario")
                proj.append(ds)
            return xr.concat([hist, xr.concat(proj, dim="scenario")], dim="time")

        else:

            def _preprocess(ds: xr.Dataset) -> xr.Dataset:
                return ds.expand_dims("realization")

            fp = [f for f in files if any(f"suitability_{s}" in f.name for s in [hist_scenario, scenario])]
            out = xr.open_mfdataset(fp, chunks={"lat": 350, "lon": 675}, combine="by_coords", preprocess=_preprocess)[
                "suitability"
            ]
            out = out.assign_coords(scenario=scenario).expand_dims("scenario")
            return out.chunk(time=-1, realization=-1)

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

        fp = nzlusdb.db.pathdoc / "_static/summary_figs"
        fp.mkdir(parents=True, exist_ok=True)

        summary_figure(
            data,
            f"Historical and Projected Suitability for {self.long_name}",
            hist_kw={"norm": suitability_boundnorm, "cmap": "cividis"},
            proj_kw={"norm": suitability_boundnorm, "cmap": "cividis"},
            scenario_labels=("SSP2-4.5", "SSP5-8.5"),
            timeline_label="Suitability",
        )
        fname = f"{self.name}_suitability_SSP245-SSP585_{self.resolution}_v{self.version}.png"
        plt.savefig(fp / fname, dpi=300)
        plt.close()

        summary_figure(
            data,
            f"Historical Suitability and Projected Changes for {self.long_name}",
            proj_var="change",
            hist_kw={"norm": suitability_boundnorm, "cmap": "cividis"},
            proj_kw={"norm": change_boundnorm, "cmap": "PiYG"},
            scenario_labels=("SSP2-4.5", "SSP5-8.5"),
            legend_labels={"suitability": "Suitability", "change": "Change in Suitability"},
            robustness=True,
            timeline_label="Changes",
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
            "scenario": {
                time: scenario for time, scenario in zip(data["time"].values, data["scenario"].values, strict=True)
            },
            "period": {time: period for time, period in zip(data["time"].values, data["period"].values, strict=True)},
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

    def add_to_doc(self, overwrite=False):
        """
        Add land use to the documentation registry and create a markdown doc.

        Parameters
        ----------
        overwrite : bool, optional
            If True, overwrite existing markdown doc if it exists. Default is False.
        """
        fp = nzlusdb.db.pathdoc / "landuses"
        doc_landuses = nzlusdb.db.doc_registry()
        if self.name in doc_landuses:
            if doc_landuses[self.name] != self.long_name:
                raise ValueError(
                    f"Land use '{self.name}' already exists with a different long name "
                    f"('{doc_landuses[self.name]}' != '{self.long_name}')"
                )
        else:
            nzlusdb.db.register_in_doc(self.name, self.long_name)

        if not overwrite and (fp / f"{self.name}.md").exists():
            raise FileExistsError(f"Markdown doc for land use '{self.name}' already exists.")
        with open(fp / "_landuse.md", encoding="utf-8") as f:
            md = f.read()
        md = md.replace('"Land Use Name"', self.long_name)
        fend = f"SSP245-SSP585_{self.resolution}_v{self.version}.png"
        md = md.replace("suitability.png", f"{self.name}_suitability_{fend}")
        md = md.replace("suitability_change.png", f"{self.name}_suitability_change_{fend}")
        md = md.replace('"criteria_table"', self._criteria_table())
        with open(fp / f"{self.name}.md", "w", encoding="utf-8") as f:
            f.write(md)

    def _run_lsa(self, scenario: str = "historical", model=None, **kwargs) -> xr.Dataset:
        """Internal method to run LSA for a single scenario and model."""

        def _compute_criteria(sc):
            out = xr.Dataset()
            for c in sc.values():
                out[c.name] = c.compute()
            return out

        lsa = LandSuitabilityAnalysis(
            land_use=self.name,
            short_name=f"{self.name}_suitability",
            long_name=f"{self.long_name} Suitability",
            criteria=self._load_criteria_indicators(scenario=scenario, model=model),
        )
        # bypass lsa.run() for criteria and categories allowing to interpolate climate
        # indicators at the end optimizing the computation time
        # soil criteria
        sc_soil = _compute_criteria({k: v for k, v in lsa.criteria.items() if v.category == "soilTerrain"})
        soil = aggregate(
            sc_soil,
            method="wgmean",
            weights=[c.weight for c in lsa.criteria.values() if c.category == "soilTerrain"],
        )

        # # climate criteria
        sc_clim = _compute_criteria({k: v for k, v in lsa.criteria.items() if v.category == "climate"})
        clim = aggregate(
            sc_clim, method="wgmean", weights=[c.weight for c in lsa.criteria.values() if c.category == "climate"]
        )

        lsa.data = xr.Dataset()
        for v in sc_soil.data_vars:
            lsa.data[v] = sc_soil[v]
        for v in sc_clim.data_vars:
            lsa.data[v] = sc_clim[v].interp_like(soil, method="nearest")
        lsa.data["climate"] = clim.interp_like(soil, method="nearest")
        lsa.data["soilTerrain"] = soil

        lsa.data = lsa._aggregate(
            lsa.data,
            agg_on={"suitability": ["climate", "soilTerrain"]},
            methods="wgmean",
            keep_vars=True,
            kwargs={"weights": [lsa.weights_by_category[c] for c in ["climate", "soilTerrain"]]},
        )
        lsa.data.attrs = {"land_use": lsa.land_use, "criteria": lsa._criteria_list, **lsa.attrs}
        return lsa.data

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

    def _load_criteria_indicators(self, scenario, model=None) -> dict:
        """Load criteria indicators based on scenario and resolution."""
        clim_res = {"5km": "25km", "1km": "5km"}.get(self.resolution, None)
        sc = self.criteria
        for key, val in sc.items():
            if key == "preprocess":
                continue
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
                if model and val.category == "climate":
                    val.indicator = val.indicator.sel(realization=model)
            else:
                raise ValueError(f"Indicator for criteria '{key}' not found in criteria indicators.")

        preprocess = self._criteria_indicators.get("preprocess")
        if preprocess:
            for key, ops in preprocess.items():
                if key in sc:
                    for op, params in ops.items():
                        if op == "func":
                            func, f_params = params
                            sc[key].indicator = func(sc[key].indicator, **f_params)
                        else:
                            sc[key].indicator = getattr(xr.DataArray, op)(sc[key].indicator, **params)
                else:
                    raise ValueError(f"Preprocess criteria '{key}' not found in criteria.")
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
        ds = xr.open_dataset(nzlusdb.db.path / "indicators" / file, decode_timedelta=False)
        if "latitude" in ds.coords:  # rename dims for 1km indicator
            ds = ds.rename({"latitude": "lat", "longitude": "lon"})

        if variable:
            return ds[variable]
        elif len(ds.data_vars) == 1:
            return list(ds.data_vars.values())[0]
        else:
            raise ValueError(f"Multiple variables found in {file}. Please specify a variable.")

    def _criteria_table(self) -> str:
        _criteria = {criteria.attrs.get("long_name"): criteria.category for _, criteria in self._criteria.items()}
        table = "| Category | Criteria |\n"
        table += "|:--------:|:---------|\n"
        for c, cat in _criteria.items():
            if cat == "soilTerrain":
                category = "soil/Terrain"
            else:
                category = cat.capitalize()
            table += f"| {category} | {c} |\n"
        table += ': {tbl-colwidths="[25,75]"}'
        return table

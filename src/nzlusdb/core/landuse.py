"""Land Use class for NZLUSDB."""

from __future__ import annotations

import copy
from pathlib import Path

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from lsapy import LandSuitabilityAnalysis
from lsapy.aggregate import aggregate
from lsapy.stats import spatial_stats_summary, stats_summary
from xclim import ensembles as xens

import nzlusdb
from nzlusdb import nir as nirmod
from nzlusdb.core.climdataset import climateDS
from nzlusdb.core.nir import KcCurve, load_nir_inputs
from nzlusdb.core.plot import (
    bndnorm_nir,
    bndnorm_nir_change,
    bndnorm_suitability,
    bndnorm_suitability_change,
    summary_figure,
)
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
        self.path = nzlusdb.db.path / self.resolution / self.name
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
        self.path = nzlusdb.db.path / self.resolution / self.name

    def run_workflow(  # noqa: C901, PLR0915
        self,
        resolution: list[str] | str | None = None,
        lsa: bool = True,
        rerun_lsa=False,
        nir: bool = True,
        rerun_nir=False,
    ):
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
        lsa : bool, optional
            Whether to run the LSA workflow. Default is True.
        rerun_lsa : bool, optional
            Whether to rerun the LSA even if output files already exist. Default is False.
        nir : bool, optional
            Whether to run the NIR workflow. Default is True.
        rerun_nir : bool, optional
            Whether to rerun the NIR even if output files already exist. Default is False.
        """

        def _check_resolution(resolution):
            if resolution is None:
                if self.resolution is None:
                    raise ValueError("Resolution must be set before running workflow.")
                resolution = [self.resolution]
            elif isinstance(resolution, str):
                resolution = [resolution]
            return resolution

        def _mmm_robustness(**kwargs):
            da = self.open_data(**kwargs)
            if not kwargs.get("variable") == "nir" or kwargs.get("nir_freq") not in ["monthly", "seasonal"]:
                return self.period_mmm_change_robustness(da)
            else:
                # For NIR, we need to compute the multi-model mean change and robustness
                # for each month or season separately
                if kwargs.get("nir_freq") == "monthly":
                    freq_name = "month"
                elif kwargs.get("nir_freq") == "seasonal":
                    freq_name = "season"
                da = da.assign_coords(
                    {freq_name: da.time.dt.strftime("%b") if freq_name == "month" else da.time.dt.season}
                )
                freq_values = np.unique(da[freq_name].values)
                out = []
                for val in freq_values:
                    ds = self.period_mmm_change_robustness(da.where(da[freq_name] == val, drop=True))
                    out.append(ds.expand_dims({freq_name: [val]}))
                out = xr.concat(out, dim=freq_name)
                return xr.concat(
                    [
                        out.isel(time=0)
                        .expand_dims(["scenario", "period"])
                        .stack(time=["scenario", "period", freq_name]),
                        out.drop_isel(time=0)
                        .set_index(time=["scenario", "period"])
                        .unstack("time")
                        .stack(time=["scenario", "period", freq_name]),
                    ],
                    dim="time",
                ).reset_index("time")

        def _set_index(ds):
            return ds.set_index(time=["scenario", "period"])

        def _1km_mmm_robustness(path, **kwargs):
            fp = []
            for s in ["ssp126", "ssp245", "ssp370", "ssp585"]:
                out = _mmm_robustness(scenario=s, **kwargs)
                freq_name = kwargs.get("nir_freq") or ""
                if freq_name:
                    freq_name = "_" + freq_name
                if s == "ssp126":
                    histfname = f"{self.name}_tmp_mmm-change-robustness{freq_name}_historical.nc"
                    write_netcdf(out.isel(time=0), path / histfname, progressbar=True, verbose=True)
                out = out.drop_isel(time=0)
                fname = f"{self.name}_tmp_mmm-change-robustness{freq_name}_{s}.nc"
                fp.append(path / fname)
                write_netcdf(out, path / fname, progressbar=True, verbose=True)
            return xr.concat(
                [
                    xr.open_dataset(path / histfname).assign_coords({"scenario": "historical", "period": "1980-2009"}),
                    xr.open_mfdataset(fp, combine="by_coords", preprocess=_set_index).reset_index("time"),
                ],
                dim="time",
            )

        def _assign_attrs(ds):
            return ds.assign_attrs(
                {
                    **self._db_attrs,
                    **{
                        "source": f"{climateDS[f'nzlusdb_{self.resolution}'].name}: "
                        + f"{', '.join(climateDS[f'nzlusdb_{self.resolution}'].model)}"
                    },
                }
            )

        resolution = _check_resolution(resolution)

        if lsa:
            # Run LSA for each resolution
            for res in resolution:
                self.resolution = res
                self.run_lsa(scenario=["historical", "ssp126", "ssp245", "ssp370", "ssp585"], rerun=rerun_lsa)
                if self.resolution == "5km":
                    ds = _mmm_robustness(variable="suitability")
                if self.resolution == "1km":
                    ds = _1km_mmm_robustness(self.path / "suitability", variable="suitability")

                ds = _assign_attrs(ds)
                self.write_output(ds, variable="suitability", path=self.path / "suitability")
                self.summary_figs("suitability", self.path / "suitability")
                self.stats_summary(" suitability", self.path / "suitability")
                self.add_to_doc(overwrite=True)

        if nir:
            for res in resolution:
                self.resolution = res
                self.compute_nir(scenario=["historical", "ssp126", "ssp245", "ssp370", "ssp585"], recompute=rerun_nir)
                for freq in ["monthly", "seasonal", "annual"]:
                    if self.resolution == "5km":
                        ds = _mmm_robustness(variable="nir", nir_freq=freq)
                    else:
                        ds = _1km_mmm_robustness(self.path / "nir", variable="nir", nir_freq=freq)
                    ds = _assign_attrs(ds)
                    self.write_output(ds, "net_irrigation_requirement", self.path / "nir", var_suffix=freq)
                    self.stats_summary(f"net-irrigation-requirement-{freq}", self.path / "nir")
            self.summary_figs("net-irrigation-requirement-annual", self.path / "nir")

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

        path = self.path / "suitability"

        for scen in scenario:
            path.mkdir(parents=True, exist_ok=True)
            if self.resolution == "5km":
                fp = path / f"{self.name}_suitability_{scen}_{self.resolution}_v{self.version}.nc"
                if not rerun and fp.exists():
                    continue
                out = _run(scen, model, **kwargs)
                write_netcdf(out, fp, progressbar=True, verbose=True)
            else:
                for m in climateDS[f"nzlusdb_{self.resolution}"].model:
                    fp = path / f"{self.name}_suitability_{scen}_{m}_{self.resolution}_v{self.version}.nc"
                    if not rerun and fp.exists():
                        continue
                    out = _run(scen, model=m, **kwargs)
                    soil_vars = [v for v in out.data_vars if "time" not in out[v].dims]
                    if m == climateDS[f"nzlusdb_{self.resolution}"].model[0] and scen == "historical":
                        fp_hist = path / f"{self.name}_soilTerrain-suitability_{self.resolution}_v{self.version}.nc"
                        write_netcdf(out[soil_vars], fp_hist, progressbar=True, verbose=True)
                    fp = path / f"{self.name}_suitability_{scen}_{m}_{self.resolution}_v{self.version}.nc"
                    write_netcdf(
                        out[[v for v in out.data_vars if v not in soil_vars]], fp, progressbar=True, verbose=True
                    )

    def open_data(self, variable: str, scenario: str | None = None, nir_freq: str | None = None) -> xr.Dataset:
        """
        Open suitability or NIR dataset for given resolution.

        Parameters
        ----------
        variable : str
            Name of the variable to open ('suitability' or 'nir').
        scenario : str, optional
            Projected scenario to open ('ssp126', 'ssp245', 'ssp370', 'ssp585').
            Required if variable is 'suitability' and resolution is '1km'.
        nir_freq : str, optional
            Frequency of NIR data to open ('monthly', 'seasonal', 'annual'). Required if variable is 'nir'.

        Returns
        -------
        xr.Dataset
            Suitability or NIR dataset.
        """
        files = list((self.path / variable).glob("*.nc"))
        if variable == "nir":
            variable = "net_irrigation_requirement"
            if nir_freq is None or nir_freq not in ["monthly", "seasonal", "annual"]:
                raise ValueError("nir_freq must be one of 'monthly', 'seasonal', or 'annual' when variable is 'nir'.")
            else:
                files = [f for f in files if nir_freq in f.name]

        hist_scenario = climateDS[f"nzlusdb_{self.resolution}"].hist_scenario
        if self.resolution == "5km":
            proj_scenarios = climateDS[f"nzlusdb_{self.resolution}"].proj_scenario
            hist = xr.open_dataset([f for f in files if hist_scenario in f.name][0])[variable]
            proj = []
            for scen in proj_scenarios:
                file = [f for f in files if scen in f.name][0]
                ds = xr.open_dataset(file)[variable].assign_coords(scenario=scen).expand_dims("scenario")
                proj.append(ds)
            return xr.concat([hist, xr.concat(proj, dim="scenario")], dim="time")

        else:

            def _preprocess(ds: xr.Dataset) -> xr.Dataset:
                return ds.expand_dims("realization")

            fp = [f for f in files if any(f"{variable}_{s}" in f.name for s in [hist_scenario, scenario])]
            out = xr.open_mfdataset(fp, chunks={"lat": 350, "lon": 675}, combine="by_coords", preprocess=_preprocess)[
                "suitability"
            ]
            out = out.assign_coords(scenario=scenario).expand_dims("scenario")
            return out.chunk(time=-1, realization=-1)

    def compute_nir(self, scenario: str | list[str] = "historical", model=None, recompute=False) -> None:
        """
        Compute net irrigation requirement (NIR) for given scenario(s) and model.

        Parameters
        ----------
        scenario : str or list of str, optional
            Scenario(s) to compute NIR for (e.g., 'historical', 'ssp126', 'ssp585'). Default is 'historical'.
        model : str, optional
            Climate model to use for the computation. If None, uses all available models. Default is None.
        recompute : bool, optional
            Whether to recompute NIR even if output files already exist. Default is False.
        """

        def _resample_season_year(da: xr.DataArray, historical: bool) -> tuple[xr.DataArray, xr.DataArray]:
            # Ensure full seasons for historical and projected scenarios
            sel_ssn = {"time": slice(2, -1)} if historical else {"time": slice(None, -1)}
            sel_yr = {"time": slice(1, None)} if not historical else {}
            da_ssn = da.isel(**sel_ssn).resample(time="QS-DEC").sum(min_count=1)
            da_yr = da.isel(**sel_yr).resample(time="YS-JUL").sum(min_count=1)
            return (da_ssn, da_yr)

        if isinstance(scenario, str):
            scenario = [scenario]

        path = self.path / "nir"

        for scen in scenario:
            path.mkdir(parents=True, exist_ok=True)
            fp = f"{self.name}_net-irrigation-requirement_monthly_{scen}_{self.resolution}_v{self.version}.nc"
            if recompute or not (path / fp).exists():
                nir = self._compute_monthly_nir(scen, model)
                write_netcdf(nir, path / fp, progressbar=True, verbose=True)
            nir = xr.open_dataarray(path / fp)

            fp = {
                freq: path / fp.replace("monthly", {"ssn": "seasonal", "yr": "annual"}[freq]) for freq in ["ssn", "yr"]
            }

            # Add last month of historical to get full season for projected scenarios
            if scen != "historical":
                hist_fp = (
                    path
                    / f"{self.name}_net-irrigation-requirement_monthly_historical_{self.resolution}_v{self.version}.nc"
                )
                if not hist_fp.exists():
                    nir_hist = self._compute_monthly_nir("historical", model)
                    write_netcdf(nir_hist, hist_fp, progressbar=True, verbose=True)
                else:
                    nir_hist = xr.open_dataarray(hist_fp)
                nir = xr.concat([nir_hist.isel(time=-1), nir], dim="time")

            nir_ssn, nir_yr = _resample_season_year(nir, historical=scen == "historical")
            for freq, da in zip(["ssn", "yr"], [nir_ssn, nir_yr], strict=True):
                if recompute or not fp[freq].exists():
                    write_netcdf(da, fp[freq], progressbar=True, verbose=True)

    def open_mmm_data(self, path: Path, variable: str = "suitability") -> xr.Dataset:
        """
        Open multi-model mean change and robustness dataset for given variable and resolution.

        Parameters
        ----------
        path : Path
            Directory path where the multi-model mean change and robustness dataset is stored.
        variable : str
            Name of the variable data corresponds to (default is 'suitability').

        Returns
        -------
        xr.Dataset
            Multi-model mean change and robustness dataset.
        """
        file = f"{self.name}_{variable}-MMM-change-robustness_{self.resolution}_v{self.version}.nc"
        return xr.open_dataset(path / file)

    def write_output(self, data: xr.Dataset, variable: str, path: Path, **kwargs) -> None:
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
        path : Path
            Directory path to save the output files.
        **kwargs : dict
            Additional keyword arguments to pass to `_write_output_as_raster`.

        Returns
        -------
        None
            Writes NetCDF and GeoTIFF files to the appropriate directories.
        """
        varname = variable.replace("_", "-")
        if kwargs.get("var_suffix"):
            varname += f"-{kwargs['var_suffix']}"
        fp = path / f"{self.name}_{varname}-MMM-change-robustness_{self.resolution}_v{self.version}.nc"
        data.to_netcdf(fp)

        data = data.set_index(time=list(data.time.coords))
        self._write_output_as_raster(data, variable, path, **kwargs)

    def summary_figs(self, variable: str, path: Path) -> None:
        """
        Generate and save summary figures.

        Two figure are made. The first shows historical and projected suitability, the second shows
        historical suitability and projected changes with robustness. In each figure, the historical
        period is 1980-2009 and the projected periods are 2010-2039, 2040-2069 and 2070-2099 for the
        SSP245 and SSP585 scenarios. The figures are saved in the `docs/_static/summary_figs` directory.

        Parameters
        ----------
        variable : str
            Name of the variable data corresponds to.
        path : Path
            Directory path where data is stored.
        """
        data = self.open_mmm_data(path, variable=variable)
        data = data.set_index(time=["scenario", "period"])

        fp = nzlusdb.db.pathdoc / "_static/summary_figs"
        fp.mkdir(parents=True, exist_ok=True)

        common_kwargs = {"scenario_labels": ("SSP2-4.5", "SSP5-8.5")}
        if variable == "suitability":
            base_kwargs = {
                **common_kwargs,
                "suptitle": f"Historical and Projected Suitability for {self.long_name}",
                "hist_kw": {"norm": bndnorm_suitability, "cmap": "cividis"},
                "proj_kw": {"norm": bndnorm_suitability, "cmap": "cividis"},
                "timeline_label": "Suitability",
            }
            change_kwargs = {
                **base_kwargs,
                "suptitle": f"Historical Suitability and Projected Changes for {self.long_name}",
                "proj_var": "change",
                "proj_kw": {"norm": bndnorm_suitability_change, "cmap": "PiYG"},
                "legend_labels": {"suitability": "Suitability", "change": "Change in Suitability"},
                "robustness": True,
                "timeline_label": "Changes",
            }
        elif variable == "net-irrigation-requirement-annual":
            base_kwargs = {
                **common_kwargs,
                "suptitle": f"Historical and Projected Annual Net Irrigation Requirement for {self.long_name}",
                "hist_var": "net_irrigation_requirement",
                "proj_var": "net_irrigation_requirement",
                "hist_kw": {"norm": bndnorm_nir, "cmap": "Blues"},
                "proj_kw": {"norm": bndnorm_nir, "cmap": "Blues"},
                "legend_labels": {"net_irrigation_requirement": "Net Irrigation Requirement (mm)"},
                "timeline_label": "Net Irrigation Requirement",
            }
            change_kwargs = {
                **base_kwargs,
                "suptitle": f"Historical Annual Net Irrigation Requirement and Projected Changes for {self.long_name}",
                "proj_var": "change",
                "proj_kw": {"norm": bndnorm_nir_change, "cmap": "BrBG"},
                "legend_labels": {
                    "net_irrigation_requirement": "Net Irrigation Requirement (mm)",
                    "change": "Change in Net Irrigation Requirement (mm)",
                },
                "robustness": True,
                "timeline_label": "Changes",
            }
        else:
            raise ValueError(f"Variable '{variable}' is not supported for summary figures.")

        summary_figure(data, **base_kwargs)
        fname = f"{self.name}_{variable}_SSP245-SSP585_{self.resolution}_v{self.version}.png"
        plt.savefig(fp / fname, dpi=300)
        plt.close()

        summary_figure(data, **change_kwargs)
        fname = f"{self.name}_{variable}_change_SSP245-SSP585_{self.resolution}_v{self.version}.png"
        plt.savefig(fp / fname, dpi=300)
        plt.close()

    def stats_summary(self, variable: str, path: Path) -> None:
        """
        Generate and save national and regional suitability statistics summary.

        Parameters
        ----------
        variable : str
            Name of the variable data corresponds to.
        path : Path
            Directory path where data is stored.
        """

        def _add_coords(df, mapping):
            for i, c in enumerate(mapping):
                df.insert(i + 1, c, df["time"].map(mapping[c]))
            return df.drop(columns=["time"])

        agmask = self._agriculture_mask()
        regions = gpd.read_file(r"R:\DATA\GIS-NZ\statsnz-regional-council-2022-clipped-generalised").to_crs(epsg=4326)

        data = self.open_mmm_data(path, variable=variable)
        data = data.where(agmask == 1)

        mapping = {c: dict(zip(data["time"].values, data[c].values, strict=True)) for c in data.time.coords}

        if variable == "suitability":
            cell_area = (int(self.resolution.replace("km", "")) ** 2, "km2")
            kwargs = {
                "on_vars": ["suitability"],
                "on_dims": ["time"],
                "dropna": True,
                "bins": np.linspace(0, 1, 11),
                "cell_area": cell_area,
                "all_bins": True,
            }
        elif "net-irrigation-requirement" in variable:
            kwargs = {"on_vars": ["net_irrigation_requirement"], "on_dims": ["time"], "dropna": True}
        reg_kwargs = {
            "areas": regions,
            "name": "region",
            "mask_kwargs": {"names": "REGC2022_1"},
        }

        nz_stats = stats_summary(data, **kwargs)
        nz_stats = _add_coords(nz_stats, mapping)

        reg_stats = spatial_stats_summary(data, **kwargs, **reg_kwargs)
        reg_stats = _add_coords(reg_stats, mapping)

        nz_stats.to_csv(
            path / f"{self.name}_national_{variable}_stats_summary_{self.resolution}_v{self.version}.csv",
            index=False,
        )
        reg_stats.to_csv(
            path / f"{self.name}_regional_{variable}_stats_summary_{self.resolution}_v{self.version}.csv",
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

        self._get_criteria_info()

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

        # climate criteria
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

    def _compute_monthly_nir(self, scenario: str = "historical", model=None) -> xr.DataArray:
        """Internal method to compute monthly NIR for a single scenario and model."""
        self._get_kc_parameters()
        etp, peff, rhmin, windspd = self._load_nir_inputs(scenario=scenario)
        if model is not None:
            etp = etp.sel(realization=model)
            peff = peff.sel(realization=model)
            rhmin = rhmin.sel(realization=model)
            windspd = windspd.sel(realization=model)

        kc = KcCurve(**self.Kc_params, time=peff.time)
        # return kc.stage_values["end"]
        kc.adjust(windspd=windspd, rhmin=rhmin)
        kc = kc.curve(like=peff)

        cwr = etp * kc
        nir = (cwr - peff).clip(min=0).rename("net_irrigation_requirement")

        nir = nir.resample(time="MS").sum(min_count=1)
        nir.attrs = {
            "long_name": f"{self.long_name} Net Irrigation Requirement",
            "short_name": f"{self.name}_net_irrigation_requirement",
            "units": "mm",
            "description": "Net irrigation requirement computed as the difference between effective precipitation "
            "(Peff) and crop water requirement (CWR).",
            **self._db_attrs,
            "source": f"{climateDS[f'nzlusdb_{self.resolution}'].name}",
        }
        return nir

    def _write_output_as_raster(
        self,
        data: xr.Dataset,
        variable: str,
        path: Path,
        var_suffix: str | None = None,
    ) -> None:
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
        path : Path
            Directory path to save the GeoTIFF files.
        var_suffix : str, optional
            Suffix to append to the variable name in the output file names. Default is None.

        Returns
        -------
        None
            Writes GeoTIFF files to the appropriate directory.
        """
        var_name = variable.replace("_", "-") + (f"_{var_suffix}" if var_suffix else "")
        vars_dict = {
            variable: f"{var_name}",
            "change": f"{var_name}-change",
            "robustness_categories": f"{var_name}-robustness-categories",
            "robustness_coefficient": f"{var_name}-robustness-coefficient",
        }
        path /= "tiff"
        path.mkdir(parents=True, exist_ok=True)

        for time in data.time.values:
            for var in [variable, "change", "robustness_categories", "robustness_coefficient"]:
                if all([i in time for i in ["historical", "1980-2009"]]) and var in [
                    "change",
                    "robustness_categories",
                    "robustness_coefficient",
                ]:
                    continue
                da = data[var].sel(time=time)
                da = da.rio.set_spatial_dims(x_dim="lon", y_dim="lat").rio.write_crs("EPSG:4326")
                fp = path / f"{self.name}_{vars_dict[var]}_{'_'.join(time)}_{self.resolution}_v{self.version}.tif"
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

    def _get_kc_parameters(self) -> None:
        """Get Kc parameters from nir module."""
        crop_params = f"{self.name}_kc_params"
        if hasattr(nirmod, crop_params):
            self.Kc_params = copy.deepcopy(getattr(nirmod, crop_params))
        else:
            raise ValueError(f"Kc parameters '{crop_params}' not found in nir module.")

    def _load_nir_inputs(
        self, scenario: str = "historical"
    ) -> tuple[xr.DataArray, xr.DataArray, xr.DataArray, xr.DataArray]:
        """Load NIR input variables based on scenario and resolution."""
        clim_res = {"5km": "25km", "1km": "5km"}.get(self.resolution, None)
        etp = load_nir_inputs("etp", scenario=scenario, resolution=clim_res)
        peff = load_nir_inputs("peff", scenario=scenario, resolution=clim_res)
        rhmin = load_nir_inputs("hursmin", scenario=scenario, resolution=clim_res)
        windspd = load_nir_inputs("windspd", scenario=scenario, resolution=clim_res)
        return etp, peff, rhmin, windspd

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

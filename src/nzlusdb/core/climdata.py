"""Clim Data class to handle climate data."""

import warnings
from pathlib import Path

import pandas as pd
import xarray as xr
from xclim.ensembles import create_ensemble

__all__ = [
    "ClimData",
    "climate_data",
    "select_hist_proj",
]


class ClimData:
    """
    Object to store climate data ensemble information.

    The climate data are expected to be in NetCDF format and stored in the data_path directory.
    Each file should be named in a way that includes the model, scenario, and variable information.

    Parameters
    ----------
    data_path : Path
        Path to the directory containing climate data files.
    model : str or list of str
        Climate model(s) to include.
    scenario : str or list of str
        Climate scenario(s) to include.
    variables : list of str
        Climate variable(s) to include (e.g., 'tasmax', 'tasmin', 'pr').
    resolution : str
        Spatial resolution of the climate data.
    hist_scenario : str, optional
        Name of the historical scenario (default is 'historical'). If the default name is not among the scenarios,
        it will be set to None.
    """

    def __init__(
        self,
        data_path: Path,
        model: str | list[str],
        scenario: str | list[str],
        variables: list[str],
        resolution: str,
        hist_scenario: str = "historical",
    ):
        self.data_path = data_path
        self.model = model
        self.scenario = scenario
        self.variables = variables
        self.res = resolution
        self.data = None
        self.hist_scenario, self.proj_scenario = self._filter_scenario(scenario, hist_scenario)

    def open(
        self,
        model: str | list[str] = None,
        scenario: str | list[str] = None,
        variable: str | list[str] = None,
        inplace: bool = False,
    ) -> xr.Dataset | None:
        """
        Open climate data from NetCDF files.

        Parameters
        ----------
        model : str or list of str, optional
            Climate model(s) to include. If None, use all available models.
        scenario : str or list of str, optional
            Climate scenario(s) to include. If None, use all available scenarios.
        variable : str or list of str, optional
            Climate variable(s) to include. If None, use all available variables.
        inplace : bool, default False
            If True, store the opened data in the instance's `data` attribute. If False, return the data.

        Returns
        -------
        xr.Dataset or None
            An xarray Dataset containing the requested climate data. If several models and/or scenarios are requested,
            the data are concatenated along new dimensions 'realization' and/or 'scenario'.
            If `inplace` is True, returns None.
        """

        def check_validity(model=None, scenario=None, variable=None):
            def _valid_invalid(inputs, valids):
                invalid = [i for i in inputs if i not in valids]
                valid = [i for i in inputs if i in valids]
                return valid, invalid

            if model:
                model, invalid_model = _valid_invalid(model, self.model)
            if scenario:
                scenario, invalid_scenario = _valid_invalid(scenario, self.scenario)
            if variable:
                variable, invalid_variable = _valid_invalid(variable, self.variables)

            msgs = []
            if model and invalid_model:
                msgs.append(f"Omitting unavailable model(s): {', '.join(invalid_model)}")
            if scenario and invalid_scenario:
                msgs.append(f"Omitting unavailable scenario(s): {', '.join(invalid_scenario)}")
            if variable and invalid_variable:
                msgs.append(f"Omitting unavailable variable(s): {', '.join(invalid_variable)}")
            if len(msgs) > 0:
                for msg in msgs:
                    warnings.warn(msg, stacklevel=2)
            return model, scenario, variable

        model = model or self.model
        scenario = scenario or self.scenario
        variable = variable or self.variables

        if isinstance(model, str):
            model = [model]
        if isinstance(scenario, str):
            scenario = [scenario]
        if isinstance(variable, str):
            variable = [variable]
        model, scenario, variable = check_validity(model, scenario, variable)

        data = {}
        fp = [f for f in self.data_path.rglob("*.nc")]
        for m in model:
            data[m] = {}
            for s in scenario:
                files = [f for f in fp if m in f.name and s in f.name and any(f"{v}_" in f.name for v in variable)]
                data[m][s] = xr.open_mfdataset(files, combine="by_coords")
            if len(scenario) == 1:
                data[m] = data[m][scenario[0]]
            else:
                data[m] = xr.concat(list(data[m].values()), dim="scenario").assign_coords(scenario=scenario)
        if len(model) == 1:
            data = data[model[0]]
        else:
            data = create_ensemble(data)

        if inplace:
            self.data = data
            return None
        return data

    def open_hist_proj(
        self, proj_scenario: str, model: str | list[str] = None, variable: str | list[str] = None, inplace: bool = False
    ) -> xr.Dataset | None:
        """
        Open climate data for the historical period and a specified projection scenario.

        Parameters
        ----------
        proj_scenario : str
            Projection scenario to open. Must be one of the projection scenarios available in the instance.
        model : str or list of str, optional
            Climate model(s) to include. If None, use all available models.
        variable : str or list of str, optional
            Climate variable(s) to include. If None, use all available variables.
        inplace : bool, default False
            If True, store the opened data in the instance's `data` attribute. If False, return the data.

        Returns
        -------
        xr.Dataset or None
            An xarray Dataset containing the concatenated historical and projection scenario data.
            If `inplace` is True, returns None.
        """
        if proj_scenario not in self.proj_scenario:
            raise ValueError(
                f"'{proj_scenario}' is not a valid projection scenario. "
                "Valid options are: {', '.join(self.proj_scenario)}"
            )
        if not self.hist_scenario:
            warnings.warn(
                "No historical scenario available; returning only the projection scenario data.", stacklevel=2
            )
            return self.open(model=model, scenario=proj_scenario, variable=variable, inplace=inplace)

        data = xr.concat(
            [
                self.open(model=model, scenario=self.hist_scenario, variable=variable, inplace=False),
                self.open(model=model, scenario=proj_scenario, variable=variable, inplace=False),
            ],
            dim="time",
        )

        if inplace:
            self.data = data
            return None
        return data

    @staticmethod
    def _filter_scenario(scenario, hist_scenario):
        if hist_scenario not in scenario:
            hist_scenario = None
        proj_scenario = [s for s in scenario if s != hist_scenario]
        return hist_scenario, proj_scenario


def select_hist_proj(
    data: xr.DataArray | xr.Dataset,
    period: str,
    start_date: str = "1960-01-01",
    end_date: str = "2099-12-31",
    hist_enddate: str = "2014-12-31",
    freq: str = "YS-JUL",
):
    """
    Select historical or projection period from climate data.

    If `freq` outputs will overlap the historical and projection periods, the projection will be extended
    to include the overlapping period.

    Parameters
    ----------
    data : xr.DataArray or xr.Dataset
        Climate data with a time dimension.
    period : str
        Period to select, either 'historical' or 'projection'.
    start_date : str, default "1960-01-01"
        Start date for the selection.
    end_date : str, default "2099-12-31"
        End date for the selection.
    hist_enddate : str, default "2014-12-31"
        End date of the historical period.
    freq : str, default "YS-JUL"
        Frequency for defining the historical and projection periods.
    """
    if period not in ["historical", "projection"]:
        raise ValueError("period must be either 'historical' or 'projection'")

    data = data.sel(time=slice(start_date, end_date))
    hist_dates = pd.date_range(start=start_date, end=hist_enddate, freq=freq)
    proj_dates = pd.date_range(start=hist_enddate, end=end_date, freq=freq)

    if period == "historical":
        return data.sel(time=slice(hist_dates[0], hist_dates[-1]))
    else:
        return data.sel(time=slice(hist_dates[-1], proj_dates[-1]))


climate_data = {
    "nzlusdb_5km": ClimData(
        data_path=Path(r"R:\DATA\NEX_GDDP_CMIP6-NZ"),
        model=["ACCESS-CM2", "CNRM-CM6-1", "EC-Earth3", "GFDL-ESM4", "NorESM2-MM"],
        scenario=["historical", "ssp126", "ssp245", "ssp370", "ssp585"],
        variables=["hurs", "huss", "pr", "rlds", "rsds", "sfcWind", "tas", "tasmax", "tasmin"],
        resolution="25km",
    ),
    "nzlusdb_1km": ClimData(
        data_path=Path(r"R:\DATA\NIWA-CMIP6"),
        model=["ACCESS-CM2", "AWI-CM-1-1-MR", "CNRM-CM6-1", "EC-Earth3", "GFDL-ESM4", "NorESM2-MM"],
        scenario=["historical", "ssp126", "ssp245", "ssp370", "ssp585"],
        variables=["hurs", "PEDsrad", "PETsrad", "pr", "rsds", "sfcWind", "sfcWindmax", "tas", "tasmax", "tasmin"],
        resolution="5km",
    ),
}

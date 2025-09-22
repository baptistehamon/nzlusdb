"""Clim Data class to handle climate data."""

import warnings
from pathlib import Path

import pandas as pd
import xarray as xr
from xclim.core.units import convert_units_to
from xclim.ensembles import create_ensemble

__all__ = [
    "ClimDataset",
    "climateDS",
    "select_hist_proj",
    "TIMEPERIOD",
    "climdata",
]

TIMEPERIOD = ["1960-01-01", "2099-12-31"]  # start of NIWA data to end of NIWA data


class ClimDataset:
    """
    Object to store climate dataset information.

    The climate data are expected to be in NetCDF format and stored in the path directory.
    Each file should be named in a way that includes the model, scenario, and variable information.

    Parameters
    ----------
    name : str
        Name of the climate dataset.
    path : Path
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
    chunks : dict, optional
        Dictionary specifying a appropriate chunking scheme to use for indicator calculations.
        If None, no chunking is applied.
    """

    def __init__(
        self,
        name: str,
        path: Path,
        model: str | list[str],
        scenario: str | list[str],
        variables: list[str],
        resolution: str,
        hist_scenario: str = "historical",
        chunks: dict = None,
    ):
        self.name = name
        self.path = path
        self.model = model
        self.scenario = scenario
        self.variables = variables
        self.res = resolution
        self.data = None
        self.chunks = chunks or {}
        self.hist_scenario, self.proj_scenario = self._filter_scenario(scenario, hist_scenario)

    def open(
        self,
        model: str | list[str] = None,
        scenario: str | list[str] = None,
        variable: str | list[str] = None,
        inplace: bool = False,
        xr_kwargs: dict = None,
        ens_kwargs: dict = None,
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
        xr_kwargs : dict, optional
            Additional keyword arguments to pass to `xr.open_mfdataset`.
        ens_kwargs : dict, optional
            Additional keyword arguments to pass to `xclim.ensembles.create_ensemble`.

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
        fp = [f for f in self.path.rglob("*.nc")]
        for m in model:
            data[m] = {}
            for s in scenario:
                files = [f for f in fp if m in f.name and s in f.name and any(f"{v}_" in f.name for v in variable)]
                data[m][s] = xr.open_mfdataset(files, combine="by_coords", **(xr_kwargs or {}))
            if len(scenario) == 1:
                data[m] = data[m][scenario[0]]
            else:
                data[m] = xr.concat(list(data[m].values()), dim="scenario").assign_coords(scenario=scenario)
        if len(model) == 1:
            data = data[model[0]]
        else:
            data = create_ensemble(data, **(ens_kwargs or {}))

        if inplace:
            self.data = data
            return None
        return data

    def open_hist_proj(
        self,
        proj_scenario: str,
        model: str | list[str] = None,
        variable: str | list[str] = None,
        inplace: bool = False,
        **kwargs,
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
        **kwargs
            Additional keyword arguments to pass to the `open` method.

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
                self.open(model=model, scenario=self.hist_scenario, variable=variable, inplace=False, **kwargs),
                self.open(model=model, scenario=proj_scenario, variable=variable, inplace=False, **kwargs),
            ],
            dim="time",
        )

        if inplace:
            self.data = data
            return None
        return data

    @staticmethod
    def _filter_scenario(scenario, hist_scenario):
        """Filter historical and projection scenarios."""
        if hist_scenario not in scenario:
            hist_scenario = None
        proj_scenario = [s for s in scenario if s != hist_scenario]
        return hist_scenario, proj_scenario


def select_hist_proj(
    data: xr.DataArray | xr.Dataset,
    period: str,
    start_date: str = "1950-01-01",
    end_date: str = "2100-12-31",
    proj_startdate: str = "2015-01-01",
    freq: str = "YS-JUL",
):
    """
    Adjust and select the historical or projection period for a given frequency.

    This is especially useful if the data are expected to be resample to a frequency (`freq`) that does not align with
    the start and end dates of the historical and projection periods. In that case, incomplete frequency periods will
    be removed and the overlapping junction between historical and projection periods will attributed to the projection
    period. For example, if the historical period is defined as 1950-01-01 to 2014-12-31 and the projection period as
    2015-01-01 to 2099-12-31, with a frequency of "YS-JUL", the historical period will be 1950-07-01 to 2014-06-30 and
    the projection period will be 2014-07-01 to 2099-06-30.

    Parameters
    ----------
    data : xr.DataArray or xr.Dataset
        Climate data with a time dimension.
    period : str
        Period to select, either 'historical' or 'projection'.
    start_date : str, optional
        Start date for the selection. Default is "1950-01-01".
    end_date : str, optional
        End date for the selection. Default is "2100-12-31". Should be later than `proj_startdate`.
    proj_startdate : str, optional
        Start date of the projection period. Default is "2015-01-01" (.i.e., CMIP6 historical ends 2014-12-31).
    freq : str, default "YS-JUL"
        Frequency for defining the historical and projection periods.
    """
    if period not in ["historical", "projection"]:
        raise ValueError("period must be either 'historical' or 'projection'")

    data = data.sel(time=slice(start_date, end_date))
    hist_dates = pd.date_range(start=start_date, end=proj_startdate, freq=freq)[[0, -1]]
    hist_start = hist_dates[0].strftime("%Y-%m-%d")
    hist_end = (hist_dates[1] - pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    proj_dates = pd.date_range(start=proj_startdate, end=end_date, freq=freq)[[0, -1]]
    proj_start = hist_dates[1].strftime("%Y-%m-%d")
    proj_end = (proj_dates[1] - pd.Timedelta(days=1)).strftime("%Y-%m-%d")

    if period == "historical":
        return data.sel(time=slice(hist_start, hist_end))
    else:
        return data.sel(time=slice(proj_start, proj_end))


climateDS = {
    "nzlusdb_5km": ClimDataset(
        name="NEX-GDDP-CMIP6",
        path=Path(r"R:\DATA\NEX_GDDP_CMIP6-NZ"),
        model=["ACCESS-CM2", "CNRM-CM6-1", "EC-Earth3", "GFDL-ESM4", "NorESM2-MM"],
        scenario=["historical", "ssp126", "ssp245", "ssp370", "ssp585"],
        variables=["hurs", "huss", "pr", "rlds", "rsds", "sfcWind", "tas", "tasmax", "tasmin"],
        resolution="25km",
        chunks={"realization": -1},
    ),
    "nzlusdb_1km": ClimDataset(
        name="NIWA CMIP6 Downscaling",
        path=Path(r"R:\DATA\NIWA-CMIP6"),
        model=["ACCESS-CM2", "AWI-CM-1-1-MR", "CNRM-CM6-1", "EC-Earth3", "GFDL-ESM4", "NorESM2-MM"],
        scenario=["historical", "ssp126", "ssp245", "ssp370", "ssp585"],
        variables=["hurs", "PEDsrad", "PETsrad", "pr", "rsds", "sfcWind", "sfcWindmax", "tas", "tasmax", "tasmin"],
        resolution="5km",
        chunks={"realization": -1, "time": 365 * 2},
    ),
}


def climdata(func):
    """Decorator to select a specific time period from the climate data before passing it to the function."""

    def wrapper(
        climDS,
        variable,
        period,
        start_date=TIMEPERIOD[0],
        end_date=TIMEPERIOD[1],
        freq="YS-JUL",
        units=None,
        offset=None,
        **kwargs,
    ):
        data = select_hist_proj(
            climDS.data[variable], period=period, start_date=start_date, end_date=end_date, freq=freq
        )
        data = data.chunk(climDS.chunks)
        res: xr.DataArray = func(data, **kwargs).convert_calendar("standard")
        if offset:
            res = res.assign_coords(time=(pd.to_datetime(res.time) + pd.DateOffset(**offset)))
        if units:
            res = convert_units_to(res, units)
        return res

    return wrapper


def open_climdata_timeserie(
    climDS: ClimDataset, scenario: str, variable: str | list[str], inplace: bool = True, ens_kwargs: dict = None
) -> str:
    """
    Open a climate data timeserie (historical + projection) from a ClimDataset instance.

    The function wraps around the `open` and `open_hist_proj` methods of the ClimDataset class and
    opens the historical and projection data for a given scenario, concatenates them along the time dimension,
    and optionally stores the result in the instance's `data` attribute.

    Parameters
    ----------
    climDS : ClimDataset
        An instance of the ClimDataset class containing climate data information.
    scenario : str
        Scenario to open. Can be either the "historical" scenario name of the instance or one of
        the projection scenarios.
    variable : str or list of str
        Climate variable(s) to include.
    inplace : bool, optional
        If True, store the opened data in the instance's `data` attribute. If False, return the data.
        Default is True.
    ens_kwargs : dict, optional
        Additional keyword arguments to pass to the `open` and `open_hist_proj` methods.

    Returns
    -------
    tuple or str
        If `inplace` is False, returns a tuple containing the opened data (xr.Dataset or xr.DataArray) and
        the time period (str). If `inplace` is True, returns the time period (str) only. The time period
        correspond to either 'historical' or 'projection' depending on the given scenario.
    """
    if ens_kwargs is None:
        ens_kwargs = {}
    if scenario == climDS.hist_scenario:
        data = climDS.open(scenario=scenario, variable=variable, inplace=inplace, ens_kwargs=ens_kwargs)
        timeperiod = "historical"
    else:
        data = climDS.open_hist_proj(proj_scenario=scenario, variable=variable, inplace=inplace, ens_kwargs=ens_kwargs)
        timeperiod = "projection"

    if not inplace:
        return (data, timeperiod)
    return timeperiod

"""Module to preprocess data from the Data Supermarket and NZLUSDB for validation purposes."""

from pathlib import Path

import numpy as np
import xarray as xr

CROPS = {
    "apple": 1,
    "avocado": 1,
    "blueberry": 1,
    "cherry": 1,
    "citrus": 2,
    "hops": 2,
    "kiwifruit": 1,
    "maize": 2,
    "manuka": 2,
    "pinotnoir": 1,
    "sauvignonblanc": 1,
    "wheat": 2,
}

DATA_SUPERMARKET_PATH = {
    "path": Path(r"R:\DATA\DataSupermarket-NZ"),
    "1": {
        "folder": "crop_climate_soil_all_score_rcp-past_1972-2004_geo",
        "file": "crop_climate_soil_all_score_RCP_past_1972-2004_geo.tif",
    },
    "2": {"folder": "crop-suitability-categories", "file": "crop-Suitability_categories.tif"},
}


def get_crop_paths(crop: str):
    """Get the path to the crop data in the Data Supermarket"""
    crop_type = CROPS[crop]
    folder = DATA_SUPERMARKET_PATH[str(crop_type)]["folder"].replace("crop", crop)
    file = DATA_SUPERMARKET_PATH[str(crop_type)]["file"].replace("crop", crop)
    return DATA_SUPERMARKET_PATH["path"] / crop.capitalize() / folder / file


def open_supermarket_data(crop: str):
    """Open the crop data from the Data Supermarket"""
    crop_path = get_crop_paths(crop)
    data = xr.open_dataset(crop_path, engine="rasterio")
    data = (
        data["band_data"].isel(band=0).rename({"x": "lon", "y": "lat"}).drop_vars(["spatial_ref", "band"]).drop_attrs()
    )
    return data


def open_nzlusdb_data(crop: str):
    """Open the crop data from the NZLUSDB"""

    def select_suitability(ds: xr.Dataset):
        return ds["suitability"].isel(time=0).drop_vars(["period", "scenario"]).drop_attrs()

    crop_type = CROPS[crop]
    crop_path = Path(rf"D:\NZLUSDB-5km\{crop}\suitability\{crop}_suitability-MMM-change-robustness_5km_v1.0.nc")
    if crop in ["maize", "wheat"]:
        early = Path(str(crop_path).replace(f"{crop}", f"{crop}early"))
        late = Path(str(crop_path).replace(f"{crop}", f"{crop}late"))
        data = (select_suitability(xr.open_dataset(early)) + select_suitability(xr.open_dataset(late))) / 2
    else:
        data = select_suitability(xr.open_dataset(crop_path))

    if crop_type == 2:  # noqa: PLR2004
        # For crops with type 2, we need to bin the suitability values into categories
        bins = [0.6, 0.75, 0.9, 1]
        data = xr.where(
            (data >= 0) & (data < bins[0]),
            4,
            xr.where(
                (data >= bins[0]) & (data < bins[1]),
                3,
                xr.where(
                    (data >= bins[1]) & (data < bins[2]), 2, xr.where((data >= bins[2]) & (data < bins[3]), 1, np.nan)
                ),
            ),
        )
    return data


for crop, crop_type in CROPS.items():
    nzlusdb = open_nzlusdb_data(crop)
    data = open_supermarket_data(crop)
    data = data.interp_like(nzlusdb).clip(min=0)
    if crop_type == 2:  # noqa: PLR2004
        # need to round the Data to get the category
        data = data.round()
    data = xr.merge([data.rename("DataSupermarket"), nzlusdb.rename("NZLUSDB")])
    df = data.to_dataframe().reset_index(drop=True).dropna()
    outpath = Path(__file__).parent / "data"
    if not outpath.exists():
        outpath.mkdir(parents=True)
    df.to_csv(outpath / f"{crop}_suitability_comparison.csv", index=False)

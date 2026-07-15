"""
Process daily IASI/METOP-C L2 NH3 files into one combined, gridded NetCDF file.

This is a generalized, script-friendly version of the original notebook
pipeline: it reads every daily L2 file it can find under `data.base_dir`,
quality/cloud-filters it, regrids it onto a regular lat/lon grid generated
from `data.grid` in the config (no external .mat file needed), and appends
it as one time step of the output NetCDF.

Usage
-----
    python -m iasi_nh3.process --config config/config.yaml
"""
from __future__ import annotations

import argparse
import datetime as dt
import logging
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import scipy.interpolate.ndgriddata as ndgriddata
import xarray as xr
from netCDF4 import Dataset, date2num

from .config import Config, GridConfig
from .functions import generate_masked_array, generate_xr_from_1D_vec

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger(__name__)


def daterange(start_date: date, end_date: date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


def build_target_grid(grid_cfg: GridConfig) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Build a regular lat/lon grid from the bounding box + resolution in the config.

    Returns
    -------
    lat_1d, lon_1d : the 1D coordinate arrays (for the NetCDF dimensions)
    lat_x, lon_x   : the 2D meshgrid arrays (as regridding targets)
    """
    lat_1d = np.arange(grid_cfg.latmin, grid_cfg.latmax + grid_cfg.resolution_deg, grid_cfg.resolution_deg)
    lon_1d = np.arange(grid_cfg.lonmin, grid_cfg.lonmax + grid_cfg.resolution_deg, grid_cfg.resolution_deg)
    lon_x, lat_x = np.meshgrid(lon_1d, lat_1d)
    return lat_1d, lon_1d, lat_x, lon_x


def process_one_day(data: xr.Dataset, cfg: Config, lat_x: np.ndarray, lon_x: np.ndarray) -> np.ndarray:
    """Apply QC masks, regrid one day's swath data onto the target grid, return a 2D array."""
    nh3_data = data["nh3_total_column"]
    iasi_nh3_da = generate_xr_from_1D_vec(
        file=data,
        lat_path="latitude",
        lon_path="longitude",
        variable=nh3_data.data,
        parameter_name=nh3_data.name,
        longname=nh3_data.long_name,
        no_of_dims=1,
        unit=nh3_data.units,
    )

    qf = data["postfilter"]
    qf_da = generate_xr_from_1D_vec(
        file=data,
        lat_path="latitude",
        lon_path="longitude",
        variable=qf.data,
        parameter_name=qf.name,
        longname=qf.long_name,
        no_of_dims=1,
        unit="-",
    )
    nh3_qc_masked = generate_masked_array(
        xarray=iasi_nh3_da, mask=qf_da,
        threshold=cfg.qc.quality_flag_threshold, operator="=", drop=False,
    )

    ampm = data["AMPM"]
    ampm_da = generate_xr_from_1D_vec(
        file=data,
        lat_path="latitude",
        lon_path="longitude",
        variable=ampm.data,
        parameter_name=ampm.name,
        longname=ampm.long_name,
        no_of_dims=1,
        unit="-",
    )
    nh3_day_masked = generate_masked_array(
        xarray=nh3_qc_masked, mask=ampm_da,
        threshold=cfg.qc.daytime_flag_threshold, operator="=", drop=False,
    )

    nh3_converted = nh3_day_masked * nh3_data.multiplication_factor_to_convert_to_molecules_per_cm2

    cloud_cov = data["cloud_coverage"]
    cloud_da = generate_xr_from_1D_vec(
        file=data,
        lat_path="latitude",
        lon_path="longitude",
        variable=cloud_cov,
        parameter_name=cloud_cov.name,
        longname=cloud_cov.long_name,
        no_of_dims=1,
        unit=cloud_cov.units,
    )
    nh3_cloud_masked = generate_masked_array(
        xarray=nh3_converted, mask=cloud_da,
        threshold=cfg.qc.cloud_cover_threshold, operator="<", drop=False,
    )

    values = nh3_cloud_masked.data * 1e-16
    longitude = nh3_cloud_masked.longitude.data
    latitude = nh3_cloud_masked.latitude.data

    gridded = ndgriddata.griddata((longitude, latitude), values, (lon_x, lat_x), method="nearest")
    return gridded


def run(cfg: Config) -> Path:
    lat_1d, lon_1d, lat_x, lon_x = build_target_grid(cfg.grid)

    out_path = Path(cfg.nc_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    ncfile = Dataset(out_path, mode="w", format="NETCDF4")
    ncfile.title = "IASI/METOP-C NH3 total column, QC-filtered and regridded"
    ncfile.subtitle = "IASI METOP-C V4r"

    ncfile.createDimension("lat", lat_1d.size)
    ncfile.createDimension("lon", lon_1d.size)
    ncfile.createDimension("time", None)

    lat_var = ncfile.createVariable("lat", np.float32, ("lat",))
    lat_var.units = "degrees_north"
    lat_var.long_name = "latitude"

    lon_var = ncfile.createVariable("lon", np.float32, ("lon",))
    lon_var.units = "degrees_east"
    lon_var.long_name = "longitude"

    time_var = ncfile.createVariable("time", np.float64, ("time",))
    time_var.units = "hours since 1800-01-01"
    time_var.long_name = "time"

    nh3_var = ncfile.createVariable("NH3", np.float64, ("time", "lat", "lon"))
    nh3_var.units = "molecules/cm^2 x 1e16"
    nh3_var.standard_name = "ammonia"

    lat_var[:] = lat_1d
    lon_var[:] = lon_1d

    n_ok, n_missing = 0, 0
    if cfg.dates:
        dates_to_process = cfg.dates
    else:
        dates_to_process = [
            single_date
            for year in cfg.years
            for single_date in daterange(date(year, 1, 1), date(year + 1, 1, 1))
        ]

    for single_date in dates_to_process:
        file_path = cfg.file_path_for(single_date)
        try:
            data = xr.open_dataset(file_path)
            gridded = process_one_day(data, cfg, lat_x, lon_x)

            time_index = ncfile.dimensions["time"].size
            single_datetime = dt.datetime(single_date.year, single_date.month, single_date.day)
            time_var[time_index] = date2num(single_datetime, time_var.units)
            nh3_var[time_index, :, :] = gridded

            n_ok += 1
            log.info("Processed %s", single_date)
            data.close()
        except Exception as exc:  # noqa: BLE001 - keep the batch going
            n_missing += 1
            log.warning("Skipping %s (%s): %s", single_date, file_path, exc)

    ncfile.close()
    log.info("Done. %d days written, %d days missing/skipped.", n_ok, n_missing)
    log.info("Output written to %s", out_path.resolve())
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config/config.yaml", help="Path to config.yaml")
    args = parser.parse_args()

    cfg = Config.load(args.config)
    run(cfg)


if __name__ == "__main__":
    main()

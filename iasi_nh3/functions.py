"""
Core data-loading, reshaping and visualization helpers.

Ported from the EUMETSAT LTPy training course `functions.ipynb`
(https://gitlab.eumetsat.int/eumetlab/atmosphere/atmosphere), MIT licensed.
Only the functions actually used by this project are kept here.
"""
from __future__ import annotations

import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER


def generate_xr_from_1D_vec(
    file, lat_path, lon_path, variable, parameter_name, longname, no_of_dims, unit
) -> xr.DataArray:
    """
    Wrap a raw 1D (or 2D) variable from an IASI L2 file into an xarray.DataArray
    with latitude / longitude attached as coordinates.

    Parameters
    ----------
    file : netCDF4.Dataset or xarray.Dataset
        The opened L2 data file.
    lat_path, lon_path : str
        Variable names for latitude / longitude within `file`.
    variable : array-like
        The data values of interest.
    parameter_name : str
        Short name assigned to the returned DataArray.
    longname : str
        CF-style long name, stored as an attribute.
    no_of_dims : int
        1 for ground-pixel (swath) data, 2 for gridded data.
    unit : str
        Units, stored as an attribute.

    Returns
    -------
    xarray.DataArray
    """
    latitude = file[lat_path]
    longitude = file[lon_path]
    param = variable

    if no_of_dims == 1:
        param_da = xr.DataArray(
            param[:].data if hasattr(param, "data") else np.asarray(param),
            dims=("ground_pixel",),
            coords={
                "latitude": ("ground_pixel", latitude[:].data),
                "longitude": ("ground_pixel", longitude[:].data),
            },
            attrs={"long_name": longname, "units": unit},
            name=parameter_name,
        )
    else:
        param_da = xr.DataArray(
            param[:],
            dims=["x", "y"],
            coords={
                "latitude": (["x", "y"], latitude[:]),
                "longitude": (["x", "y"], longitude[:]),
            },
            attrs={"long_name": longname, "units": unit},
            name=parameter_name,
        )

    return param_da


def generate_masked_array(xarray, mask, threshold, operator, drop=True):
    """
    Apply a threshold mask (e.g. quality flag, cloud cover) onto a DataArray.

    Parameters
    ----------
    xarray : xarray.DataArray
        Data to mask.
    mask : xarray.DataArray
        Same-shape array used to build the mask (e.g. cloud fraction).
    threshold : float
    operator : str
        One of '<', '>', '!=' or '=' (default, equality).
    drop : bool
        If True, drop NaNs from the result.
    """
    if operator == "<":
        cloud_mask = xr.where(mask < threshold, 1, 0)
    elif operator == "!=":
        cloud_mask = xr.where(mask != threshold, 1, 0)
    elif operator == ">":
        cloud_mask = xr.where(mask > threshold, 1, 0)
    else:
        cloud_mask = xr.where(mask == threshold, 1, 0)

    xarray_masked = xr.where(cloud_mask == 1, xarray, np.nan)
    xarray_masked.attrs = xarray.attrs
    if drop:
        return xarray_masked[~np.isnan(xarray_masked)]
    return xarray_masked


def generate_geographical_subset(xarray, latmin, latmax, lonmin, lonmax, reassign=False):
    """Subset a DataArray to a lat/lon bounding box (optionally reassigning 0-360 -> -180/180)."""
    if reassign:
        xarray = xarray.assign_coords(
            longitude=(((xarray.longitude + 180) % 360) - 180)
        )
    return xarray.where(
        (xarray.latitude < latmax)
        & (xarray.latitude > latmin)
        & (xarray.longitude < lonmax)
        & (xarray.longitude > lonmin),
        drop=True,
    )


def visualize_pcolormesh(
    data_array,
    longitude,
    latitude,
    projection,
    color_scale,
    unit,
    long_name,
    vmin,
    vmax,
    set_global=True,
    lonmin=-180,
    lonmax=180,
    latmin=-90,
    latmax=90,
):
    """Plot a 2D gridded DataArray with matplotlib's pcolormesh on a cartopy map."""
    fig = plt.figure(figsize=(12, 10))
    ax = plt.axes(projection=projection)

    img = ax.pcolormesh(
        longitude,
        latitude,
        data_array,
        cmap=plt.get_cmap(color_scale),
        transform=ccrs.PlateCarree(),
        vmin=vmin,
        vmax=vmax,
        shading="auto",
    )

    ax.add_feature(cfeature.BORDERS, edgecolor="black", linewidth=0.8)
    ax.add_feature(cfeature.COASTLINE, edgecolor="black", linewidth=0.8)

    if projection == ccrs.PlateCarree():
        ax.set_extent([lonmin, lonmax, latmin, latmax], projection)
        gl = ax.gridlines(draw_labels=True, linestyle="--", linewidth=0.5)
        gl.top_labels = False
        gl.right_labels = False
        gl.xformatter = LONGITUDE_FORMATTER
        gl.yformatter = LATITUDE_FORMATTER
        gl.xlabel_style = {"size": 11}
        gl.ylabel_style = {"size": 11}

    if set_global:
        ax.set_global()
        ax.gridlines()

    cbar = fig.colorbar(img, ax=ax, orientation="horizontal", fraction=0.045, pad=0.08)
    cbar.set_label(unit, fontsize=13)
    cbar.ax.tick_params(labelsize=11)
    ax.set_title(long_name, fontsize=16, pad=15.0)

    return fig, ax

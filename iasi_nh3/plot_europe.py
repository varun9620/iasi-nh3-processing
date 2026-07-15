"""
Plot the combined IASI NH3 NetCDF file over a region (default: Europe).

Usage
-----
    # Mean over the whole time series, Europe extent
    python -m iasi_nh3.plot_europe --config config/config.yaml

    # A single date
    python -m iasi_nh3.plot_europe --config config/config.yaml --date 2023-01-02

    # A different region defined in config.yaml, or a custom bbox
    python -m iasi_nh3.plot_europe --config config/config.yaml --region global
    python -m iasi_nh3.plot_europe --config config/config.yaml --bbox -10 30 35 60
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cartopy.crs as ccrs
import matplotlib.pyplot as plt
import xarray as xr

from .config import Config, RegionConfig
from .functions import visualize_pcolormesh


def load_region(cfg: Config, region_name: str | None, bbox: list[float] | None) -> RegionConfig:
    if bbox is not None:
        lonmin, lonmax, latmin, latmax = bbox
        return RegionConfig(lonmin=lonmin, lonmax=lonmax, latmin=latmin, latmax=latmax)

    name = region_name or cfg.default_region
    if name not in cfg.regions:
        raise ValueError(f"Unknown region '{name}'. Available: {list(cfg.regions)}")
    return cfg.regions[name]


def plot(cfg: Config, region_name: str | None = None, bbox: list[float] | None = None,
         single_date: str | None = None, vmax: float | None = None) -> Path:
    region = load_region(cfg, region_name, bbox)

    ds = xr.open_dataset(cfg.nc_file)

    if single_date:
        nh3 = ds["NH3"].sel(time=single_date, method="nearest")
        title_suffix = f"{single_date}"
    else:
        nh3 = ds["NH3"].mean(dim="time", skipna=True)
        title_suffix = f"mean {ds.time.dt.year.values.min()}-{ds.time.dt.year.values.max()}"

    fig, ax = visualize_pcolormesh(
        data_array=nh3.values,
        longitude=ds["lon"].values,
        latitude=ds["lat"].values,
        projection=ccrs.PlateCarree(),
        color_scale="YlOrRd",
        unit="NH3 total column [x1e16 molec/cm^2]",
        long_name=f"IASI/METOP-C NH3 total column - {region_name or cfg.default_region} ({title_suffix})",
        vmin=0,
        vmax=vmax if vmax is not None else float(nh3.quantile(0.98)),
        set_global=False,
        lonmin=region.lonmin,
        lonmax=region.lonmax,
        latmin=region.latmin,
        latmax=region.latmax,
    )

    out_dir = Path(cfg.plot_output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = single_date if single_date else "mean"
    out_path = out_dir / f"nh3_{region_name or cfg.default_region}_{suffix}.png"
    fig.savefig(out_path, dpi=200)
    plt.close(fig)

    ds.close()
    return out_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--config", default="config/config.yaml", help="Path to config.yaml")
    parser.add_argument("--region", default=None, help="Region name defined in config.yaml (default: europe)")
    parser.add_argument("--bbox", nargs=4, type=float, default=None,
                         metavar=("LONMIN", "LONMAX", "LATMIN", "LATMAX"),
                         help="Custom bounding box, overrides --region")
    parser.add_argument("--date", default=None, help="Single date YYYY-MM-DD; default is the full-period mean")
    parser.add_argument("--vmax", type=float, default=None, help="Colorbar max; default is the 98th percentile")
    args = parser.parse_args()

    cfg = Config.load(args.config)
    out_path = plot(cfg, region_name=args.region, bbox=args.bbox, single_date=args.date, vmax=args.vmax)
    print(f"Saved plot to {out_path.resolve()}")


if __name__ == "__main__":
    main()

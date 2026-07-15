"""Load and validate the project YAML configuration."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date as date_type
from pathlib import Path
from typing import Dict, List, Optional

import yaml


@dataclass
class QCConfig:
    quality_flag_threshold: float = 1
    daytime_flag_threshold: float = 0
    cloud_cover_threshold: float = 0.25


@dataclass
class RegionConfig:
    lonmin: float
    lonmax: float
    latmin: float
    latmax: float


@dataclass
class GridConfig:
    lonmin: float
    lonmax: float
    latmin: float
    latmax: float
    resolution_deg: float = 0.1


@dataclass
class Config:
    base_dir: str
    file_pattern: str
    years: List[int]
    grid: GridConfig
    nc_file: str
    qc: QCConfig
    regions: Dict[str, RegionConfig]
    plot_output_dir: str
    default_region: str = "europe"
    dates: Optional[List[date_type]] = None

    @classmethod
    def load(cls, path: str | Path) -> "Config":
        path = Path(path)
        with open(path, "r") as f:
            raw = yaml.safe_load(f)

        data = raw["data"]
        output = raw["output"]
        qc_raw = raw.get("qc", {})
        plot_raw = raw.get("plot", {})

        regions = {
            name: RegionConfig(**bounds)
            for name, bounds in plot_raw.get("regions", {}).items()
        }

        dates_raw = data.get("dates")
        dates = None
        if dates_raw:
            dates = [date_type.fromisoformat(str(d)) for d in dates_raw]

        return cls(
            base_dir=data["base_dir"],
            file_pattern=data["file_pattern"],
            years=data.get("years", []),
            grid=GridConfig(**data["grid"]),
            nc_file=output["nc_file"],
            qc=QCConfig(**qc_raw),
            regions=regions,
            plot_output_dir=plot_raw.get("output_dir", "outputs/plots"),
            default_region=plot_raw.get("region", "europe"),
            dates=dates,
        )

    def file_path_for(self, single_date) -> Path:
        """Build the on-disk path for a given date, e.g. .../2023/IASI_METOPC_L2_NH3_20230102_....nc"""
        filename = self.file_pattern.format(date=single_date.strftime("%Y%m%d"))
        return Path(self.base_dir) / single_date.strftime("%Y") / filename

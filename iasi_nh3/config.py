"""Load and validate the project YAML configuration."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

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
class Config:
    base_dir: str
    file_pattern: str
    years: List[int]
    grid_file: str
    nc_file: str
    qc: QCConfig
    regions: Dict[str, RegionConfig]
    plot_output_dir: str
    default_region: str = "europe"

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

        return cls(
            base_dir=data["base_dir"],
            file_pattern=data["file_pattern"],
            years=data["years"],
            grid_file=data["grid_file"],
            nc_file=output["nc_file"],
            qc=QCConfig(**qc_raw),
            regions=regions,
            plot_output_dir=plot_raw.get("output_dir", "outputs/plots"),
            default_region=plot_raw.get("region", "europe"),
        )

    def file_path_for(self, single_date) -> Path:
        """Build the on-disk path for a given date, e.g. .../2023/IASI_METOPC_L2_NH3_20230102_....nc"""
        filename = self.file_pattern.format(date=single_date.strftime("%Y%m%d"))
        return Path(self.base_dir) / single_date.strftime("%Y") / filename

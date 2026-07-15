import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from iasi_nh3.config import Config
from datetime import date


def test_load_config():
    cfg = Config.load(Path(__file__).parents[1] / "config" / "config.yaml")
    assert cfg.years[0] == 2023
    assert "europe" in cfg.regions
    assert cfg.regions["europe"].lonmin == -25


def test_file_path_for():
    cfg = Config.load(Path(__file__).parents[1] / "config" / "config.yaml")
    p = cfg.file_path_for(date(2023, 1, 2))
    assert str(p).endswith("2023/IASI_METOPC_L2_NH3_20230102_ULB-LATMOS_V4.0.0R.nc") or \
           str(p).replace("\\", "/").endswith("2023/IASI_METOPC_L2_NH3_20230102_ULB-LATMOS_V4.0.0R.nc")

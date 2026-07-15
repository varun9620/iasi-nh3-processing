# Data

Sample raw IASI/METOP-C Level‑2 NH3 files, laid out the way `iasi_nh3/process.py`
expects (`data/METOP-C/<year>/<file>.nc`), matching `config/config.yaml`:

```
data/
└── METOP-C/
    └── 2023/
        ├── IASI_METOPC_L2_NH3_20230101_ULB-LATMOS_V4.0.0R.nc
        ├── IASI_METOPC_L2_NH3_20230102_ULB-LATMOS_V4.0.0R.nc
        └── IASI_METOPC_L2_NH3_20230103_ULB-LATMOS_V4.0.0R.nc
```

These three days are enough to run the full pipeline end-to-end as a demo
without needing the complete 2019-2023 archive.

Note: GitHub blocks pushes with individual files over 100 MB. If your NH3
L2 files are close to or over that, use
[Git LFS](https://git-lfs.com/) instead of committing them directly:

```bash
git lfs install
git lfs track "data/**/*.nc"
git add .gitattributes
```

The `.mat` grid file (`grid_file` in `config.yaml`) isn't included here —
add it separately if you want to commit it too (same size caveat applies).

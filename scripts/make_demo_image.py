"""
Generate a synthetic NH3-like field over Europe, purely to illustrate what
`plot_europe.py` produces once real IASI data has been processed.
Not part of the pipeline itself - just a README/demo image generator.
"""
import numpy as np
import matplotlib.pyplot as plt

rng = np.random.default_rng(7)

lon = np.linspace(-25, 45, 175)
lat = np.linspace(34, 72, 148)
LON, LAT = np.meshgrid(lon, lat)

# fake NH3 "hotspots" roughly over a few agricultural regions, plus noise
hotspots = [(5, 51, 3.0), (12, 45, 2.2), (20, 52, 2.0), (-3, 40, 1.5), (30, 50, 1.8)]
field = np.zeros_like(LON)
for hlon, hlat, amp in hotspots:
    field += amp * np.exp(-(((LON - hlon) ** 2) / 30 + ((LAT - hlat) ** 2) / 15))
field += rng.normal(0, 0.15, size=field.shape)
field = np.clip(field, 0, None)

fig, ax = plt.subplots(figsize=(10, 8))
img = ax.pcolormesh(LON, LAT, field, cmap="YlOrRd", shading="auto")
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title("IASI/METOP-C NH3 total column - Europe (demo)", fontsize=14, pad=15)

cbar = fig.colorbar(img, ax=ax, orientation="horizontal", fraction=0.045, pad=0.1)
cbar.set_label("NH3 total column [x1e16 molec/cm^2] (synthetic demo data)")

fig.savefig("assets/demo_output.png", dpi=150, bbox_inches="tight")
print("Saved assets/demo_output.png")
print("Note: this is synthetic placeholder data, not real IASI output.")
print("When cartopy can reach Natural Earth (needs internet), plot_europe.py")
print("will additionally draw coastlines/borders via cartopy.")

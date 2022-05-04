# EOmaps example 3: Customize the appearance of the plot

from eomaps import Maps
import pandas as pd
import numpy as np

# ----------- create some example-data
lon, lat = np.meshgrid(np.arange(-30, 60, 0.25), np.arange(30, 60, 0.3))
data = pd.DataFrame(
    dict(lon=lon.flat, lat=lat.flat, data_variable=np.sqrt(lon**2 + lat**2).flat)
)
data = data.sample(3000)  # take 3000 random datapoints from the dataset
# ------------------------------------

m = Maps(
    crs=3857, figsize=(9, 5)
)  # create a map in a pseudo-mercator (epsg 3857) projection
m.add_feature.preset.ocean(fc="lightsteelblue")
m.add_feature.preset.coastline(lw=0.25)
m.set_data(
    data=data,
    x="lon",
    y="lat",
    in_crs=4326,
    cpos="c",  # pixel-coordinates represent "center-position" (default)
    cpos_radius=None,  # radius to shift the center-position if "cpos" is not "c"
)

m.ax.set_title("What a nice figure")
m.set_shape.geod_circles(radius=30000)  # plot geodesic-circles with 30 km radius

# set the classification scheme that should be applied to the data
m.set_classify_specs(
    scheme="UserDefined", bins=[35, 36, 37, 38, 45, 46, 47, 48, 55, 56, 57, 58]
)

m.plot_map(
    edgecolor="k",  # give shapes a black edgecolor
    linewidth=0.5,  # ... with a linewidth of 0.5
    cmap="RdYlBu",  # use a red-yellow-blue colormap
    vmin=35,  # map colors to values above 35
    vmax=60,  # map colors to values below 60
    alpha=0.75,  # add some transparency
)  # pass some additional arguments to the plotted collection

# ------------------ add a colorbar and change it's appearance
m.add_colorbar(histbins="bins", label="some parameter", density=True)
_ = m.figure.ax_cb_plot.set_ylabel("The Y label")  # add a y-label to the histogram

m.subplots_adjust(
    bottom=0.1, top=0.95, left=0.075, right=0.95, hspace=0.2
)  # adjust the padding
m.figure.set_colorbar_position(
    pos=[0.125, 0.1, 0.83, 0.15], ratio=999
)  # manually re-position the colorbar

m.add_logo(position="lr", pad=(-1.1, 0), size=0.1)

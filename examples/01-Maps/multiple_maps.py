# EOmaps example: Data-classification and multiple Maps in one figure

from eomaps import Maps, MapsGrid
import pandas as pd
import numpy as np

# ----------- create some example-data
lon, lat = np.meshgrid(np.arange(-20, 40, 0.5), np.arange(30, 60, 0.5))
data = np.sqrt(lon**2 + lat**2)
# take 4000 random datapoints from the dataset
df = pd.DataFrame({"lon": lon.flat, "lat": lat.flat, "data": data.flat}).sample(4000)
# ------------------------------------

# initialize a grid of Maps objects
mg = MapsGrid(1, 3, crs=[4326, Maps.CRS.Stereographic(), 3035])

# add titles
mg[0].add_title("epsg=4326")
mg[1].add_title("Stereographic")
mg[2].add_title("epsg=3035")

# add background features
mg.add_feature.preset("coastline", "ocean", "land")
mg[1]["delaunay"].add_feature.preset.coastline()

# set classification specs
mg[0].set_classify.EqualInterval(k=10)
mg[1][:].set_classify.Quantiles(k=8)
mg[2].set_classify.StdMean(multiples=[-1, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1])

# set shapes to use
mg[[0, 1]].set_shape.ellipses()
mg[1].set_shape.rectangles()
mg[1]["delaunay"].set_shape.delaunay_triangulation(mask_radius=0.5)

# assign the data to all layers of all maps
mg[:][:].set_data(data=df, x="lon", y="lat", crs=4326)

# plot data
mg[:]["base"].plot_map(cmap="viridis")
mg[1]["delaunay"].plot_map(cmap="RdYlBu")

# add colorbars
mg[:][:].add_colorbar(extend="neither")
mg[:][:].colorbar.ax_cb.tick_params(rotation=90, labelsize=8)

# add logos to all maps
mg.add_logo(size=0.05)

# attach callbacks
mg.cb.pick.attach.mark(fc=["r", "none"], ec="r", lw=1, buffer=[1, 5], permanent=True)
mg.cb.move.attach.mark(fc="none", ec="k", lw=2, buffer=10, permanent=False)

mg[1].cb.pick.attach.annotate(text="the closest point is here!", zorder=99)
mg[1]["delaunay"].cb.move.attach.annotate(text="callbacks are layer-sensitive!")

# share move & pick-events between maps
mg.cb.move.share_events(*mg)
mg.cb.pick.share_events(*mg)

# add a layer-selector widget
mg.util.layer_selector(ncol=2, loc="lower center", draggable=False)

# apply a pre-defined layout (obtained via the LayoutEditor)
layout = {
    "figsize": [11.0, 5.0],
    "0_map": [0.015, 0.495, 0.30994, 0.34375],
    "1_map": [0.35151, 0.4125, 0.32413, 0.5095],
    "2_map": [0.705, 0.495, 0.28707, 0.37602],
    "3_cb": [0.05522, 0.1375, 0.2625, 0.2805],
    "3_cb_histogram_size": 0.8,
    "4_cb": [0.33625, 0.165, 0.3525, 0.2],
    "4_cb_histogram_size": 0.8,
    "5_cb": [0.72022, 0.1375, 0.2625, 0.2805],
    "5_cb_histogram_size": 0.8,
    "6_logo": [0.2725, 0.495, 0.05, 0.04538],
    "7_logo": [0.625, 0.4125, 0.05, 0.04538],
    "8_logo": [0.93864, 0.495, 0.05, 0.04538],
}

mg.apply_layout(layout)
mg.show()

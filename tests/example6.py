# EOmaps example 6: WebMap services and layer-switching

# %matplotlib widget
from eomaps import Maps
import numpy as np
import pandas as pd

# create some data
lon, lat = np.meshgrid(np.linspace(-50, 50, 150), np.linspace(30, 60, 150))
data = pd.DataFrame(
    dict(lon=lon.flat, lat=lat.flat, data=np.sqrt(lon**2 + lat**2).flat)
)
# --------------------------------

m = Maps(Maps.CRS.GOOGLE_MERCATOR, layer="S1GBM_vv")
# set the crs to GOOGLE_MERCATOR to avoid reprojecting the WebMap data
# (makes it a lot faster and it will also look much nicer!)
# ------------- LAYER 0
# add a layer showing S1GBM
m.add_wms.S1GBM.add_layer.vv()

# ------------- LAYER 1
# if you just want to add features, you can also do it within the same Maps-object!
# add OpenStreetMap on the currently invisible layer (OSM)
m.add_wms.OpenStreetMap.add_layer.default(layer="OSM")

# ------------- LAYER 2
# create a new layer and plot some data
m2 = m.new_layer(layer="data")
m2.set_data(data=data.sample(5000), x="lon", y="lat", crs=4326)
m2.set_shape.geod_circles(radius=20000)
m2.plot_map()

# add a callback that is only executed if the "data" layer is visible
m2.cb.pick.attach.annotate(zorder=100)  # use a high zorder to put it on top

# ------------ CALLBACKS
# since m.layer == "all", the callbacks assigned to "m" will be executed on all layers!

# on a left-click, show layers ("data", "OSM") in a rectangle
# (with a size of 20% of the axis)
m.all.cb.click.attach.peek_layer(layer="data|OSM", how=0.2)

# on a right-click, "swipe" the layers ("data", "S1GBM_vv") from the left
m.all.cb.click.attach.peek_layer(
    layer="data|S1GBM_vv",
    how="left",
    button=3,
)

# switch between the layers with the keys 0, 1 and 2
m.all.cb.keypress.attach.switch_layer(layer="S1GBM_vv", key="0")
m.all.cb.keypress.attach.switch_layer(layer="OSM", key="1")
m.all.cb.keypress.attach.switch_layer(layer="data", key="2")

# ------------------------------
m.f.set_size_inches(9, 4)
m.subplots_adjust(left=0.01, right=0.99, bottom=0.01, top=0.99)

m.add_logo()

# add a utility-widget for switching the layers
m.util.layer_selector(
    loc="upper left",
    ncol=3,
    bbox_to_anchor=(0.01, 0.99),
    layers=["OSM", "S1GBM_vv", "data"],
)

m.util.layer_slider(
    pos=(0.5, 0.93, 0.38, 0.025),
    color="r",
    handle_style=dict(facecolor="r"),
    txt_patch_props=dict(fc="w", ec="none", alpha=0.75, boxstyle="round, pad=.25"),
    layers=["OSM", "S1GBM_vv", "data"],
)

# show the S1GBM layer on start
m.show_layer("S1GBM_vv")

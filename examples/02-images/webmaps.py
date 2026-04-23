# EOmaps example: WebMap services and layer-switching

from eomaps import Maps
import numpy as np
import pandas as pd

# ------ create some data --------
lon, lat = np.meshgrid(np.linspace(-50, 50, 150), np.linspace(30, 60, 150))
data = pd.DataFrame(
    dict(lon=lon.flat, lat=lat.flat, data=np.sqrt(lon**2 + lat**2).flat)
)

# -------- plot the map ----------
# set the crs to epsg=3857 (e.g. WebMercator to avoid reprojecting the WebMaps
# (makes it a lot faster and it will also look much nicer!)
m = Maps(3857, figsize=(9, 4))
m.add_logo()

# add webmaps to dedicated layers
m["S1GBM_vv"].add_wms.S1GBM.add_layer.vv()
m["OSM"].add_wms.OpenStreetMap.add_layer.default()

# create a new layer named "data" and plot some data
# (do this "non lazy" so that the extent is set to the data limits)
with Maps.lazy(False):
    m["data"].set_data(data=data.sample(5000), x="lon", y="lat", crs=4326)
    m["data"].set_shape.geod_circles(radius=20000)
    m["data"].plot_map()

    # add a pick callback that is only executed if the "data" layer is visible
    m["data"].cb.pick.attach.annotate()

# -------- CALLBACKS ----------
# (use m.all to execute independent of the visible layer)
# on a left-click, show layers ("data", "OSM") in a rectangle
m.all.cb.click.attach.peek_layer(("OSM", "data"), size=0.4)

# on a right-click, "swipe" the layers ("S1GBM_vv" and "data") from the left
m.all.cb.click.attach.peek_layer(("S1GBM_vv", "data"), shape="left", button=3)

# switch between the layers by pressing the keys 1, 2 and 3
m.all.cb.keypress.attach.switch_layer("data", key="1")
m.all.cb.keypress.attach.switch_layer("OSM", key="2")
m.all.cb.keypress.attach.switch_layer("S1GBM_vv", key="3")

# ------ UTILITY WIDGETS --------
# add a clickable widget to switch between layers
m.util.layer_selector(
    loc="upper left",
    ncol=3,
    bbox_to_anchor=(0.01, 0.99),
    layers=["OSM", "S1GBM_vv", "data"],
)
# add a slider to switch between layers
s = m.util.layer_slider(
    pos=(0.5, 0.93, 0.38, 0.025),
    color="r",
    handle_style=dict(facecolor="r"),
    txt_patch_props=dict(fc="w", ec="none", alpha=0.75, boxstyle="round, pad=.25"),
)

# explicitly set the layers you want to use in the slider
# (Note: you can also use combinations of multiple existing layers!)
s.set_layers(["data", "OSM", "S1GBM_vv", "OSM|data{0.5}"])

# ---------- layout ----------

m.apply_layout(
    {
        "figsize": [9.0, 4.0],
        "0_map": [0.00625, 0.01038, 0.9875, 0.97924],
        "1_logo": [0.865, 0.02812, 0.12, 0.11138],
        "2_slider": [0.45, 0.93, 0.38, 0.025],
    }
)

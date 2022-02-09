# EOmaps example 6: WebMap services and layer-switching

from eomaps import Maps
import numpy as np
import pandas as pd

# create some data
lon, lat = np.meshgrid(np.linspace(-50, 50, 150), np.linspace(30, 60, 150))
data = pd.DataFrame(
    dict(lon=lon.flat, lat=lat.flat, data=np.sqrt(lon**2 + lat**2).flat)
)
# --------------------------------

m = Maps(Maps.CRS.GOOGLE_MERCATOR)
# set the crs to GOOGLE_MERCATOR to avoid reprojecting the WebMap data
# (makes it a lot faster and it will also look much nicer!)

# ------------- LAYER 0
# add S1GBM as a base-layer
wms1 = m.add_wms.S1GBM
wms1.add_layer.vv()

# ------------- LAYER 1
# if you just want to add features, you can do it within the same Maps-object!
# add OpenStreetMap on the currently invisible layer (1)
wms2 = m.add_wms.OpenStreetMap.OSM_mundialis
wms2.add_layer.OSM_WMS(layer=1)

# ------------- LAYER 2
# create a connected maps-object and plot some data on a new layer (2)
m2 = m.new_layer(layer=2)
m2.set_data(data=data.sample(5000), xcoord="lon", ycoord="lat", crs=4326)
m2.set_shape.geod_circles(radius=20000)
m2.plot_map()
m2.add_wms.S1GBM.add_layer.vv()  # add S1GBM as background on layer 2 as well


# ------------ CALLBACKS
# on a left-click, show layer 1 in a rectangle (with a size of 20% of the axis)
m.cb.click.attach.peek_layer(layer=1, how=(0.2, 0.2))

# on a right-click, "swipe" layer (2) from the left
m.cb.click.attach.peek_layer(layer=2, how="left", button=3)

m.cb.keypress.attach.switch_layer(layer=0, key="0")
m.cb.keypress.attach.switch_layer(layer=1, key="1")
m.cb.keypress.attach.switch_layer(layer=2, key="2")

# ------------------------------
m.figure.f.set_size_inches(9, 4)
m.figure.gridspec.update(left=0.01, right=0.99, bottom=0.01, top=0.99)

m.add_logo()

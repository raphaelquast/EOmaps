# EOmaps example 2: Data-classification and multiple Maps in one figure

from eomaps import MapsGrid, Maps
import pandas as pd
import numpy as np

# ----------- create some example-data
lon, lat = np.meshgrid(np.arange(-20, 40, 0.5), np.arange(30, 60, 0.5))
data = pd.DataFrame(
    dict(lon=lon.flat, lat=lat.flat, data_variable=np.sqrt(lon**2 + lat**2).flat)
)
data = data.sample(4000)  # take 4000 random datapoints from the dataset
# ------------------------------------

mg = MapsGrid(
    1, 3, crs=[4326, Maps.CRS.Stereographic(), 3035], figsize=(11, 5), bottom=0.15
)  # initialize a grid of Maps objects
# set the data on ALL maps-objects of the grid
mg.set_data(data=data, xcoord="lon", ycoord="lat", in_crs=4326)

# --------- set specs for the first axes
mg.m_0_0.set_plot_specs(title="epsg=4326")
mg.m_0_0.set_classify_specs(scheme="EqualInterval", k=10)

# --------- set specs for the second axes
mg.m_0_1.set_plot_specs(title="Stereographic")
mg.m_0_1.set_shape.rectangles()
mg.m_0_1.set_classify_specs(scheme="Quantiles", k=4)

# --------- set specs for the third axes

mg.m_0_2.ax.set_extent(mg.m_0_2.crs_plot.area_of_use.bounds)

mg.m_0_2.set_plot_specs(title="epsg=3035")
mg.m_0_2.set_classify_specs(
    scheme="StdMean", multiples=[-1, -0.75, -0.5, -0.25, 0.25, 0.5, 0.75, 1]
)

# --------- plot all maps and add colorbars to all maps
mg.plot_map()
mg.add_colorbar()

mg.add_feature.preset.ocean()
mg.add_feature.preset.land()
mg.add_feature.preset.coastline()

# --------- plot all maps and rotate the ticks of the colorbar
for m in mg:
    m.figure.ax_cb.tick_params(rotation=90, labelsize=8)
# --------- add some callbacks to indicate the clicked data-point to all maps
for m in mg:
    m.cb.pick.attach.mark(
        fc="r", ec="none", buffer=1, permanent=True, shape=m.shape.name
    )
    m.cb.pick.attach.mark(
        fc="none", ec="r", lw=1, buffer=5, permanent=True, shape=m.shape.name
    )

    m.cb.click.attach.mark(
        fc="none", ec="k", lw=2, buffer=10, permanent=False, shape=m.shape.name
    )
    m.add_logo()
# add a specific annotation-callback to the second map
# (put it on a layer > 10 (the default for markers) so that it appears above the markers)
mg.m_0_1.cb.pick.attach.annotate(layer=11, text="the closest point is here!")

# share click & pick-events between all Maps-objects of the MapsGrid
mg.share_click_events()
mg.share_pick_events()

# EOmaps example 5: Add overlays and indicators

from eomaps import Maps
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# create some data
lon, lat = np.meshgrid(np.linspace(-20, 40, 100), np.linspace(30, 60, 100))
data = pd.DataFrame(
    dict(
        lon=lon.flat,
        lat=lat.flat,
        param=(((lon - lon.mean()) ** 2 - (lat - lat.mean()) ** 2)).flat,
    )
)
data_OK = data[data.param >= 0]
data_OK.var = np.sqrt(data_OK.param)
data_mask = data[data.param < 0]

# --------- initialize a Maps object and plot a basic map
m = Maps()
m.set_data(data=data_OK, xcoord="lon", ycoord="lat", in_crs=4326)
m.set_plot_specs(
    crs=m.crs_list.Orthographic(),
    title="Wooohoo, a flashy map-widget with static indicators!",
    histbins=200,
    cmap="Spectral_r",
)
m.set_shape.rectangles(mesh=True)
m.set_classify_specs(scheme="Quantiles", k=10)

m.plot_map()
m.figure.f.set_figheight(7)

# ... add a basic "annotate" callback
cid = m.cb.click.attach.annotate(bbox=dict(alpha=0.75), color="w")

# --------- add another layer of data to indicate the values in the masked area
#           (copy all defined specs but the classification)
m2 = m.copy(connect=True, copy_classify_specs=False)
m2.data_specs.data = data_mask
m2.set_shape.rectangles(mesh=False)
m2.plot_specs.cmap = "magma"
m2.plot_map()

# --------- add another layer with data that is dynamically updated if we click on the masked area
m3 = m.copy(connect=True, copy_classify_specs=False)
m3.data_specs.data = data_OK.sample(1000)
m3.set_shape.ellipses(radius=25000, radius_crs=3857)
m3.set_plot_specs(cmap="gist_ncar")
# plot the map and assign a "dynamic_layer_idx" to allow dynamic updates of the collection
m3.plot_map(edgecolor="w", linewidth=0.25, layer=10, dynamic=True)

# --------- define a callback that will change the position and data-values of the additional layer
def callback(self, **kwargs):
    selection = np.random.randint(0, len(m3.data), 1000)
    m3.figure.coll.set_array(data_OK.param.iloc[selection])


# attach the callback to the second Maps object such that it triggers when we click on the masked-area
m2.cb.click.attach(callback)

# --------- add some basic overlays from NaturalEarth
m.add_overlay(
    dataspec=dict(resolution="10m", category="physical", name="lakes"),
    styledict=dict(ec="none", fc="b"),
)
m.add_overlay(
    dataspec=dict(resolution="10m", category="cultural", name="admin_0_countries"),
    styledict=dict(ec=".75", fc="none", lw=0.5),
)
m.add_overlay(
    dataspec=dict(resolution="10m", category="cultural", name="urban_areas"),
    styledict=dict(ec="none", fc="r"),
)
m.add_overlay(
    dataspec=dict(
        resolution="10m", category="physical", name="rivers_lake_centerlines"
    ),
    styledict=dict(ec="b", fc="none", lw=0.25),
)

# --------- add a customized legend for the overlays
m.add_overlay_legend(
    ncol=2,
    loc="lower center",
    facecolor="w",
    framealpha=1,
    update_hl={
        "admin_0_countries": [plt.Line2D([], [], c=".75"), "Country boarders"],
        "rivers_lake_centerlines": [plt.Line2D([], [], c="b", alpha=0.5), "Rivers"],
        "lakes": [None, "Lakes"],
        "urban_areas": [None, "Urban Areas"],
    },
    sort_order=["lakes", "rivers_lake_centerlines", "urban_areas", "admin_0_countries"],
)

# --------- add some fancy (static) indicators for selected pixels
mark_id = 6060
for buffer in np.linspace(1, 5, 10):
    m.add_marker(
        ID=mark_id,
        shape="ellipses",
        radius="pixel",
        fc=[1, 0, 0, 0.1],
        ec="r",
        buffer=buffer * 5,
    )
m.add_marker(
    ID=mark_id, shape="rectangles", radius="pixel", fc="g", ec="y", buffer=3, alpha=0.5
)
m.add_marker(
    ID=mark_id, shape="ellipses", radius="pixel", fc="k", ec="none", buffer=0.2
)
m.add_annotation(
    ID=mark_id,
    text=f"Here's Vienna!\n... the data-value is={m.data.param.loc[mark_id]:.2f}",
    xytext=(80, 85),
    textcoords="offset points",
    bbox=dict(boxstyle="round", fc="w", ec="r"),
    horizontalalignment="center",
    arrowprops=dict(arrowstyle="fancy", facecolor="r", connectionstyle="arc3,rad=0.35"),
)

mark_id = 3324
m.add_marker(ID=mark_id, shape="ellipses", radius=3, fc="none", ec="g", ls="--", lw=2)
m.add_annotation(
    ID=mark_id,
    text="",
    xytext=(0, 98),
    textcoords="offset points",
    arrowprops=dict(
        arrowstyle="fancy", facecolor="g", connectionstyle="arc3,rad=-0.25"
    ),
)

m.add_marker(
    ID=mark_id,
    shape="geod_circles",
    radius=500000,
    radius_crs=3857,
    fc="none",
    ec="b",
    ls="--",
    lw=2,
)
m.add_annotation(
    ID=mark_id,
    text=(
        "Here's the center of:\n"
        + "    $\\bullet$ a blue 'circle' with 50km radius\n"
        + "    $\\bullet$ a green 'circle' with 3deg radius"
    ),
    xytext=(-80, 100),
    textcoords="offset points",
    bbox=dict(boxstyle="round", fc="w", ec="k"),
    horizontalalignment="left",
    arrowprops=dict(arrowstyle="fancy", facecolor="w", connectionstyle="arc3,rad=0.35"),
)

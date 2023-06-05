from eomaps import Maps
import numpy as np

m = Maps(Maps.CRS.Orthographic())
m.add_feature.preset.coastline()  # add some coastlines

# ---------- create a new inset-map
#            showing a 15 degree rectangle around the xy-point
m2 = m.new_inset_map(
    xy=(5, 45),
    xy_crs=4326,
    shape="rectangles",
    radius=15,
    plot_position=(0.75, 0.4),
    plot_size=0.5,
    inset_crs=4326,
    boundary=dict(ec="r", lw=1),
    indicate_extent=dict(fc=(1, 0, 0, 0.25)),
)

# populate the inset with some more detailed features
m2.add_feature.preset.coastline()
m2.add_feature.preset.ocean()
m2.add_feature.preset.land()
m2.add_feature.preset.countries()
m2.add_feature.preset.urban_areas()


# ---------- create another inset-map
#            showing a 400km circle around the xy-point
m3 = m.new_inset_map(
    xy=(5, 45),
    xy_crs=4326,
    shape="geod_circles",
    radius=400000,
    plot_position=(0.25, 0.4),
    plot_size=0.5,
    inset_crs=3035,
    boundary=dict(ec="g", lw=2),
    indicate_extent=dict(fc=(0, 1, 0, 0.25)),
)

# populate the inset with some features
m3.add_wms.OpenStreetMap.add_layer.stamen_terrain_background()

# print some data on all of the maps

x, y = np.meshgrid(np.linspace(-50, 50, 100), np.linspace(-30, 70, 100))
data = x + y

m.set_data(data, x, y, crs=4326)
m.set_classify.Quantiles(k=4)
m.plot_map(alpha=0.5, ec="none", set_extent=False)

# use the same data and classification for the inset-maps
for m_i in [m2, m3]:
    m_i.inherit_data(m)
    m_i.inherit_classification(m)

m2.set_shape.ellipses(np.mean(m.shape.radius) / 2)
m2.plot_map(alpha=0.75, ec="k", lw=0.5, set_extent=False)

m3.set_shape.ellipses(np.mean(m.shape.radius) / 2)
m3.plot_map(alpha=1, ec="k", lw=0.5, set_extent=False)


# add an annotation for the second datapoint to the inset-map
m3.add_annotation(ID=1, xytext=(-120, 80))

# indicate the extent of the second inset on the first inset
m3.indicate_inset_extent(m2, ec="g", lw=2, fc="g", alpha=0.5, zorder=0)

# add some additional text to the inset-maps
for m_i, txt, color in zip([m2, m3], ["epsg: 4326", "epsg: 3035"], ["r", "g"]):
    txt = m_i.ax.text(
        0.5,
        0,
        txt,
        transform=m_i.ax.transAxes,
        horizontalalignment="center",
        bbox=dict(facecolor=color),
    )
    # add the text-objects as artists to the blit-manager
    m_i.BM.add_artist(txt)

m3.add_colorbar(hist_bins=20, margin=dict(bottom=-0.2), label="some parameter")
# move the inset map (and the colorbar) to a different location
m3.set_inset_position(x=0.3)

# share pick events
for mi in [m, m2, m3]:
    mi.cb.pick.attach.annotate(text=lambda ID, val, **kwargs: f"ID={ID}\nval={val:.2f}")
m.cb.pick.share_events(m2, m3)

m.apply_layout(
    {
        "figsize": [6.4, 4.8],
        "0_map": [0.1625, 0.09, 0.675, 0.9],
        "1_inset_map": [0.5625, 0.15, 0.375, 0.5],
        "2_inset_map": [0.0875, 0.33338, 0.325, 0.43225],
        "3_cb": [0.0875, 0.12, 0.4375, 0.12987],
        "3_cb_histogram_size": 0.8,
    }
)

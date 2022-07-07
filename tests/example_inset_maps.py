from eomaps import Maps

m = Maps(Maps.CRS.Orthographic())
m.add_feature.preset.coastline(lw=0.25)  # add some coastlines

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

# populate the inset with some features
m2.add_feature.preset.coastline()
m2.add_feature.preset.ocean()
m2.add_feature.preset.land()

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

# populate the inset with some more detailed features
m3.add_feature.preset.coastline()
m3.add_feature.preset.ocean()
m3.add_feature.preset.land()
m3.add_feature.cultural_10m.admin_0_countries(fc="none", ec=".5")
m3.add_feature.cultural_10m.urban_areas(fc="r", ec="none")

# print some data on all of the maps
m3.set_shape.ellipses(n=100)  # use a higher ellipse-resolution on the inset-map
for m_i in [m, m2, m3]:
    m_i.set_data([1, 2, 3, 1], [5, 6, 7, 6.6], [45, 46, 47, 48.5], crs=4326)
    m_i.plot_map(alpha=0.75, ec="k", lw=0.5, set_extent=False)

# add an annotation for the second datapoint to the inset-map
m3.add_annotation(ID=1, xytext=(-120, 80))

# indicate the extent of the second inset on the first inset
m3.indicate_inset_extent(m2)

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

m3.add_colorbar(histbins=20, top=0.15)
# move the inset map (and the colorbar) to a different location
m3.set_inset_position(x=0.3)
# set the y-ticks of the colorbar histogram
m3.figure.ax_cb_plot.set_yticks([0, 1, 2])
m3.redraw()

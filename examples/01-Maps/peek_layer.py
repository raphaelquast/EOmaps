from eomaps import Maps
import numpy as np
from matplotlib.text import TextPath
import matplotlib.pyplot as plt

text_path = TextPath(
    (0, 0), r"A nice text placed on a gridline", prop=dict(weight="bold")
)

m = Maps(Maps.CRS.EckertV(), facecolor="k")

n = 15
for i in reversed(range(n)):
    m[f"test{i}"].add_feature.preset.ocean(fc=plt.cm.magma_r(i / n))
    m[f"test{i}"].add_feature.preset.land(fc=plt.cm.terrain_r(i / n))

    x, y = (0, 45)
    size = (
        np.linspace(1, 20 * 5, n)[i] * np.sqrt(2),
        np.linspace(1, 20 * 5, n)[i] * np.sqrt(2),
    )

    m.add_peek_layer(
        f"test{i}",
        shape=".",
        # size=float((i+1)/(n-2)),
        # shape_crs="axes",
        # xy=(.5,.5),
        # xy_crs="axes",
        size=size,
        shape_crs=4326,
        xy_crs=4326,
        xy=(-x, y),
        boundary=dict(ec="k", lw=2),
    )

    m.cb.move.attach.peek_layer(
        (f"test{i}", "overlay"),
        shape="geod_circle",
        # how=float((i+1)/n),
        # shape_crs="axes",
        # xy=(.5,.5),
        # xy_crs="axes",
        size=(i + 1) * 1e5,
        # shape_crs=4326,
        # xy_crs=4326,
        # xy=(-x,y),
        boundary=False,
        # boundary=dict(ec="k", lw=2)
    )


m.add_feature.preset.ocean()

# m.l.overlay.add_feature.preset.urban_areas(fc="r", ec="r")
# m.l.overlay.add_feature.preset.lakes(fc="b")
# m.l.overlay.add_feature.preset.rivers_lake_centerlines(lw=0.1)
# m.l.overlay.add_feature.preset.coastline(lw=0.5)


# (m + m.l.overlay).show()
# m.f.canvas.draw()
# m.savefig(r"C:\Users\rquast\Desktop\EOmaps_figure1.png", dpi=500)

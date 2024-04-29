import pytest

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

from eomaps import Maps

np.random.seed(0)

# TODO add proper (extensive) tests for each shape!

x, y = np.linspace(-40, 40, 50), np.linspace(-25, 30, 150)
x2d, y2d = np.meshgrid(x, y, indexing="ij")
data = x2d**2 + y2d**2

# use an irregular sample of the data to check irregular datasets as well
data_pandas = dict(
    data=pd.DataFrame(
        dict(lon=x2d.ravel(), lat=y2d.ravel(), value=data.ravel())
    ).sample(1000),
    x="lon",
    y="lat",
    parameter="value",
)
data_1d = dict(x=x2d.ravel(), y=y2d.ravel(), data=data.ravel())
data_1d_2d = dict(x=x, y=y, data=data)
data_2d = dict(x=x2d, y=y2d, data=data)

testdata = [data_pandas, data_1d, data_1d_2d, data_2d]
ids = ["pandas", "1D", "1D2D", "2D"]

# %%


@pytest.fixture
def close_all():
    yield
    plt.close("all")


@pytest.mark.usefixtures("close_all")
@pytest.mark.parametrize("data", testdata, ids=ids)
@pytest.mark.mpl_image_compare()
def test_hexbin(data):
    m = Maps(ax=221, figsize=(10, 6))
    m.set_data(**data)
    m.set_shape.hexbin(size=(10, 5))
    m.plot_map()
    cb = m.add_colorbar()

    m2 = m.new_map(ax=222, inherit_data=True)
    m2.set_shape.hexbin(size=20, aggregator="median")
    m2.plot_map(cmap="RdYlBu")
    m2.add_colorbar()

    m3 = m.new_map(ax=223, inherit_data=True)
    m3.set_shape.hexbin(size=10, aggregator="min")
    m3.plot_map(cmap="RdYlBu")
    m3.add_colorbar()

    m4 = m.new_map(ax=224, inherit_data=True)
    m4.set_shape.hexbin(size=10, aggregator="max")
    m4.set_classify.EqualInterval(k=5)
    m4.plot_map(cmap="RdYlBu")
    m4.add_colorbar()

    return m


@pytest.mark.usefixtures("close_all")
@pytest.mark.parametrize("data", testdata, ids=ids)
@pytest.mark.mpl_image_compare()
def test_contour(data):
    m = Maps(ax=221, figsize=(10, 6))
    m.subplots_adjust(left=0.01, right=0.99)
    m.set_data(**data)
    m.set_shape.contour(filled=True)
    m.plot_map()
    m.add_colorbar()

    m1 = m.new_map(ax=222, inherit_data=True)
    m1.set_shape.contour(filled=False)
    m1.plot_map()
    m1.add_colorbar()

    m2 = m.new_map(ax=223, inherit_data=True)
    m2.add_feature.preset("ocean", "land")
    m2.set_shape.contour(filled=True)
    m2.plot_map(
        colors=["none", "r", (0, 1, 0, 0.25), "r"],
        hatches=["", "xxxx", "///", "xxxx"],
    )

    m3 = m.new_map(ax=224, inherit_data=True)
    m3.set_shape.voronoi_diagram()
    m3.plot_map(alpha=0.25, lw=0.25, ec="k")
    cb3 = m3.add_colorbar()

    m3_1 = m3.new_layer("contours", inherit_data=True)
    m3_1.set_shape.contour(filled=False)
    m3_1.plot_map(linestyles=["--", "-", ":", "-."])

    cb3.indicate_contours(
        contour_map=m3_1,
        add_labels="top",
        exclude_levels=[0, -1],
        label_kwargs=dict(color="r", rotation=90, xytext=(-5, -10)),
    )

    cb3.indicate_contours(
        contour_map=m3_1,
        add_labels="top",
        use_levels=[1],
        label_names=["This one!"],
        label_kwargs=dict(
            xytext=(-40, 20), zorder=-1, arrowprops={"arrowstyle": "fancy"}
        ),
    )

    # TODO using 'clabel' causes collections to be re-drawn
    # which puts the new contours on the default layer and leaves
    # the old contours as "artists without a figure" in the blit-manager!
    # see https://github.com/raphaelquast/EOmaps/issues/218

    # arts = m3_1.ax.clabel(m3_1.coll.contour_set)
    # for a in arts:
    #     m3_1.BM.add_bg_artist(a, layer=m3_1.layer)

    m.show_layer("base", "contours")

    return m


@pytest.mark.usefixtures("close_all")
@pytest.mark.parametrize("data", testdata, ids=ids)
@pytest.mark.mpl_image_compare()
def test_shade_points(data):
    m = Maps(ax=221, figsize=(10, 6))

    m.set_data(**data)
    m.set_shape.shade_points(aggregator="mean")
    m.set_shade_dpi(100)
    m.plot_map()
    m.add_colorbar()

    m2 = m.new_map(ax=222, inherit_data=True)
    m2.set_shape.shade_points(aggregator="max")
    m2.set_shade_dpi(30)
    m2.plot_map(cmap="RdYlBu")
    m2.add_colorbar()

    m3 = m.new_map(ax=223, inherit_data=True)
    m3.set_shape.shade_points(aggregator="max")
    m3.set_shade_dpi(20)
    m3.plot_map(cmap="RdYlBu")
    m3.add_colorbar()

    m4 = m.new_map(ax=224, inherit_data=True)
    m4.set_shape.shade_points(aggregator="max")
    m4.set_shade_dpi(10)
    m4.set_classify.EqualInterval(k=5)
    m4.plot_map(cmap="RdYlBu")
    m4.add_colorbar()

    for mi in [m, m2, m3, m4]:
        mi.add_title(f"shade dpi = {mi._shade_dpi}")

    return m

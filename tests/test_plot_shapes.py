import unittest

import pandas as pd
import numpy as np

from eomaps import Maps
import matplotlib.pyplot as plt

# TODO add proper (extensive) tests for each shape!


class TestPlotShapes(unittest.TestCase):
    def setUp(self):
        x, y = np.meshgrid(np.linspace(-40, 40, 50), np.linspace(-25, 30, 50))
        data = x**2 + y**2

        # use an irregular sample of the data to check irregular datasets as well
        self.data_pandas = dict(
            data=pd.DataFrame(
                dict(lon=x.ravel(), lat=y.ravel(), value=data.ravel())
            ).sample(500),
            x="lon",
            y="lat",
            parameter="value",
        )

        self.data_1d = dict(x=x.ravel(), y=y.ravel(), data=data.ravel())

        self.data_2d = dict(x=x, y=y, data=data)

    def test_contour(self):
        for data in (self.data_pandas, self.data_1d, self.data_2d):
            m = Maps(ax=221, figsize=(10, 6))
            m.subplots_adjust(left=0.01, right=0.99)
            m.set_data(**data)
            m.set_shape.contour(filled=True)
            m.plot_map()
            cb = m.add_colorbar()

            m1 = m.new_map(ax=222, inherit_data=True)
            m1.set_shape.contour(filled=False)
            m1.plot_map()
            cb1 = m1.add_colorbar()

            m2 = m.new_map(ax=223, inherit_data=True)
            m2.add_feature.preset("ocean", "land")
            m2.set_shape.contour(filled=True)
            m2.plot_map(
                colors=["none", "r", (0, 1, 0, 0.25), "r"],
                hatches=["", "xxxx", "///", "xxxx"],
            )

            m3 = m.new_map(ax=224, inherit_data=True)
            m3.set_shape.ellipses()
            m3.plot_map(alpha=0.25)
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
            plt.close("all")

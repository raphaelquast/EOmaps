import matplotlib as mpl

mpl.rcParams["toolbar"] = "None"

import unittest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from eomaps import Maps


class TestWMS(unittest.TestCase):
    def setUp(self):
        x, y = np.meshgrid(
            np.linspace(-19000000, 19000000, 50), np.linspace(-19000000, 19000000, 50)
        )
        x, y = x.ravel(), y.ravel()

        self.data = pd.DataFrame(dict(x=x, y=y, value=y - x))

    def test_WMS_OSM(self):
        m = Maps()
        m.plot_specs.crs = Maps.CRS.GOOGLE_MERCATOR
        m.add_wms.OpenStreetMap.add_layer.default()
        plt.close(m.figure.f)

    def test_WMS_S1GBM(self):
        m = Maps()
        m.plot_specs.crs = Maps.CRS.GOOGLE_MERCATOR
        m.add_wms.S1GBM.add_layer.vv()
        plt.close(m.figure.f)

    def test_WMS_ESA_WorldCover(self):
        m = Maps()
        m.plot_specs.crs = Maps.CRS.GOOGLE_MERCATOR

        m.plot_map(colormap=False)
        ESA_layer = m.add_wms.ESA_WorldCover.add_layer.WORLDCOVER_2020_MAP
        ESA_layer.set_extent_to_bbox()
        ESA_layer.info

        ESA_layer()

        plt.close(m.figure.f)

    def test_WMS_legend_capabilities_NASA_GIBS(self):
        m = Maps()
        m.plot_specs.crs = 4326
        m.plot_map(colormap=False)

        # use a layer that provides a legend
        NASA_layer = (
            m.add_wms.NASA_GIBS.EPSG_3857.add_layer.AIRS_L2_Cloud_Top_Height_Night
        )
        NASA_layer.set_extent_to_bbox()

        NASA_layer.info

        NASA_layer(transparent=True)
        NASA_layer.add_legend()

        legax = m.figure.f.axes[-1]
        leg_cpos = (
            (legax.bbox.x0 + legax.bbox.x1) / 2,
            (legax.bbox.y0 + legax.bbox.y1) / 2,
        )

        # pick up the the legend (e.g. click on it)
        m.figure.f.canvas.button_press_event(*leg_cpos, 1, False)

        # resize the legend
        m.figure.f.canvas.scroll_event(*leg_cpos, 20, False)

        # move the legend
        m.figure.f.canvas.motion_notify_event(
            (m.figure.ax.bbox.x0 + m.figure.ax.bbox.x1) / 2,
            (m.figure.ax.bbox.y0 + m.figure.ax.bbox.y1) / 2,
            None,
        )

        # release the legend
        m.figure.f.canvas.button_press_event(0, 0, 1, False)
        plt.close(m.figure.f)

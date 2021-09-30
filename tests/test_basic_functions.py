import unittest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from mapit import MapIt


class TestBasicPlotting(unittest.TestCase):
    def setUp(self):
        x, y = np.meshgrid(
            np.linspace(-19000000, 19000000, 100), np.linspace(-19000000, 19000000, 100)
        )
        x, y = x.ravel(), y.ravel()

        self.data = pd.DataFrame(dict(x=x, y=y, value=np.random.normal(0, 1, len(x))))

    def test_simple_map(self):
        m = MapIt()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=4326)
        m.plot_map()

        plt.close(m.figure.f)

    def test_simple_rectangles(self):
        m = MapIt()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=4326, shape="rectangles")
        m.plot_map()

        plt.close(m.figure.f)

    def test_add_callbacks(self):
        m = MapIt()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=3857, shape="rectangles")

        m.plot_map()

        # attach all callbacks
        double_click, mouse_button = True, 1
        for n, cb in enumerate([i for i in m.cb.__dir__() if not i.startswith("_")]):
            if n == 1:
                double_click = False
            if n == 2:
                double_click = False
            if n == 1:
                mouse_button = 1
            if n == 2:
                mouse_button = 2

            m.add_callback(cb, double_click=double_click, mouse_button=mouse_button)

        # TODO how to check if callbacks actually work in a unittest?
        plt.close(m.figure.f)

    def test_add_overlay(self):
        m = MapIt()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=3857, shape="rectangles")

        m.plot_map()

        m.add_overlay(
            dataspec=dict(resolution="10m", category="cultural", name="urban_areas"),
            styledict=dict(facecolor="r"),
        )

        plt.close(m.figure.f)

    def test_add_discrete_layer(self):
        m = MapIt()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=3857, shape="rectangles")

        m.plot_map()

        coll = m.add_discrete_layer(self.data, "value", "x", "y", in_crs=3857)
        coll.set_facecolor("none")
        coll.set_edgecolor("r")

        plt.close(m.figure.f)

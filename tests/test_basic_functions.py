import unittest
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from eomaps import Maps


class TestBasicPlotting(unittest.TestCase):
    def setUp(self):
        x, y = np.meshgrid(
            np.linspace(-19000000, 19000000, 50), np.linspace(-19000000, 19000000, 50)
        )
        x, y = x.ravel(), y.ravel()

        self.data = pd.DataFrame(dict(x=x, y=y, value=np.random.normal(0, 1, len(x))))

    def test_simple_map(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=4326)
        m.plot_map()

        plt.close(m.figure.f)

    def test_simple_plot_shapes(self):
        usedata = self.data.sample(500)
        for shape in Maps._shapes:
            m = Maps()
            m.data = usedata
            m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
            m.set_plot_specs(plot_epsg=4326, shape=shape)
            m.plot_map()

            plt.close(m.figure.f)

    def test_simple_map2(self):
        m = Maps()
        m.data = self.data

        for cpos in ["ul", "ur", "ll", "lr", "c"]:
            m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
            m.set_plot_specs(
                plot_epsg=4326,
                title="asdf",
                label="bsdf",
                radius=1,
                radius_crs="out",
                histbins=100,
                density=True,
                cpos=cpos,
            )
            m.plot_map()

            plt.close(m.figure.f)
            # m.figure.reinit()  # do this explicitly since it does not work with unittests

    def test_simple_map(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(
            plot_epsg=4326,
            title="asdf",
            label="bsdf",
            radius=1,
            radius_crs="out",
            histbins=100,
            density=True,
            cpos="ur",
        )
        m.plot_map()

        plt.close(m.figure.f)

    def test_alpha_and_splitbins(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=4326, shape="rectangles", alpha=0.4)
        m.set_classify_specs(scheme="Percentiles", pct=[0.1, 0.2])

        m.plot_map()

        plt.close(m.figure.f)

    def test_classification(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=4326, shape="rectangles")

        m.set_classify_specs(scheme="Quantiles", k=5)

        m.plot_map()

        plt.close(m.figure.f)

    def test_add_callbacks(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=3857, shape="rectangles")

        m.plot_map()

        # attach all callbacks
        double_click, mouse_button = True, 1
        for n, cb in enumerate(m.cb.cb_list):
            if n == 1:
                double_click = False
            if n == 2:
                double_click = False
            if n == 1:
                mouse_button = 1
            if n == 2:
                mouse_button = 2

            m.add_callback(cb, double_click=double_click, mouse_button=mouse_button)
            self.assertTrue(
                list(m._attached_cbs) == [f"{cb}__{double_click}_{mouse_button}"]
            )
            m.remove_callback(f"{cb}__{double_click}_{mouse_button}")
            self.assertTrue(len(m._attached_cbs) == 0)

        plt.close(m.figure.f)

    def test_callbacks(self):

        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=3857, shape="rectangles")

        m.plot_map()

        # test all callbacks
        for n, cb in enumerate(m.cb.cb_list):

            kwargs = dict(ID=1, pos=(1, 2), val=3.365734, ind=None)
            if cb == "load":
                kwargs["database"] = pd.DataFrame([1, 2, 3, 4])
                kwargs["load_method"] = "xs"
            callback = getattr(m.cb, cb)
            callback = callback.__func__.__get__(m.cb)
            callback(**kwargs)

        plt.close(m.figure.f)

    def test_add_overlay(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=3857, shape="rectangles")

        m.plot_map()

        m.add_overlay(
            dataspec=dict(resolution="10m", category="cultural", name="urban_areas"),
            styledict=dict(facecolor="r"),
        )
        m.add_overlay(
            dataspec=dict(resolution="10m", category="physical", name="lakes"),
            styledict=dict(facecolor="b"),
        )

        m.add_overlay_legend(
            loc="upper center",
            update_hl={
                "lakes": [None, "asdf"],
                "urban_areas": [plt.Line2D([], [], c="r"), "bsdf"],
            },
            sort_order=["lakes", "urban_areas"],
        )

        plt.close(m.figure.f)

    def test_add_discrete_layer(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=3857, shape="rectangles")

        m.plot_map()

        coll = m.add_discrete_layer(self.data, "value", "x", "y", in_crs=3857)
        coll.set_facecolor("none")
        coll.set_edgecolor("r")

        plt.close(m.figure.f)

    def test_add_annotate(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=4326, shape="rectangles")

        m.plot_map()

        m.add_annotation(ID=m.data["value"].idxmax(), fontsize=15, text="adsf")

        def customtext(m, ID, val, pos, ind):
            return f"{m.data_specs}\n {val}\n {pos}\n {ID} \n {ind}"

        m.add_annotation(ID=m.data["value"].idxmin(), text=customtext)

        m.add_annotation(
            xy=(m.data.x[0], m.data.y[0]), xy_crs=3857, fontsize=15, text="adsf"
        )

        plt.close(m.figure.f)

    def test_add_marker(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
        m.set_plot_specs(plot_epsg=3857, shape="rectangles")

        m.plot_map()

        m.add_marker(20, facecolor=[1, 0, 0, 0.5], edgecolor="r")
        m.add_marker(250, facecolor=[1, 0, 0, 0.5], edgecolor="r", radius=5000000)
        m.add_marker(
            250, facecolor="b", edgecolor="m", linewidth=3, buffer=3, alpha=0.5
        )
        m.add_marker(250, fc="none", ec="k", ls="--", radius=35, radius_crs=4326)

        m.add_marker(
            xy=(-14000000, -8500000),
            xy_crs=3857,
            facecolor="none",
            edgecolor="r",
        )

        with self.assertRaises(TypeError):
            # it's not possible to use radius="pixel" and xy
            m.add_marker(
                xy=(m.data.x[100], m.data.y[100]),
                xy_crs=3857,
                facecolor="none",
                edgecolor="r",
                radius="pixel",
            )

        for shape in ["circle", "ellipse", "rectangle"]:
            m.add_marker(
                85,
                facecolor="none",
                edgecolor="r",
                radius="pixel",
                shape=shape,
            )

        plt.close(m.figure.f)

    # TODO re-implement test once copy is re-implemented
    # def test_copy(self):
    #     m = Maps()
    #     m.data = self.data
    #     m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857)
    #     m.set_plot_specs(plot_epsg=3857, shape="rectangles")
    #     m.set_classify_specs(scheme="Quantiles", k=5)

    #     m2 = m.copy()

    #     m.data_specs == m2.data_specs
    #     m.data_specs == m2.plot_specs
    #     m.classify_specs == m2.classify_specs

    #     m3 = m.copy(copy_data=True)

    #     m.data_specs == m3.data_specs
    #     m.data_specs == m3.plot_specs
    #     m.classify_specs == m3.classify_specs
    #     m.data == m3.data
    #     m3.plot_map()
    #     plt.close(m3.figure.f)

    def test_prepare_data(self):
        m = Maps()
        m.data = self.data
        m.set_data_specs(xcoord="x", ycoord="y", in_crs=3857, parameter="value")
        m.set_plot_specs(shape="ellipses")
        data = m._prepare_data()
        self.assertTrue(
            sorted(list(data.keys()))
            == sorted(
                [
                    "x0",
                    "y0",
                    "w",
                    "h",
                    "theta",
                    "ids",
                    "z_data",
                    "p0",
                    "p1",
                    "p2",
                    "p3",
                    "radius",
                ]
            )
        )

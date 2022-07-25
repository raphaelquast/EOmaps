import matplotlib as mpl

# mpl.rcParams["toolbar"] = "None"

import unittest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from eomaps import Maps, MapsGrid


class TestCallbacks(unittest.TestCase):
    def setUp(self):
        self.lon, self.lat = np.meshgrid(
            np.linspace(-50, 50, 50), np.linspace(-25, 25, 50)
        )

        self.data = pd.DataFrame(
            dict(lon=self.lon.flat, lat=self.lat.flat, value=(self.lon + self.lat).flat)
        )

    def create_basic_map(self):
        if not hasattr(self, "nfig"):
            self.nfig = 0
        self.nfig += 1

        m = Maps()
        # use either a pandas.DataFrame or a 2D numpy-array for testing
        if self.nfig % 2 == 0:
            m.set_data(self.data, x="lon", y="lat")
        else:
            m.set_data(self.lon + self.lat, x=self.lon, y=self.lat)

        m.plot_map()
        m.figure.f.canvas.draw()

        return m

    def get_ax_center(self, ax):
        return

    def click_ax_center(self, m, dx=0, dy=0, release=True):
        ax = m.figure.ax
        cv = m.figure.f.canvas
        x, y = (ax.bbox.x0 + ax.bbox.x1) / 2, (ax.bbox.y0 + ax.bbox.y1) / 2
        cv.button_press_event(x + dx, y + dy, 1, False)
        if release:
            cv.button_release_event(x + dx, y + dy, 1, False)

    def test_get_values(self):

        # ---------- test as CLICK callback
        m = self.create_basic_map()
        cid = m.cb.click.attach.get_values()

        m.cb.pick.attach.annotate()

        self.click_ax_center(m)
        self.assertEqual(len(m.cb.click.get.picked_vals["pos"]), 1)
        self.assertTrue(m.cb.click.get.picked_vals["ID"][0] is None)
        self.assertTrue(m.cb.click.get.picked_vals["val"][0] is None)

        self.click_ax_center(m)
        self.assertEqual(len(m.cb.click.get.picked_vals["pos"]), 2)
        self.assertTrue(m.cb.click.get.picked_vals["ID"][1] is None)
        self.assertTrue(m.cb.click.get.picked_vals["val"][1] is None)

        m.cb.click.remove(cid)
        plt.close("all")

        # ---------- test as PICK callback
        m = self.create_basic_map()
        cid = m.cb.pick.attach.get_values()

        self.click_ax_center(m)
        self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 1)
        self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 1)
        self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 1)

        self.assertTrue(m.cb.pick.get.picked_vals["ID"][0] == 1225)

        self.click_ax_center(m)
        self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 2)
        self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 2)
        self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 2)

        m.cb.click.remove(cid)
        plt.close("all")

    def test_print_to_console(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()
        cid = m.cb.click.attach.print_to_console()

        self.click_ax_center(m)
        m.cb.click.remove(cid)
        plt.close("all")

        # ---------- test as PICK callback
        m = self.create_basic_map()
        cid = m.cb.pick.attach.print_to_console()

        self.click_ax_center(m)
        m.cb.click.remove(cid)
        plt.close("all")

    def test_annotate(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()
        cid = m.cb.click.attach.annotate()
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.annotate(
            pos_precision=8, val_precision=8, permanent=True, xytext=(-30, -50)
        )
        self.click_ax_center(m)

        cid = m.cb.click.attach.annotate(text="hellooo", xytext=(200, 200))
        self.click_ax_center(m)

        def text(m, ID, val, pos, ind):
            return f"{ID}\n {val}\n {pos}\n {ind}\n {m.data_specs.crs}"

        props = dict(
            xytext=(-50, 100),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="g", ec="r"),
            arrowprops=dict(arrowstyle="fancy"),
        )

        cid = m.cb.click.attach.annotate(text=text, **props)
        self.click_ax_center(m)

        # ---------- test as PICK callback
        m = self.create_basic_map()
        cid = m.cb.pick.attach.annotate()
        self.click_ax_center(m)
        m.cb.pick.remove(cid)

        m.cb.pick.attach.annotate(
            pos_precision=8, val_precision=8, permanent=False, xytext=(-30, -50)
        )
        self.click_ax_center(m)

        m.cb.pick.attach.annotate(text="hellooo", xytext=(200, 200))
        self.click_ax_center(m)

        def text(m, ID, val, pos, ind):
            return f"{ID}\n {val}\n {pos}\n {ind}\n {m.data_specs.crs}"

        props = dict(
            xytext=(-50, 100),
            textcoords="offset points",
            bbox=dict(boxstyle="round", fc="g", ec="r"),
            arrowprops=dict(arrowstyle="fancy"),
        )

        m.cb.pick.attach.annotate(text=text, **props)
        self.click_ax_center(m)

        plt.close("all")

    def test_mark(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()
        cid = m.cb.click.attach.mark()

        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.mark(
            radius=400000,
            radius_crs=3857,
            shape="rectangles",
            fc="r",
            ec="g",
            permanent=False,
        )
        self.click_ax_center(m)

        cid = m.cb.click.attach.mark(
            radius=500000, shape="geod_circles", fc="none", ec="k", n=6, permanent=True
        )

        self.click_ax_center(m)

        cid = m.cb.click.attach.mark(
            radius=500000,
            shape="geod_circles",
            fc="none",
            ec="m",
            n=100,
            permanent=False,
        )

        self.click_ax_center(m)

        cid = m.cb.click.attach.mark(
            fc=(1, 0, 0, 0.5), ec="k", n=100, permanent=False, buffer=15
        )

        self.click_ax_center(m)
        plt.close("all")

        # ---------- test as PICK callback
        m = self.create_basic_map()
        cid = m.cb.pick.attach.mark()

        self.click_ax_center(m)
        m.cb.pick.remove(cid)

        cid = m.cb.pick.attach.mark(
            radius=400000,
            radius_crs=3857,
            shape="rectangles",
            fc="r",
            ec="g",
            permanent=False,
        )
        self.click_ax_center(m)

        cid = m.cb.pick.attach.mark(
            radius=500000, shape="geod_circles", fc="none", ec="k", n=6, permanent=True
        )

        self.click_ax_center(m)

        cid = m.cb.pick.attach.mark(
            radius=500000,
            shape="geod_circles",
            fc="none",
            ec="m",
            n=100,
            permanent=False,
        )

        self.click_ax_center(m)

        cid = m.cb.pick.attach.mark(
            fc=(1, 0, 0, 0.5), ec="k", n=100, permanent=False, buffer=15
        )

        self.click_ax_center(m)
        plt.close("all")

    def test_peek_layer(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()

        m2 = m.new_layer(copy_data_specs=True)
        m2.plot_map(layer=2, cmap="Reds")

        cid = m.cb.click.attach.peek_layer(layer=2)
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer=2, how="left")
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer=2, how="right")
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer=2, how="top")
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(
            layer=2, how="bottom", hatch="/////", ec="g", lw=4
        )
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer=2, how=(0.25))
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(
            layer=2, how=(0.25, 0.25), hatch="/////", ec="g", lw=4
        )
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        plt.close("all")

    def test_clear_annotations(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()

        m.add_annotation(xy=(20, 20))
        self.assertTrue(len(m.cb.click.get.permanent_annotations) == 1)

        cid = m.cb.click.attach.clear_annotations()
        self.click_ax_center(m)
        self.assertTrue(len(m.cb.click.get.permanent_annotations) == 0)

        m.cb.click.remove(cid)

        plt.close("all")

    def test_clear_markers(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()

        m.add_marker(xy=(20, 20))
        self.assertTrue(len(m.cb.click.get.permanent_markers) == 1)

        cid = m.cb.click.attach.clear_markers()
        self.click_ax_center(m)
        self.assertTrue(m.cb.click.get.permanent_markers is None)

        m.cb.click.remove(cid)
        plt.close("all")

    def test_plot(self):
        m = self.create_basic_map()
        cid = m.cb.pick.attach.plot(precision=2)
        self.click_ax_center(m)
        self.click_ax_center(m, 20, 20)
        self.click_ax_center(m, 50, 50)
        m.cb.pick.remove(cid)

        cid = m.cb.pick.attach.plot(x_index="ID", ls="--", lw=0.5, marker="*")
        self.click_ax_center(m)
        self.click_ax_center(m, 20, 20)
        self.click_ax_center(m, 50, 50)

        m.cb.pick.remove(cid)
        plt.close("all")

    def test_load(self):

        db = self.data

        m = self.create_basic_map()
        m.cb.pick.attach.get_values()

        cid = m.cb.pick.attach.load(database=db, load_method="xs")

        self.assertTrue(m.cb.pick.get.picked_object is None)

        self.click_ax_center(m)
        ID = m.cb.pick.get.picked_vals["ID"]

        self.assertTrue(all(m.cb.pick.get.picked_object == self.data.loc[ID[0]]))

        m.cb.pick.remove(cid)

        def loadmethod(db, ID):
            return db.loc[ID].lon

        cid = m.cb.pick.attach.load(database=db, load_method=loadmethod)
        self.click_ax_center(m)

        self.assertTrue(m.cb.pick.get.picked_object == self.data.loc[ID[0]].lon)

        m.cb.pick.remove(cid)
        plt.close("all")

    def test_switch_layer(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()

        m2 = m.new_layer(copy_data_specs=True)

        m2.plot_map(layer=2, cmap="Reds")

        cid0 = m.cb.keypress.attach.switch_layer(layer=0, key="0")
        cid1 = m.cb.keypress.attach.switch_layer(layer=2, key="2")

        m.figure.f.canvas.key_press_event("2")
        m.figure.f.canvas.key_release_event("2")
        m.BM._bg_layer == 2

        m.figure.f.canvas.key_press_event("0")
        m.figure.f.canvas.key_release_event("0")
        m.BM._bg_layer == 0

        m.cb.keypress.remove(cid0)
        m.cb.keypress.remove(cid1)
        plt.close("all")

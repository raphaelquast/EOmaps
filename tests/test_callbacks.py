# mpl.rcParams["toolbar"] = "None"

import unittest
from itertools import product
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from eomaps import Maps

from matplotlib.backend_bases import MouseEvent, KeyEvent

# copy of depreciated matplotlib function
def button_press_event(canvas, x, y, button, dblclick=False, guiEvent=None):
    canvas._button = button
    s = "button_press_event"
    mouseevent = MouseEvent(
        s, canvas, x, y, button, canvas._key, dblclick=dblclick, guiEvent=guiEvent
    )
    canvas.callbacks.process(s, mouseevent)


# copy of depreciated matplotlib function
def button_release_event(canvas, x, y, button, guiEvent=None):
    s = "button_release_event"
    event = MouseEvent(s, canvas, x, y, button, canvas._key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)
    canvas._button = None


def key_press_event(canvas, key, guiEvent=None):
    s = "key_press_event"
    event = KeyEvent(s, canvas, key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)


def key_release_event(canvas, key, guiEvent=None):
    s = "key_release_event"
    event = KeyEvent(s, canvas, key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)
    canvas._key = None


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
        m.f.canvas.draw()

        return m

    def get_ax_center(self, ax):
        return

    def click_ax_center(self, m, dx=0, dy=0, release=True):
        ax = m.ax
        cv = m.f.canvas
        x, y = (ax.bbox.x0 + ax.bbox.x1) / 2, (ax.bbox.y0 + ax.bbox.y1) / 2

        button_press_event(cv, x + dx, y + dy, 1, False)
        if release:
            button_release_event(cv, x + dx, y + dy, 1, False)

    def click_ID(self, m, ID, release=True):
        cv = m.f.canvas
        x, y = m.ax.transData.transform((self.data.lon[ID], self.data.lat[ID]))
        button_press_event(cv, x, y, 1, False)
        if release:
            button_release_event(cv, x, y, 1, False)

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
        for n, cpick, relpick, r in product(
            [1, 5], [True, False], [True, False], ["10", 12.65]
        ):

            with self.subTest(
                n=n,
                consecutive_pick=cpick,
                pick_relative_to_closest=relpick,
                search_radius=r,
            ):
                m = self.create_basic_map()
                m.cb.pick.set_props(
                    n=n,
                    consecutive_pick=cpick,
                    pick_relative_to_closest=relpick,
                    search_radius=r,
                )

                cid = m.cb.pick.attach.get_values()
                m.cb.pick.attach.annotate()
                m.cb.click.attach.mark(radius=0.1)

                self.click_ID(m, 1225)

                if n == 1:
                    self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 1)
                    self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 1)
                    self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 1)

                    self.assertTrue(m.cb.pick.get.picked_vals["ID"][0] == 1225)

                elif n == 5:
                    if cpick is True:
                        self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 5)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 5)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 5)
                    else:
                        self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 1)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 1)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 1)
                        if relpick is True:
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["ID"][0],
                                    np.array([1225, 1275, 1175, 1224, 1226]),
                                )
                            )
                        else:
                            # TODO this might be failing irregularly
                            # (figure size, extent, dpi etc. might have an impact)

                            # check only closest point for now
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["ID"][0][0],
                                    np.array([1225, 1275, 1175, 1224, 1325][0]),
                                )
                            )

                # click on another pixel
                self.click_ID(m, 317)

                if n == 1:
                    self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 2)
                    self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 2)
                    self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 2)

                    self.assertTrue(m.cb.pick.get.picked_vals["ID"][1] == 317)

                elif n == 5:
                    if cpick is True:
                        self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 10)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 10)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 10)
                    else:
                        self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 2)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 2)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 2)

                        if relpick is True:
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["ID"][1],
                                    np.array([317, 367, 267, 316, 417]),
                                )
                            )
                        else:
                            # TODO this might be failing irregularly
                            # (figure size, extent, dpi etc. might have an impact)

                            # check only closest point for now
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["ID"][1][0],
                                    np.array([317, 367, 267, 316, 417][0]),
                                )
                            )

                m.cb.pick.remove(cid)
                plt.close("all")

    def test_print_to_console(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()
        cid = m.cb.click.attach.print_to_console()

        self.click_ax_center(m)
        m.cb.click.remove(cid)
        plt.close("all")

        # ---------- test as PICK callback
        for n, cpick, relpick, r in product(
            [1, 5], [True, False], [True, False], ["10", 12.65]
        ):

            with self.subTest(
                n=n,
                consecutive_pick=cpick,
                pick_relative_to_closest=relpick,
                search_radius=r,
            ):

                # ---------- test as CLICK callback
                m = self.create_basic_map()
                m.cb.pick.set_props(
                    n=n,
                    consecutive_pick=cpick,
                    pick_relative_to_closest=relpick,
                    search_radius=r,
                )
                cid = m.cb.pick.attach.print_to_console()

                self.click_ax_center(m)
                m.cb.pick.remove(cid)
                plt.close("all")

    def test_annotate(self):

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
        plt.close("all")

        # ---------- test as PICK callback
        for n, cpick, relpick, r in product(
            [1, 5], [True, False], [True, False], ["10", 12.65]
        ):

            with self.subTest(
                n=n,
                consecutive_pick=cpick,
                pick_relative_to_closest=relpick,
                search_radius=r,
            ):

                # ---------- test as CLICK callback
                m = self.create_basic_map()
                m.cb.pick.set_props(
                    n=n,
                    consecutive_pick=cpick,
                    pick_relative_to_closest=relpick,
                    search_radius=r,
                )

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

        # test different pick-properties
        for n, cpick, relpick, r in product(
            [1, 5], [True, False], [True, False], ["10", 12.65]
        ):

            with self.subTest(
                n=n,
                consecutive_pick=cpick,
                pick_relative_to_closest=relpick,
                search_radius=r,
            ):

                m = self.create_basic_map()
                m.cb.pick.set_props(
                    n=n,
                    consecutive_pick=cpick,
                    pick_relative_to_closest=relpick,
                    search_radius=r,
                )

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
                    radius=500000,
                    shape="geod_circles",
                    fc="none",
                    ec="k",
                    n=6,
                    permanent=True,
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

        cid = m.cb.click.attach.peek_layer(layer=2, how="full")
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
        m.cb.click.attach.annotate(permanent=True)
        self.click_ax_center(m)
        self.assertTrue(len(m.cb.click.get.permanent_annotations) == 1)

        cid = m.cb.click.attach.clear_annotations()
        self.click_ax_center(m)
        self.assertTrue(len(m.cb.click.get.permanent_annotations) == 0)

        m.cb.click.remove(cid)

        plt.close("all")

    def test_clear_markers(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()
        m.cb.click.attach.mark(permanent=True)
        self.click_ax_center(m)
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
        for n, cpick, relpick, r in product(
            [1, 5], [True, False], [True, False], ["10", 12.65]
        ):

            with self.subTest(
                n=n,
                consecutive_pick=cpick,
                pick_relative_to_closest=relpick,
                search_radius=r,
            ):

                db = self.data

                m = self.create_basic_map()
                m.cb.pick.attach.get_values()

                cid = m.cb.pick.attach.load(database=db, load_method="xs")

                self.assertTrue(m.cb.pick.get.picked_object is None)

                self.click_ax_center(m)
                ID = m.cb.pick.get.picked_vals["ID"]

                self.assertTrue(
                    all(m.cb.pick.get.picked_object == self.data.loc[ID[0]])
                )

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

        cid0 = m.all.cb.keypress.attach.switch_layer(layer="base", key="0")
        cid1 = m.all.cb.keypress.attach.switch_layer(layer="2", key="2")

        # a callback only active on the "base" layer
        cid3 = m.cb.keypress.attach.switch_layer(layer="3", key="3")

        # switch to layer 2
        key_press_event(m.f.canvas, "2")
        key_release_event(m.f.canvas, "2")
        self.assertTrue(m.BM._bg_layer == "2")

        # the 3rd callback should not trigger
        key_press_event(m.f.canvas, "3")
        key_release_event(m.f.canvas, "3")
        self.assertTrue(m.BM._bg_layer == "2")

        # switch to the "base" layer
        key_press_event(m.f.canvas, "0")
        key_release_event(m.f.canvas, "0")
        self.assertTrue(m.BM._bg_layer == "base")

        # now the 3rd callback should trigger
        key_press_event(m.f.canvas, "3")
        key_release_event(m.f.canvas, "3")
        self.assertTrue(m.BM._bg_layer == "3")

        m.all.cb.keypress.remove(cid0)
        m.all.cb.keypress.remove(cid1)
        m.cb.keypress.remove(cid3)
        plt.close("all")

    def test_make_dataset_pickable(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()

        m2 = m.new_layer(copy_data_specs=True)

        # adding pick callbacks is only possible after plotting data
        with self.assertRaises(AssertionError):
            m2.cb.pick.attach.annotate()

        m2.make_dataset_pickable()
        m2.cb.pick.attach.annotate()
        m2.cb.pick.attach.mark(fc="r", ec="g", lw=2, ls="--")
        m2.cb.pick.attach.print_to_console()
        m2.cb.pick.attach.get_values()

        self.click_ID(m2, 1225)

        self.assertEqual(len(m2.cb.pick.get.picked_vals["pos"]), 1)
        self.assertEqual(len(m2.cb.pick.get.picked_vals["ID"]), 1)
        self.assertEqual(len(m2.cb.pick.get.picked_vals["val"]), 1)
        self.assertTrue(m2.cb.pick.get.picked_vals["ID"][0] == 1225)
        plt.close("all")

    def test_keypress_callbacks_for_any_key(self):
        m = self.create_basic_map()
        m.new_layer("0")
        m.new_layer("1")

        def cb(key):
            m.show_layer(key)

        m.all.cb.keypress.attach(cb, key=None)

        key_press_event(m.f.canvas, "0")
        key_release_event(m.f.canvas, "0")
        self.assertTrue(m.BM._bg_layer == "0")

        key_press_event(m.f.canvas, "1")
        key_release_event(m.f.canvas, "1")
        self.assertTrue(m.BM._bg_layer == "1")
        plt.close("all")

    def test_geodataframe_contains_picking(self):
        m = Maps()
        m.show()  # do this to make sure transforms are correctly set
        gdf = m.add_feature.cultural.admin_0_countries.get_gdf(scale=110)

        m.add_gdf(gdf, column="NAME", picker_name="col", pick_method="contains")

        m.add_gdf(gdf, picker_name="nocol", pick_method="contains")

        def customcb(picked_vals, val, **kwargs):
            picked_vals.append(val)

        picked_vals_col = []
        picked_vals_nocol = []

        m.cb.pick["col"].attach.annotate()
        m.cb.pick["col"].attach(customcb, picked_vals=picked_vals_col)
        m.cb.pick__col.attach.highlight_geometry(fc="r", ec="g")

        m.cb.pick["nocol"].attach.annotate()
        m.cb.pick["nocol"].attach(customcb, picked_vals=picked_vals_nocol)
        m.cb.pick__nocol.attach.highlight_geometry(fc="r", ec="g")

        # evaluate pick position AFTER plotting geodataframes since the plot
        # extent might have changed!
        pickid = 50
        clickpt = gdf.centroid[pickid]
        clickxy = m.ax.transData.transform((clickpt.x, clickpt.y))

        button_press_event(m.f.canvas, *clickxy, 1)
        button_release_event(m.f.canvas, *clickxy, 1)

        self.assertTrue(picked_vals_col[0] == gdf.NAME.loc[pickid])
        self.assertTrue(picked_vals_nocol[0] is None)
        plt.close("all")

    def test_geodataframe_centroid_picking(self):
        m = Maps()
        m.redraw()  # do this to make sure transforms are correctly set
        gdf = m.add_feature.cultural.populated_places.get_gdf(scale=110)

        m.add_gdf(gdf, column="NAME", picker_name="col", pick_method="centroids")

        m.add_gdf(
            gdf,
            fc="none",
            ec="k",
            markersize=10,
            picker_name="nocol",
            pick_method="centroids",
        )

        def customcb(picked_vals, val, **kwargs):
            picked_vals.append(val)

        picked_vals_col = []
        picked_vals_nocol = []

        m.cb.pick["col"].attach.annotate()
        m.cb.pick["col"].attach(customcb, picked_vals=picked_vals_col)
        m.cb.pick__col.attach.highlight_geometry(fc="r", ec="g")

        m.cb.pick["nocol"].attach.annotate(xytext=(20, -20))
        m.cb.pick["nocol"].attach(customcb, picked_vals=picked_vals_nocol)
        m.cb.pick__nocol.attach.highlight_geometry(fc="r", ec="g")

        # evaluate pick position AFTER plotting geodataframes since the plot
        # extent might have changed!
        pickid = 50
        clickpt = gdf.centroid[pickid]
        clickxy = m.ax.transData.transform((clickpt.x, clickpt.y))

        button_press_event(m.f.canvas, *clickxy, 1)
        button_release_event(m.f.canvas, *clickxy, 1)

        self.assertTrue(picked_vals_col[0] == gdf.NAME.loc[pickid])
        self.assertTrue(picked_vals_nocol[0] is None)
        plt.close("all")

# mpl.rcParams["toolbar"] = "None"

import unittest
from itertools import product
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.spatial import KDTree

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
            np.linspace(-50, 50, 50), np.linspace(-25, 25, 60)
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

        # get coordinates in plot-crs
        plotx, ploty = m._transf_lonlat_to_plot.transform(
            self.data.lon[ID], self.data.lat[ID]
        )

        # get coordinates in figure points
        x, y = m.ax.transData.transform((plotx, ploty))
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

        df = self.data
        x1d = df["lon"].values
        y1d = df["lat"].values
        data1d = df["value"].values

        data2d = self.data.set_index(["lon", "lat"]).unstack("lon")
        x1d2d, y1d2d = data2d.columns.get_level_values(1).values, data2d.index.values
        data2d = data2d["value"].values

        x2d, y2d = np.meshgrid(x1d2d, y1d2d)

        data_selections = [
            dict(data=self.data, x="lon", y="lat", test="pandas"),
            dict(data=data1d, x=x1d, y=y1d, test="1d"),
            dict(data=data2d.T, x=x1d2d, y=y1d2d, test="1d2d"),
            dict(data=data2d, x=x2d, y=y2d, test="2d"),
        ]

        # ---------- test as PICK callback
        # for ID, n, cpick, relpick, r, data, plotcrs in product(
        #     [1225, 350],
        #     [1, 5],
        #     [True, False],
        #     [True, False],
        #     ["10", 12.65],
        #     data_selections,
        #     [4326, Maps.CRS.Mollweide()],
        # ):
        for ID, n, cpick, relpick, r, data, plotcrs in product(
            [1225],
            [5],
            [True],
            [True],
            ["10", None],
            data_selections,
            [4326, Maps.CRS.Mollweide()],
        ):

            # note r is defined in units of the plot crs!
            if r is None:
                if plotcrs == 4326:
                    r = 12.65
                else:
                    r = 1e6

            with self.subTest(
                n=n,
                consecutive_pick=cpick,
                pick_relative_to_closest=relpick,
                search_radius=r,
                data=data["test"],
            ):
                print(
                    "--------------- TESTING:", ID, n, cpick, relpick, r, data["test"]
                )

                m = Maps(crs=plotcrs)
                m.set_data(**{key: val for key, val in data.items() if key != "test"})
                m.plot_map()

                # identify x-y in plot_crs
                ref_x, ref_y = m._transf_lonlat_to_plot.transform(
                    *self.data.loc[ID][["lon", "lat"]]
                )

                m.cb.pick.set_props(
                    n=n,
                    consecutive_pick=cpick,
                    pick_relative_to_closest=relpick,
                    search_radius=r,
                )

                cid = m.cb.pick.attach.get_values()
                m.cb.pick.attach.print_to_console()
                m.cb.click.attach.mark(radius=0.1)
                m.f.canvas.draw()  # make sure figure is drawn before testing
                self.click_ID(m, ID)

                if n == 1:
                    self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 1)
                    self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 1)
                    self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 1)

                    self.assertTrue(m.cb.pick.get.picked_vals["ID"][0] == ID)
                    self.assertTrue(
                        np.allclose(
                            m.cb.pick.get.picked_vals["val"][0],
                            self.data.loc[ID]["value"],
                        )
                    )
                    self.assertTrue(
                        np.allclose(m.cb.pick.get.picked_vals["pos"][0][0], ref_x)
                    )
                    self.assertTrue(
                        np.allclose(m.cb.pick.get.picked_vals["pos"][0][1], ref_y)
                    )

                elif n == 5:
                    # get n nearest neighbours from pandas dataframe
                    tree = KDTree(self.data[["lon", "lat"]].values)
                    d, pickids = tree.query(
                        self.data.loc[ID][["lon", "lat"]].values, k=n
                    )
                    pickids.sort()  # sort found IDs since KDtree sorting might be different
                    ref_x, ref_y = m._transf_lonlat_to_plot.transform(
                        *self.data.loc[pickids][["lon", "lat"]].values.T
                    )

                    if cpick is True:
                        self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 5)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 5)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 5)
                    else:
                        self.assertEqual(len(m.cb.pick.get.picked_vals["pos"]), 1)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["ID"]), 1)
                        self.assertEqual(len(m.cb.pick.get.picked_vals["val"]), 1)
                        if relpick is True:
                            # sort found IDs to make sure sorting is same
                            # as reference IDs
                            sortp = np.argsort(m.cb.pick.get.picked_vals["ID"][0])

                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["ID"][0][sortp],
                                    pickids,
                                )
                            )
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["val"][0][sortp],
                                    self.data.loc[pickids]["value"].values,
                                )
                            )
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["pos"][0][0][sortp],
                                    ref_x,
                                )
                            )
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["pos"][0][1][sortp],
                                    ref_y,
                                )
                            )

                        else:
                            # TODO this might be failing irregularly
                            # (figure size, extent, dpi etc. might have an impact)

                            # sort found IDs to make sure sorting is same
                            # as reference IDs
                            sortp = np.argsort(m.cb.pick.get.picked_vals["ID"][0])

                            # check only closest point for now
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["ID"][0][sortp][0],
                                    pickids[0],
                                )
                            )
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["val"][0][sortp][0],
                                    self.data.loc[pickids]["value"].values[0],
                                )
                            )
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["pos"][0][0][sortp][0],
                                    ref_x[0],
                                )
                            )
                            self.assertTrue(
                                np.allclose(
                                    m.cb.pick.get.picked_vals["pos"][0][1][sortp][0],
                                    ref_y[0],
                                )
                            )

                m.cb.pick.remove(cid)
                plt.close("all")

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

        m2 = m.new_layer(inherit_data=True)
        m2.plot_map(layer="2", cmap="Reds")

        m.add_feature.preset.ocean(layer="ocean")

        cid = m.cb.click.attach.peek_layer(layer="2")
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer="2", how="left")
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer=["2", "ocean"], how="right")
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer=["2", ("ocean", 0.6)], how="top")
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(
            layer="2", how="bottom", hatch="/////", ec="g", lw=4
        )
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer="2", how="full")
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(layer="2", how=(0.25))
        self.click_ax_center(m)
        m.cb.click.remove(cid)

        cid = m.cb.click.attach.peek_layer(
            layer="2", how=(0.25, 0.25), hatch="/////", ec="g", lw=4
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
        cid = m.cb.click.attach.mark(permanent=True)
        self.click_ax_center(m)
        self.assertTrue(len(m.cb.click.get.permanent_markers) == 1)
        m.cb.click.remove(cid)

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

    def test_overlay_layer(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()
        m_a = m.new_layer("A")
        m_b = m.new_layer("B")

        cid0 = m.all.cb.keypress.attach.overlay_layer(layer="A", key="0")
        cid1 = m.all.cb.keypress.attach.overlay_layer(layer=("B", 0.5), key="1")
        cid2 = m.all.cb.keypress.attach.overlay_layer(layer=["A", ("B", 0.5)], key="2")

        init_layer = m.layer

        key_press_event(m.f.canvas, "0")
        key_release_event(m.f.canvas, "0")
        self.assertTrue(m.BM._bg_layer == m.BM._get_combined_layer_name(m.layer, "A"))
        key_press_event(m.f.canvas, "0")
        key_release_event(m.f.canvas, "0")
        self.assertTrue(m.BM._bg_layer == m.layer)

        key_press_event(m.f.canvas, "1")
        key_release_event(m.f.canvas, "1")
        self.assertTrue(
            m.BM._bg_layer == m.BM._get_combined_layer_name(m.layer, ("B", 0.5))
        )
        key_press_event(m.f.canvas, "1")
        key_release_event(m.f.canvas, "1")
        self.assertTrue(m.BM._bg_layer == m.layer)

        key_press_event(m.f.canvas, "2")
        key_release_event(m.f.canvas, "2")
        self.assertTrue(
            m.BM._bg_layer == m.BM._get_combined_layer_name(m.layer, "A", ("B", 0.5))
        )
        key_press_event(m.f.canvas, "2")
        key_release_event(m.f.canvas, "2")
        self.assertTrue(m.BM._bg_layer == m.layer)

    def test_switch_layer(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()

        m2 = m.new_layer(inherit_data=True)
        m3 = m.new_layer("3")
        m2.plot_map(layer="2", cmap="Reds")

        cid0 = m.all.cb.keypress.attach.switch_layer(layer="base", key="0")
        cid1 = m.all.cb.keypress.attach.switch_layer(layer="2", key="2")

        # a callback only active on the "base" layer
        cid3 = m.cb.keypress.attach.switch_layer(layer=["2", ("3", 0.5)], key="3")

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
        self.assertTrue(
            m.BM._bg_layer == m.BM._get_combined_layer_name("2", ("3", 0.5))
        )

        m.all.cb.keypress.remove(cid0)
        m.all.cb.keypress.remove(cid1)
        m.cb.keypress.remove(cid3)
        plt.close("all")

    def test_make_dataset_pickable(self):
        # ---------- test as CLICK callback
        m = self.create_basic_map()

        m2 = m.new_layer(inherit_data=True)

        # in EOmaps v6 its now possible to attach callbacks before
        # plotting the data (they will only start to trigger once the
        # data is plotted)
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
        gdf = m.add_feature.cultural.admin_0_countries.get_gdf(scale=110)

        m.add_gdf(gdf, column="NAME", picker_name="col", pick_method="contains")

        m.add_gdf(gdf, picker_name="nocol", pick_method="contains", fc="none")

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
        m.f.canvas.draw()  # make sure figure is drawn before testing

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
        m.f.canvas.draw()  # do this to make sure transforms are correctly set

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

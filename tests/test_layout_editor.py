import matplotlib as mpl

mpl.rcParams["toolbar"] = "None"

import unittest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from eomaps import Maps, MapsGrid


class TestLayoutEditor(unittest.TestCase):
    def setUp(self):
        pass

    def test_layout_editor(self):
        # %%
        lon, lat = np.meshgrid(np.linspace(20, 50, 50), np.linspace(20, 50, 50))
        data = pd.DataFrame(dict(lon=lon.flat, lat=lat.flat, value=1))

        mg = MapsGrid()
        mg.set_data(data)
        mg.plot_map()
        mg.add_colorbar()

        initial_layout = mg.get_layout()

        cv = mg.f.canvas

        # activate draggable axes
        cv.key_press_event("alt+l")
        cv.key_release_event("alt+l")

        # ################ check handling axes

        # click on top left axes
        x0 = (mg.m_0_0.figure.ax.bbox.x1 + mg.m_0_0.figure.ax.bbox.x0) / 2
        y0 = (mg.m_0_0.figure.ax.bbox.y1 + mg.m_0_0.figure.ax.bbox.y0) / 2
        cv.button_press_event(x0, y0, 1, False)

        # move the axes to the center
        x1 = (mg.m_0_0.figure.f.bbox.x1 + mg.m_0_0.figure.f.bbox.x0) / 2
        y1 = (mg.m_0_0.figure.f.bbox.y1 + mg.m_0_0.figure.f.bbox.y0) / 2
        cv.motion_notify_event(x1, y1, False)

        # release the mouse
        cv.button_release_event(0, 0, 1, False)

        # resize the axis
        cv.scroll_event(x1, y1, 10)

        # click on bottom right
        x2 = (mg.m_1_1.figure.ax.bbox.x1 + mg.m_1_1.figure.ax.bbox.x0) / 2
        y2 = (mg.m_1_1.figure.ax.bbox.y1 + mg.m_1_1.figure.ax.bbox.y0) / 2
        cv.button_press_event(x2, y2, 1, False)

        # move the axes to the top left
        cv.motion_notify_event(x0, y0, False)

        # release the mouse
        cv.button_release_event(0, 0, 1, False)

        # resize the axis
        cv.scroll_event(x1, y1, -10)

        # ------------- check keystrokes

        # click on bottom left axis
        x3 = (mg.m_1_0.figure.ax.bbox.x1 + mg.m_1_0.figure.ax.bbox.x0) / 2
        y3 = (mg.m_1_0.figure.ax.bbox.y1 + mg.m_1_0.figure.ax.bbox.y0) / 2
        cv.button_press_event(x3, y3, 1, False)

        cv.key_press_event("left")
        cv.key_press_event("right")
        cv.key_press_event("up")
        cv.key_press_event("down")

        # release the mouse
        cv.button_release_event(0, 0, 1, False)

        # ################ check handling colorbars

        # click on top left colorbar
        x4 = (mg.m_1_0.figure.ax_cb.bbox.x1 + mg.m_1_0.figure.ax_cb.bbox.x0) / 2
        y4 = (mg.m_1_0.figure.ax_cb.bbox.y1 + mg.m_1_0.figure.ax_cb.bbox.y0) / 2
        cv.button_press_event(x4, y4, 1, False)

        # move it around with keys
        cv.key_press_event("left")
        cv.key_press_event("right")
        cv.key_press_event("up")
        cv.key_press_event("down")

        # move it around with the mouse
        cv.motion_notify_event(x0, y0, False)

        # resize it
        cv.scroll_event(x1, y1, 10)

        # release the mouse
        cv.button_release_event(0, 0, 1, False)

        # ------ test re-showing axes on click
        # click on bottom right histogram
        x5 = (
            mg.m_1_1.figure.ax_cb_plot.bbox.x1 + mg.m_1_1.figure.ax_cb_plot.bbox.x0
        ) / 2
        y5 = (
            mg.m_1_1.figure.ax_cb_plot.bbox.y1 + mg.m_1_1.figure.ax_cb_plot.bbox.y0
        ) / 2
        cv.button_press_event(x5, y5, 1, False)

        # click on bottom right colorbar
        x6 = (mg.m_1_1.figure.ax_cb.bbox.x1 + mg.m_1_1.figure.ax_cb.bbox.x0) / 2
        y6 = (mg.m_1_1.figure.ax_cb.bbox.y1 + mg.m_1_1.figure.ax_cb.bbox.y0) / 2
        cv.button_press_event(x6, y6, 1, False)

        # deactivate draggable axes
        cv.key_press_event("alt+l")
        cv.key_release_event("alt+l")

        # save the new layout
        new_layout = mg.get_layout()

        # restore the initial layout
        mg.apply_layout(initial_layout)
        restored_layout = mg.get_layout()
        for key, val in restored_layout.items():
            # check if all positions have been properly restored
            self.assertTrue(np.allclose(val, initial_layout[key]))

        # restore the new layout
        mg.apply_layout(new_layout)
        restored_layout = mg.get_layout()
        for key, val in restored_layout.items():
            # check if all positions have been properly restored
            self.assertTrue(np.allclose(val, new_layout[key]))

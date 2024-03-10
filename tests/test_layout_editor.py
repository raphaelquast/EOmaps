import matplotlib as mpl

mpl.rcParams["toolbar"] = "None"

import unittest
import numpy as np
import pandas as pd

from eomaps import MapsGrid

from matplotlib.backend_bases import MouseEvent, KeyEvent


def button_press_event(canvas, x, y, button, dblclick=False, guiEvent=None):
    canvas._button = button
    s = "button_press_event"
    mouseevent = MouseEvent(
        s, canvas, x, y, button, canvas._key, dblclick=dblclick, guiEvent=guiEvent
    )
    canvas.callbacks.process(s, mouseevent)


def button_release_event(canvas, x, y, button, guiEvent=None):
    s = "button_release_event"
    event = MouseEvent(s, canvas, x, y, button, canvas._key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)
    canvas._button = None


def motion_notify_event(canvas, x, y, guiEvent=None):
    s = "motion_notify_event"
    event = MouseEvent(s, canvas, x, y, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)


def scroll_event(canvas, x, y, step, guiEvent=None):
    s = "scroll_event"
    event = MouseEvent(s, canvas, x, y, step=step, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)


def key_press_event(canvas, key, guiEvent=None):
    s = "key_press_event"
    event = KeyEvent(s, canvas, key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)


def key_release_event(canvas, key, guiEvent=None):
    s = "key_release_event"
    event = KeyEvent(s, canvas, key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)
    canvas._key = None


class TestLayoutEditor(unittest.TestCase):
    def setUp(self):
        pass

    def test_layout_editor(self):
        # %%
        lon, lat = np.meshgrid(np.linspace(20, 50, 50), np.linspace(20, 50, 50))
        data = pd.DataFrame(dict(lon=lon.flat, lat=lat.flat, value=lon.flat))
        data.set_index(["lon", "lat"], inplace=True)

        mg = MapsGrid()
        mg.set_data(data)
        mg.plot_map()
        mg.add_colorbar()

        initial_layout = mg.get_layout()

        cv = mg.f.canvas

        # activate draggable axes
        key_press_event(cv, "alt+l")
        key_release_event(cv, "alt+l")

        # ################ check handling axes

        # click on top left axes
        x0 = (mg.m_0_0.ax.bbox.x1 + mg.m_0_0.ax.bbox.x0) / 2
        y0 = (mg.m_0_0.ax.bbox.y1 + mg.m_0_0.ax.bbox.y0) / 2
        button_press_event(cv, x0, y0, 1, False)

        # move the axes to the center
        x1 = (mg.m_0_0.f.bbox.x1 + mg.m_0_0.f.bbox.x0) / 2
        y1 = (mg.m_0_0.f.bbox.y1 + mg.m_0_0.f.bbox.y0) / 2
        motion_notify_event(cv, x1, y1, False)

        # release the mouse
        button_release_event(cv, 0, 0, 1, False)

        # resize the axis
        scroll_event(cv, x1, y1, 10)

        # click on bottom right
        x2 = (mg.m_1_1.ax.bbox.x1 + mg.m_1_1.ax.bbox.x0) / 2
        y2 = (mg.m_1_1.ax.bbox.y1 + mg.m_1_1.ax.bbox.y0) / 2
        button_press_event(cv, x2, y2, 1, False)

        # move the axes to the top left
        motion_notify_event(cv, x0, y0, False)

        # release the mouse
        button_release_event(cv, 0, 0, 1, False)

        # resize the axis
        scroll_event(cv, x1, y1, -10)

        # ------------- check keystrokes

        # click on bottom left axis
        x3 = (mg.m_1_0.ax.bbox.x1 + mg.m_1_0.ax.bbox.x0) / 2
        y3 = (mg.m_1_0.ax.bbox.y1 + mg.m_1_0.ax.bbox.y0) / 2
        button_press_event(cv, x3, y3, 1, False)

        key_press_event(cv, "left")
        key_press_event(cv, "right")
        key_press_event(cv, "up")
        key_press_event(cv, "down")

        # release the mouse
        button_release_event(cv, 0, 0, 1, False)

        # ################ check handling colorbars

        # click on top left colorbar
        x4 = (mg.m_1_0.colorbar.ax_cb.bbox.x1 + mg.m_1_0.colorbar.ax_cb.bbox.x0) / 2
        y4 = (mg.m_1_0.colorbar.ax_cb.bbox.y1 + mg.m_1_0.colorbar.ax_cb.bbox.y0) / 2
        button_press_event(cv, x4, y4, 1, False)

        # move it around with keys
        key_press_event(cv, "left")
        key_press_event(cv, "right")
        key_press_event(cv, "up")
        key_press_event(cv, "down")

        # move it around with the mouse
        motion_notify_event(cv, x0, y0, False)

        # resize it
        scroll_event(cv, x1, y1, 10)

        # release the mouse
        button_release_event(cv, 0, 0, 1, False)

        # ------ test re-showing axes on click
        # click on bottom right histogram
        x5 = (
            mg.m_1_1.colorbar.ax_cb_plot.bbox.x1 + mg.m_1_1.colorbar.ax_cb_plot.bbox.x0
        ) / 2
        y5 = (
            mg.m_1_1.colorbar.ax_cb_plot.bbox.y1 + mg.m_1_1.colorbar.ax_cb_plot.bbox.y0
        ) / 2
        button_press_event(cv, x5, y5, 1, False)

        # click on bottom right colorbar
        x6 = (mg.m_1_1.colorbar.ax_cb.bbox.x1 + mg.m_1_1.colorbar.ax_cb.bbox.x0) / 2
        y6 = (mg.m_1_1.colorbar.ax_cb.bbox.y1 + mg.m_1_1.colorbar.ax_cb.bbox.y0) / 2
        button_press_event(cv, x6, y6, 1, False)

        # undo the last 5 events
        nhist = len(mg.parent._layout_editor._history)
        nhist_undone = len(mg.parent._layout_editor._history_undone)
        for i in range(5):
            key_press_event(cv, "ctrl+z")
            self.assertTrue(len(mg.parent._layout_editor._history) == nhist - i - 1)
            self.assertTrue(
                len(mg.parent._layout_editor._history_undone) == nhist_undone + i + 1
            )

        # redo the last 5 events
        nhist = len(mg.parent._layout_editor._history)
        nhist_undone = len(mg.parent._layout_editor._history_undone)
        for i in range(5):
            key_press_event(cv, "ctrl+y")
            self.assertTrue(
                len(mg.parent._layout_editor._history_undone) == nhist_undone - i - 1
            )
            self.assertTrue(len(mg.parent._layout_editor._history) == nhist + i + 1)

        # deactivate draggable axes
        key_press_event(cv, "alt+l")
        key_release_event(cv, "alt+l")

        # check that history has been properly cleared
        nhist = len(mg.parent._layout_editor._history)
        nhist_undone = len(mg.parent._layout_editor._history_undone)
        self.assertTrue(nhist == 0)
        self.assertTrue(nhist_undone == 0)

        # save the new layout
        new_layout = mg.get_layout()

        # restore the initial layout
        mg.apply_layout(initial_layout)
        restored_layout = mg.get_layout()
        for key, val in restored_layout.items():
            # check if all positions have been properly restored
            self.assertTrue(np.allclose(val, initial_layout[key], atol=0.001))

        # restore the new layout
        mg.apply_layout(new_layout)
        restored_layout = mg.get_layout()
        for key, val in restored_layout.items():
            # check if all positions have been properly restored
            print(key, val, new_layout[key])
            self.assertTrue(np.allclose(val, new_layout[key], atol=0.001))

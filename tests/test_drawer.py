import unittest
import numpy as np
from matplotlib.backend_bases import MouseEvent
from eomaps import Maps

# copy of depreciated matplotlib function
def button_press_event(canvas, x, y, button, dblclick=False, guiEvent=None):
    """
    Callback processing for mouse button press events.

    Backend derived classes should call this function on any mouse
    button press.  (*x*, *y*) are the canvas coords ((0, 0) is lower left).
    button and key are as defined in `MouseEvent`.

    This method will call all functions connected to the
    'button_press_event' with a `MouseEvent` instance.
    """
    canvas._button = button
    s = "button_press_event"
    mouseevent = MouseEvent(
        s, canvas, x, y, button, canvas._key, dblclick=dblclick, guiEvent=guiEvent
    )
    canvas.callbacks.process(s, mouseevent)


# copy of depreciated matplotlib function
def button_release_event(canvas, x, y, button, guiEvent=None):
    """
    Callback processing for mouse button release events.

    Backend derived classes should call this function on any mouse
    button release.

    This method will call all functions connected to the
    'button_release_event' with a `MouseEvent` instance.

    Parameters
    ----------
    x : float
        The canvas coordinates where 0=left.
    y : float
        The canvas coordinates where 0=bottom.
    guiEvent
        The native UI event that generated the Matplotlib event.
    """
    s = "button_release_event"
    event = MouseEvent(s, canvas, x, y, button, canvas._key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)
    canvas._button = None


class TestDraw(unittest.TestCase):
    def setUp(self):
        pass

    def click_ax_center(self, m, dx=0, dy=0, release=True, button=1):
        ax = m.ax
        cv = m.f.canvas
        x, y = (ax.bbox.x0 + ax.bbox.x1) / 2, (ax.bbox.y0 + ax.bbox.y1) / 2
        button_press_event(cv, x + dx, y + dy, button, False)
        if release:
            button_release_event(cv, x + dx, y + dy, button, False)

    def test_basic_drawing_capabilities(self):
        m = Maps()
        m.add_feature.preset.coastline()
        m.f.canvas.draw()
        m.draw.rectangle(fc="none", ec="r")
        self.click_ax_center(m)
        self.click_ax_center(m, dx=20, dy=20, button=2)
        self.assertTrue(len(m.draw._artists) == 1)

        m.draw.circle(fc="b", ec="g", alpha=0.5)
        self.click_ax_center(m, dx=50)
        self.click_ax_center(m, dx=20, dy=20, button=2)
        self.assertTrue(len(m.draw._artists) == 2)

        m.draw.polygon(fc="g", ec="b", lw=2)
        for i, j in np.random.randint(0, 100, (20, 2)):
            self.click_ax_center(m, dx=i, dy=j)

        self.click_ax_center(m, dx=20, dy=20, button=2)
        self.assertTrue(len(m.draw._artists) == 3)

        # -----------------------------
        m.new_layer("shapes")
        d = m.draw.new_drawer(layer="shapes")

        d.rectangle(fc="none", ec="r")
        self.click_ax_center(m)
        self.click_ax_center(m, dx=20, dy=20, button=2)
        self.assertTrue(len(d._artists) == 1)

        d.circle(fc="b", ec="g", alpha=0.5)
        self.click_ax_center(m, dx=50)
        self.click_ax_center(m, dx=20, dy=20, button=2)
        self.assertTrue(len(d._artists) == 2)

        d.polygon(fc="g", ec="b", lw=2)
        for i, j in np.random.randint(0, 100, (20, 2)):
            self.click_ax_center(m, dx=i, dy=j)

        self.click_ax_center(m, dx=20, dy=20, button=2)
        self.assertTrue(len(d._artists) == 3)

        m.show_layer("shapes")

        m.draw.remove_last_shape()
        self.assertTrue(len(m.draw._artists) == 2)
        m.draw.remove_last_shape()
        self.assertTrue(len(m.draw._artists) == 1)
        m.draw.remove_last_shape()
        self.assertTrue(len(m.draw._artists) == 0)

        d.remove_last_shape()
        self.assertTrue(len(d._artists) == 2)
        d.remove_last_shape()
        self.assertTrue(len(d._artists) == 1)
        d.remove_last_shape()
        self.assertTrue(len(d._artists) == 0)

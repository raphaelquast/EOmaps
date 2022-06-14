"""
This is a first proove-of-concept on how to implement basic drawing
capabilities in EOmaps.

It is NOT YET MATURE and needs further work before going officially into EOmaps!


The idea is to provide a simple interface to quickly draw geo-coded shapes on a map.


TODO's:
-------
- general concept... what is feasible, what is too much?

- come up with ideas for a proper user-interface
  - how to start/stop/reset a shape
  - how to select shapes
  - undo / redo operations

  - add capabilities to
    - delete shapes on click?
    - move shapes
    - edit shapes

- what basic shapes to provide?  currently there are:
  - rectangle
  - circle
  - polygon


Issues:
-------

It can happen that geopandas silently ignores the crs when writing shapefiles
(in case WKT2 strings are required to represent the crs)
->>

... already reported to geopandas... might take some time to resolve:
https://github.com/geopandas/geopandas/issues/2387

"""

from cartopy import crs as ccrs
import numpy as np
import matplotlib.pyplot as plt

from matplotlib import _blocking_input
from matplotlib.backend_bases import MouseButton
import matplotlib as mpl

from shapely.geometry import Polygon
import geopandas as gpd
from scipy.interpolate import splprep, splev


# This is basically a copy of matplotlib's ginput function adapted to work with EOmaps
# matplotlib's original ginput function is here:
# https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.ginput.html


def ginput(
    m,
    n=1,
    timeout=30,
    show_clicks=True,
    draw_on_drag=True,
    mouse_add=MouseButton.LEFT,
    mouse_pop=MouseButton.RIGHT,
    mouse_stop=MouseButton.MIDDLE,
):
    """
    Blocking call to interact with a figure.
    Wait until the user clicks *n* times on the figure, and return the
    coordinates of each click in a list.
    There are three possible interactions:
    - Add a point.
    - Remove the most recently added point.
    - Stop the interaction and return the points added so far.
    The actions are assigned to mouse buttons via the arguments
    *mouse_add*, *mouse_pop* and *mouse_stop*.
    Parameters
    ----------
    n : int, default: 1
        Number of mouse clicks to accumulate. If negative, accumulate
        clicks until the input is terminated manually.
    timeout : float, default: 30 seconds
        Number of seconds to wait before timing out. If zero or negative
        will never timeout.
    show_clicks : bool, default: True
        If True, show a red cross at the location of each click.
    mouse_add : `.MouseButton` or None, default: `.MouseButton.LEFT`
        Mouse button used to add points.
    mouse_pop : `.MouseButton` or None, default: `.MouseButton.RIGHT`
        Mouse button used to remove the most recently added point.
    mouse_stop : `.MouseButton` or None, default: `.MouseButton.MIDDLE`
        Mouse button used to stop input.
    Returns
    -------
    list of tuples
        A list of the clicked (x, y) coordinates.
    Notes
    -----
    The keyboard can also be used to select points in case your mouse
    does not have one or more of the buttons.  The delete and backspace
    keys act like right clicking (i.e., remove last point), the enter key
    terminates input and any other key (not already used by the window
    manager) selects a point.
    """

    canvas = m.BM.canvas

    clicks = []
    marks = []
    endline = []

    def handler(event):
        if event.name == "close_event":
            canvas.stop_event_loop()
            return

        if (canvas.toolbar is not None) and canvas.toolbar.mode != "":
            return

        is_button = (
            event.name == "button_press_event" or event.name == "motion_notify_event"
        )
        is_key = event.name == "key_press_event"
        # Quit (even if not in infinite mode; this is consistent with
        # MATLAB and sometimes quite useful, but will require the user to
        # test how many points were actually returned before using data).

        if (
            is_button
            and event.button == mouse_stop
            or is_key
            and event.key in ["escape", "enter"]
        ):
            canvas.stop_event_loop()

        # Pop last click.
        elif (
            is_button
            and event.button == mouse_pop
            or is_key
            and event.key in ["backspace", "delete"]
        ):
            if clicks:
                clicks.pop()
                if show_clicks:
                    lastmark = marks.pop()
                    m.BM.remove_artist(lastmark)
                    lastmark.remove()
                    m.BM.update()

                    while len(endline) > 0:
                        el = endline.pop()
                        m.BM.remove_artist(el)
                        el.remove()

        # Add new click.
        elif (
            is_button
            and event.button == mouse_add
            # On macOS/gtk, some keys return None.
            or is_key
            and event.key is not None
        ):
            if event.inaxes:
                while len(endline) > 0:
                    el = endline.pop()
                    m.BM.remove_artist(el)
                    el.remove()

                clicks.append((event.xdata, event.ydata))
                if show_clicks:
                    if len(clicks) < 2:
                        x, y = [event.xdata], [event.ydata]
                    else:
                        x, y = [i[0] for i in clicks], [i[1] for i in clicks]
                    line = mpl.lines.Line2D(x, y, marker="+", color="r")
                    event.inaxes.add_line(line)
                    marks.append(line)

                    m.BM.add_artist(line)

                    if len(clicks) > 2:
                        endline.append(
                            mpl.lines.Line2D(
                                [event.xdata, clicks[0][0]],
                                [event.ydata, clicks[0][1]],
                                color=".5",
                                lw=0.5,
                                ls="--",
                            )
                        )
                        event.inaxes.add_line(endline[-1])

                        m.BM.add_artist(endline[-1])

                    m.BM.update()

        if len(clicks) == n and n > 0:
            canvas.stop_event_loop()

    eventnames = ["button_press_event", "key_press_event", "close_event"]
    if draw_on_drag:
        eventnames.append("motion_notify_event")

    _blocking_input.blocking_input_loop(canvas.figure, eventnames, timeout, handler)

    # Cleanup.
    if plt.fignum_exists(m.figure.f.number):
        for mark in marks + endline:
            m.BM.remove_artist(mark)
            mark.remove()

        m.BM.update()

    return clicks


# This is basically a copy of matplotlib's ginput function adapted to work with EOmaps
# matplotlib's original ginput function is here:
# https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.ginput.html

# draw only a single point and draw a second point on escape
def ginput2(
    m,
    n=1,
    timeout=30,
    show_clicks=True,
    draw_on_drag=True,
    mouse_add=MouseButton.LEFT,
    mouse_pop=MouseButton.RIGHT,
    mouse_stop=MouseButton.MIDDLE,
    movecb=None,
):
    """
    Blocking call to interact with a figure.
    Wait until the user clicks *n* times on the figure, and return the
    coordinates of each click in a list.
    There are three possible interactions:
    - Add a point.
    - Remove the most recently added point.
    - Stop the interaction and return the points added so far.
    The actions are assigned to mouse buttons via the arguments
    *mouse_add*, *mouse_pop* and *mouse_stop*.
    Parameters
    ----------
    n : int, default: 1
        Number of mouse clicks to accumulate. If negative, accumulate
        clicks until the input is terminated manually.
    timeout : float, default: 30 seconds
        Number of seconds to wait before timing out. If zero or negative
        will never timeout.
    show_clicks : bool, default: True
        If True, show a red cross at the location of each click.
    mouse_add : `.MouseButton` or None, default: `.MouseButton.LEFT`
        Mouse button used to add points.
    mouse_pop : `.MouseButton` or None, default: `.MouseButton.RIGHT`
        Mouse button used to remove the most recently added point.
    mouse_stop : `.MouseButton` or None, default: `.MouseButton.MIDDLE`
        Mouse button used to stop input.
    Returns
    -------
    list of tuples
        A list of the clicked (x, y) coordinates.
    Notes
    -----
    The keyboard can also be used to select points in case your mouse
    does not have one or more of the buttons.  The delete and backspace
    keys act like right clicking (i.e., remove last point), the enter key
    terminates input and any other key (not already used by the window
    manager) selects a point.
    """

    canvas = m.BM.canvas

    clicks = []
    marks = []
    endline = []

    def handler(event):
        if event.name == "close_event":
            canvas.stop_event_loop()
            return

        if (canvas.toolbar is not None) and canvas.toolbar.mode != "":
            return

        if event.name == "motion_notify_event":
            if movecb:
                movecb(event, clicks)

        is_button = (
            event.name == "button_press_event" or event.name == "motion_notify_event"
        )
        is_key = event.name == "key_press_event"
        # Quit (even if not in infinite mode; this is consistent with
        # MATLAB and sometimes quite useful, but will require the user to
        # test how many points were actually returned before using data).

        if is_button and event.button == mouse_stop:
            clicks.append((event.xdata, event.ydata))
            canvas.stop_event_loop()
        elif is_key and event.key in ["escape", "enter"]:
            canvas.stop_event_loop()

        # Pop last click.
        elif (
            is_button
            and event.button == mouse_pop
            or is_key
            and event.key in ["backspace", "delete"]
        ):
            if clicks:
                clicks.pop()
                if show_clicks:
                    lastmark = marks.pop()
                    m.BM.remove_artist(lastmark)
                    lastmark.remove()
                    m.BM.update()

                    while len(endline) > 0:
                        el = endline.pop()
                        m.BM.remove_artist(el)
                        el.remove()

        # Add new click.
        elif (
            is_button
            and event.button == mouse_add
            # On macOS/gtk, some keys return None.
            or is_key
            and event.key is not None
        ):
            if len(clicks) >= n - 1:
                print("EOmaps: Use RIGHT-click to remove, and MIDDLE-click to draw.")
                return

            if event.inaxes:
                while len(endline) > 0:
                    el = endline.pop()
                    m.BM.remove_artist(el)
                    el.remove()

                clicks.append((event.xdata, event.ydata))
                if show_clicks:
                    if len(clicks) < 2:
                        x, y = [event.xdata], [event.ydata]
                    else:
                        x, y = [i[0] for i in clicks], [i[1] for i in clicks]
                    line = mpl.lines.Line2D(x, y, marker="+", color="r")
                    event.inaxes.add_line(line)
                    marks.append(line)

                    m.BM.add_artist(line)

                    if len(clicks) > 2:
                        endline.append(
                            mpl.lines.Line2D(
                                [event.xdata, clicks[0][0]],
                                [event.ydata, clicks[0][1]],
                                color=".5",
                                lw=0.5,
                                ls="--",
                            )
                        )
                        event.inaxes.add_line(endline[-1])

                        m.BM.add_artist(endline[-1])

                    m.BM.update()

    eventnames = ["button_press_event", "key_press_event", "close_event"]
    if draw_on_drag:
        eventnames.append("motion_notify_event")

    _blocking_input.blocking_input_loop(canvas.figure, eventnames, timeout, handler)

    # Cleanup.
    if plt.fignum_exists(m.figure.f.number):
        for mark in marks + endline:
            m.BM.remove_artist(mark)
            mark.remove()

        m.BM.update()

    return clicks


# ----------------------------------------------------------------------------------

import eomaps._shapes as eoshp


class shape_drawer:
    def __init__(self, m, savepath=None):
        """
        Container class for draw-shapes

        Parameters
        ----------
        m : eomaps.Maps
            the maps-object.
        savepath : str, optional
            A path to a folder that will be used to store the drawn shapes
            as shapefiles.
            The default is None (e.g. no shapefiles are saved).

        """
        self._m = m

        if self._m.crs_plot == ccrs.PlateCarree():
            # temporary workaround for geopandas issue with WKT2 strings
            # https://github.com/geopandas/geopandas/issues/2387
            self._crs = 4326
        else:
            self._crs = self._m.crs_plot.to_wkt()

        self._savepath = savepath
        self.gdf = gpd.GeoDataFrame(geometry=[], crs=self._crs)

    def new_poly(self, **kwargs):
        return self.__class__(self._m, **kwargs)

    def polygon(self, smooth=False, draw_on_drag=True, **kwargs):
        """
        Draw arbitarary polygons

        Parameters
        ----------
        smooth : int or float, optional

            # TODO
            # copied from "scipy.interpolate.fitpack.splprep"

            A smoothing condition. The amount of smoothness is determined by
            satisfying the conditions: sum((w * (y - g))**2,axis=0) <= s, where g(x)
            is the smoothed interpolation of (x,y). The user can use s to control
            the trade-off between closeness and smoothness of fit. Larger s means
            more smoothing while smaller values of s indicate less smoothing.
            Recommended values of s depend on the weights, w. If the weights
            represent the inverse of the standard-deviation of y, then a good
            s value should be found in the range (m-sqrt(2*m),m+sqrt(2*m)),
            where m is the number of data points in x, y, and w.

            The default is False.
        draw_on_drag : bool, optional
            Continue adding points to the polygon on drag-events
            (e.g. mouse-button down + move).
            The default is True.
        kwargs :
            additional kwargs passed to the shape.
        """
        kwargs.setdefault("alpha", 0.5)

        pts = ginput(self._m, -1, timeout=-1, draw_on_drag=draw_on_drag)
        if pts is not None and len(pts) > 2:
            pts = np.asarray(pts)

            if smooth:
                # TODO this does not yet work
                # drawing smooth splines still needs a proper treatment!
                if isinstance(smooth, (int, float, np.number)):
                    s = smooth
                else:
                    s = 0.0
                tck, u = splprep(pts.T, u=None, s=s, per=1)
                u_new = np.linspace(u.min(), u.max(), 1000)
                x_new, y_new = splev(u_new, tck, der=0)
                pts = np.column_stack((x_new, y_new))

            (ph,) = self._m.ax.fill(pts[:, 0], pts[:, 1], **kwargs)
            self._m.BM.add_bg_artist(ph)
            self._m.BM.update()

            if self._savepath:
                gdf = gpd.GeoDataFrame(geometry=[Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = self.gdf.append(gdf)
                self.gdf.to_file(self._savepath)

    def circle(self, **kwargs):
        """
        Draw a circle.

        - RIGHT click to set the center
        - move the mouse to set the radius
        - MIDDLE click to fix the circle
        - LEFT click to abort

        Parameters
        ----------
        kwargs :
            additional kwargs passed to the shape.

        """
        kwargs.setdefault("alpha", 0.5)

        def movecb(event, pts):
            if len(pts) == 1:
                x, y = event.xdata, event.ydata
                if (x is None) or (y is None):
                    return

                r = np.sqrt((x - pts[0][0]) ** 2 + (y - pts[0][1]) ** 2)

                pts = eoshp.shapes._ellipses(self._m)._get_ellipse_points(
                    np.array([pts[0][0]]),
                    np.array([pts[0][1]]),
                    "out",
                    [r, r],
                    "out",
                    50,
                )

                (ph,) = self._m.ax.fill(
                    pts[0][0], pts[1][0], fc="none", ec="r", animated=True
                )
                self._m.ax.draw_artist(ph)
                self._m.BM.update(artists=[ph])

        pts = ginput2(self._m, 2, timeout=-1, draw_on_drag=True, movecb=movecb)

        if pts is not None and len(pts) == 2:
            pts = np.asarray(pts)

            r = np.sqrt(sum((pts[1] - pts[0]) ** 2))
            pts = eoshp.shapes._ellipses(self._m)._get_ellipse_points(
                np.array([pts[0][0]]), np.array([pts[0][1]]), "out", [r, r], "out", 100
            )

            (ph,) = self._m.ax.fill(pts[0][0], pts[1][0], **kwargs)
            self._m.BM.add_bg_artist(ph)
            self._m.BM.update()

            if self._savepath:
                pts = np.column_stack((pts[0][0], pts[1][0]))
                gdf = gpd.GeoDataFrame(geometry=[Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = self.gdf.append(gdf)
                self.gdf.to_file(self._savepath)

    def rectangle(self, **kwargs):
        """
        Draw a rectangle.

        - RIGHT click to set the center
        - move the mouse to set the radius
        - MIDDLE click to fix the circle
        - LEFT click to abort

        Parameters
        ----------
        kwargs :
            additional kwargs passed to the shape.

        """

        kwargs.setdefault("alpha", 0.5)

        def movecb(event, pts):
            if len(pts) == 1:
                x, y = event.xdata, event.ydata
                if (x is None) or (y is None):
                    return

                r = abs(x - pts[0][0]), abs(y - pts[0][1])
                pts = eoshp.shapes._rectangles(self._m)._get_rectangle_verts(
                    np.array([pts[0][0]]), np.array([pts[0][1]]), "out", r, "out", 50
                )[0][0]
                (ph,) = self._m.ax.fill(
                    pts[:, 0], pts[:, 1], fc="none", ec="r", animated=True
                )
                self._m.ax.draw_artist(ph)
                self._m.BM.update(artists=[ph])

        pts = ginput2(self._m, 2, timeout=-1, draw_on_drag=True, movecb=movecb)

        if pts is not None and len(pts) == 2:
            r = abs(pts[1][0] - pts[0][0]), abs(pts[1][1] - pts[0][1])

            pts = eoshp.shapes._rectangles(self._m)._get_rectangle_verts(
                np.array([pts[0][0]]), np.array([pts[0][1]]), "out", r, "out", 50
            )[0][0]

            (ph,) = self._m.ax.fill(pts[:, 0], pts[:, 1], **kwargs)
            self._m.BM.add_bg_artist(ph)
            self._m.BM.update()

            if self._savepath:
                gdf = gpd.GeoDataFrame(geometry=[Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = self.gdf.append(gdf)
                self.gdf.to_file(self._savepath)

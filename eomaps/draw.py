"""
A class to draw shapes on maps created with EOmaps

Known Issues:
-------------

It can happen that geopandas silently ignores the crs when writing shapefiles
(in case WKT2 strings are required to represent the crs)
->>

... already reported to geopandas... might take some time to resolve:
https://github.com/geopandas/geopandas/issues/2387

"""
from contextlib import contextmanager
from functools import wraps

import numpy as np
import matplotlib.pyplot as plt

import eomaps._shapes as eoshp

gpd = None


def _register_geopandas():
    global gpd
    try:
        import geopandas as gpd
    except ImportError:
        return False

    return True


if _register_geopandas():
    from shapely.geometry import Polygon


@contextmanager
def autoscale_turned_off(ax=None):
    ax = ax or plt.gca()
    lims = [ax.get_xlim(), ax.get_ylim()]
    yield
    ax.set_xlim(*lims[0])
    ax.set_ylim(*lims[1])


# ----------------------------------------------------------------------------------


class ShapeDrawer:
    def __init__(self, m, layer=None):
        """
        Base-class for drawing shapes on a map.

        Parameters
        ----------
        m : eomaps.Maps
            the maps-object.
        layer : str
            The layer-name to put the shapes on.
            If None, the currently active layer will be used.
            The default is None.
        """

        self._m = m
        # add a slot to remember active drawers
        # (used to make sure that 2 ShapeDrawer instances do not draw at the same time)
        self._m._active_drawer = None

        if layer is None:
            layer = self._m.BM.bg_layer
        self._layer = layer

        if self._m.crs_plot == self._m.CRS.PlateCarree():
            # temporary workaround for geopandas issue with WKT2 strings
            # https://github.com/geopandas/geopandas/issues/2387
            self._crs = 4326
        else:
            self._crs = self._m.crs_plot.to_wkt()

        if _register_geopandas():
            self.gdf = gpd.GeoDataFrame(geometry=[], crs=self._crs)
        else:
            self.gdf = None

        self._cids = []

        self._clicks = []
        self._marks = []
        self._endline = []

        self._on_new_poly = []
        self._on_poly_remove = []

        self._artists = dict()

    def new_drawer(self, layer=None):
        """
        Initialize a new ShapeDrawer.

        Parameters
        ----------
        layer : str
            The layer-name to put the shapes on.
            If None, the currently active layer will be used.
            The default is None.

        Returns
        -------
        ShapeDrawer
            A new instance of the ShapeDrawer that can be used to draw shapes.
        """

        return self.__class__(self._m, layer=layer)

    def set_layer(self, layer):
        """
        Set the layer to which the final shape will be added.

        Parameters
        ----------
        layer : str
            The layer name.
        """
        self._layer = layer

    def _finish_drawing(self, cb=None):
        """
        Stop the current draw, cleanup all temporary artists and execute
        an optional callback provided as "cb".

        Parameters
        ----------
        cb : callable, optional
            A callable executed after finishing the draw. The default is None.
        """

        active_drawer = self._m._active_drawer
        if active_drawer is None:
            return

        while len(active_drawer._cids) > 0:
            active_drawer._m.figure.f.canvas.mpl_disconnect(active_drawer._cids.pop())

        # Cleanup.
        if plt.fignum_exists(active_drawer._m.figure.f.number):
            while len(active_drawer._marks) > 0:
                a = active_drawer._marks.pop()
                active_drawer._m.BM.remove_artist(a)
                a.remove()

            while len(active_drawer._endline) > 0:
                a = active_drawer._endline.pop()
                active_drawer._m.BM.remove_artist(a)
                a.remove()

        if cb is not None:
            try:
                cb()
            except Exception:
                print("EOmaps: There was a problem while executing a draw-callback!")

        active_drawer._clicks.clear()

        self._m.BM.update()
        self._m._active_drawer = None

    if _register_geopandas():

        @wraps(gpd.GeoDataFrame.to_file)
        def save_shapes(self, filename, **kwargs):
            if len(self.gdf) > 0:
                self.gdf.to_file(filename, **kwargs)
            else:
                print("EOmaps: There are no polygons to save!")

    def remove_last_shape(self):
        """
        Remove the most recently plotted polygon from the map.
        """
        if len(self._artists) == 0:
            print("EOmaps: There is no shape to remove!")
            return

        ID = list(self._artists)[-1]
        a = self._artists.pop(ID)
        self._m.BM.remove_bg_artist(a)
        a.remove()

        if _register_geopandas():
            self.gdf = self.gdf.drop(ID)

        for cb in self._on_poly_remove:
            cb()

    # This is basically a copy of matplotlib's ginput function adapted for EOmaps
    # matplotlib's original ginput function is here:
    # https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.ginput.html
    def _ginput(
        self,
        n=1,
        timeout=30,
        show_clicks=True,
        draw_on_drag=True,
        mouse_add=plt.MouseButton.LEFT,
        mouse_pop=plt.MouseButton.RIGHT,
        mouse_stop=plt.MouseButton.MIDDLE,
        cb=None,
    ):
        """
        ... this is an adaption of plt.ginput() to work with a non-blocking eventloop

        The function waits until a stop-event is triggered and then calls
        the callback provided as "cb".

        Wait until the user clicks *n* times on the figure, and add the
        coordinates of each click to "self._clicks"

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

        # make sure all active drawings are finished before starting a new one
        self._finish_drawing()
        self._m._active_drawer = self

        canvas = self._m.BM.canvas

        def handler(event):
            if event.name == "close_event":
                self._finish_drawing(cb=cb)
                return

            if (canvas.toolbar is not None) and canvas.toolbar.mode != "":
                return

            is_button = (
                event.name == "button_press_event"
                or event.name == "motion_notify_event"
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
                self._finish_drawing(cb=cb)

            # Pop last click.
            elif (
                is_button
                and event.button == mouse_pop
                or is_key
                and event.key in ["backspace", "delete"]
            ):
                if self._clicks:
                    self._clicks.pop()
                    if show_clicks:
                        lastmark = self._marks.pop()
                        self._m.BM.remove_artist(lastmark)
                        lastmark.remove()
                        self._m.BM.update()

                        while len(self._endline) > 0:
                            el = self._endline.pop()
                            self._m.BM.remove_artist(el)
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
                    while len(self._endline) > 0:
                        el = self._endline.pop()
                        self._m.BM.remove_artist(el)
                        el.remove()

                    self._clicks.append((event.xdata, event.ydata))
                    if show_clicks:
                        if len(self._clicks) < 2:
                            x, y = [event.xdata], [event.ydata]
                        else:
                            x, y = [i[0] for i in self._clicks], [
                                i[1] for i in self._clicks
                            ]
                        line = plt.Line2D(x, y, marker="+", color="r")
                        event.inaxes.add_line(line)
                        self._marks.append(line)

                        self._m.BM.add_artist(line, "all")

                        if len(self._clicks) > 2:
                            self._endline.append(
                                plt.Line2D(
                                    [event.xdata, self._clicks[0][0]],
                                    [event.ydata, self._clicks[0][1]],
                                    color=".5",
                                    lw=0.5,
                                    ls="--",
                                )
                            )
                            event.inaxes.add_line(self._endline[-1])

                            self._m.BM.add_artist(self._endline[-1], "all")

                        self._m.BM.update()

            if len(self._clicks) == n and n > 0:
                self._finish_drawing(cb=cb)

        eventnames = ["button_press_event", "key_press_event", "close_event"]
        if draw_on_drag:
            eventnames.append("motion_notify_event")

        for event in eventnames:
            self._cids.append(canvas.mpl_connect(event, handler))

    # draw only a single point and draw a second point on escape
    # This is basically a copy of matplotlib's ginput function adapted for EOmaps
    # matplotlib's original ginput function is here:
    # https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.ginput.html
    def _ginput2(
        self,
        n=1,
        timeout=30,
        show_clicks=True,
        draw_on_drag=True,
        mouse_add=plt.MouseButton.LEFT,
        mouse_pop=plt.MouseButton.RIGHT,
        mouse_stop=plt.MouseButton.MIDDLE,
        movecb=None,
        cb=None,
    ):
        """
        ... this is an adaption of plt.ginput() to work with a non-blocking eventloop

        The function waits until a stop-event is triggered and then calls
        the callback provided as "cb".

        ginput2 adds only a first point and only adds the second point on escape

        Wait until the user clicks *n* times on the figure, and add the
        coordinates of each click to

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

        # make sure all active drawings are finished before starting a new one
        self._finish_drawing()
        self._m._active_drawer = self

        canvas = self._m.BM.canvas

        def handler(event):
            if event.name == "close_event":
                self._finish_drawing(cb=cb)
                return

            if (canvas.toolbar is not None) and canvas.toolbar.mode != "":
                return

            if event.name == "motion_notify_event":
                if movecb:
                    movecb(event, self._clicks)

            is_button = (
                event.name == "button_press_event"
                or event.name == "motion_notify_event"
            )
            is_key = event.name == "key_press_event"
            # Quit (even if not in infinite mode; this is consistent with
            # MATLAB and sometimes quite useful, but will require the user to
            # test how many points were actually returned before using data).

            if is_button and event.button == mouse_stop:
                self._clicks.append((event.xdata, event.ydata))
                self._finish_drawing(cb=cb)
            elif is_key and event.key in ["escape", "enter"]:
                self._finish_drawing(cb=cb)

            # Pop last click.
            elif (
                is_button
                and event.button == mouse_pop
                or is_key
                and event.key in ["backspace", "delete"]
            ):
                if self._clicks:
                    self._clicks.pop()
                    if show_clicks:
                        lastmark = self._marks.pop()
                        self._m.BM.remove_artist(lastmark)
                        lastmark.remove()
                        self._m.BM.update()

                        while len(self._endline) > 0:
                            el = self._endline.pop()
                            self._m.BM.remove_artist(el)
                            el.remove()

            # Add new click.
            elif (
                is_button
                and event.button == mouse_add
                # On macOS/gtk, some keys return None.
                or is_key
                and event.key is not None
            ):
                if len(self._clicks) >= n - 1:
                    return

                if event.inaxes:
                    while len(self._endline) > 0:
                        el = self._endline.pop()
                        self._m.BM.remove_artist(el)
                        el.remove()

                    self._clicks.append((event.xdata, event.ydata))
                    if show_clicks:
                        if len(self._clicks) < 2:
                            x, y = [event.xdata], [event.ydata]
                        else:
                            x, y = [i[0] for i in self._clicks], [
                                i[1] for i in self._clicks
                            ]
                        line = plt.Line2D(x, y, marker="+", color="r")
                        event.inaxes.add_line(line)
                        self._marks.append(line)

                        self._m.BM.add_artist(line, "all")

                        if len(self._clicks) > 2:
                            self._endline.append(
                                plt.Line2D(
                                    [event.xdata, self._clicks[0][0]],
                                    [event.ydata, self._clicks[0][1]],
                                    color=".5",
                                    lw=0.5,
                                    ls="--",
                                )
                            )
                            event.inaxes.add_line(self._endline[-1])

                            self._m.BM.add_artist(self._endline[-1], "all")

                        self._m.BM.update()

        eventnames = ["button_press_event", "key_press_event", "close_event"]
        if draw_on_drag:
            eventnames.append("motion_notify_event")

        for event in eventnames:
            self._cids.append(canvas.mpl_connect(event, handler))

    def polygon(self, smooth=False, draw_on_drag=True, **kwargs):
        """
        Draw arbitarary polygons

        - RIGHT click to add points
          (or drag while holding RIGHT mouse button)
        - MIDDLE click to finalize the polygon
        - LEFT click to successively remove most recently added points

        Parameters
        ----------
        draw_on_drag : bool, optional
            Continue adding points to the polygon on drag-events
            (e.g. mouse-button down + move).
            The default is True.
        kwargs :
            additional kwargs passed to the shape.
        """

        def cb():
            self._polygon(**kwargs)

        self._ginput(-1, timeout=-1, draw_on_drag=draw_on_drag, cb=cb)

    def _polygon(self, **kwargs):
        pts = self._clicks
        if pts is not None and len(pts) > 2:
            pts = np.asarray(pts)

            with autoscale_turned_off(self._m.ax):
                (ph,) = self._m.ax.fill(pts[:, 0], pts[:, 1], **kwargs)

                if self._layer is None:
                    self._m.BM.add_bg_artist(ph, layer=self._m.BM._bg_layer)
                else:
                    self._m.BM.add_bg_artist(ph, layer=self._layer)

                ID = max(self._artists) + 1 if self._artists else 0
                self._artists[ID] = ph

            self._m.BM.update()

            if _register_geopandas():
                gdf = gpd.GeoDataFrame(index=[ID], geometry=[Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = self.gdf.append(gdf)

            for cb in self._on_new_poly:
                cb()

    def circle(self, **kwargs):
        """
        Draw a circle.

        - RIGHT click to set the center
        - MOVE the mouse to set the radius
        - MIDDLE click to fix the circle
        - LEFT click to abort

        Parameters
        ----------
        kwargs :
            additional kwargs passed to the shape.

        """

        def cb():
            self._circle(**kwargs)

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

        self._ginput2(2, timeout=-1, draw_on_drag=True, movecb=movecb, cb=cb)

    def _circle(self, **kwargs):
        pts = self._clicks
        if pts is not None and len(pts) == 2:
            pts = np.asarray(pts)

            r = np.sqrt(sum((pts[1] - pts[0]) ** 2))
            pts = eoshp.shapes._ellipses(self._m)._get_ellipse_points(
                np.array([pts[0][0]]), np.array([pts[0][1]]), "out", [r, r], "out", 100
            )

            with autoscale_turned_off(self._m.ax):
                (ph,) = self._m.ax.fill(pts[0][0], pts[1][0], **kwargs)

                if self._layer is None:
                    self._m.BM.add_bg_artist(ph, layer=self._m.BM._bg_layer)
                else:
                    self._m.BM.add_bg_artist(ph, layer=self._layer)

                ID = max(self._artists) + 1 if self._artists else 0
                self._artists[ID] = ph

            self._m.BM.update()

            if _register_geopandas():
                pts = np.column_stack((pts[0][0], pts[1][0]))
                gdf = gpd.GeoDataFrame(index=[ID], geometry=[Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = self.gdf.append(gdf)

            for cb in self._on_new_poly:
                cb()

    def rectangle(self, **kwargs):
        """
        Draw a rectangle.

        - RIGHT click to set the center
        - MOVE the mouse to set the radius
        - MIDDLE click to fix the circle
        - LEFT click to abort

        Parameters
        ----------
        kwargs :
            additional kwargs passed to the shape.

        """

        def cb():
            self._rectangle(**kwargs)

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

        self._ginput2(2, timeout=-1, draw_on_drag=True, movecb=movecb, cb=cb)

    def _rectangle(self, **kwargs):
        pts = self._clicks
        if pts is not None and len(pts) == 2:
            r = abs(pts[1][0] - pts[0][0]), abs(pts[1][1] - pts[0][1])

            pts = eoshp.shapes._rectangles(self._m)._get_rectangle_verts(
                np.array([pts[0][0]]), np.array([pts[0][1]]), "out", r, "out", 50
            )[0][0]

            with autoscale_turned_off(self._m.ax):
                (ph,) = self._m.ax.fill(pts[:, 0], pts[:, 1], **kwargs)

                if self._layer is None:
                    self._m.BM.add_bg_artist(ph, layer=self._m.BM._bg_layer)
                else:
                    self._m.BM.add_bg_artist(ph, layer=self._layer)

                ID = max(self._artists) + 1 if self._artists else 0
                self._artists[ID] = ph

            self._m.BM.update()

            if _register_geopandas():
                gdf = gpd.GeoDataFrame(index=[ID], geometry=[Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = self.gdf.append(gdf)

            for cb in self._on_new_poly:
                cb()

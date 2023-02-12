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

import numpy as np
import matplotlib.pyplot as plt

import eomaps._shapes as eoshp

gpd = None
pd = None
shapely_Polygon = None


def _register_geopandas():
    global pd
    global gpd
    global shapely_Polygon
    try:
        import geopandas as gpd
        import pandas as pd
        from shapely.geometry import Polygon as shapely_Polygon
    except ImportError:
        return False

    return True


@contextmanager
def autoscale_turned_off(ax=None):
    ax = ax or plt.gca()
    lims = [ax.get_xlim(), ax.get_ylim()]
    yield
    ax.set_xlim(*lims[0])
    ax.set_ylim(*lims[1])


# ----------------------------------------------------------------------------------


class ShapeDrawer:
    def __init__(self, m, layer=None, dynamic=True):
        """
        Base-class for drawing shapes on a map.

        Parameters
        ----------
        m : eomaps.Maps
            the maps-object.
        layer : str or None
            The layer-name to put the shapes on.
            If None, the currently active layer will be used.
            The default is None.
        dynamic : bool
            If True, shapes are added as dynamic artists to avoid re-drawing
            the background after the draw is finished.
            If False, the shapes are added as background-artists.
        """

        self._m = m

        # # add a slot to remember active drawers
        # # (used to make sure that 2 ShapeDrawer instances do not draw at the same time)
        # if not hasattr(self._m.parent, "_active_drawer"):
        #     self._m.parent._active_drawer = None

        self._layer = layer
        self._dynamic = dynamic

        if self._m.crs_plot == self._m.CRS.PlateCarree():
            # temporary workaround for geopandas issue with WKT2 strings
            # https://github.com/geopandas/geopandas/issues/2387
            self._crs = 4326
        else:
            self._crs = self._m.crs_plot.to_wkt()

        if _register_geopandas():
            self.gdf = gpd.GeoDataFrame(geometry=[], crs=self._crs)
            ShapeDrawer.save_shapes.__doc__ = gpd.GeoDataFrame.to_file.__doc__
        else:
            self.gdf = None

        self._cids = []
        self._clicks = []

        # indicator-line when drawing polygons
        self._line = None
        # a pointer indicating the mouse-position during a draw-event
        self._pointer = None
        # a line indicating the polygon end-segment
        self._endline = None
        # indicator shape when drawing circles / rectangles
        self._shape_indicator = None

        self._on_new_poly = []
        self._on_poly_remove = []

        self._artists = dict()

    @property
    def _active_drawer(self):
        d = getattr(self._m.parent, "_active_drawer", None)
        if d is None:
            return self
        else:
            return d

    @property
    def layer(self):
        # always draw on the active layer if no explicit layer is specified
        if self._layer is None:
            return self._m.BM._bg_layer
        else:
            return self._layer

    @property
    def _background(self):
        # always use the currently active background as draw-background
        layer = self._m.BM._get_showlayer_name(self._m.BM._bg_layer)
        return self._m.BM._bg_layers.get(layer, None)

    @_active_drawer.setter
    def _active_drawer(self, val):
        self._m.parent._active_drawer = val

    def new_drawer(self, layer=None, dynamic=True):
        """
        Initialize a new ShapeDrawer.

        Parameters
        ----------
        layer : str
            The layer-name to put the shapes on.
            If None, the currently active layer will be used.
            The default is None.
        dynamic : bool
            If True, shapes are added as dynamic artists to avoid re-drawing
            the background after the draw is finished.
            If False, the shapes are added as background-artists.

        Returns
        -------
        ShapeDrawer
            A new instance of the ShapeDrawer that can be used to draw shapes.
        """

        return self.__class__(self._m, layer=layer, dynamic=dynamic)

    def set_layer(self, layer=None):
        """
        Set the layer to which the final shape will be added.
        If None, the shape will always be added to the currently active layer.

        Parameters
        ----------
        layer : str or None
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
        self._m.cb.execute_callbacks(True)

        active_drawer = self._active_drawer
        if active_drawer is None:
            return

        while len(active_drawer._cids) > 0:
            active_drawer._m.f.canvas.mpl_disconnect(active_drawer._cids.pop())

        # Cleanup.
        if plt.fignum_exists(active_drawer._m.f.number):
            self._line = None
            self._pointer = None
            self._endline = None
            self._shape_indicator = None

        if cb is not None:
            try:
                cb()
            except Exception:
                print("EOmaps: There was a problem while executing a draw-callback!")

        active_drawer._clicks.clear()

        self._m.BM.update()
        self._active_drawer = None

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
        if self._dynamic:
            self._m.BM.remove_artist(a)
        else:
            self._m.BM.remove_bg_artist(a)
        a.remove()

        if _register_geopandas():
            self.gdf = self.gdf.drop(ID)

        for cb in self._on_poly_remove:
            cb()

        self._m.BM.on_draw(None)

    def _init_draw_line(self):
        if self._line is None:
            props = dict(
                transform=self._m.ax.transData, clip_box=self._m.ax.bbox, clip_on=True
            )

            # the line to use for indicating polygon-shape during draw
            self._line = plt.Line2D([], [], marker="+", color="r", **props)
            self._pointer = plt.Line2D([], [], marker="+", color="r", lw=0.5, **props)
            self._endline = plt.Line2D([], [], color=".5", lw=0.5, ls="--", **props)

    def _init_shape_indicator(self):
        if self._shape_indicator is None:
            # a polygon to use for indicating circles/rectangles during draw
            self._shape_indicator = plt.Polygon(
                np.empty(shape=(0, 2)),
                fc="none",
                ec="r",
                animated=True,
                transform=self._m.ax.transData,
                clip_box=self._m.ax.bbox,
                clip_on=True,
            )

    @property
    def _indicator_artists(self):
        return (
            i
            for i in (self._shape_indicator, self._line, self._pointer, self._endline)
            if i is not None
        )

    def redraw(self, blit=True, *args):
        # NOTE: If a drawer is active, this function is also called on any ordinary
        # draw-event (e.g. zoom/pan/resize) to keep the indicators visible.
        # see "m.BM.on_draw()"

        artists = self._indicator_artists

        if self._dynamic:
            # draw all previously drawn shapes as well
            artists = (*artists, *self._artists.values())

        self._m.BM.blit_artists(artists, bg=self._background, blit=blit)

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
        self._active_drawer._finish_drawing()
        self._active_drawer = self

        canvas = self._m.BM.canvas
        # self.fetch_bg()

        self._m.cb.execute_callbacks(False)

        def handler(event):
            self._init_draw_line()

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

            if event.name == "motion_notify_event":
                if len(self._clicks) > 0:
                    self._pointer.set_data(
                        [self._clicks[-1][0], event.xdata],
                        [self._clicks[-1][1], event.ydata],
                    )
                else:
                    self._pointer.set_data([event.xdata], [event.ydata])

            if is_key and event.key in ["escape"]:
                self._finish_drawing()
                return

            if (
                is_button
                and event.button == mouse_stop
                or is_key
                and event.key in ["enter"]
            ):
                self._finish_drawing(cb=cb)
                return

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
                        if len(self._clicks) > 0:
                            self._line.set_data(*zip(*self._clicks))
                        else:
                            self._line.set_data([], [])

                        if len(self._clicks) > 2:
                            self._endline.set_data(
                                [self._clicks[-1][0], self._clicks[0][0]],
                                [self._clicks[-1][1], self._clicks[0][1]],
                            )
                        else:
                            self._endline.set_data([], [])

            # Add new click.
            elif (
                is_button
                and event.button == mouse_add
                # On macOS/gtk, some keys return None.
                or is_key
                and event.key is not None
            ):
                if event.inaxes:
                    self._clicks.append((event.xdata, event.ydata))
                    if show_clicks:
                        self._line.set_data(*zip(*self._clicks))

                        if len(self._clicks) > 2:
                            self._endline.set_data(
                                [event.xdata, self._clicks[0][0]],
                                [event.ydata, self._clicks[0][1]],
                            )

            if len(self._clicks) == n and n > 0:
                self._finish_drawing(cb=cb)

            self.redraw()

        eventnames = [
            "button_press_event",
            "key_press_event",
            "close_event",
        ]
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
        self._active_drawer._finish_drawing()
        self._active_drawer = self

        canvas = self._m.BM.canvas
        # self.fetch_bg()
        self._m.cb.execute_callbacks(False)

        def handler(event):
            self._init_draw_line()
            self._init_shape_indicator()

            if event.name == "close_event":
                self._finish_drawing()
                return

            if (canvas.toolbar is not None) and canvas.toolbar.mode != "":
                return

            if event.name == "motion_notify_event":
                if movecb:
                    # indicate current mouse-position (e.g. the center of the shape)
                    if len(self._clicks) == 0:
                        self._pointer.set_data([event.xdata], [event.ydata])
                    else:
                        self._pointer.set_data([], [])

                    movecb(event, self._clicks)

                artists = (
                    i for i in (self._shape_indicator, self._line, self._pointer) if i
                )
                if self._dynamic:
                    # draw all previously drawn shapes as well
                    artists = (*artists, *self._artists.values())

                self._m.BM.blit_artists(artists, bg=self._background)
                return

            is_button = event.name == "button_press_event"
            is_key = event.name == "key_press_event"
            # Quit (even if not in infinite mode; this is consistent with
            # MATLAB and sometimes quite useful, but will require the user to
            # test how many points were actually returned before using data).

            if is_button and event.button == mouse_stop:
                self._clicks.append((event.xdata, event.ydata))
                self._finish_drawing(cb=cb)
                return
            elif is_key and event.key in ["escape"]:
                self._finish_drawing()
                return

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
                        if len(self._clicks) > 0:
                            self._line.set_data(*zip(*self._clicks))
                        else:
                            self._line.set_data([], [])

                        self._shape_indicator.set_xy(np.empty(shape=(0, 2)))

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
                    self._clicks.append((event.xdata, event.ydata))
                    if show_clicks:
                        self._line.set_data(*zip(*self._clicks))

            self.redraw()

        eventnames = [
            "button_press_event",
            "key_press_event",
            "close_event",
        ]
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
        kwargs.setdefault("zorder", 10)

        def cb():
            self._polygon(**kwargs)

        self._ginput(-1, timeout=-1, draw_on_drag=draw_on_drag, cb=cb)

    def _polygon(self, **kwargs):
        pts = self._clicks
        if pts is not None and len(pts) > 2:
            pts = np.asarray(pts)

            with autoscale_turned_off(self._m.ax):
                (ph,) = self._m.ax.fill(pts[:, 0], pts[:, 1], **kwargs)

                if self._dynamic:
                    self._m.BM.add_artist(ph, layer=self.layer)
                else:
                    self._m.BM.add_bg_artist(ph, layer=self.layer)
                    self._m.BM.on_draw(None)

                ID = max(self._artists) + 1 if self._artists else 0
                self._artists[ID] = ph

            if _register_geopandas():
                gdf = gpd.GeoDataFrame(index=[ID], geometry=[shapely_Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = pd.concat([self.gdf, gdf])

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
        kwargs.setdefault("zorder", 10)

        self._init_shape_indicator()
        self._init_draw_line()

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
                    100,
                )
                self._shape_indicator.set_xy(np.column_stack((pts[0][0], pts[1][0])))

                artists = (self._shape_indicator, self._line)
                if self._dynamic:
                    # draw all previously drawn shapes as well
                    artists = (*artists, *self._artists.values())

                self._m.BM.blit_artists(artists, bg=self._background)

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

                if self._dynamic:
                    self._m.BM.add_artist(ph, layer=self.layer)
                else:
                    self._m.BM.add_bg_artist(ph, layer=self.layer)
                    self._m.BM.on_draw(None)

                ID = max(self._artists) + 1 if self._artists else 0
                self._artists[ID] = ph

            if _register_geopandas():
                pts = np.column_stack((pts[0][0], pts[1][0]))
                gdf = gpd.GeoDataFrame(index=[ID], geometry=[shapely_Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = pd.concat([self.gdf, gdf])

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
        kwargs.setdefault("zorder", 10)

        self._init_shape_indicator()

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

                self._shape_indicator.set_xy(np.column_stack((pts[:, 0], pts[:, 1])))

                artists = (self._shape_indicator, self._line)
                if self._dynamic:
                    # draw all previously drawn shapes as well
                    artists = (*artists, *self._artists.values())

                self._m.BM.blit_artists(artists, bg=self._background)

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

                if self._dynamic:
                    self._m.BM.add_artist(ph, layer=self.layer)
                else:
                    self._m.BM.add_bg_artist(ph, layer=self.layer)
                    self._m.BM.on_draw(None)

                ID = max(self._artists) + 1 if self._artists else 0
                self._artists[ID] = ph

            if _register_geopandas():
                gdf = gpd.GeoDataFrame(index=[ID], geometry=[shapely_Polygon(pts)])
                gdf = gdf.set_crs(crs=self._crs)
                self.gdf = pd.concat([self.gdf, gdf])

            for cb in self._on_new_poly:
                cb()

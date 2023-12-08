"""Collection of pre-defined click/pick/move/keypress callbacks."""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.transforms import TransformedPath
import warnings
import logging
import sys

_log = logging.getLogger(__name__)


def _removesuffix(s, suffix):
    if s.endswith(suffix):
        return s[: -len(suffix)]
    else:
        return s[:]


class _ClickCallbacks(object):
    """
    A collection of callback-functions.

    to attach a callback, use:
        >>> cid = m.cb.click.attach.annotate(**kwargs)
        or
        >>> cid = m.cb.pick.attach.annotate(**kwargs)

    to remove an already attached callback, use:
        >>> m.cb.click.remove(cid)
        or
        >>> m.cb.pick.remove(cid)


    you can also define custom callback functions as follows:

        >>> def some_callback(self, **kwargs):
        >>>     print("hello world")
        >>>     print("the position of the clicked pixel", kwargs["pos"])
        >>>     print("the data-index of the clicked pixel", kwargs["ID"])
        >>>     print("data-value of the clicked pixel", kwargs["val"])
    and attach them via:
        >>> cid = m.cb.click.attach(some_callback)
        or
        >>> cid = m.cb.click.attach(some_callback)
    (... and remove them in the same way as pre-defined callbacks)
    """

    # the naming-convention of the functions is as follows:
    #
    # _<NAME>_cleanup : a function that is executed if the callback
    #                   is removed from the plot
    #

    # ID : any
    #     The index-value of the pixel in the data.
    # pos : tuple
    #     A tuple of the position of the pixel in plot-coordinates.
    #     (ONLY relevant if ID is NOT provided!)
    # val : int or float
    #     The parameter-value of the pixel.
    # ind : int
    #     The index of the clicked pixel
    #     (ONLY relevant if ID is NOT provided!)

    # this list determines the order at which callbacks are executed!
    # (custom callbacks are always added to the end)
    _cb_list = [
        "get_values",
        "load",
        "print_to_console",
        "annotate",
        "mark",
        "plot",
        "peek_layer",
        "clear_annotations",
        "clear_markers",
    ]

    def __init__(self, m, temp_artists):
        self.m = m

        # a list shared with the container that is used to store temporary artists
        # (artists will be removed after each draw-event!)
        self._temporary_artists = temp_artists

    def _popargs(self, kwargs):
        # pop the default kwargs passed to each callback function
        # (to avoid showing them as kwargs when called)
        ID = kwargs.pop("ID", None)
        pos = kwargs.pop("pos", None)
        val = kwargs.pop("val", None)
        ind = kwargs.pop("ind", None)
        picker_name = kwargs.pop("picker_name", "default")
        val_color = kwargs.pop("val_color", None)

        # decode values in case a encoding is provided
        val = self.m._decode_values(val)

        return ID, pos, val, ind, picker_name, val_color

    @staticmethod
    def _fmt(x, **kwargs):
        # make sure to format arrays with "," separator to make them
        # copy-pasteable
        kwargs.setdefault("separator", ",")
        try:
            return np.array2string(np.asanyarray(x), **kwargs)
        except Exception:
            return str(x)

    def print_to_console(
        self,
        pos_precision=4,
        val_precision=4,
        text=None,
        show_all_values=True,
        **kwargs,
    ):
        """
        Print details on the clicked pixel to the console.

        Parameters
        ----------

        pos_precision : int
            The floating-point precision of the coordinates.
            The default is 4.
        val_precision : int
            The floating-point precision of the parameter-values (only used if
            "val_fmt=None"). The default is 4.
        text : callable or str, optional
            if str: the string to print
            if callable: A function that returns the string that should be
            printed in the annotation with the following call-signature:

                >>> def text(m, ID, val, pos, ind):
                >>>     # m   ... the Maps object
                >>>     # ID  ... the ID in the dataframe
                >>>     # pos ... the position
                >>>     # val ... the value
                >>>     # ind ... the index
                >>>
                >>>     return "the string to print"

            The default is None.
        show_all_values : bool, optional
            If True, show all values and coordinates of picked points.
            If False, only (min...max) values are shown if multiple datapoints are
            picked. The default is True.
        """
        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)

        printstr = self._get_annotation_text(
            ID=ID,
            pos=pos,
            val=val,
            ind=ind,
            pos_precision=pos_precision,
            val_precision=val_precision,
            text=text,
            show_all_values=show_all_values,
        )

        if text is None:
            print("\n# ---------------\n" + printstr)
        else:
            print(printstr)

    def _get_annotation_text(
        self,
        ID=None,
        pos=None,
        val=None,
        ind=None,
        pos_precision=4,
        val_precision=4,
        text=None,
        show_all_values=False,
    ):

        if isinstance(ind, (list, np.ndarray)):
            try:
                n_ids = len(ind)
            except TypeError:
                n_ids = "??"

            if n_ids == 1:
                multipick = False
            else:
                multipick = True
        else:
            multipick = False

        if isinstance(self.m.data_specs.x, str):
            xlabel = self.m.data_specs.x
        else:
            xlabel = "x"
        if isinstance(self.m.data_specs.y, str):
            ylabel = self.m.data_specs.y
        else:
            ylabel = "y"

        if self.m.data_specs.parameter is None:
            parameter = "value"
        else:
            parameter = self.m.data_specs.parameter

        crs_is_lonlat = self.m._get_cartopy_crs(4326) is self.m.crs_plot

        if text is None:
            # use "ind is not None" to distinguish between click and pick
            # TODO implement better distinction between click and pick!
            if self.m.data is not None and ind is not None:
                if not multipick:
                    x, y = [
                        np.format_float_positional(i, trim="-", precision=pos_precision)
                        for i in self.m._data_manager._get_xy_from_index(ind)
                    ]
                    x0, y0 = [
                        np.format_float_positional(i, trim="-", precision=pos_precision)
                        for i in pos
                    ]

                    if isinstance(val, (int, float)):
                        val = np.format_float_positional(
                            val, trim="-", precision=val_precision
                        )
                else:
                    if not show_all_values:
                        # only show min-max values of picked points
                        coords = [
                            *self.m._data_manager._get_xy_from_index(ind),
                            *self.m._data_manager._get_xy_from_index(
                                ind, reprojected=True
                            ),
                        ]

                        for n, c in enumerate(coords):
                            mi = np.format_float_positional(
                                np.nanmin(c), trim="-", precision=pos_precision
                            )
                            ma = np.format_float_positional(
                                np.nanmax(c), trim="-", precision=pos_precision
                            )
                            coords[n] = f"{mi} ... {ma}"

                        x, y, x0, y0 = coords

                        if ID is not None:
                            ID = f"{np.nanmin(ID)} ... {np.nanmax(ID)}"

                        if val is not None:
                            val = np.array(val, dtype=float)  # to handle None

                            # catch warnings here to avoid showing "all-nan-slice"
                            # all the time when clicking on empty pixels
                            with warnings.catch_warnings():
                                mi = np.format_float_positional(
                                    np.nanmin(val), trim="-", precision=pos_precision
                                )
                                ma = np.format_float_positional(
                                    np.nanmax(val), trim="-", precision=pos_precision
                                )
                            val = f"{mi}...{ma}"
                    else:
                        coords = (
                            *self.m._data_manager._get_xy_from_index(ind),
                            *self.m._data_manager._get_xy_from_index(
                                ind, reprojected=True
                            ),
                        )

                        x, y, x0, y0 = map(
                            lambda x: self._fmt(x, precision=pos_precision), coords
                        )
                        if val is not None:
                            val = self._fmt(
                                np.array(val, dtype=float), precision=val_precision
                            )
                        if ID is not None:
                            ID = self._fmt(np.asanyarray(ID))

                equal_crs = self.m.data_specs.crs == self.m._crs_plot
                printstr = (
                    (f"# Picked {n_ids} points\n" if multipick else "")
                    + f"{xlabel} = {x}\n"
                    + (f"{xlabel}_plot = {x0}\n" if not equal_crs else "")
                    + f"{ylabel} = {y}\n"
                    + (f"{ylabel}_plot = {y0}\n" if not equal_crs else "")
                    + (f"ID = {ID}\n" if ID is not None else "")
                    + (f"{parameter} = {val}" if val is not None else "")
                )

            else:
                if not crs_is_lonlat:
                    xlabel, ylabel = "x", "y"
                    lon, lat = self.m._transf_plot_to_lonlat.transform(*pos)
                    lon, lat = [
                        np.format_float_positional(i, trim="-", precision=pos_precision)
                        for i in (lon, lat)
                    ]
                else:
                    xlabel, ylabel = "lon", "lat"

                x, y = [
                    np.format_float_positional(i, trim="-", precision=pos_precision)
                    for i in pos
                ]

                printstr = (
                    f"{xlabel} = {x}\n"
                    + f"{ylabel} = {y}"
                    + (f"\nlon = {lon}" if not crs_is_lonlat else "")
                    + (f"\nlat = {lat}" if not crs_is_lonlat else "")
                    + (f"\nvalue = {val}" if val is not None else "")
                )

        elif isinstance(text, str):
            printstr = text
        elif callable(text):
            printstr = text(m=self.m, ID=ID, val=val, pos=pos, ind=ind)
        else:
            printstr = None

        return printstr

    def annotate(
        self,
        pos_precision=4,
        val_precision=4,
        permanent=False,
        text=None,
        zorder=20,
        layer=None,
        show_all_values=False,
        **kwargs,
    ):
        """
        Add a text-annotation to the plot at the position where the map was clicked.

        Parameters
        ----------
        pos_precision : int
            The floating-point precision of the coordinates.
            The default is 4.
        val_precision : int
            The floating-point precision of the parameter-values (only used if
            "val_fmt=None"). The default is 4.
        permanent : bool or None
            Indicator if the annotation should be temporary (False) or permanent (True).

            If True, the generated annotations are stored in a list
            which is accessible via `m.cb.[click/pick].get.permanent_annotations`

            If None, the artists will be permanent but NOT added to the
            `permanent_annotations` list and NOT editable!

            If "fixed" the artists will become invariable background artists that
            are only re-drawn if necessary (useful if you want to draw many annotations)

            The default is False
        text : callable or str, optional
            if str: the string to print
            if callable: A function that returns the string that should be
            printed in the annotation with the following call-signature:

                >>> def text(m, ID, val, pos, ind):
                >>>     # m   ... the Maps object
                >>>     # ID  ... the ID in the dataframe
                >>>     # pos ... the position
                >>>     # val ... the value
                >>>     # ind ... the index
                >>>
                >>>     return "the string to print"

            The default is None.
        zorder : int or float
            The zorder of the artist. (e.g. the drawing-order)
            For details, have a look at:

            - https://matplotlib.org/stable/gallery/misc/zorder_demo.html

            The default is 20
        layer : str or None, optional
            The layer to put the marker on.
            If None, the layer associated with the used Maps-object (e.g. `m.layer`)
            The default is None
        show_all_values : bool, optional
            If True, show all values and coordinates of picked points.
            If False, only (min...max) values are shown if multiple datapoints are
            picked. The default is True.
        kwargs
            kwargs passed to matplotlib.pyplot.annotate(). The default is:

            >>> dict(xytext=(20, 20),
            >>>      textcoords="offset points",
            >>>      bbox=dict(boxstyle="round", fc="w"),
            >>>      arrowprops=dict(arrowstyle="->"),
            >>>      annotation_clip=True,
            >>>     )

        """
        if layer is None:
            layer = self.m.layer

        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)
        if isinstance(ind, (list, np.ndarray)):
            # multipick = True
            picked_pos = (pos[0][0], pos[1][0])

            try:
                n_ids = len(ind)
            except TypeError:
                n_ids = "??"

            if n_ids == 1:
                multipick = False
            else:
                multipick = True

        else:
            multipick = False
            picked_pos = pos

        printstr = self._get_annotation_text(
            ID=ID,
            pos=pos,
            val=val,
            ind=ind,
            pos_precision=4,
            val_precision=4,
            text=text,
            show_all_values=show_all_values,
        )

        if printstr is not None:
            # create a new annotation
            if not multipick:
                bbox = dict(boxstyle="round", fc="w", ec=val_color)
                bbox.update(kwargs.pop("bbox", dict()))
            else:
                bbox = dict(boxstyle="round", fc="w", ec="k")
                bbox.update(kwargs.pop("bbox", dict()))

            styledict = dict(
                xytext=(20, 20),
                textcoords="offset points",
                bbox=bbox,
                arrowprops=dict(arrowstyle="->"),
                annotation_clip=True,
            )

            styledict.update(**kwargs)
            # use a black font-color by default to avoid issues if rcparams are
            # set differently
            styledict.setdefault("color", "k")
            annotation = self.m.ax.annotate("", xy=picked_pos, **styledict)
            annotation.set_zorder(zorder)

            # remember text (in case functions are used so that annotation texts can be
            # dynamically updated later as well)
            if text is None:
                annotation._EOmaps_text = self._get_annotation_text
            else:
                annotation._EOmaps_text = text

            if permanent is False:
                # make the annotation temporary
                self._temporary_artists.append(annotation)
                self.m.BM.add_artist(annotation, layer=layer)
            else:

                if isinstance(permanent, str) and permanent == "fixed":
                    self.m.BM.add_bg_artist(annotation, layer=layer)
                else:
                    self.m.BM.add_artist(annotation, layer=layer)

                    if not hasattr(self, "permanent_annotations"):
                        self.permanent_annotations = []

                    self.permanent_annotations.append(annotation)

                    # permanent annotations are also editable!
                    self.m._edit_annotations._add(
                        a=annotation,
                        kwargs={"ID": ID, "xy": picked_pos, "text": text, **styledict},
                        transf=None,
                        drag_coords=ID is None,
                    )

            annotation.set_visible(True)
            annotation.xy = picked_pos
            annotation.set_text(printstr)
            annotation.set_label(f"Annotation {pos}")

            return annotation

    def clear_annotations(self, **kwargs):
        """Remove all temporary and permanent annotations from the plot."""
        if hasattr(self, "permanent_annotations"):
            while len(self.permanent_annotations) > 0:
                ann = self.permanent_annotations.pop(0)
                self.m.BM.remove_artist(ann)
                ann.remove()

    # def _annotate_cleanup(self):
    #     self.clear_annotations()

    def get_values(self, **kwargs):
        """
        Successively collect return-values in a dict.

        The dict is accessible via `m.cb.[click/pick].get.picked_vals`

        The structure of the picked_vals dict is as follows:
        (lists are appended as you click on more pixels)

            >>> dict(
            >>>     pos=[... center-position tuples in plot_crs ...],
            >>>     ID=[... the corresponding IDs in the dataframe...],
            >>>     val=[... the corresponding values ...]
            >>> )

        removing the callback will also remove the associated value-dictionary!
        """
        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)

        if not hasattr(self, "picked_vals"):
            self.picked_vals = dict()

        for key, val in zip(["pos", "ID", "val"], [pos, ID, val]):
            self.picked_vals.setdefault(key, []).append(val)

    def _get_values_cleanup(self):
        # cleanup method for get_values callback
        if hasattr(self, "picked_vals"):
            del self.picked_vals

    def mark(
        self,
        radius=None,
        radius_crs=None,
        shape=None,
        buffer=1,
        permanent=False,
        n=20,
        zorder=10,
        layer=None,
        **kwargs,
    ):
        """
        Draw markers at the location where the map was clicked.

        If permanent = True, the generated annotations are stored in a list
        which is accessible via `m.cb.[click/pick].get.permanent_markers`

        Removing the callback will remove ALL markers that have been
        added to the map.

        Parameters
        ----------
        radius : float, string or None, optional
            - If float: The radius of the marker in units of the "radius_crs".
            - If "pixel" the pixel dimensions of the clicked pixel are used
            - If None: The radius of the data used for plotting (if available),
              otherwise 1/10 of the width and height

            The default is None.
        radius_crs : any
            (only relevant if radius is NOT specified as "pixel")

            The crs specification in which the radius is provided.
            - use "in" for input-crs, "out" for plot-crs
            - or use any other crs-specification (e.g. wkt-string, epsg-code etc.)

            If None, the radius_crs of the assigned plot-shape is used if possible
            (e.g. m.shape.radius_crs) and otherwise the input-crs is used (e.g. "in").

            The default is None.

        shape : str, optional
            Indicator which shape to draw. Currently supported shapes are:
            - ellipses
            - rectangles
            - geod_circles

            The default is None which defaults to the used shape for plotting
            if possible and else "ellipses".
        buffer : float, optional
            A factor to scale the size of the shape. The default is 1.
        permanent : bool or None
            Indicator if the markers should be temporary (False) or permanent (True).

            If True, the generated markers are stored in a list
            which is accessible via `m.cb.[click/pick].get.permanent_markers`

            If None, the artists will be permanent but NOT added to the
            `permanent_markers` list!

            The default is False
        n : int
            The number of points to calculate for the shape.
            The default is 20.
        zorder : int or float
            The zorder of the artist. (e.g. the drawing-order)
            For details, have a look at:

            - https://matplotlib.org/stable/gallery/misc/zorder_demo.html

            The default is 10
        layer : str or None, optional
            The layer to put the marker on.
            If None, the layer associated with the used Maps-object (e.g. `m.layer`)
            The default is None
        kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)
        """
        possible_shapes = ["ellipses", "rectangles", "geod_circles", "scatter_points"]

        if shape is None:
            if self.m.shape is not None:
                m_shape = self.m.shape.name
                if m_shape in possible_shapes:
                    shape = m_shape
                elif m_shape in ["raster", "shade_raster"]:
                    shape = "rectangles"
                else:
                    shape = "ellipses"
            else:
                "ellipses"
        else:
            assert (
                shape in possible_shapes
            ), f"'{shape}' is not a valid marker-shape... use one of {possible_shapes}"

        if radius_crs is None:
            radius_crs = getattr(self.m.shape, "radius_crs", "in")

        if radius is None:
            if self.m.coll is not None:
                radius = "pixel"
            else:
                t = self.m.ax.bbox.transformed(self.m.ax.transData.inverted())
                if shape == "scatter_points":
                    radius = getattr(self.m.shape, "_size", 20)
                else:
                    # make a dot with 1/20 of the width & height of the figure
                    radius = (t.width / 10.0, t.height / 10.0)

        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)
        if ID is not None and picker_name == "default":
            if ind is None:
                pos = self.m._data_manager._get_xy_from_ID(ID)
            else:
                pos = self.m._data_manager._get_xy_from_index(ind)
            pos_crs = "in"
        else:
            pos_crs = "out"

        if isinstance(radius, str) and radius == "pixel":
            pixelQ = True
            if not hasattr(self.m.shape, "radius"):
                _log.error(
                    "EOmaps: You cannot attach markers with 'radius=pixel' if the "
                    + "plot-shape does not set a radius! Please specify it explicitly."
                )
                return

            if shape == "scatter_points":
                radius = getattr(self.m.shape, "_size", 20)
            else:
                radius = self.m.shape.radius
        else:
            pixelQ = False

        # get manually specified radius (e.g. if radius != "estimate")
        if isinstance(radius, list):
            radius = [i * buffer for i in radius]
        elif isinstance(radius, tuple):
            radius = tuple([i * buffer for i in radius])
        elif isinstance(radius, (int, float)):
            radius = radius * buffer

        if self.m.shape and self.m.shape.name == "geod_circles":
            if shape != "geod_circles" and pixelQ:
                warnings.warn(
                    "EOmaps: Only `geod_circles` markers are possible"
                    + "if you use radius='pixel' after plotting `geod_circles`"
                    + "Specify an explicit radius to use other shapes!"
                )
                shape = "geod_circles"

        elif self.m.shape and self.m.shape.name in [
            "voronoi_diagram",
            "delaunay_triangulation",
        ]:
            assert radius != "pixel", (
                "EOmaps: Using `radius='pixel' is not possible"
                + "if the plot-shape was '{self.m.shape.name}'."
            )

        if shape == "geod_circles":
            shp = self.m.set_shape._get("geod_circles", radius=radius, n=n)
        elif shape == "ellipses":
            shp = self.m.set_shape._get(
                "ellipses", radius=radius, radius_crs=radius_crs, n=n
            )
        elif shape == "rectangles":
            shp = self.m.set_shape._get(
                "rectangles", radius=radius, radius_crs=radius_crs, mesh=False, n=n
            )
        elif shape == "scatter_points":
            marker = getattr(self.m.shape, "_marker", "o")
            shp = self.m.set_shape._get("scatter_points", _size=radius, _marker=marker)
        else:
            raise TypeError(f"EOmaps: '{shape}' is not a valid marker-shape")

        coll = shp.get_coll(
            np.atleast_1d(pos[0]), np.atleast_1d(pos[1]), pos_crs, **kwargs
        )

        marker = self.m.ax.add_collection(coll, autolim=False)

        marker.set_zorder(zorder)

        marker.set_label(f"Marker {pos}")

        if layer is None:
            layer = self.m.layer

        # explicitly use True/False here to allow overriding the "permanent"
        # behavior by using permanent=None (or anything other than True/False)
        if permanent is False:
            # make the annotation temporary
            self._temporary_artists.append(marker)
            self.m.BM.add_artist(marker, layer)
        elif permanent is None:
            self.m.BM.add_bg_artist(marker, layer)
        elif permanent is True:
            self.m.BM.add_artist(marker, layer)

            if not hasattr(self, "permanent_markers"):
                self.permanent_markers = [marker]
            else:
                self.permanent_markers.append(marker)

        return marker

    def clear_markers(self, **kwargs):
        """Remove all temporary and permanent annotations from the plot."""
        if hasattr(self, "permanent_markers"):
            while len(self.permanent_markers) > 0:
                marker = self.permanent_markers.pop(0)
                self.m.BM.remove_artist(marker)
                marker.remove()
            del self.permanent_markers

    # def _mark_cleanup(self):
    #     self.clear_markers()

    def _get_clip_path(self, x, y, xy_crs, radius, radius_crs, shape, n=100):
        shp = self.m.set_shape._get(shape)

        if shape == "ellipses":
            shp_pts = shp._get_ellipse_points(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = np.stack(shp_pts[:2], axis=2)[0]

        elif shape == "rectangles":
            shp_pts = shp._get_rectangle_verts(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = shp_pts[0][0]

        elif shape == "geod_circles":
            shp_pts = shp._get_geod_circle_points(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                # radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = np.stack(shp_pts[:2], axis=2).squeeze()
        from matplotlib.path import Path

        return Path(bnd_verts)

    def peek_layer(
        self, layer="1", how=(0.4, 0.4), alpha=1, shape="rectangular", **kwargs
    ):
        """
        Overlay a part of the map with a different layer if you click on the map.

        This callback allows you to overlay one (or more) existing layers on top
        of the currently visible layer if you click on the map.

        You can show a rectangular or circular area of the "peek-layer" centered at
        the mouse-position or swipe beween layers (e.g. from left/right/top or bottom).


        Parameters
        ----------
        layer : str or list

            - if str: The name of the layer you want to peek at.
            - if list: A list of layer-names of the following form:

                - A layer-name (string)
                - A tuple (< layer-name >, < transparency [0-1] >)

            see `m.show_layer()` for more details on how to provide combined layer-names

        how : str , float or tuple, optional
            The method you want to visualize the second layer.
            (e.g. swipe from a side or display a rectangle)

                - "left" (→), "right" (←), "top" (↓), "bottom" (↑):
                  swipe the layer at the mouse-position.
                - "full": overlay the layer on the whole figure
                - if float: peek a square at the mouse-position, specified as
                  percentage of the axis-width (0-1)
                - if tuple: (width, height) peek a rectangle at the mouse-position,
                  specified as percentage of the axis-size (0-1)

            The default is "left".
        alpha : float, optional
            The transparency of the peeked layer. (between 0 and 1)
            If you overlay a (possibly transparent) combination of multiple layers,
            this transparency will be assigned as a global transparency for the
            obtained "combined layer".
            The default is 1.
        shape : str, optional
            The shape of the peek-window.

            - "rectangular": peek a rectangle
            - "round": peek an ellipse

            The default is "rectangular"

        **kwargs :
            additional kwargs passed to a rectangle-marker.
            the default is `(fc="none", ec="k", lw=1)`


        Examples
        --------
        Overlay a single layer:

        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>> m2 = m.new_layer(layer="ocean")
        >>> m2.add_feature.preset.ocean()
        >>> m.cb.click.attach.peek_layer(layer="ocean")

        Overlay a (transparent) combination of multiple layers:

        >>> m = Maps()
        >>> m.all.add_feature.preset.coastline()
        >>> m.add_feature.preset.urban_areas()
        >>> m.add_feature.preset.ocean(layer="ocean")
        >>> m.add_feature.physical.land(layer="land", fc="g")
        >>> m.cb.click.attach.peek_layer(layer=["ocean", ("land", 0.5)],
        >>>                              shape="round", how=0.4)

        """
        shape = "ellipses" if shape == "round" else "rectangles"

        if not isinstance(layer, str):
            layer = self.m._get_combined_layer_name(*layer)

        # add spines and relevant inset-map layers to the specified peek-layer
        layer = self.m.BM._get_showlayer_name(layer, transparent=True)

        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)

        ax = self.m.ax

        # default boundary args
        args = dict(fc="none", ec="k", lw=1.1)
        args.update(kwargs)

        if isinstance(how, str):
            # base transformations on transData to ensure correct treatment
            # for shared axes
            if how == "left":
                x, _ = ax.transData.transform((pos[0], pos[1]))
                x0, y0 = ax.transAxes.transform((0, 0))
                blitw = x - x0
                blith = ax.bbox.height
            elif how == "right":
                x0, _ = ax.transData.transform((pos[0], pos[1]))
                xa0, y0 = ax.transAxes.transform((0, 0))
                blitw = ax.bbox.width - x0 + xa0
                blith = ax.bbox.height
            elif how == "top":
                x0, ya0 = ax.transAxes.transform((0, 0))
                _, y0 = ax.transData.transform((pos[0], pos[1]))

                blitw = ax.bbox.width
                blith = ax.bbox.height - y0 + ya0
            elif how == "bottom":
                x0, y0 = ax.transAxes.transform((0, 0))
                _, y = ax.transData.transform((pos[0], pos[1]))

                blitw = ax.bbox.width
                blith = y - y0
            elif how == "full":
                x0, y0 = ax.transAxes.transform((0, 0))
                blitw = ax.bbox.width
                blith = ax.bbox.height

            else:
                raise TypeError(f"EOmaps: '{how}' is not a valid input for 'how'")

            if how != "full":
                x0m, y0m = ax.transData.inverted().transform((x0, y0))
                x1m, y1m = ax.transData.inverted().transform((x0 + blitw, y0 + blith))
                w, h = abs(x1m - x0m), abs(y1m - y0m)

                clip_path = self._get_clip_path(
                    (x0m + x1m) / 2,
                    (y0m + y1m) / 2,
                    "out",
                    (w / 2, h / 2),
                    "out",
                    "rectangles",
                    100,
                )
            else:
                clip_path = None

        elif isinstance(how, (float, list, tuple)):
            if isinstance(how, float):
                w0, h0 = self.m.ax.transAxes.transform((0, 0))
                w1, h1 = self.m.ax.transAxes.transform((how, how))
                blitw, blith = [min(w1 - w0, h1 - h0)] * 2

            else:
                w0, h0 = self.m.ax.transAxes.transform((0, 0))
                w1, h1 = self.m.ax.transAxes.transform(how)
                blitw, blith = (w1 - w0, h1 - h0)

            x0, y0 = ax.transData.transform((pos[0], pos[1]))
            x0, y0 = x0 - blitw / 2, y0 - blith / 2

            # make sure that we don't blit outside the axis
            bbox = self.m.ax.bbox
            x1 = x0 + blitw
            y1 = y0 + blith
            if x0 < bbox.x0:
                dx = bbox.x0 - x0
                x0 = bbox.x0
                blitw = blitw - dx * 2
            if x1 > bbox.x1:
                dx = x1 - bbox.x1
                x0 = x0 + dx
                blitw = blitw - dx * 2
            if y0 < bbox.y0:
                dy = bbox.y0 - y0
                y0 = bbox.y0
                blith = blith - dy * 2
            if y1 > bbox.y1:
                dy = y1 - bbox.y1
                y0 = y0 + dy
                blith = blith - dy * 2

            x0m, y0m = ax.transData.inverted().transform(
                (x0 - blitw / 2.0, y0 - blith / 2)
            )

            # TODO check why a 1 pixel offset is required for a tight fit!
            # (rounding issues?)
            x1m, y1m = ax.transData.inverted().transform(
                (x0 + blitw / 2.0 - 1, y0 + blith / 2)
            )
            w, h = abs(x1m - x0m), abs(y1m - y0m)

            clip_path = self._get_clip_path(
                x1m, y1m, "out", (w / 2, h / 2), "out", shape, 100
            )
        else:
            raise TypeError(f"EOmaps: {how} is not a valid peek method!")

        if clip_path is not None:
            patch = PathPatch(clip_path, ec="k", fc="none")
            marker = self.m.ax.add_patch(patch)
            self.m.cb.click.add_temporary_artist(marker)

            # make sure to clear the marker at the next update to avoid savefig issues
            def doit():
                self.m.BM._artists_to_clear.setdefault("peek", []).append(marker)
                self.m.BM._clear_temp_artists("peek")

            self.m.BM._after_update_actions.append(doit)

        # create a TransformedPath as needed for clipping
        clip_path = TransformedPath(
            clip_path, self.m.ax.projection._as_mpl_transform(self.m.ax)
        )

        self.m.BM._after_restore_actions.append(
            self.m.BM._get_restore_bg_action(
                "|".join([self.m.BM.bg_layer, layer]),
                (x0, y0, blitw, blith),
                alpha=alpha,
                clip_path=clip_path,
                set_clip_path=False if shape == "rectangles" else True,
            )
        )

    def load(
        self, database=None, load_method="load_fit", load_multiple=False, **kwargs
    ):
        """
        Load objects from a given database using the ID of the picked pixel.

        The returned object(s) are accessible via `m.cb.pick.get.picked_object`.

        Parameters
        ----------
        database : any
            The database object to use for loading the object
        load_method : str or callable
            If str: The name of the method to use for loading objects from the provided
                    database (the call-signature used is `database.load_method(ID)`)
            If callable: A callable that will be executed on the database with the
                         following call-signature: `load_method(database, ID)`
        load_multiple : bool
            True: A single-object is returned, replacing `m.cb.picked_object` on each pick.
            False: A list of objects is returned that is extended with each pick.
        """
        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)
        assert database is not None, "you must provide a database object!"
        try:
            if isinstance(load_method, str):
                assert hasattr(
                    database, load_method
                ), "The provided database has no method '{load_method}'"
                pick = getattr(database, load_method)(ID)
            elif callable(load_method):
                pick = load_method(database, ID)
            else:
                raise TypeError("load_method must be a string or a callable!")
        except Exception:
            _log.error(
                f"EOmaps: Unable to load object with ID:  '{ID}' from {database}"
            )
        if load_multiple is True:
            self.picked_object = getattr(self, "picked_object", list()) + [pick]
        else:
            self.picked_object = pick

    def _load_cleanup(self):
        if hasattr(self, "picked_object"):
            del self.picked_object

    def plot(
        self,
        x_index="pos",
        precision=4,
        **kwargs,
    ):
        """
        Generate a dynamically updated plot showing the values of the picked pixels.

            - x-axis represents pixel-coordinates (or IDs)
            - y-axis represents pixel-values

        a new figure is started whenever the figure is closed!

        Parameters
        ----------
        x_index : str
            Indicator how the x-axis is labelled

                - pos : The position of the pixel in plot-coordinates
                - ID  : The index of the pixel in the data
        precision : int
            The floating-point precision of the coordinates printed to the
            x-axis if `x_index="pos"` is used.
            The default is 4.
        **kwargs :
            kwargs forwarded to the call to `plt.plot([...], [...], **kwargs)`.

        """
        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)

        style = dict(marker=".")
        style.update(**kwargs)

        if not hasattr(self, "_pick_f"):
            self._pick_f, self._pick_ax = plt.subplots()
            self._pick_ax.tick_params(axis="x", rotation=90)
            self._pick_ax.set_ylabel(self.m.data_specs.parameter)

            # call the cleanup function if the figure is closed
            def on_close(event):
                self._plot_cleanup()

            self._pick_f.canvas.mpl_connect("close_event", on_close)

        if isinstance(self.m.data_specs.x, str):
            _pick_xlabel = self.m.data_specs.x
        else:
            _pick_xlabel = "x"

        if isinstance(self.m.data_specs.y, str):
            _pick_ylabel = self.m.data_specs.y
        else:
            _pick_ylabel = "y"

        if x_index == "pos":
            x, y = [
                np.format_float_positional(i, trim="-", precision=precision)
                for i in pos
            ]
            xindex = f"{_pick_xlabel}={x}\n{_pick_ylabel}={y}"
        elif x_index == "ID":
            xindex = str(ID)

        if not hasattr(self, "_pick_l"):
            (self._pick_l,) = self._pick_ax.plot([xindex], [val], **style)
        else:
            self._pick_l.set_xdata(list(self._pick_l.get_xdata()) + [xindex])
            self._pick_l.set_ydata(list(self._pick_l.get_ydata()) + [val])

        self._pick_ax.relim()
        self._pick_ax.autoscale_view(True, True, True)
        self._pick_f.tight_layout()
        self._pick_f.canvas.draw()

    def _plot_cleanup(self):
        # cleanup method for plot callback
        if hasattr(self, "_pick_f"):
            del self._pick_f
        if hasattr(self, "_pick_ax"):
            del self._pick_ax
        if hasattr(self, "_pick_l"):
            del self._pick_l


class PickCallbacks(_ClickCallbacks):
    """A collection of callbacks that are executed if you click on a datapoint."""

    _cb_list = [
        "get_values",
        "load",
        "print_to_console",
        "annotate",
        "mark",
        "plot",
        "clear_annotations",
        "clear_markers",
        "highlight_geometry",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def highlight_geometry(self, permanent=False, **kwargs):
        """
        Temporarily highlite the picked geometry of a GeoDataFrame.

        Parameters
        ----------
        **kwargs :
            keyword-arguments to style the geometry
            (e.g. facecolor, edgecolor, linewidth etc. )

        """
        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)

        if ID is not None:
            # get the selected geometry and re-project it to the desired crs
            geom = self.m.cb.pick[picker_name].data.loc[[ID]].geometry
            # add the geometry to the map
            if permanent is False:
                self.m.add_gdf(geom, temporary_picker=picker_name, **kwargs)
            else:
                self.m.add_gdf(geom, permanent=permanent, **kwargs)


class ClickCallbacks(_ClickCallbacks):
    """Collection of callbacks that are executed if you click anywhere on the map."""

    _cb_list = [
        "get_values",
        "print_to_console",
        "annotate",
        "mark",
        "peek_layer",
        "clear_annotations",
        "clear_markers",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class MoveCallbacks(_ClickCallbacks):
    """Collection of callbacks that are executed on mouse-movement."""

    _cb_list = [
        "print_to_console",
        "annotate",
        "mark",
        "peek_layer",
    ]

    def _decorate(self, f):
        def inner(*args, **kwargs):
            f(*args, **kwargs)
            self.m.BM.update()

        return inner

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for cb in self._cb_list:
            if cb not in ["print_to_console"]:
                setattr(self, cb, self._decorate(getattr(super(), cb)))


class KeypressCallbacks:
    """Collection of callbacks that are executed if you press a key on the keyboard."""

    _cb_list = ["switch_layer", "fetch_layers", "overlay_layer"]

    def __init__(self, m, temp_artists):
        self._temporary_artists = temp_artists
        self._m = m

    def switch_layer(self, layer, key="x"):
        """
        Set the currently visible layer of the map.

        Parameters
        ----------
        layer : str or list
            The layer-name to use (or a list of layer-names to combine).

            For details on how to specify layer-names, see :py:meth:`Maps.show_layer`

        Additional Parameters
        ---------------------
        key : str, optional
            The key to use for triggering the callback.
            Modifiers are indicated with a "+", e.g. "alt+x".
            The default is "x".

        Examples
        --------
        Show layer A:

        >>> m.cb.keypress.attach.overlay_layer(layer="A", key="x")

        Show layer B with 50% transparency on top of layer A

        >>> m.cb.keypress.attach.overlay_layer(layer="A|B{0.5}", key="x")

        Show layer B on top of layer A:

        >>> m.cb.keypress.attach.overlay_layer(layer=["A", "B"], key="x")

        Show layer B with 50% transparency on top of layer A

        >>> m.cb.keypress.attach.overlay_layer(layer=["A", ("B", 0.5)], key="x")


        """
        if isinstance(layer, (list, tuple)):
            self._m.show_layer(*layer)
        elif isinstance(layer, str):
            self._m.show_layer(layer)

    def overlay_layer(self, layer, key="x"):
        """
        Toggle displaying a layer on top of the currently visible layers.

        - If the layer is not part of the currently visible layers, it will be
          added on top.
        - If the layer is part of the currently visible layers, it will be removed.

        Parameters
        ----------
        layer : str, tuple or list
            The layer-name to use, a tuple (layer, transparency) or a list of
            the aforementioned types to combine.

            For details on how to specify layer-names, see :py:meth:`Maps.show_layer`

        Additional Parameters
        ---------------------
        key : str, optional
            The key to use for triggering the callback.
            Modifiers are indicated with a "+", e.g. "alt+x".
            The default is "x".

        Note
        ----
        If the visible layer changes **while the overlay-layer is active**,
        triggering the callback again might not properly remove the previous overlay!
        (e.g. the overlay is only removed if the top-layer corresponds exactly to
         the overlay-layer specifications)

        Examples
        --------
        Toggle overlaying layer A:

        >>> m.cb.keypress.attach.overlay_layer(layer="A", key="x")

        Toggle overlaying layer A with 50% transparency:

        >>> m.cb.keypress.attach.overlay_layer(layer=("A", 0.5), key="x")

        Toggle overlaying a combined layer (showing layer B with 50% transparency
        on top of layer A)

        >>> m.cb.keypress.attach.overlay_layer(layer="A|B{0.5}", key="x")

        Toggle overlaying a combined layer (showing layer B on top of layer A)

        >>> m.cb.keypress.attach.overlay_layer(layer=["A", "B"], key="x")

        Toggle overlaying a combined layer (showing layer B with 50% transparency
        on top of layer A)

        >>> m.cb.keypress.attach.overlay_layer(layer=["A", ("B", 0.5)], key="x")

        """

        if isinstance(layer, list):
            layer = self._m._get_combined_layer_name(*layer)
        elif isinstance(layer, tuple):
            # e.g. (layer-name, layer-transparency)
            layer = self._m._get_combined_layer_name(layer)

        # in case the layer is currently on top, remove it
        if not self._m.BM.bg_layer.endswith(f"|{layer}"):
            self._m.show_layer(self._m.BM.bg_layer, layer)
        else:
            if sys.version_info >= (3, 9):
                newlayer = self._m.BM.bg_layer.removesuffix(f"|{layer}")
            else:
                newlayer = _removesuffix(self._m.BM.bg_layer, f"|{layer}")

            if len(newlayer) > 0:
                self._m.show_layer(newlayer)

    def fetch_layers(self, layers=None, verbose=True, key="x"):
        """
        Fetch (and cache) layers of a map.

        This is particularly useful if you want to use sliders or buttons to quickly
        switch between the layers (e.g. once the backgrounds are cached, switching
        layers will be fast).

        Note: After zooming or re-sizing the map, the cache is cleared and
        you need to call this function again!


        Note
        ----
        Callbacks are layer-sensitive, so you most probably want to attach this
        callback to the "all"-layer so that it can be triggered independent of the
        active layer. (e.g. `m.all.cb.keypress.attach.fetch_layer()`

        Parameters
        ----------
        layers : list or None, optional
            A list of layer-names that should be fetched.
            If None, all layers (except the "all" layer) are fetched.
            The default is None.
        verbose : bool
            Indicator if status-messages should be printed or not.
            The default is True.

        Additional Parameters
        ---------------------
        key : str, optional
            The key to use for triggering the callback.
            Modifiers are indicated with a "+", e.g. "alt+x".
            The default is "x".

        """
        self._m.fetch_layers(layers=layers, verbose=verbose)

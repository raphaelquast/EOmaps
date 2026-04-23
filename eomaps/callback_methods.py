# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Collection of pre-defined click/pick/move/keypress callbacks."""

import numpy as np
import warnings
import logging
import sys

import matplotlib.path as mpath

_log = logging.getLogger(__name__)


def _removesuffix(s, suffix):
    if s.endswith(suffix):
        return s[: -len(suffix)]
    else:
        return s[:]


def _fmt(x, **kwargs):
    # make sure to format arrays with "," separator to make them
    # copy-pasteable
    kwargs.setdefault("separator", ",")
    try:
        return np.array2string(np.asanyarray(x), **kwargs)
    except Exception:
        return str(x)


class _CallbackMixin:
    def _popargs(self, kwargs):
        if "event" in kwargs:
            event = kwargs.pop("event")
            props = [
                getattr(event, prop, None)
                for prop in ("ID", "pos", "val", "ind", "picker_name", "val_color")
            ]
            if event.name != "pick_event":
                props[1] = (event.xdata, event.ydata)

        else:
            props = [
                kwargs.pop(prop, None)
                for prop in ("ID", "pos", "val", "ind", "picker_name", "val_color")
            ]
            if props[4] is None:
                props[4] = "default"

        return props

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
            if self.m.data_specs.data is not None and ind is not None:
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
                            lambda x: _fmt(x, precision=pos_precision), coords
                        )
                        if val is not None:
                            val = _fmt(
                                np.array(val, dtype=float), precision=val_precision
                            )
                        if ID is not None:
                            ID = _fmt(np.asanyarray(ID))

                equal_crs = self.m.data_specs.crs == self.m._crs_plot
                if len(parameter) > 15:
                    parameter = parameter[:15] + " ..."
                printstr = (
                    (f"# Picked {n_ids} points\n" if multipick else "")
                    + f"{xlabel} = {x}\n"
                    + f"{ylabel} = {y}\n"
                    + (f"x_plot = {x0}\n" if not equal_crs else "")
                    + (f"y_plot = {y0}\n" if not equal_crs else "")
                    + (f"ID = {ID}\n" if ID is not None else "")
                    + (f"{parameter} = {val}" if val is not None else "")
                )

            else:
                if not crs_is_lonlat:
                    xlabel, ylabel = "x", "y"
                    lon, lat = self.m.transform_plot_to_lonlat(*pos)
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
            inp_bbox = kwargs.pop("bbox", dict())

            if inp_bbox is not None:
                if not multipick:
                    bbox = dict(boxstyle="round", fc="w", ec=val_color)
                    bbox.update(inp_bbox)
                else:
                    bbox = dict(boxstyle="round", fc="w", ec="k")
                    bbox.update(inp_bbox)
            else:
                bbox = None

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
                self.m.l[layer].add_artist(annotation)
            else:

                if isinstance(permanent, str) and permanent == "fixed":
                    self.m.l[layer].add_bg_artist(annotation)
                else:
                    self.m.l[layer].add_artist(annotation)

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
                self.m._bm.remove_artist(ann)

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
        buffer : float or array of float, optional
            A factor to scale the size of the shape.

            If a list of buffer values is provided, style-arguments like
            linewidth, facecolor etc. can also be lists to style each buffer
            shape individually.

            The default is 1.
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
        if isinstance(radius, (list, int, float)):
            radius = np.multiply(radius, buffer)
        elif isinstance(radius, tuple):
            radius = tuple([np.multiply(i, buffer) for i in radius])

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
            marker = getattr(self.m.shape, "_marker", kwargs.pop("marker", "o"))
            shp = self.m.set_shape._get("scatter_points", _size=radius, _marker=marker)
        else:
            raise TypeError(f"EOmaps: '{shape}' is not a valid marker-shape")

        n_buffer = len(np.atleast_1d(buffer))

        coll = shp.get_coll(
            np.tile(np.atleast_1d(pos[0]), n_buffer),
            np.tile(np.atleast_1d(pos[1]), n_buffer),
            pos_crs,
            **kwargs,
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
            self.m.l[layer].add_artist(marker)
        elif permanent is None:
            self.m.l[layer].add_bg_artist(marker)
        elif permanent is True:
            self.m.l[layer].add_artist(marker)

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
                self.m._bm.remove_artist(marker)
            del self.permanent_markers

    def peek_layer(self, layer, **kwargs):
        event = kwargs.pop("event")

        kwargs.setdefault("shape", "s")
        kwargs.setdefault("size", 0.25)
        kwargs.setdefault("shape_crs", "axes")

        # make sure the layer has been fetched once to avoid making
        # all pending artists temporary

        # TODO create a proper "ensure layer was initialized" method
        # that fetches all potential sublayers of a layers
        if not isinstance(layer, str):
            layer = self.m._bm._get_combined_layer_name(*layer)
        layers, _ = self.m._bm._parse_multi_layer_str(layer)

        for l in layers:
            if (
                l
                in self.m._bm._Hooks__hooks.get("layer_activation", {})
                .get(False, {})
                .keys()
            ):
                self.m._bm.fetch_bg(layer)

        self.m._bm.add_hook(
            "extent_changed",
            lambda *args, **kwargs: self.m._bm._clear_temp_artists(event._method),
        )

        with getattr(self.m.cb, event._method).make_artists_temporary(
            use_artists=[self.m]
        ):
            self.m.add_peek_layer(
                layer,
                xy=(event.xdata, event.ydata),
                xy_crs="plot",
                dynamic=True,
                **kwargs,
            )

    def _get_clip_path(self, x, y, xy_crs, radius, radius_crs, shape, n=100):
        shp = self.m.set_shape._get(shape)

        if shape == "ellipses":
            shp_pts = shp._get_points(
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
            shp_pts = shp._get_points(
                x=np.atleast_1d(x),
                y=np.atleast_1d(y),
                crs=xy_crs,
                radius=radius,
                # radius_crs=radius_crs,
                n=n,
            )
            bnd_verts = np.stack(shp_pts[:2], axis=2).squeeze()

        return mpath.Path(bnd_verts)

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

    def switch_layer(self, layer, **kwargs):
        """
        Set the currently visible layer of the map.

        Parameters
        ----------
        layer : str or list
            The layer-name to use (or a list of layer-names to combine).

            For details on how to specify layer-names, see :py:meth:`Maps.show_layer`

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
            self.m.show_layer(*layer)
        elif isinstance(layer, str):
            self.m.show_layer(layer)

    def overlay_layer(self, layer, **kwargs):
        """
        Toggle displaying a layer on top of the currently visible layers.

        This callback is useful to quickly show/hide a data-layer on top
        of a basemap by pressing a key on the keyboard.

        Parameters
        ----------
        layer : str, tuple or list
            The layer-name to use, a tuple (layer, transparency) or a list of
            the aforementioned types to combine.

            For details on how to specify layer-names, see :py:meth:`Maps.show_layer`

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
            layer = self.m._bm._get_combined_layer_name(*layer)
        elif isinstance(layer, tuple):
            # e.g. (layer-name, layer-transparency)
            layer = self.m._bm._get_combined_layer_name(layer)

        # in case the layer is currently on top, remove it
        if not self.m._bm.bg_layer.endswith(f"|{layer}"):
            self.m.show_layer(self.m._bm.bg_layer, layer)
        else:
            if sys.version_info >= (3, 9):
                newlayer = self.m._bm.bg_layer.removesuffix(f"|{layer}")
            else:
                newlayer = _removesuffix(self.m._bm.bg_layer, f"|{layer}")

            if len(newlayer) > 0:
                self.m.show_layer(newlayer)

    def fetch_layers(self, layers=None, verbose=True, **kwargs):
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

        """
        self.m.fetch_layers(layers=layers, verbose=verbose)

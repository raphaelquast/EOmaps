import numpy as np
import matplotlib.pyplot as plt
import warnings


class _click_callbacks(object):
    """
    a collection of callback-functions

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

    def print_to_console(self, **kwargs):
        """Print details on the clicked pixel to the console"""
        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)

        if isinstance(self.m.data_specs.x, str):
            xlabel = self.m.data_specs.x
            ylabel = self.m.data_specs.y
        else:
            xlabel = "x"
            ylabel = "y"

        if ID is not None:
            printstr = "---------------\n"
            x, y = pos
            printstr += f"{xlabel} = {x}\n{ylabel} = {y}\n"
            printstr += f"ID = {ID}\n"

            paramname = self.m.data_specs.parameter
            if paramname is None:
                paramname = "val"
            printstr += f"{paramname} = {val}"
        else:
            lon, lat = self.m._transf_plot_to_lonlat.transform(*pos)

            printstr = (
                "---------------\n"
                f"x = {pos[0]}\n"
                f"y = {pos[1]}\n"
                f"lon = {lon}\n"
                f"lat = {lat}"
            )

        print(printstr)

    def annotate(
        self,
        pos_precision=4,
        val_precision=4,
        permanent=False,
        text=None,
        zorder=20,
        layer=None,
        **kwargs,
    ):
        """
        Add a basic text-annotation to the plot at the position where the map
        was clicked.

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
            `permanent_annotations` list!

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
        kwargs
            kwargs passed to matplotlib.pyplot.annotate(). The default is:

            >>> dict(xytext=(20, 20),
            >>>      textcoords="offset points",
            >>>      bbox=dict(boxstyle="round", fc="w"),
            >>>      arrowprops=dict(arrowstyle="->")
            >>>     )

        """

        if layer is None:
            layer = self.m.layer

        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)

        try:
            n_ids = len(ID)
        except TypeError:
            n_ids = 1

        if ID is not None and n_ids > 1:
            multipick = True
            picked_pos = (pos[0][0], pos[1][0])
        else:
            multipick = False
            picked_pos = pos

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

        ax = self.m.ax

        if text is None:
            if ID is not None and self.m.data is not None:
                if not multipick:
                    x, y = [
                        np.format_float_positional(i, trim="-", precision=pos_precision)
                        for i in self.m._get_xy_from_index(ind)
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
                    coords = [
                        *self.m._get_xy_from_index(ind),
                        *self.m._get_xy_from_index(ind, reprojected=True),
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
                        mi = np.format_float_positional(
                            np.nanmin(val), trim="-", precision=pos_precision
                        )
                        ma = np.format_float_positional(
                            np.nanmax(val), trim="-", precision=pos_precision
                        )
                        val = f"{mi}...{ma}"

                equal_crs = self.m.data_specs.crs != self.m._crs_plot
                printstr = (
                    (f"Picked {n_ids} points\n" if multipick else "")
                    + f"{xlabel} = {x}"
                    + (f" ({x0})\n" if equal_crs else "\n")
                    + f"{ylabel} = {y}"
                    + (f" ({y0})\n" if equal_crs else "\n")
                    + (f"ID = {ID}" if ID is not None else "")
                    + (f"\n{parameter} = {val}" if val is not None else "")
                )

            else:
                lon, lat = self.m._transf_plot_to_lonlat.transform(*pos)
                x, y = [
                    np.format_float_positional(i, trim="-", precision=pos_precision)
                    for i in pos
                ]
                lon, lat = [
                    np.format_float_positional(i, trim="-", precision=pos_precision)
                    for i in (lon, lat)
                ]

                printstr = (
                    f"x = {x}\n"
                    + f"y = {y}\n"
                    + f"lon = {lon}\n"
                    + f"lat = {lat}"
                    + (f"\nvalue = {val}" if val is not None else "")
                )

        elif isinstance(text, str):
            printstr = text
        elif callable(text):
            printstr = text(m=self.m, ID=ID, val=val, pos=pos, ind=ind)

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
            )

            styledict.update(**kwargs)
            annotation = ax.annotate("", xy=picked_pos, **styledict)
            annotation.set_zorder(zorder)

            if permanent is False:
                # make the annotation temporary
                self._temporary_artists.append(annotation)
                self.m.BM.add_artist(annotation, layer=layer)
            else:
                self.m.BM.add_artist(annotation, layer=layer)

                if permanent is True:
                    if not hasattr(self, "permanent_annotations"):
                        self.permanent_annotations = [annotation]
                    else:
                        self.permanent_annotations.append(annotation)

            annotation.set_visible(True)
            annotation.xy = picked_pos
            annotation.set_text(printstr)

    def clear_annotations(self, **kwargs):
        """
        Remove all temporary and permanent annotations from the plot
        """
        if hasattr(self, "permanent_annotations"):
            while len(self.permanent_annotations) > 0:
                ann = self.permanent_annotations.pop(0)
                self.m.BM.remove_artist(ann)
                ann.remove()

    # def _annotate_cleanup(self):
    #     self.clear_annotations()

    def get_values(self, **kwargs):
        """
        Successively collect return-values in a dict accessible via
        `m.cb.[click/pick].get.picked_vals`.

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
        possible_shapes = ["ellipses", "rectangles", "geod_circles"]

        if shape is None:
            if self.m.shape is not None:
                shape = (
                    self.m.shape.name
                    if (self.m.shape.name in possible_shapes)
                    else "ellipses"
                )
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
                # make a dot with 1/20 of the width & height of the figure
                t = self.m.ax.bbox.transformed(self.m.ax.transData.inverted())
                radius = (t.width / 10.0, t.height / 10.0)

        ID, pos, val, ind, picker_name, val_color = self._popargs(kwargs)
        if ID is not None and picker_name == "default":
            if ind is None:
                pos = self.m._get_xy_from_ID(ID)
            else:
                pos = self.m._get_xy_from_index(ind)
            pos_crs = "in"
        else:
            pos_crs = "out"

        if isinstance(radius, str) and radius == "pixel":
            pixelQ = True
            if not hasattr(self.m.shape, "radius"):
                print(
                    "EOmaps: You cannot attach markers with 'radius=pixel' if the "
                    + "plot-shape does not set a radius! Please specify it explicitly."
                )
                return
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
        else:
            raise TypeError(f"EOmaps: '{shape}' is not a valid marker-shape")

        coll = shp.get_coll(
            np.atleast_1d(pos[0]), np.atleast_1d(pos[1]), pos_crs, **kwargs
        )

        marker = self.m.ax.add_collection(coll, autolim=False)

        marker.set_zorder(zorder)

        if layer is None:
            layer = self.m.layer

        if permanent is False:
            # make the annotation temporary
            self._temporary_artists.append(marker)
            self.m.BM.add_artist(marker, layer)
        else:
            self.m.BM.add_artist(marker, layer)

            if permanent is True:
                if not hasattr(self, "permanent_markers"):
                    self.permanent_markers = [marker]
                else:
                    self.permanent_markers.append(marker)

        return marker

    def clear_markers(self, **kwargs):
        """
        Remove all temporary and permanent annotations from the plot.
        """
        if hasattr(self, "permanent_markers"):
            while len(self.permanent_markers) > 0:
                marker = self.permanent_markers.pop(0)
                self.m.BM.remove_artist(marker)
                marker.remove()
            del self.permanent_markers

    # def _mark_cleanup(self):
    #     self.clear_markers()

    def peek_layer(self, layer="1", how=(0.4, 0.4), alpha=1, **kwargs):
        """
        Swipe between data- or WebMap layers or peek a layers through a rectangle.

        Parameters
        ----------
        layer : str or list

            - if str: The name of the layer you want to peek at.
            - if list: A list of layer-names to peek at.
              (alternatively you can also separate individual layer-names with a "|"
              character, e.g.: "layer1|layer2")

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
            The transparency of the peeked layer.
            (must be between 0 and 1)
            The default is 1.
        **kwargs :
            additional kwargs passed to a rectangle-marker.
            the default is `(fc="none", ec="k", lw=1)`

        Note
        ----
        You must draw something on the layer first!

        To assign a layer to an object, either use the `layer=...` argument when
        adding objects (e.g. `m.plot_map(layer=1)`), or use a new Maps-layer via

        >>> m = Maps()
        >>> m2 = m.new_layer(layer="the layer name")
        >>> # now all artists added with m2 will be added to the layer
        >>> # "the layer name" (if not explicitly specified otherwise)
        >>> m2.plot_map()
        >>> m.peek_layer(layer="the layer name")
        """

        if "overlay" in kwargs:
            kwargs.pop("overlay")
            warnings.warn(
                "EOmaps: The 'overlay' argument of peek_layer is depreciated! "
                "(It has no effect and can be removed.)"
            )

        if isinstance(layer, list):
            layer = "|".join(map(str, layer))
        else:
            if not isinstance(layer, str):
                print("EOmaps v5.0 Warning: All layer-names are converted to strings!")
                layer = str(layer)

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
                marker = self.mark(
                    pos=((x0m + x1m) / 2, (y0m + y1m) / 2),
                    radius_crs="out",
                    shape="rectangles",
                    radius=(w / 2, h / 2),
                    permanent=False,
                    **args,
                )
            else:
                marker = None

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
            x1m, y1m = ax.transData.inverted().transform(
                (x0 + blitw / 2.0, y0 + blith / 2)
            )
            w, h = abs(x1m - x0m), abs(y1m - y0m)

            marker = self.mark(
                pos=pos,
                radius_crs="out",
                shape="rectangles",
                radius=(w / 1.99, h / 1.99),  # 1.99 to be larger than the blit-region
                permanent=False,
                layer="all",
                **args,
            )

        else:
            raise TypeError(f"EOmaps: {how} is not a valid peek method!")

        if marker is not None:
            # make sure to clear the marker at the next update
            def doit():
                self.m.BM._artists_to_clear.setdefault("move", []).append(marker)

            self.m.BM._after_restore_actions.append(doit)

        self.m.BM._after_restore_actions.append(
            self.m.BM._get_restore_bg_action(layer, (x0, y0, blitw, blith), alpha=alpha)
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
            print(f"could not load object with ID:  '{ID}' from {database}")
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


class pick_callbacks(_click_callbacks):
    """
    A collection of callback functions that are executed when clicking on
    a pixel of the plotted collection.
    """

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
            self.m.add_gdf(geom, temporary_picker=picker_name, **kwargs)


class click_callbacks(_click_callbacks):
    """
    A collection of callback functions that are executed when clicking anywhere
    on the map.
    """

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


class move_callbacks(_click_callbacks):
    """
    A collection of callback functions that are executed on mouse-movement.
    """

    _cb_list = [
        "print_to_console",
        "annotate",
        "mark",
        "peek_layer",
    ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class keypress_callbacks:
    """
    A collection of callback functions that are executed when the assigned
    key is pressed.
    """

    _cb_list = ["switch_layer", "fetch_layers"]

    def __init__(self, m, temp_artists):
        self._temporary_artists = temp_artists
        self._m = m

    def switch_layer(self, layer, key="x"):
        """
        Change the default layer of the map.

        Use the keyboard events to set the default layer (e.g. the visible layer)
        displayed in the plot.

        Parameters
        ----------
        layer : str
            The layer-name to use.
            If a non-string value is provided, it will be converted to string!

        Additional Parameters
        ---------------------
        key : str, optional
            The key to use for triggering the callback.
            Modifiers are indicated with a "+", e.g. "alt+x".
            The default is "x".
        """

        self._m.BM.bg_layer = str(layer)
        self._m.BM.fetch_bg()

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

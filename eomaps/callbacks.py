import numpy as np
from pandas import DataFrame
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib.patches import Circle, Ellipse, Rectangle, Polygon
from pyproj import CRS, Transformer


class callbacks(object):
    """
    a collection of callback-functions

    to attach a callback, use:
        >>> m.add_callback(m.cb.annotate)
        >>> # or
        >>> m.add_callback("annotate")

    to remove an already attached callback, use:
        >>> m.remove_callback(m.cb.annotate)
        >>> # or
        >>> m.remove_callback("annotate")

    you can also define custom callback functions as follows:

        >>> def some_callback(self, **kwargs):
        >>>     print("hello world")
        >>>     print("the position of the clicked pixel", kwargs["pos"])
        >>>     print("the data-index of the clicked pixel", kwargs["ID"])
        >>>     print("data-value of the clicked pixel", kwargs["val"])
        >>>
        >>> m.add_callback(some_callback)
    and remove them again via
        >>> m.remove_callback(some_callback)
    """

    # the naming-convention of the functions is as follows:
    #
    # _<NAME>_cleanup : a function that is executed if the callback
    #                   is removed from the plot
    #
    # _<NAME>_nopick_callback : a function that is executed if an empty area
    #                           is clicked within the plot

    def __init__(self, m):
        self.m = m

    def __repr__(self):
        return "available callbacks:\n    - " + "\n    - ".join(self.cb_list)

    @property
    def cb_list(self):
        return [
            "annotate",
            "mark",
            "plot",
            "print_to_console",
            "get_values",
            "load",
            "clear_annotations",
            "clear_markers",
        ]

    def load(
        self,
        ID=None,
        pos=None,
        val=None,
        ind=None,
        database=None,
        load_method="load_fit",
        load_multiple=False,
    ):
        """
        A callback-function that can be used to load objects from a given
        database.

        The returned object(s) are accessible via `m.cb.picked_object`.

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the dataframe.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        ind : int
            The index of the clicked pixel
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

    def print_to_console(self, ID=None, pos=None, val=None, ind=None):
        """
        a callback-function that prints details on the clicked pixel to the
        console

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        ind : int
            The index of the clicked pixel
        """

        xlabel = self.m.data_specs["xcoord"]
        ylabel = self.m.data_specs["ycoord"]

        printstr = ""
        x, y = [np.format_float_positional(i, trim="-", precision=4) for i in pos]
        printstr += f"{xlabel} = {x}\n{ylabel} = {y}\n"
        printstr += f"ID = {ID}\n"

        if isinstance(val, (int, float)):
            val = np.format_float_positional(val, trim="-", precision=4)
        printstr += f"{self.m.data_specs['parameter']} = {val}"

        print(printstr)

    def annotate(
        self,
        ID=None,
        pos=None,
        val=None,
        ind=None,
        pos_precision=4,
        val_precision=4,
        permanent=False,
        text=None,
        layer=10,
        **kwargs,
    ):
        """
        a callback-function to annotate basic properties from the fit on
        double-click, use as:    spatial_plot(... , callback=cb_annotate)

        if permanent = True, the generated annotations are stored in a list
        which is accessible via `m.cb.permanent_annotations`

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        ind : int
            The index of the clicked pixel
        pos_precision : int
            The floating-point precision of the coordinates.
            The default is 4.
        val_precision : int
            The floating-point precision of the parameter-values (only used if
            "val_fmt=None"). The default is 4.
        permanent : bool
            Indicator if the annotation should be temporary (False) or
            permanent (True). The default is False
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
        layer : int
            The layer-level on which to draw the artist.
            (First layer 0 is drawn, then layer 1 on top then layer 2 etc...)
            The default is 10.
        **kwargs
            kwargs passed to matplotlib.pyplot.annotate(). The default is:

            >>> dict(xytext=(20, 20),
            >>>      textcoords="offset points",
            >>>      bbox=dict(boxstyle="round", fc="w"),
            >>>      arrowprops=dict(arrowstyle="->"))
            >>>     )

        """

        xlabel = self.m.data_specs["xcoord"]
        ylabel = self.m.data_specs["ycoord"]

        ax = self.m.figure.ax

        if hasattr(self, "annotation") and not permanent:
            # re-use the existing annotation if possible
            annotation = self.annotation
        else:
            # create a new annotation
            styledict = dict(
                xytext=(20, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round", fc="w"),
                arrowprops=dict(arrowstyle="->"),
            )

            styledict.update(**kwargs)
            annotation = ax.annotate("", xy=pos, **styledict)

            if not permanent:
                # save the annotation for re-use
                self.annotation = annotation
            else:
                if not hasattr(self, "permanent_annotations"):
                    self.permanent_annotations = [annotation]
                else:
                    self.permanent_annotations.append(annotation)

            if layer is not None:
                self.m.BM.add_artist(annotation, layer=layer)

        annotation.set_visible(True)
        annotation.xy = pos

        if text is None:
            x, y = [
                np.format_float_positional(i, trim="-", precision=pos_precision)
                for i in self.m.data.loc[ID][[xlabel, ylabel]]
            ]
            x0, y0 = [
                np.format_float_positional(i, trim="-", precision=pos_precision)
                for i in pos
            ]
            if isinstance(val, (int, float)):
                val = np.format_float_positional(val, trim="-", precision=val_precision)

            printstr = (
                f"{xlabel} = {x} ({x0})\n"
                + f"{ylabel} = {y} ({y0})\n"
                + (f"ID = {ID}\n" if ID is not None else "")
                + (
                    f"{self.m.data_specs['parameter']} = {val}"
                    if val is not None
                    else ""
                )
            )
        elif isinstance(text, str):
            printstr = text
        elif callable(text):
            printstr = text(self.m, ID, val, pos, ind)

        annotation.set_text(printstr)

        self.m.BM.update()

    def clear_annotations(self, remove_permanent=True, remove_temporary=True, **kwargs):
        """
        remove all temporary and permanent annotations from the plot
        """
        if remove_permanent and hasattr(self, "permanent_annotations"):
            while len(self.permanent_annotations) > 0:
                ann = self.permanent_annotations.pop(0)
                self.m.BM.remove_artist(ann)
                ann.remove()
        if remove_temporary and hasattr(self, "annotation"):
            self.annotation.set_visible(False)
            self.m.BM.remove_artist(self.annotation)
            del self.annotation

        self.m.BM.update()

    def _clear_annotations_nopick_callback(self):
        self.clear_annotations()

    def _annotate_cleanup(self):
        self.clear_annotations()

    def _annotate_nopick_callback(self):
        if hasattr(self, "annotation"):
            self.annotation.set_visible(False)
        self.m.BM.update()

    def plot(
        self,
        ID=None,
        pos=None,
        val=None,
        ind=None,
        x_index="pos",
        precision=4,
        **kwargs,
    ):
        """
        a callback-function to generate a dynamically updated plot of the
        values

            - x-axis represents pixel-coordinates (or IDs)
            - y-axis represents pixel-values

        a new figure is started if the callback is removed and added again, e.g.

            >>> m.remove_callback("scatter")
            >>> m.add_callback("scatter")


        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        ind : int
            The index of the clicked pixel
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

        style = dict(marker=".")
        style.update(**kwargs)

        if not hasattr(self, "_pick_f"):
            self._pick_f, self._pick_ax = plt.subplots()
            self._pick_ax.tick_params(axis="x", rotation=90)
            self._pick_ax.set_ylabel(self.m.data_specs["parameter"])

            # call the cleanup function if the figure is closed
            def on_close(event):
                self._scatter_cleanup()

            self._pick_f.canvas.mpl_connect("close_event", on_close)

        _pick_xlabel = self.m.data_specs["xcoord"]
        _pick_ylabel = self.m.data_specs["ycoord"]

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

        # self._pick_ax.autoscale()
        self._pick_ax.relim()
        self._pick_ax.autoscale_view(True, True, True)

        self._pick_f.canvas.draw()
        self._pick_f.tight_layout()

    def _scatter_cleanup(self):
        # cleanup method for scatter callback
        if hasattr(self, "_pick_f"):
            del self._pick_f
        if hasattr(self, "_pick_ax"):
            del self._pick_ax
        if hasattr(self, "_pick_l"):
            del self._pick_l

    def get_values(self, ID=None, pos=None, val=None, ind=None):
        """
        a callback-function that successively collects return-values in a dict
        accessible via "m.cb.picked_vals", with the following structure:

            >>> m.cb.picked_vals = dict(
            >>>     pos=[... center-position tuples in plot_crs ...],
            >>>     ID=[... the corresponding IDs in the dataframe...],
            >>>     val=[... the corresponding values ...]
            >>> )

        removing the callback will also remove the associated value-dictionary!

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        ind : int
            The index of the clicked pixel
        """

        if not hasattr(self, "picked_vals"):
            self.picked_vals = defaultdict(list)

        for key, val in zip(["pos", "ID", "val"], [pos, ID, val]):
            self.picked_vals[key].append(val)

    def _get_values_cleanup(self):
        # cleanup method for get_values callback
        if hasattr(self, "picked_vals"):
            del self.picked_vals

    def mark(
        self,
        ID=None,
        pos=None,
        val=None,
        ind=None,
        radius="pixel",
        radius_crs="in",
        shape="circle",
        buffer=1,
        permanent=True,
        layer=10,
        **kwargs,
    ):
        """
        A callback to draw indicators over double-clicked pixels.

        Removing the callback will remove ALL markers that have been
        added to the map.

        The added patches are accessible via `m.cb._pick_markers`

        Note: If radius="pixel", the shape is determined from the
              center plus/minus the width & height of the corresponding pixel.
              For highly distorted projections this can lead to a "shift"
              of the shape since the shape is then no longer properly centered.

        Parameters
        ----------
        ID : any
            The index-value of the pixel in the data.
        pos : tuple
            A tuple of the position of the pixel in plot-coordinates.
        val : int or float
            The parameter-value of the pixel.
        ind : int
            The index of the clicked pixel
        radius : float, string or None, optional
            The radius of the marker.
            If None, it will be evaluated based on the pixel-spacing of the
            provided dataset
            If "pixel" the pixel dimensions of the clicked pixel are used

            The default is None.
        radius_crs : any
            The crs specification in which the radius is provided.
            The default is "in" (e.g. the crs of the input-data).
            (only relevant if radius is NOT specified as "pixel")

        shape : str, optional
            Indicator which shape to draw. Currently supported shapes are:
                - circle
                - ellipse
                - rectangle

            The default is "circle".
        buffer : float, optional
            A factor to scale the size of the shape. The default is 1.
        permanent : bool, optional
            Indicator if the shapes should be permanent (True) or removed
            on each new double-click (False)
        layer : int
            The layer-level on which to draw the artist.
            (First layer 0 is drawn, then layer 1 on top then layer 2 etc...)
            The default is 10.
        **kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)
        """

        if radius_crs == "in":
            radius_crs = self.m.data_specs["in_crs"]
        elif radius_crs == "out":
            radius_crs = self.m.plot_specs["plot_epsg"]

        if ID is not None:
            if ind is None:
                ind = self.m.data.index.get_loc(ID)

        if radius == "pixel":
            d = self.m._prepare_data(
                data=DataFrame(
                    dict(
                        x=[self.m._props["x0"][ind]],
                        y=[self.m._props["y0"][ind]],
                        z=[self.m._props["z_data"][ind]],
                    )
                ),
                # data=self.m.data.loc[[ID]],
                xcoord="x",
                ycoord="y",
                parameter="z",
                in_crs=self.m.plot_specs["plot_epsg"],
                radius_crs=self.m.data_specs["in_crs"],
                shape="rectangles",
                buffer=buffer,
                radius=self.m._props["radius"],
            )
            radiusx = self.m._props["w"][ind]
            radiusy = self.m._props["h"][ind]
            theta = self.m._props["theta"][ind]

        elif isinstance(radius, (int, float, list, tuple)):
            theta = 0
            if isinstance(radius, (list, tuple)):
                radiusx, radiusy = radius
            else:
                radiusx = radiusy = radius

            # transform the radius if radius_crs is not None
            if radius_crs is not None:
                d = self.m._prepare_data(
                    data=DataFrame(
                        dict(
                            x=[self.m._props["x0"][ind]],
                            y=[self.m._props["y0"][ind]],
                            z=[self.m._props["z_data"][ind]],
                        )
                    ),
                    # data=self.m.data.loc[[ID]],
                    xcoord="x",
                    ycoord="y",
                    parameter="z",
                    in_crs=self.m.plot_specs["plot_epsg"],
                    radius_crs=radius_crs,
                    shape="rectangles",
                    buffer=buffer,
                    radius=(radiusx, radiusy),
                )

                radiusx = d["w"][0]
                radiusy = d["h"][0]
                theta = d["theta"][0]

        else:
            radiusx, radiusy = self.m._props["radius"]
            theta = self.m._props["theta"][ind]

        if hasattr(self, "marker") and not permanent:
            # remove existing marker
            self.marker.set_visible(False)
            self.m.BM.remove_artist(self.marker)
            del self.marker

        if permanent and not hasattr(self, "permanent_markers"):
            self.permanent_markers = []

        if shape == "circle":
            p = Circle(pos, np.sqrt(radiusx ** 2 + radiusy ** 2) * buffer, **kwargs)
        elif shape == "ellipse":
            p = Ellipse(
                pos,
                radiusx * 2 * buffer,
                radiusy * 2 * buffer,
                theta,
                **kwargs,
            )
        elif shape == "rectangle":
            if radius == "pixel":
                p = Polygon(
                    d["verts"][0],
                    **kwargs,
                )
            else:
                p = Rectangle(
                    [pos[0] - radiusx * buffer, pos[1] - radiusy * buffer],
                    radiusx * 2 * buffer,
                    radiusy * 2 * buffer,
                    theta,
                    **kwargs,
                )
        else:
            raise TypeError(f"{shape} is not a valid marker-shape")

        marker = self.m.figure.ax.add_patch(p)

        if permanent:
            self.permanent_markers.append(marker)
        else:
            self.marker = marker

        if layer is not None:
            self.m.BM.add_artist(marker, layer)

        self.m.BM.update()

    def clear_markers(self, remove_permanent=True, remove_temporary=True, **kwargs):
        """
        remove all temporary and permanent annotations from the plot
        """
        if remove_permanent and hasattr(self, "permanent_markers"):
            while len(self.permanent_markers) > 0:
                marker = self.permanent_markers.pop(0)
                self.m.BM.remove_artist(marker)
                marker.remove()
            del self.permanent_markers
        if remove_temporary and hasattr(self, "marker"):
            self.marker.set_visible(False)
            self.m.BM.remove_artist(self.marker)
            del self.marker

        self.m.BM.update()

    def _clear_markers_nopick_callback(self):
        self.clear_markers()

    def _mark_cleanup(self):
        self.clear_markers()

    def _mark_nopick_callback(self):
        if hasattr(self, "marker"):
            self.marker.set_visible(False)
        self.m.BM.update()

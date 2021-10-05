import numpy as np
import matplotlib.pyplot as plt
from collections import defaultdict
from matplotlib.patches import Circle, Ellipse, Rectangle


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

    def __init__(self, m):
        self.m = m

    def __repr__(self):
        return "available callbacks:\n    - " + "\n    - ".join(self.cb_list)

    @property
    def cb_list(self):
        return ["load", "print_to_console", "annotate", "plot", "get_values", "mark"]

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
        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # xlabel, ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
        # xlabel, ylabel = [i.name for i in self.m.figure.ax.projection.axis_info[:2]]
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
        **kwargs,
    ):
        """
        a callback-function to annotate basic properties from the fit on
        double-click, use as:    spatial_plot(... , callback=cb_annotate)

        if permanent = True, the generated annotations are accessible via
        `m.permanent_annotations`

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

        **kwargs
            kwargs passed to matplotlib.pyplot.annotate(). The default is:

            >>> dict(xytext=(20, 20),
            >>>      textcoords="offset points",
            >>>      bbox=dict(boxstyle="round", fc="w"),
            >>>      arrowprops=dict(arrowstyle="->"))
            >>>     )

        """

        if not hasattr(self.m, "background"):
            # cache the background before the first annotation is drawn
            # in case there is no cached background yet
            self.m._grab_background(redraw=False)

        if not hasattr(self.m, "draw_cid"):
            # attach draw_event that handles blitting
            self.m.draw_cid = self.m.figure.f.canvas.mpl_connect(
                "draw_event", self.m._grab_background
            )

        # to hide the annotation, Maps._cb_hide_annotate() is called when an empty
        # area is clicked!
        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # xlabel, ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
        # xlabel, ylabel = [i.abbrev for i in self.m.figure.ax.projection.axis_info[:2]]
        xlabel = self.m.data_specs["xcoord"]
        ylabel = self.m.data_specs["ycoord"]

        ax = self.m.figure.ax

        if hasattr(self, "annotation") and not permanent:
            # re-use the attached annotation
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
                self.annotation = annotation
            else:
                if not hasattr(self, "permanent_annotations"):
                    self.permanent_annotations = [annotation]
                else:
                    self.permanent_annotations.append(annotation)

        annotation.set_visible(True)
        annotation.xy = pos

        if text is None:
            x, y = [
                np.format_float_positional(i, trim="-", precision=pos_precision)
                for i in pos
            ]
            if isinstance(val, (int, float)):
                val = np.format_float_positional(val, trim="-", precision=val_precision)

            printstr = (
                f"{xlabel} = {x}\n{ylabel} = {y}\n"
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

        # use blitting instead of f.canvas.draw() to speed up annotation generation
        # in case a large collection is plotted

        if permanent:
            self.m._blit(annotation)
            self.m._grab_background(redraw=False)
        else:
            self.m._blit(annotation)

    def clear_annotations(self):
        """
        remove all permanent annotations from the plot
        """
        if hasattr(self, "permanent_annotations"):
            while len(self.permanent_annotations) > 0:
                ann = self.permanent_annotations.pop(0)
                ann.remove()

    def _annotate_cleanup(self):
        if hasattr(self.m, "background"):
            # delete cached background
            del self.m.background
        # remove draw_event callback
        if hasattr(self.m, "draw_cid"):
            self.m.figure.f.canvas.mpl_disconnect(self.m.draw_cid)
            del self.m.draw_cid
        # remove draw_event callback
        if hasattr(self, "annotation"):
            self.annotation.set_visible(False)
            del self.annotation

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

        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # _pick_xlabel, _pick_ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
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
        shape="circle",
        buffer=1,
        permanent=True,
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
            TODO: permanent=False not yet implemented!
        **kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)
        """

        if not hasattr(self.m, "background"):
            # cache the background before the first annotation is drawn
            # in case there is no cached background yet
            self.m._grab_background(redraw=False)

        if not hasattr(self.m, "draw_cid"):
            # attach draw_event that handles blitting
            self.m.draw_cid = self.m.figure.f.canvas.mpl_connect(
                "draw_event", self.m._grab_background
            )

        if not hasattr(self, "_pick_markers"):
            self._pick_markers = []

        if radius is None:
            radiusx = np.abs(np.diff(np.unique(self.m._props["x0"])).mean()) / 2.0
            radiusy = np.abs(np.diff(np.unique(self.m._props["y0"])).mean()) / 2.0
        elif radius == "pixel":
            if ID is not None:
                if ind is None:
                    ind = self.m.data.index.get_loc(ID)
                radiusx = self.m._props["w"][ind] / 2
                radiusy = self.m._props["h"][ind] / 2
            else:
                raise TypeError("you must provide eiter the ID or an explicit radius!")
        else:
            if isinstance(radius, (list, tuple)):
                radiusx, radiusy = radius
            else:
                radiusx = radiusy = radius

        if shape == "circle":
            p = Circle(pos, np.sqrt(radiusx ** 2 + radiusy ** 2) * buffer, **kwargs)
        elif shape == "ellipse":
            p = Ellipse(
                pos,
                radiusx * 2 * buffer,
                radiusy * 2 * buffer,
                **kwargs,
            )
        elif shape == "rectangle":
            p = Rectangle(
                [pos[0] - radiusx * buffer, pos[1] - radiusy * buffer],
                radiusx * 2 * buffer,
                radiusy * 2 * buffer,
                **kwargs,
            )
        else:
            raise TypeError(f"{shape} is not a valid marker-shape")

        artist = self.m.figure.ax.add_patch(p)

        self._pick_markers.append(artist)

        if permanent:
            # first draw the marker, then cache the new background
            self.m._blit(artist)
            self.m._grab_background(redraw=False)

        if not permanent:
            raise NotImplementedError("non-permanent markers not yet implemented!")

    def _mark_cleanup(self):
        if hasattr(self, "_pick_markers"):
            while len(self._pick_markers) > 0:
                self._pick_markers.pop(0).remove()
            del self._pick_markers

        # remove draw_event callback
        if hasattr(self.m, "draw_cid"):
            self.m.figure.f.canvas.mpl_disconnect(self.m.draw_cid)
            del self.m.draw_cid

import numpy as np
from matplotlib import cm, collections
import matplotlib.pyplot as plt
from pyproj import CRS
from collections import defaultdict


class callbacks(object):
    """
    a collection of callback-functions

    to attach a callback, use:
        >>> m.attach_callback(m.cb.annotate)

    to remove an already attached callback, use:
        >>> m.remove_callback(m.cb.annotate)

    you can also define custom callback functions as follows:

        >>> def some_callback(self, **kwargs):
        >>>     print("hello world")
        >>>     print("the position of the clicked pixel", kwargs["pos"])
        >>>     print("the data-index of the clicked pixel", kwargs["ID"])
        >>>     print("data-value of the clicked pixel", kwargs["val"])
        >>>
        >>> m.attach_callback(some_callback)
    """

    def __init__(self, m):
        pass
        # self = m

    def __repr__(self):
        return "available callbacks:\n    - " + "\n    - ".join(
            [i for i in self.__dir__() if not i.startswith("_")]
        )

    def load(self, **kwargs):
        """
        a callback-function that can be used to load the corresponding fit-objects
        stored in `dumpfolder / dumps / *.dump` on double-clicking a shape
        """
        try:
            self.fit = self.useres.load_fit(kwargs["ID"])
        except FileNotFoundError:
            print(f"could not load fit with ID:  '{kwargs['ID']}'")

    def print_to_console(self, **kwargs):
        """
        a callback-function that prints details on the clicked pixel to the
        console
        """
        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # xlabel, ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
        xlabel, ylabel = [i.name for i in self.figure.ax.projection.axis_info[:2]]

        printstr = ""
        for key, val in kwargs.items():
            if key == "f":
                continue
            if key == "pos":
                x, y = [
                    np.format_float_positional(i, trim="-", precision=4) for i in val
                ]
                printstr += f"{xlabel} = {x}\n{ylabel} = {y}\n"
            else:
                if isinstance(val, (int, float)):
                    val = np.format_float_positional(val, trim="-", precision=4)
                printstr += f"{self.data_specs['parameter']} = {val}\n"
        print(printstr)

    def annotate(self, **kwargs):
        """
        a callback-function to annotate basic properties from the fit on double-click
        use as:    spatial_plot(... , callback=cb_annotate)
        """

        if not hasattr(self, "background"):
            # cache the background before the first annotation is drawn
            self.background = self.figure.f.canvas.copy_from_bbox(self.figure.f.bbox)

        # to hide the annotation, Maps._cb_hide_annotate() is called when an empty
        # area is clicked!
        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # xlabel, ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
        xlabel, ylabel = [i.abbrev for i in self.figure.ax.projection.axis_info[:2]]

        ax = self.figure.ax

        if not hasattr(self, "annotation"):
            self.annotation = ax.annotate(
                "",
                xy=kwargs["pos"],
                xytext=(20, 20),
                textcoords="offset points",
                bbox=dict(boxstyle="round", fc="w"),
                arrowprops=dict(arrowstyle="->"),
            )

        self.annotation.set_visible(True)
        self.annotation.xy = kwargs["pos"]

        printstr = ""
        x, y = [
            np.format_float_positional(i, trim="-", precision=4) for i in kwargs["pos"]
        ]
        printstr += f"{xlabel} = {x}\n{ylabel} = {y}\n"

        val = kwargs["val"]
        if isinstance(val, (int, float)):
            val = np.format_float_positional(val, trim="-", precision=4)
        printstr += f"{self.data_specs['parameter']} = {val}"

        self.annotation.set_text(printstr)
        self.annotation.get_bbox_patch().set_alpha(0.75)

        # use blitting instead of f.canvas.draw() to speed up annotation generation
        # in case a large collection is plotted
        self._blit(self.annotation)

    def scatter(self, **kwargs):
        """
        a callback-function to generate a dynamically updated scatterplot

            - x-axis represents pixel-coordinates
            - y-axis represents pixel-values

        """
        if not hasattr(self, "_pick_f"):
            self._pick_f, self._pick_ax = plt.subplots()
            self._pick_ax.tick_params(axis="x", rotation=90)

            self._pick_ax.set_ylabel(self.data_specs["parameter"])

        # crs = self._get_crs(self.plot_specs["plot_epsg"])
        # _pick_xlabel, _pick_ylabel = [crs.axis_info[0].abbrev, crs.axis_info[1].abbrev]
        _pick_xlabel, _pick_ylabel = [
            i.abbrev for i in self.figure.ax.projection.axis_info[:2]
        ]

        x, y = [
            np.format_float_positional(i, trim="-", precision=4) for i in kwargs["pos"]
        ]

        self._pick_ax.plot(
            [f"{_pick_xlabel}={x}\n{_pick_ylabel}={y}"], [kwargs["val"]], marker="."
        )
        self._pick_ax.autoscale()
        self._pick_f.tight_layout()
        self._pick_f.canvas.draw()

    def _scatter_cleanup(self, m):
        if hasattr(m, "_pick_f"):
            del m._pick_f
        if hasattr(m, "_pick_ax"):
            del m._pick_ax

    def get_values(self, **kwargs):
        """
        a callback-function that successively collects return-values in a dict
        that can be accessed via "m.picked_vals", with the following structure:

            >>> m.picked_vals = dict(pos=[... center-position tuples in plot_crs ...],
                                     ID=[... the IDs in the dataframe...],
                                     val=[... the values ...])
        """

        if not hasattr(self, "picked_vals"):
            self.picked_vals = defaultdict(list)

        for key, val in kwargs.items():
            if key in ["pos", "ID", "val"]:
                self.picked_vals[key].append(val)

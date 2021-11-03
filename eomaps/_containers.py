from textwrap import dedent, indent, fill
from warnings import warn
from operator import attrgetter
from inspect import signature, _empty
from types import SimpleNamespace
from matplotlib.pyplot import get_cmap
from matplotlib.collections import PolyCollection, EllipseCollection, TriMesh

import mapclassify
from functools import update_wrapper, partial

from .callbacks import callbacks
from warnings import warn


class data_specs(object):
    """
    a container for accessing the data-properties
    """

    def __init__(
        self,
        m,
        data=None,
        xcoord=None,
        ycoord=None,
        crs=None,
        parameter=None,
    ):
        self._m = m
        self._data = None
        self._xcoord = None
        self._ycoord = None
        self._crs = None
        self._parameter = None

    def __repr__(self):
        txt = f"""\
              # parameter = {self.parameter}
              # coordinates = ({self.xcoord}, {self.ycoord})
              # crs: {indent(fill(self.crs.__repr__(), 60),
                              "                      ").strip()}

              # data:\
              {indent(self.data.__repr__(), "                ")}
              """

        return dedent(txt)

    def __getitem__(self, key):
        if isinstance(key, (list, tuple)):
            if "crs" in key:
                key[key.index("crs")] = "in_crs"

            for i in key:
                assert i in self.keys(), f"{i} is not a valid data-specs key!"
            if len(key) == 0:
                item = dict()
            else:
                key = list(key)
                if len(key) == 1:
                    item = {key[0]: getattr(self, key[0])}
                else:
                    item = dict(zip(key, attrgetter(*key)(self)))
        else:
            if key == "crs":
                key = "in_crs"
            assert key in self.keys(), f"{key} is not a valid data-specs key!"
            item = getattr(self, key)
        return item

    def __setitem__(self, key, val):
        key = self._sanitize_keys(key)
        return setattr(self, key, val)

    def __setattr__(self, key, val):
        key = self._sanitize_keys(key)
        super().__setattr__(key, val)

    def __iter__(self):
        return iter(self[self.keys()].items())

    def _sanitize_keys(self, key):
        # pass any keys starting with _
        if key.startswith("_"):
            return key

        if key == "crs":
            key = "in_crs"

        assert key in self.keys(), f"{key} is not a valid data-specs key!"

        return key

    def keys(self):
        return ("parameter", "xcoord", "ycoord", "in_crs", "data")

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data):
        self._data = data

    @property
    def crs(self):
        return self._crs

    @crs.setter
    def crs(self, crs):
        self._crs = crs

    in_crs = crs

    @property
    def xcoord(self):
        return self._xcoord

    @xcoord.setter
    def xcoord(self, xcoord):
        self._xcoord = xcoord

    @property
    def ycoord(self):
        return self._ycoord

    @ycoord.setter
    def ycoord(self, ycoord):
        self._ycoord = ycoord

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, parameter):
        self._parameter = parameter

    @parameter.getter
    def parameter(self):
        if self._parameter is None:
            if (
                self.data is not None
                and self.xcoord is not None
                and self.ycoord is not None
            ):

                try:
                    self.parameter = next(
                        i
                        for i in self.data.keys()
                        if i not in [self.xcoord, self.ycoord]
                    )
                    print(f"EOmaps: Parameter was set to: '{self.parameter}'")

                except Exception:
                    warn(
                        "EOmaps: Parameter-name could not be identified!"
                        + "\nCheck the data-specs!"
                    )
        return self._parameter


class map_objects(object):
    """
    A container for accessing objects of the generated figure

        - f : the matplotlib figure
        - ax : the geo-axes used for plotting the map
        - ax_cb : the axis of the colorbar
        - ax_cb_plot : the axis used to plot the histogram on top of the colorbar
        - cb : the matplotlib colorbar-instance
        - gridspec : the matplotlib GridSpec instance
        - cb_gridspec : the GridSpecFromSubplotSpec for the colorbar and the histogram
        - coll : the collection representing the data on the map

    """

    def __init__(
        self,
        f=None,
        ax=None,
        ax_cb=None,
        ax_cb_plot=None,
        cb=None,
        gridspec=None,
        cb_gridspec=None,
        coll=None,
        orientation=None,
    ):

        self.f = f
        self.ax = ax
        self.ax_cb = ax_cb
        self.ax_cb_plot = ax_cb_plot
        self.gridspec = gridspec
        self.cb_gridspec = cb_gridspec
        self.coll = coll
        self.orientation = orientation

    def set_items(self, **kwargs):
        for key, val in kwargs.items():
            setattr(self, key, val)

    @classmethod
    def reinit(cls, **kwargs):
        return cls(**kwargs)

    # @wraps(plt.Axes.set_position)
    def set_colorbar_position(self, pos=None, ratio=None, cb=None):
        """
        a wrapper to set the position of the colorbar and the histogram at
        the same time

        Parameters
        ----------
        pos : list    [left, bottom, width, height]
            The bounding-box of the colorbar & histogram in relative
            units [0,1] (with respect to the figure)
            If None the current position is maintained.
        ratio : float, optional
            The ratio between the size of the colorbar and the size of the histogram.
            'ratio=10' means that the histogram is 10 times as large as the colorbar!
            The default is None in which case the current ratio is maintained.
        cb : list, optional
            The colorbar-objects (as returned by `m.add_colorbar()`)
            If None, the existing colorbar will be used.
        """

        if cb is None:
            cb_gridspec, ax_cb, ax_cb_plot, orientation = [
                self.cb_gridspec,
                self.ax_cb,
                self.ax_cb_plot,
                "vertical" if self.orientation == "horizontal" else "horizontal",
            ]
        else:
            cb_gridspec, ax_cb, ax_cb_plot, orientation, _ = cb

        if orientation == "horizontal":
            if pos is None:
                pcb = ax_cb.get_position()
                pcbp = ax_cb_plot.get_position()

                pos = [pcb.x0, pcb.y0, pcb.width, pcb.height + pcbp.height]

            if ratio is None:
                hratio = cb_gridspec.get_height_ratios()
                ratio = hratio[0] / hratio[1]

            hcb = pos[3] / (1 + ratio)
            hp = ratio * hcb

            ax_cb.set_position(
                [pos[0], pos[1], pos[2], hcb],
            )
            ax_cb_plot.set_position(
                [pos[0], pos[1] + hcb, pos[2], hp],
            )

        elif orientation == "vertical":
            if pos is None:
                pcb = ax_cb.get_position()
                pcbp = ax_cb_plot.get_position()

                pos = [pcbp.x0, pcbp.y0, pcb.width + pcbp.width, pcb.height]

            if ratio is None:
                wratio = cb_gridspec.get_width_ratios()
                ratio = wratio[0] / wratio[1]

            wcb = pos[2] / (1 + ratio)
            wp = ratio * wcb

            ax_cb.set_position(
                [pos[0] + wp, pos[1], wcb, pos[3]],
            )
            ax_cb_plot.set_position(
                [pos[0], pos[1], wp, pos[3]],
            )
        else:
            raise TypeError(f"EOmaps: '{orientation}' is not a valid orientation")


class plot_specs(object):
    """
    a container for accessing the plot specifications
    """

    def __init__(self, m, **kwargs):
        self._m = m

        for key in kwargs:
            assert key in self.keys(), f"'{key}' is not a valid data-specs key"

        for key in self.keys():
            setattr(self, key, kwargs.get(key, None))

    def __repr__(self):
        txt = "\n".join(
            f"# {key}: {indent(fill(self[key].__repr__(), 60),  ' '*(len(key) + 4)).strip()}"
            for key in self.keys()
        )
        return txt

    def __getitem__(self, key):
        if isinstance(key, (list, tuple)):
            for i in key:
                assert i in self.keys(), f"{i} is not a valid plot-specs key!"
            if len(key) == 0:
                item = dict()
            else:
                key = list(key)
                if len(key) == 1:
                    item = {key[0]: getattr(self, key[0])}
                else:
                    item = dict(zip(key, attrgetter(*key)(self)))
        else:
            assert key in self.keys(), f"'{key}' is not a valid plot-specs key!"
            item = getattr(self, key)
        return item

    def __setitem__(self, key, val):
        key = self._sanitize_keys(key)
        return setattr(self, key, val)

    def __setattr__(self, key, val):
        key = self._sanitize_keys(key)

        super().__setattr__(key, val)

    def __iter__(self):
        return iter(self[self.keys()].items())

    def _sanitize_keys(self, key):
        # pass any keys starting with _
        if key.startswith("_"):
            return key

        if key == "plot_epsg":
            warn(
                "EOmaps: the plot-spec 'plot_epsg' has been depreciated... "
                + "try to use 'crs' or 'plot_crs' instead!"
            )
            key = "plot_crs"
        elif key == "crs":
            key = "plot_crs"

        assert key in self.keys(), f"{key} is not a valid plot-specs key!"

        return key

    def keys(self):
        # fmt: off
        return ('label', 'title', 'cmap', 'plot_crs', 'histbins', 'tick_precision',
                'vmin', 'vmax', 'cpos', 'cpos_radius', 'alpha', 'add_colorbar',
                'coastlines', 'density')
        # fmt: on

    @property
    def cmap(self):
        return self._cmap

    @cmap.getter
    def cmap(self):
        return self._cmap

    @cmap.setter
    def cmap(self, val):
        self._cmap = get_cmap(val)


class classify_specs(object):
    """
    a container for accessing the data classification specifications

    SCHEMES : accessor Namespace for the available classification-schemes

    """

    def __init__(self, m):
        self._defaults = dict()

        self._keys = set()
        self._m = m
        self.scheme = None

    def __repr__(self):
        txt = f"# scheme: {self.scheme}\n" + "\n".join(
            f"# {key}: {indent(fill(self[key].__repr__(), 60),  ' '*(len(key) + 4)).strip()}"
            for key in list(self.keys())
        )
        return txt

    def __getitem__(self, key):
        if isinstance(key, (list, tuple, set)):
            if len(key) == 0:
                item = dict()
            else:
                key = list(key)
                if len(key) == 1:
                    item = {key[0]: getattr(self, key[0])}
                else:
                    item = dict(zip(key, attrgetter(*key)(self)))
        else:
            item = getattr(self, key)
        return item

    def __setitem__(self, key, val):
        return setattr(self, key, val)

    def __setattr__(self, key, val):
        if not key.startswith("_") and key != "scheme":
            assert self.scheme is not None, "please specify the scheme first!"
            assert key in self._defaults, (
                f"The key is not a valid argument of the '{self.scheme}' classification!"
                + f" ...possible parameters are: {self._defaults}"
            )

            self._keys.add(key)

        super().__setattr__(key, val)

    def __iter__(self):
        return iter(self[self.keys()].items())

    def keys(self):
        return self._keys

    @property
    def scheme(self):
        return self._scheme

    @scheme.setter
    def scheme(self, val):
        self._scheme = val
        self._keys = set()
        s = self._get_default_args()
        if len(self._keys) > 0:
            print(f"EOmaps: classification has been reset to '{val}{s}'")
        for key, val in self._defaults.items():
            if val != _empty:
                setattr(self, key, val)

    def _get_default_args(self):
        if hasattr(self, "_scheme") and self._scheme is not None:
            assert self._scheme in mapclassify.CLASSIFIERS, (
                f"the classification-scheme '{self._scheme}' is not valid... "
                + " use one of:"
                + ", ".join(mapclassify.CLASSIFIERS)
            )
            s = signature(getattr(mapclassify, self._scheme))
            self._defaults = {
                key: val.default for key, val in s.parameters.items() if str(key) != "y"
            }
        else:
            self._defaults = dict()
            s = None
        return s

    def _set_scheme_and_args(self, scheme, **kwargs):
        reset = False
        if len(self._keys) > 0:
            reset = True
            self._keys = set()

        self._scheme = scheme
        _ = self._get_default_args()
        for key, val in self._defaults.items():
            setattr(self, key, val)
        for key, val in kwargs.items():
            setattr(self, key, val)

        args = (
            "("
            + ", ".join([f"{key}={self[key]}" for key, val in self._defaults.items()])
            + ")"
        )

        if reset:
            print(f"EOmaps: classification has been reset to '{scheme}{args}'")

    @property
    def SCHEMES(self):
        """
        accessor for possible classification schemes
        """
        return SimpleNamespace(
            **dict(zip(mapclassify.CLASSIFIERS, mapclassify.CLASSIFIERS))
        )


class cb_container(object):
    """
    A container for attaching callbacks and accessing return-objects.

    attach : accessor for callbacks.
        Executing the functions will attach the associated callback to the map!

    get : accessor for return-objects
        A container to provide easy-access to the return-values of the callbacks.

    """

    def __init__(self, m, parent=None):
        self._m = m
        self._cb = callbacks(m)

        self.get = self._get(self)
        self.attach = self._attach(self)

    def __repr__(self):
        txt = "Attached callbacks:\n    " + "\n    ".join(
            f"{val} : {key}" for key, val in self.get.attached_callbacks
        )
        return txt

    class _attach:
        """
        Attach custom or pre-defined callbacks to the map.

        Each callback takes 2 additional keyword-arguments:

        double_click : bool
            Indicator if the callback should be executed on double-click (True)
            or on single-click events (False). The default is False
        mouse_button : int
            The mouse-button to use for executing the callback:

                - LEFT = 1
                - MIDDLE = 2
                - RIGHT = 3
                - BACK = 8
                - FORWARD = 9

            The default is 1

        For additional keyword-arguments check the doc of the callback-functions!

        Examples:
        ---------
        Get a (temporary) annotation on a LEFT-double-click:

            >>> m.cb.attach.annotate(double_click=True, mouse_button=1, permanent=False)
        Permanently color LEFT-clicked pixels red with a black border:

            >>> m.cb.attach.mark(facecolor="r", edgecolor="k", permanent=True)
        Attach a customly defined callback

            >>> def some_callback(self, asdf, **kwargs):
            >>>     print("hello world")
            >>>     print("the position of the clicked pixel", kwargs["pos"])
            >>>     print("the data-index of the clicked pixel", kwargs["ID"])
            >>>     print("data-value of the clicked pixel", kwargs["val"])
            >>>     print("the plot-crs is:", self.plot_specs["plot_crs"])

            >>> m.cb.attach(some_callback, double_click=False, mouse_button=1, asdf=1)


        """

        def __init__(self, parent):
            self.parent = parent

            # attach all existing pre-defined callbacks
            for cb in callbacks._cb_list:
                setattr(
                    self,
                    cb,
                    update_wrapper(
                        partial(self.parent._add_callback, callback=cb),
                        getattr(self.parent._cb, cb),
                    ),
                )

            self.custom = self.parent._add_callback

        def __call__(self, f, double_click=False, mouse_button=1, **kwargs):
            """
            add a custom callback-function to the map

            Parameters
            ----------
            f : callable
                the function to attach to the map.
                The call-signature is:

                >>> def some_callback(self, **kwargs):
                >>>     print("hello world")
                >>>     print("the position of the clicked pixel", kwargs["pos"])
                >>>     print("the data-index of the clicked pixel", kwargs["ID"])
                >>>     print("data-value of the clicked pixel", kwargs["val"])
                >>>     print("the plot-crs is:", self.plot_specs["plot_crs"])
                >>>
                >>> m.cb.attach.custom(some_callback)


            double_click : bool
                Indicator if the callback should be executed on double-click (True)
                or on single-click events (False)
            mouse_button : int
                The mouse-button to use for executing the callback:

                    - LEFT = 1
                    - MIDDLE = 2
                    - RIGHT = 3
                    - BACK = 8
                    - FORWARD = 9
            **kwargs :
                kwargs passed to the callback-function
                For documentation of the individual functions check the docs in `m.cb`


            Returns
            -------
            cid : int
                the ID of the attached callback

            """
            return self.parent._add_callback(f, double_click, mouse_button, **kwargs)

    class _get:
        def __init__(self, parent):
            self.m = parent._m
            self.cb = parent._cb

            from collections import defaultdict

            self.cbs = defaultdict(lambda: defaultdict(dict))

        @property
        def picked_object(self):
            if hasattr(self.cb, "picked_object"):
                return self.cb.picked_object
            else:
                print("EOmaps: attach the 'load' callback first!")

        @property
        def picked_vals(self):
            if hasattr(self.cb, "picked_vals"):
                return self.cb.picked_vals
            else:
                print("EOmaps: attach the 'get_vals' callback first!")

        @property
        def permanent_markers(self):
            if hasattr(self.cb, "permanent_markers"):
                return self.cb.permanent_markers
            else:
                print("EOmaps: attach the 'mark' callback with 'permanent=True' first!")

        @property
        def marker(self):
            if hasattr(self.cb, "marker"):
                return self.cb.marker
            else:
                print(
                    "EOmaps: attach the 'mark' callback with 'permanent=False' first!"
                )

        @property
        def attached_callbacks(self):
            cbs = []
            for ds, dsdict in self.cbs.items():
                for b, bdict in dsdict.items():
                    for name in bdict.keys():
                        cbs.append(f"{name}__{ds}__{b}")

            return cbs

    def _add_callback(self, callback, double_click=False, mouse_button=1, **kwargs):
        """
        Attach a callback to the plot that will be executed if a pixel is clicked

        A list of pre-defined callbacks (accessible via `m.cb`) or customly defined
        functions can be used.

            >>> # to add a pre-defined callback use:
            >>> cid = m._add_callback("annotate", <kwargs passed to m.cb.annotate>)
            >>> # to remove the callback again, call:
            >>> m.remove_callback(cid)

        Parameters
        ----------
        callback : callable or str
            The callback-function to attach.

            If a string is provided, it will be used to assign the associated function
            from the `m.cb` collection:
                - "annotate" : add annotations to the clicked pixel
                - "mark" : add markers to the clicked pixel
                - "plot" : dynamically update a plot with the clicked values
                - "print_to_console" : print info of the clicked pixel to the console
                - "get_values" : save properties of the clicked pixel to a dict
                - "load" : use the ID of the clicked pixel to load data
                - "clear_annotations" : clear all existing annotations
                - "clear_markers" : clear all existing markers

            You can also define a custom function with the following call-signature:
                >>> def some_callback(self, asdf, **kwargs):
                >>>     print("hello world")
                >>>     print("the position of the clicked pixel", kwargs["pos"])
                >>>     print("the data-index of the clicked pixel", kwargs["ID"])
                >>>     print("data-value of the clicked pixel", kwargs["val"])
                >>>     print("the plot-crs is:", self.m.plot_specs["plot_crs"])
                >>>     print("asdf is:", asdf)

                >>> m.cb.attach(some_callback, double_click=False, mouse_button=1, asdf=1)

        double_click : bool
            Indicator if the callback should be executed on double-click (True)
            or on single-click events (False)
        mouse_button : int
            The mouse-button to use for executing the callback:

                - LEFT = 1
                - MIDDLE = 2
                - RIGHT = 3
                - BACK = 8
                - FORWARD = 9
        **kwargs :
            kwargs passed to the callback-function
            For documentation of the individual functions check the docs in `m.cb`

        Returns
        -------
        cbname : str
            the identification string of the callback
            (to remove the callback, use `m.cb.remove(cbname)`)

        """

        assert not all(
            i in kwargs for i in ["pos", "ID", "val", "double_click", "mouse_button"]
        ), 'the names "pos", "ID", "val" cannot be used as keyword-arguments!'

        if isinstance(callback, str):
            assert hasattr(self._cb, callback), (
                f"The function '{callback}' does not exist as a pre-defined callback."
                + " Use one of:\n    - "
                + "\n    - ".join(callbacks._cb_list)
            )
            callback = getattr(self._cb, callback)
        elif callable(callback):
            # re-bind the callback methods to the eomaps.Maps.cb object
            # in case custom functions are used
            if hasattr(callback, "__func__"):
                callback = callback.__func__.__get__(self._m)
            else:
                callback = callback.__get__(self._m)

        # make sure multiple callbacks of the same funciton are only assigned
        # if multiple assignments are properly handled
        multi_cb_functions = ["mark", "annotate"]

        if double_click:
            d = self.get.cbs["double"][mouse_button]
        else:
            d = self.get.cbs["single"][mouse_button]

        # get a unique name for the callback
        ncb = [int(i.rsplit("_", 1)[1]) for i in d if i.startswith(callback.__name__)]
        cbkey = callback.__name__ + f"_{max(ncb) + 1 if len(ncb) > 0 else 0}"

        if callback.__name__ not in multi_cb_functions:
            assert len(ncb) == 0, (
                "Multiple assignments of the callback"
                + f" '{callback.__name__}' are not (yet) supported..."
            )

        d[cbkey] = partial(callback, **kwargs)

        # add mouse-button assignment as suffix to the name (with __ separator)
        cbname = cbkey + f"__{'double' if double_click else 'single'}__{mouse_button}"

        return cbname

    def _get_clickdict(self, event):
        ind = event.ind
        if ind is not None:
            if isinstance(
                event.artist,
                (
                    EllipseCollection,
                    PolyCollection,
                    TriMesh,
                ),
            ):
                clickdict = dict(
                    pos=(self._m._props["x0"][ind], self._m._props["y0"][ind]),
                    ID=self._m._props["ids"][ind],
                    val=self._m._props["z_data"][ind],
                    ind=ind,
                )

                return clickdict

    def _add_pick_callback(self):
        # ------------- add a callback
        def onpick(event):
            self.event = event
            if event.artist != self._m.figure.coll:
                return
            else:
                clickdict = self._get_clickdict(event)

            if event.double_click:
                cbs = self.get.cbs["double"]
            else:
                cbs = self.get.cbs["single"]

            if event.mouse_button in cbs:
                for key, cb in cbs[event.mouse_button].items():
                    if clickdict is not None:
                        cb(**clickdict)
                    else:
                        if hasattr(
                            self._cb, f"_{key.rsplit('_', 1)[0]}_nopick_callback"
                        ):
                            getattr(
                                self._cb, f"_{key.rsplit('_', 1)[0]}_nopick_callback"
                            )()

            self._m.BM.update()

        self._m.figure.f.canvas.mpl_connect("pick_event", onpick)

    def remove(self, ID=None):
        """
        remove an attached callback from the figure

        Parameters
        ----------
        callback : int, str or tuple
            if str: the name of the callback to remove
                    (`<function_name>_<count>__<double/single>__<button_ID>`)
        """
        if ID is not None:
            name, ds, b = ID.split("__")

        dsdict = self.get.cbs.get(ds, None)
        if dsdict is not None:
            bdict = dsdict.get(int(b))
        else:
            return

        if bdict is not None:
            if name in bdict:
                del bdict[name]

                # call cleanup methods on removal
                fname = name.rsplit("_", 1)[0]
                if hasattr(self._cb, f"_{fname}_cleanup"):
                    getattr(self._cb, f"_{fname}_cleanup")()

                print(f"Removed the callback: '{ID}'.")

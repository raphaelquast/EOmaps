# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Base class for Maps objects."""

import gc
import logging
from contextlib import ExitStack
from pyproj import CRS, Transformer
from functools import lru_cache, wraps
from itertools import chain
import weakref

import numpy as np

from cartopy import crs as ccrs

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, SubplotSpec

_log = logging.getLogger(__name__)

from .helpers import _parse_log_level
from .layout_editor import LayoutEditor
from ._blit_manager import BlitManager
from .projections import Equi7Grid_projection  # import also supercharges cartopy.ccrs


def _handle_backends():
    from .eomaps import Maps  # TODO

    # make sure that the backend is activated
    # (backends are loaded lazily and values such as plt.isinteractive() might not
    # yet show the correct value in case the backend is not yet fully loaded)

    # This is especially important for the IPython/inline backend which explicitly
    # calls plt.ion() when the backend is loaded.
    # (see https://github.com/matplotlib/matplotlib/issues/26221)
    plt.install_repl_displayhook()

    active_backend = plt.get_backend()

    # to avoid flickering in the layout editor in jupyter notebooks
    if active_backend in ["module://ipympl.backend_nbagg"]:
        plt.ioff()
    else:
        if Maps._use_interactive_mode is True:
            plt.ion()
            _log.debug(
                "EOmaps: matplotlib's interactive mode is turned on. "
                "Maps will show up immediately and the console is NOT blocking! "
                "To change, use Maps.config(use_interactive_mode=True/False)."
            )
        elif Maps._use_interactive_mode is False:
            plt.ioff()
            _log.debug(
                "EOmaps: matplotlib's interactive mode is turned off. "
                "Call `m.show()` to show the map (and block the console)! "
                "To change, use Maps.config(use_interactive_mode=True/False)."
            )


class _MapsMeta(type):
    _use_interactive_mode = None
    _always_on_top = False

    _backend_warning_shown = False

    def config(
        cls,
        snapshot_on_update=None,
        companion_widget_key=None,
        always_on_top=None,
        use_interactive_mode=None,
        log_level=None,
    ):
        """
        Set global configuration parameters for figures created with EOmaps.

        This function must be called before initializing any :py:class:`Maps` object!

        >>> from eomaps import Maps
        >>> Maps.config(always_on_top=True)

        (parameters set to None are NOT updated!)

        Parameters
        ----------
        snapshot_on_update : bool, optional
            Only relevant when using an IPython console or a jupyter notebook together
            with the `inline` backend! (e.g. using `%matplotlib inline`)

            - If True, figure updates automatically trigger drawing a snapshot
              of the current state of the figure to the active cell.
            - If False, an explicit call to `m.show()` is required to draw the figure.

            The default is True.
        companion_widget_key : str, optional
            The keyboard shortcut to use for activating the companion-widget.
            The default is "w".
        always_on_top : bool, optional
            Only relevant if `PyQt5` is used as matplotlib backend.

            - If True, the figure will be kept "always on top" of other applications.

            The default is False.
        use_interactive_mode : bool or None, optional
            If True, matplotlibs interactive mode (`plt.ion()`) is activated by default
            for all backends except jupyter-notebook backends (`inline` and `ipympl`).

            If False, interactive mode is turned off (`plt.ioff()` and a call
            to `m.show()` is required to trigger showing the figure!
            Note that this will block the terminal!

            If None, No changes are applied.

            The default is True.
        log_level : str or int, optional
            The logging level.
            If set, a StreamHandler will be attached to the logger that prints to
            the active terminal at the specified log level.

            See :py:meth:`set_loglevel` on how to customize logging format.

            The default is None.
        """

        from . import set_loglevel

        if companion_widget_key is not None:
            cls._companion_widget_key = companion_widget_key

        if always_on_top is not None:
            cls._always_on_top = always_on_top

        if snapshot_on_update is not None:
            BlitManager._snapshot_on_update = snapshot_on_update

        if use_interactive_mode is not None:
            cls._use_interactive_mode = use_interactive_mode

        if log_level is not None:
            set_loglevel(log_level)

    def apply_webagg_fix(cls):
        """
        Apply fix to avoid slow updates and lags due to event-accumulation in webagg backend.

        (e.g. when using `matplotlib.use("webagg")`)

        - Events that occur while draws are pending are dropped and only the
          last event of each type that occurred during the wait is finally executed.

        Note
        ----

        Using this fix is **experimental** and will monkey-patch matplotlibs
        `FigureCanvasWebAggCore` and `FigureManagerWebAgg` to avoid event accumulation!

        You MUST call this function at the very beginning of the script to ensure
        changes are applied correctly!

        There might be unwanted side-effects for callbacks that require all events
        to be executed consecutively independent of the draw-state (e.g. typing text).

        """
        from matplotlib.backends.backend_webagg_core import (
            FigureCanvasWebAggCore,
            FigureManagerWebAgg,
        )

        def handle_ack(self, event):
            self._ack_cnt += 1  # count the number of received images

        def refresh_all(self):
            if self.web_sockets:
                diff = self.canvas.get_diff_image()
                if diff is not None:
                    for s in self.web_sockets:
                        s.send_binary(diff)

                    self._send_cnt += 1  # count the number of sent images

        def handle_event(self, event):
            if not hasattr(self, "_event_cache"):
                self._event_cache = dict()

            cnt_equal = self._ack_cnt == self.manager._send_cnt

            # always process ack and draw events
            # process other events only if "ack count" equals "send count"
            # (e.g. if we received and handled all pending images)
            if cnt_equal or event["type"] in ["ack", "draw"]:
                # immediately process all cached events
                for cache_event_type, cache_event in self._event_cache.items():
                    getattr(
                        self,
                        "handle_{0}".format(cache_event_type),
                        self.handle_unknown_event,
                    )(cache_event)
                self._event_cache.clear()

                # reset counters to avoid overflows (just a precaution to avoid overflows)
                if cnt_equal:
                    self._ack_cnt, self.manager._send_cnt = 0, 0

                # process event
                e_type = event["type"]
                handler = getattr(
                    self, "handle_{0}".format(e_type), self.handle_unknown_event
                )
            else:
                # ignore events in case we have a pending image that is on the way to be processed
                # cache the latest event of each type so we can process it once we are ready
                self._event_cache[event["type"]] = event

                # a final safety precaution in case send count is lower than ack count
                # (e.g. we wait for an image but there was no image sent)
                if self.manager._send_cnt < self._ack_cnt:
                    # reset counts... they seem to be incorrect
                    self._ack_cnt, self.manager._send_cnt = 0, 0
                return

            return handler(event)

        FigureCanvasWebAggCore._ack_cnt = 0
        FigureCanvasWebAggCore.handle_ack = handle_ack
        FigureCanvasWebAggCore.handle_event = handle_event

        FigureManagerWebAgg._send_cnt = 0
        FigureManagerWebAgg.refresh_all = refresh_all


class MapsBase(metaclass=_MapsMeta):
    def __init__(
        self,
        crs=None,
        layer="base",
        f=None,
        ax=None,
        **kwargs,
    ):

        self._BM = None
        self._layout_editor = None

        # make sure the used layer-name is valid
        layer = BlitManager._check_layer_name(layer)
        self._layer = layer

        if isinstance(ax, plt.Axes) and hasattr(ax, "figure"):
            if isinstance(ax.figure, plt.Figure):
                if f is not None:
                    assert (
                        f == ax.figure
                    ), "EOmaps: The provided axis is in a different figure!"

                self._f = ax.figure
        else:
            self._f = f

        self._ax = None
        self._parent = None
        self._children = set()  # weakref.WeakSet()
        self._after_add_child = list()

        # check if the self represents a new-layer or an object on an existing layer
        if any(
            i.layer == layer for i in (self.parent, *self.parent._children) if i != self
        ):
            self._is_sublayer = True
        else:
            self._is_sublayer = False

        if isinstance(ax, plt.Axes):
            # set the plot_crs only if no explicit axes is provided
            if crs is not None:
                raise AssertionError(
                    "You cannot set the crs if you already provide an explicit axes!"
                )
            if hasattr(ax, "projection"):
                if ax.projection == ccrs.PlateCarree():
                    self._crs_plot = 4326
                else:
                    self._crs_plot = ax.projection
        else:
            if crs is None or crs == ccrs.PlateCarree():
                crs = 4326

            self._crs_plot = crs

        self._init_figure(**kwargs)

        # Make sure the figure-background patch is on an explicit layer
        # This is used to avoid having the background patch on each fetched
        # background while maintaining the capability of restoring it
        if self.f.patch not in self.BM._bg_artists.get("__BG__", []):
            self.f.patch.set_zorder(-2)
            self.BM.add_bg_artist(self.f.patch, layer="__BG__")

        self._init_axes(ax=ax, plot_crs=crs, **kwargs)

        if self.ax.patch not in self.BM._bg_artists.get("__BG__", []):
            self.ax.patch.set_zorder(-1)
            self.BM.add_bg_artist(self.ax.patch, layer="__BG__")

        # Treat cartopy geo-spines separately in the blit-manager
        # to avoid issues with overlapping spines that are drawn on each layer
        # if multiple layers of a map are combined.
        # (Note: spines need to be visible on each layer in case the layer
        # is viewed on its own, but overlapping spines cause blurry boundaries)
        # TODO find a better way to deal with this!
        self._handle_spines()

        self._crs_plot_cartopy = self._get_cartopy_crs(self._crs_plot)

    def __repr__(self):
        try:
            return f"<eomaps.Maps object on layer '{self.layer}'>"
        except Exception:
            return object.__repr__(self)

    def __getattribute__(self, key):
        if key == "set_layout":
            raise AttributeError(
                "'Maps' object has no attribute 'set_layout'... "
                "did you mean 'apply_layout'?"
            )
        else:
            return object.__getattribute__(self, key)

    def __enter__(self):
        assert not self._is_sublayer, (
            "EOmaps: using a Maps-object as a context-manager is only possible "
            "if you create a NEW layer (not a Maps-object on an existing layer)!"
        )

        return self

    def __exit__(self, type, value, traceback):
        self.cleanup()
        if self.parent == self:
            plt.close(self.f)
        gc.collect()

    def _emit_signal(self, *args, **kwargs):
        # TODO
        pass

    def _handle_spines(self):
        # put cartopy spines on a separate layer
        for spine in self.ax.spines.values():
            if spine and spine not in self.BM._bg_artists.get("__SPINES__", []):
                self.BM.add_bg_artist(spine, layer="__SPINES__")

    def _on_resize(self, event):
        # make sure the background is re-fetched if the canvas has been resized
        # (required for peeking layers after the canvas has been resized
        #  and for webagg and nbagg backends to correctly re-draw the layer)

        self.BM._refetch_bg = True
        self.BM._refetch_blank = True

        # update the figure dimensions in case shading is used.
        # Avoid flushing events during resize
        # TODO
        if hasattr(self, "_update_shade_axis_size"):
            self._update_shade_axis_size(flush=False)

    def _on_close(self, event):
        # reset attributes that might use up a lot of memory when the figure is closed
        for m in [self.parent, *self.parent._children]:
            if hasattr(m.f, "_EOmaps_parent"):
                m.f._EOmaps_parent = None

            m.cleanup()

        # run garbage-collection to immediately free memory
        gc.collect

    def _on_xlims_change(self, *args, **kwargs):
        self.BM._refetch_bg = True

    def _on_ylims_change(self, *args, **kwargs):
        self.BM._refetch_bg = True

    @property
    def BM(self):
        """The Blit-Manager used to dynamically update the plots."""
        m = weakref.proxy(self)
        if self.parent._BM is None:
            self.parent._BM = BlitManager(m)
            self.parent._BM._bg_layer = m.parent.layer
        return self.parent._BM

    @property
    def ax(self):
        """The matplotlib (cartopy) GeoAxes associated with this Maps-object."""
        return self._ax

    @property
    def f(self):
        """The matplotlib Figure associated with this Maps-object."""
        # always return the figure of the parent object
        return self._f

    @property
    def layer(self):
        """The layer-name associated with this Maps-object."""
        return self._layer

    @property
    def all(self):
        """
        Get a Maps-object on the "all" layer.

        Use it just as any other Maps-object. (It's the same as `Maps(layer="all")`)

        >>> m.all.cb.click.attach.annotate()

        """
        if not hasattr(self, "_all"):
            self._all = self.new_layer("all")
        return self._all

    @property
    def parent(self):
        """
        The parent-object to which this Maps-object is connected to.

        If None, `self` is returned!
        """
        if self._parent is None:
            self._set_parent()

        return self._parent

    def _init_figure(self, **kwargs):
        if self.parent.f is None:
            # do this on any new figure since "%matplotlib inline" tries to re-activate
            # interactive mode all the time!
            _handle_backends()

            self._f = plt.figure(**kwargs)
            # to hide canvas header in jupyter notebooks (default figure label)
            self._f.canvas.header_visible = False

            _log.debug("EOmaps: New figure created")

            # make sure we keep a "real" reference otherwise overwriting the
            # variable of the parent Maps-object while keeping the figure open
            # causes all weakrefs to be garbage-collected!
            self.parent.f._EOmaps_parent = self.parent._real_self
        else:
            if not hasattr(self.parent.f, "_EOmaps_parent"):
                self.parent.f._EOmaps_parent = self.parent._real_self
            self.parent._add_child(self)

        if self.parent == self:  # use == instead of "is" since the parent is a proxy!

            # override Figure.savefig with Maps.savefig but keep original
            # method accessible via Figure._mpl_orig_savefig
            # (this ensures that using the save-buttons in the gui or pressing
            # control+s will redirect the save process to the eomaps routine)
            self._f._mpl_orig_savefig = self._f.savefig
            self._f.savefig = self.savefig

            # only attach resize- and close-callbacks if we initialize a parent
            # Maps-object
            # attach a callback that is executed when the figure is closed
            self._cid_onclose = self.f.canvas.mpl_connect("close_event", self._on_close)
            # attach a callback that is executed if the figure canvas is resized
            self._cid_resize = self.f.canvas.mpl_connect(
                "resize_event", self._on_resize
            )

        # if we haven't attached an axpicker so far, do it!
        if self.parent._layout_editor is None:
            self.parent._layout_editor = LayoutEditor(self.parent, modifier="alt+l")

        active_backend = plt.get_backend()

        if active_backend == "module://matplotlib_inline.backend_inline":
            # close the figure to avoid duplicated (empty) plots created
            # by the inline-backend manager in jupyter notebooks
            plt.close(self.f)

    def _init_axes(self, ax, plot_crs, **kwargs):
        if isinstance(ax, plt.Axes):
            # check if the axis is already used by another maps-object
            if ax not in (i.ax for i in (self.parent, *self.parent._children)):
                newax = True
                ax.set_animated(True)
                # make sure axes are drawn once to properly set transforms etc.
                # (otherwise pan/zoom, ax.contains_point etc. will not work)
                ax.draw(self.f.canvas.get_renderer())

            else:
                newax = False
        else:
            newax = True
            # create a new axis
            if ax is None:
                gs = GridSpec(
                    nrows=1, ncols=1, left=0.01, right=0.99, bottom=0.05, top=0.95
                )
                gsspec = [gs[:]]
            elif isinstance(ax, SubplotSpec):
                gsspec = [ax]
            elif isinstance(ax, (list, tuple)) and len(ax) == 4:
                # absolute position
                l, b, w, h = ax

                gs = GridSpec(
                    nrows=1, ncols=1, left=l, bottom=b, right=l + w, top=b + h
                )
                gsspec = [gs[:]]
            elif isinstance(ax, int) and len(str(ax)) == 3:
                gsspec = [ax]
            elif isinstance(ax, tuple) and len(ax) == 3:
                gsspec = ax
            else:
                raise TypeError("EOmaps: The provided value for 'ax' is invalid.")

            projection = self._get_cartopy_crs(plot_crs)

            ax = self.f.add_subplot(
                *gsspec,
                projection=projection,
                aspect="equal",
                adjustable="box",
                label=self._get_ax_label(),
                animated=True,
            )
            # make sure axes are drawn once to properly set transforms etc.
            # (otherwise pan/zoom, ax.contains_point etc. will not work)
            ax.draw(self.f.canvas.get_renderer())

        self._ax = ax
        self._gridspec = ax.get_gridspec()

        # add support for "frameon" kwarg
        if kwargs.get("frameon", True) is False:
            self.ax.spines["geo"].set_edgecolor("none")

        if newax:  # only if a new axis has been created
            self._new_axis_map = True

            # explicitly set initial limits to global to avoid issues if NE-features
            # are added (and clipped) before actual limits are set
            # TODO
            if hasattr(self.ax, "set_global"):
                self.ax.set_global()

            self._cid_xlim = self.ax.callbacks.connect(
                "xlim_changed", self._on_xlims_change
            )
            self._cid_xlim = self.ax.callbacks.connect(
                "ylim_changed", self._on_ylims_change
            )
        else:
            self._new_axis_map = False

    def _get_ax_label(self):
        return "map"

    def _set_parent(self):
        """Identify the parent object."""
        assert self._parent is None, "EOmaps: There is already a parent Maps object!"
        # check if the figure to which the Maps-object is added already has a parent
        parent = None
        if getattr(self._f, "_EOmaps_parent", False):
            parent = self._proxy(self._f._EOmaps_parent)

        if parent is None:
            parent = self

        self._parent = self._proxy(parent)

        if parent not in [self, None]:
            # add the child to the topmost parent-object
            self.parent._add_child(self)

    @staticmethod
    def _proxy(obj):
        # None cannot be weak-referenced!
        if obj is None:
            return None

        # create a proxy if the object is not yet a proxy
        if type(obj) is not weakref.ProxyType:
            return weakref.proxy(obj)
        else:
            return obj

    @property
    def _real_self(self):
        # workaround to obtain a non-weak reference for the parent
        # (e.g. self.parent._real_self is a non-weak ref to parent)
        # see https://stackoverflow.com/a/49319989/9703451
        return self

    def _add_child(self, m):
        self.parent._children.add(m)

        # execute hooks to notify the gui that a new child was added
        for action in self._after_add_child:
            try:
                action()
            except Exception:
                _log.exception("EOmaps: Problem executing 'on_add_child' action:")

    def redraw(self, *args):
        """
        Force a re-draw of cached background layers.

        - Use this at the very end of your code to trigger a final re-draw
          to make sure artists not managed by EOmaps are properly drawn!

        Note
        ----
        Don't use this to interactively update artists on a map!
        since it will trigger a re-draw background-layers!

        To dynamically re-draw an artist whenever you interact with the map, use:

        >>> m.BM.add_artist(artist)

        To make an artist temporary (e.g. remove it on the next event), use
        one of :

        >>> m.cb.click.add_temporary_artist(artist)
        >>> m.cb.pick.add_temporary_artist(artist)
        >>> m.cb.keypress.add_temporary_artist(artist)
        >>> m.cb.move.add_temporary_artist(artist)

        Parameters
        ----------
        *args : str
            Positional arguments provided to redraw are identified as layer-names
            that should be re-drawn. If no arguments are provided, all layers
            are re-drawn!

        """
        if len(args) == 0:
            # in case no argument is provided, force a complete re-draw of
            # all layers (and datasets) of the map
            self.BM._refetch_bg = True
        else:
            # only re-fetch the required layers
            for l in args:
                self.BM._refetch_layer(l)

        self.f.canvas.draw_idle()

    def show_layer(self, *args, clear=True):
        """
        Show a single layer or (transparently) overlay multiple selected layers.

        Parameters
        ----------
        args : str, tuple

            - if str: The name of the layer to show.
            - if tuple: A combination of a layer-name and a transparency assignment
              ( < layer name >, < transparency [0-1] > )

        Examples
        --------
        Show a **single layer** by providing the name of the layer as string:

        >>> m.show_layer("A")

        To show **multiple layers**, use one of the following options:

        Provide multiple layer-names (stacking is done from left to right), e.g.:

        >>> m.show_layer("A", "B", "C")

        Provide the combined layer-name, e.g.:

        >>> m.show_layer("A|B|C")

        To **transparently overlay multiple layers**, use one of the following options:

        Provide tuples of layer-names and transparency-assignments, e.g.:

        >>> m.show_layer("A", ("B", 0.5), ("C", 0.25))

        Provide the combined layer-name, e.g.:

        >>> m.show_layer("A|B{0.5}|C{0.25}")

        See Also
        --------
        Maps.util.layer_selector : Add a button-widget to switch layers to the map.
        Maps.util.layer_slider : Add a slider to switch layers to the map.

        """
        name = self.BM._get_combined_layer_name(*args)
        if not isinstance(name, str):
            _log.info("EOmaps: All layer-names are converted to strings!")
            name = str(name)

        # check if all layers exist
        existing_layers = self._get_layers()
        layers_to_show, _ = self.BM._parse_multi_layer_str(name)

        # don't check private layer-names
        layers_to_show = [i for i in layers_to_show if not i.startswith("_")]
        missing_layers = set(layers_to_show).difference(set(existing_layers))
        if len(missing_layers) > 0:
            lstr = " - " + "\n - ".join(map(str, existing_layers))

            _log.error(
                f"EOmaps: The layers {missing_layers} do not exist...\n"
                + f"Use one of: \n{lstr}"
            )
            return

        # invoke the bg_layer setter of the blit-manager
        self.BM.bg_layer = name
        self.BM.update()

        # plot a snapshot to jupyter notebook cell if inline backend is used
        if not self.BM._snapshot_on_update and plt.get_backend() in [
            "module://matplotlib_inline.backend_inline"
        ]:
            self.snapshot(clear=clear)

    def show(self, clear=True):
        """
        Show the map (only required for non-interactive matplotlib backends).

        This is just a convenience function to call matplotlib's `plt.show()`!

        To switch the currently visible layer, see :py:meth:`Maps.show_layer`

        Parameters
        ----------
        clear : bool, optional
            Only relevant if the `inline` backend is used in a jupyter-notebook
            or an Ipython console.

            If True, clear the active cell before plotting a snapshot of the figure.
            The default is True.
        See Also
        --------
        show_layer : Set the currently visible layer.
        """

        try:
            __IPYTHON__
        except NameError:
            plt.show()
        else:
            active_backend = plt.get_backend()
            # print a snapshot to the active ipython cell in case the
            # inline-backend is used
            if active_backend in ["module://matplotlib_inline.backend_inline"]:
                self.snapshot(clear=clear)
            else:
                plt.show()

    def fetch_layers(self, layers=None):
        """
        Fetch (and cache) the layers of a map.

        This is particularly useful if you want to use sliders or buttons to quickly
        switch between the layers (e.g. once the backgrounds are cached, switching
        layers will be fast).

        Note: After zooming or re-sizing the map, the cache is cleared and
        you need to call this function again.

        Parameters
        ----------
        layers : list or None, optional
            A list of layer-names that should be fetched.
            If None, all layers (except the "all" layer) are fetched.
            The default is None.

        See Also
        --------
        Maps.cb.keypress.attach.fetch_layers : use a keypress callback to fetch layers

        """
        active_layer = self.BM._bg_layer
        all_layers = self._get_layers()

        if layers is None:
            layers = all_layers
            if "all" in layers:
                layers.remove("all")  # don't explicitly fetch the "all" layer
        else:
            if not set(layers).issubset(all_layers):
                raise AssertionError(
                    "EOmaps: Unable to fetch the following layers:\n - "
                    + "\n - ".join(set(layers).difference(all_layers))
                )

        nlayers = len(layers)
        assert nlayers > 0, "EOmaps: There are no layers to fetch."

        for i, l in enumerate(layers):
            _log.info(f"EOmaps: fetching layer {i + 1}/{nlayers}: {l}")
            self.show_layer(l)

        self.show_layer(active_layer)
        self.BM.update()

    def _get_layers(self, exclude=None, exclude_private=True):
        # return a list of all (empty and non-empty) layer-names
        layers = set((m.layer for m in (self.parent, *self.parent._children)))
        # add layers that are not yet activated (but have an activation
        # method defined...)
        layers = layers.union(set(self.BM._on_layer_activation[True]))
        layers = layers.union(set(self.BM._on_layer_activation[False]))

        # add all (possibly still invisible) layers with artists defined
        # (ONLY do this for unique layers... skip multi-layers )
        layers = layers.union(
            chain(
                *(
                    self.BM._parse_multi_layer_str(i)[0]
                    for i in (*self.BM._bg_artists, *self.BM._artists)
                )
            )
        )

        # exclude private layers
        if exclude_private:
            # for python <3.9 compatibility
            def remove_prefix(text, prefix):
                if text.startswith(prefix):
                    return text[len(prefix) :]
                return text

            layers = {remove_prefix(i, "__inset_") for i in layers}
            layers = {i for i in layers if not i.startswith("__")}

        if exclude:
            for i in exclude:
                if i in layers:
                    layers.remove(i)

        # sort the layers
        layers = sorted(layers, key=lambda x: str(x))

        return layers

    def snapshot(self, *layer, transparent=False, clear=False):
        """
        Print a static image of the figure to the active IPython display.

        This is useful if you want to print a snapshot of the current state of the map
        to the active Jupyter Notebook cell or the currently active IPython console
        while using a backend that creates popup-plots (e.g. `qt` or `tkinter`)

        ONLY use this if you work in an interactive IPython terminal, a Jupyter
        Notebook or a Jupyter Lab environment!

        Parameters
        ----------
        *layer: str or None
            The layer to show on the snapshot.
            Any positional arguments are used as layer-assignments similar
            to `m.show_layer()`
            If None, the currently visible layer is used.
            The default is None.
        transparent: bool
            Indicator if the snapshot should have a transparent background or not.
            The default is False.
        clear: bool
            Indicator if the current cell-output should be cleared prior
            to showing the snapshot or not. The default is False

        Examples
        --------
        >>> m = Maps(layer="base")
        >>> m.add_feature.preset.coastline()
        >>> m2 = m.new_layer("ocean")
        >>> m.add_feature.preset.ocean()
        >>> m.snapshot("base", ("ocean", .5), transparent=True)

        """
        if getattr(self, "_snapshotting", False):
            # this is necessary to avoid recursions with show_layer
            # in jupyter-notebook inline backend
            return

        try:
            self._snapshotting = True

            from PIL import Image

            with ExitStack() as stack:
                # don't clear on layer-changes
                stack.enter_context(self.BM._cx_dont_clear_on_layer_change())

                if len(layer) == 0:
                    layer = None

                if layer is not None:
                    layer = self.BM._get_combined_layer_name(*layer)

                # add the figure background patch as the bottom layer
                initial_layer = self.BM.bg_layer

                if transparent is False:
                    showlayer_name = self.BM._get_showlayer_name(
                        layer=layer, transparent=transparent
                    )
                    self.show_layer(showlayer_name)
                    sn = self._get_snapshot()
                    # restore the previous layer
                    self.BM._refetch_layer(showlayer_name)
                    self.show_layer(initial_layer)
                else:
                    if layer is not None:
                        self.show_layer(layer)
                        sn = self._get_snapshot()
                        self.show_layer(initial_layer)
                    else:
                        sn = self._get_snapshot()
            try:
                from IPython.display import display_png, clear_output

                if clear:
                    clear_output(wait=True)
                # use display_png to avoid issues with transparent snapshots
                display_png(Image.fromarray(sn, "RGBA"), raw=False)

            except Exception:
                _log.exception(
                    "Unable to display the snapshot... is the script "
                    "running in an IPython console?",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )
        except Exception:
            _log.exception(
                "Encountered an error while trying to create a snapshot.",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )
        finally:
            self._snapshotting = False

    def _get_snapshot(self, layer=None):
        if layer is None:
            buf = self.f.canvas.print_to_buffer()
            x = np.frombuffer(buf[0], dtype=np.uint8).reshape(buf[1][1], buf[1][0], 4)
        else:
            x = self.BM._get_array(layer)[::-1, ...]
        return x

    @wraps(LayoutEditor.get_layout)
    def get_layout(self, *args, **kwargs):
        """Get the current layout."""
        return self.parent._layout_editor.get_layout(*args, **kwargs)

    @wraps(LayoutEditor.apply_layout)
    def apply_layout(self, *args, **kwargs):
        """Apply a given layout."""
        return self.parent._layout_editor.apply_layout(*args, **kwargs)

    def edit_layout(self, filepath=None):
        """
        Activate the "layout-editor" to quickly re-arrange the positions of subplots.

        - This is the same as pressing "alt + l" on the keyboard!
        - To exit the editor, press "escape" or "alt + l" on the keyboard!

        Parameters
        ----------
        filepath : str, pathlib.Path or None, optional
            A path to a file that will be used to store the layout after you exit
            the layout-editor.
            This file can then be used to apply the layout to the map with

            >>> m.apply_layout(filepath=filepath)

            NOTE: The file will be overwritten if it already exists!!
            The default is None.

        """
        self.parent._layout_editor._make_draggable(filepath=filepath)

    @wraps(GridSpec.update)
    def subplots_adjust(self, **kwargs):
        """Adjust the margins of subplots."""
        self.parent._gridspec.update(**kwargs)
        # after changing margins etc. a redraw is required
        # to fetch the updated background!

        self.redraw()

    @wraps(plt.savefig)
    def savefig(self, *args, refetch_wms=False, rasterize_data=True, **kwargs):
        """Save the figure."""

        dpi = kwargs.get("dpi", None)

        # get the currently visible layer (to restore it after saving is done)
        initial_layer = self.BM.bg_layer

        if plt.get_backend() == "agg":
            # make sure that a draw-event was triggered when using the agg backend
            # (to avoid export-issues with some shapes)
            # TODO properly assess why this is necessary!
            self.f.canvas.draw_idle()

        with ExitStack() as stack:

            # don't clear on layer-changes
            stack.enter_context(self.BM._cx_dont_clear_on_layer_change())

            # add the figure background patch as the bottom layer if transparent=False
            transparent = kwargs.get("transparent", False)
            showlayer_name = self.BM._get_showlayer_name(initial_layer, transparent)
            self.show_layer(showlayer_name)

            redraw = False
            if dpi is not None and dpi != self.f.dpi or "bbox_inches" in kwargs:
                redraw = True

                # clear all cached background layers before saving to make sure they
                # are re-drawn with the correct dpi-settings
                self.BM._refetch_bg = True

            # get all layer names that should be drawn
            savelayers, alphas = self.BM._parse_multi_layer_str(showlayer_name)

            # make sure inset-maps are drawn on top of normal maps
            savelayers.sort(key=lambda x: x.startswith("__inset_"))

            zorder = 0
            for layer, alpha in zip(savelayers, alphas):
                # get all (sorted) artists of a layer
                if layer.startswith("__inset"):
                    artists = self.BM.get_bg_artists(["__inset_all", layer])
                else:
                    if layer.startswith("__"):
                        artists = self.BM.get_bg_artists([layer])
                    else:
                        artists = self.BM.get_bg_artists(["all", layer])

                for a in artists:
                    if isinstance(a, plt.Axes):
                        continue
                    zorder += 1
                    stack.enter_context(a._cm_set(zorder=zorder, animated=False))
                    if alpha < 1:
                        current_alpha = a.get_alpha()
                        if current_alpha is None:
                            current_alpha = alpha
                        else:
                            current_alpha = current_alpha * alpha

                        stack.enter_context(a._cm_set(alpha=current_alpha))

            if any(l.startswith("__inset") for l in savelayers):
                if "__inset_all" not in savelayers:
                    savelayers.append("__inset_all")
                    alphas.append(1)
            if "all" not in savelayers:
                savelayers.append("all")
                alphas.append(1)

            # always draw dynamic artists on top of background artists
            for layer, alpha in zip(savelayers, alphas):
                # get all (sorted) artists of a layer
                artists = self.BM.get_artists([layer])

                for a in artists:
                    zorder += 1
                    stack.enter_context(a._cm_set(zorder=zorder, animated=False))

            # hide all artists on non-visible layers
            for key, val in chain(
                self.BM._bg_artists.items(), self.BM._artists.items()
            ):
                if key not in savelayers:
                    for a in val:
                        stack.enter_context(a._cm_set(visible=False, animated=True))

            for m in (self.parent, *self.parent._children):
                # re-enable normal axis draw cycle by making axes non-animated.
                # This is needed for backward-compatibility, since saving a figure
                # ignores the animated attribute for axis-children but not for the axis
                # itself. See:
                # https://github.com/matplotlib/matplotlib/issues/26007#issuecomment-1568812089
                stack.enter_context(m.ax._cm_set(animated=False))

            # explicitly set axes to non-animated to re-enable draw cycle
            for a in m.BM._managed_axes:
                stack.enter_context(a._cm_set(animated=False))

            # trigger a redraw of all savelayers to make sure unmanaged artists
            # and ordinary matplotlib axes are properly drawn
            # flush events prior to savefig to avoid issues with pending draw events
            # that cause wrong positioning of grid-labels and missing artists!
            self.f.canvas.flush_events()
            self.redraw(*savelayers)
            self.f._mpl_orig_savefig(*args, **kwargs)

        # restore the previous layer (if background was added on save)
        self.show_layer(initial_layer)

        if redraw is True:
            # redraw after the save to ensure that backgrounds are correctly cached
            self.redraw()

    def cleanup(self):
        """
        Cleanup all references to the object so that it can be safely deleted.

        This function is primarily used internally to clear objects if the figure
        is closed.

        Note
        ----
        Executing this function will remove ALL attached callbacks
        and delete all assigned datasets & pre-computed values.

        ONLY execute this if you do not need to do anything with the layer
        """

        try:
            # disconnect callback on xlim-change (only relevant for parent)
            if not self._is_sublayer:
                try:
                    if hasattr(self, "_cid_xlim"):
                        self.ax.callbacks.disconnect(self._cid_xlim)
                        del self._cid_xlim
                except Exception:
                    _log.error(
                        "EOmaps-cleanup: Problem while clearing xlim-cid",
                        exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                    )

            # cleanup all artists and cached background-layers from the blit-manager
            if not self._is_sublayer:
                self.BM._cleanup_layer(self.layer)

            # remove the child from the parent Maps object
            if self in self.parent._children:
                self.parent._children.remove(self)
        except Exception:
            _log.error(
                "EOmaps: Cleanup problem!",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

    @property
    def crs_plot(self):
        """The crs used for plotting."""
        return self._crs_plot_cartopy

    @staticmethod
    @lru_cache()
    def _get_cartopy_crs(crs):
        if isinstance(crs, str):
            try:
                # TODO use crs=int(crs.upper().removeprefix("EPSG:")) when python>=3.9
                # is required
                crs = crs.upper()
                if crs.startswith("EPSG:"):
                    crs = crs[5:]
                crs = int(crs)
            except ValueError:
                raise ValueError(
                    f"The provided crs '{crs}' cannot be identified. "
                    "If a string is provided as CRS, it must be either an integer "
                    "(e.g. '4326') or a string of the form: 'EPSG:4326'."
                )
        if isinstance(crs, ccrs.CRS):  # already a cartopy CRS
            cartopy_proj = crs
        elif crs == 4326:
            cartopy_proj = ccrs.PlateCarree()
        elif crs == 3857:
            cartopy_proj = ccrs.Mercator.GOOGLE
        elif isinstance(crs, (int, np.integer)):
            cartopy_proj = ccrs.epsg(crs)
        elif isinstance(crs, CRS):  # pyproj CRS
            cartopy_proj = None
            for (
                subgrid,
                equi7crs,
            ) in Equi7Grid_projection._pyproj_crs_generator():
                if equi7crs == crs:
                    cartopy_proj = Equi7Grid_projection(subgrid)
                    break
            if cartopy_proj is None:
                cartopy_proj = ccrs.CRS(crs)

        else:
            raise AssertionError(f"EOmaps: cannot identify the CRS for: {crs}")

        return cartopy_proj

    @staticmethod
    @lru_cache()
    def _get_transformer(crs_from, crs_to):
        # create a pyproj Transformer object and cache it for later use
        return Transformer.from_crs(crs_from, crs_to, always_xy=True)

    @property
    def _transf_plot_to_lonlat(self):
        return self._get_transformer(
            self.crs_plot,
            self.get_crs(self.crs_plot.as_geodetic()),
        )

    @property
    def _transf_lonlat_to_plot(self):
        return self._get_transformer(
            self.get_crs(self.crs_plot.as_geodetic()),
            self.crs_plot,
        )

    def on_layer_activation(self, func, layer=None, persistent=False, **kwargs):
        """
        Attach a callback that is executed if the associated layer is activated.

        Useful to "lazily" populate layers with features that are expensive to
        create (e.g. fetching data from files etc.).

        Parameters
        ----------
        func : callable
            The callable to use.
            The call-signature is:

            >>> def func(m, **kwargs):
            >>>    # m... the Maps-object used for calling this function

            NOTE: The Maps-object that is passed to the function is determined by
            the 'layer' argument!
        layer : str or None, optional
            If provided, a NEW layer will be created and passed to the execution of the
            function. Otherwise, the calling Maps-object is used.

            To clarify: The following two code-snippets are equivalent:

            >>> m = Maps()
            >>> m2 = m.new_layer("my_layer")
            >>> m2.on_layer_activation(func)

            >>> m = Maps()
            >>> m.on_layer_activation(func, layer="my_layer")

        persistent : bool, optional
            Indicator if the function should be called only once (False) or if it
            should be called each time the layer is activated (True).
            The default is False.
        kwargs :
            Additional keyword-arguments passed to the call of the function.

        See Also
        --------
        Maps.layer : The layer-name associated with the Maps-object
        Maps.fetch_layers : Fetch and cache all layers of the map

        Examples
        --------
        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>>
        >>> def f(m, ocean_color, coastline_color):
        >>>     print(f"EOmaps: creating features for the layer {m.layer}")
        >>>     m.add_feature.preset.coastline(ec=coastline_color)
        >>>     m.add_feature.preset.ocean(fc=ocean_color)
        >>>
        >>> # create a new (initially empty) layer "ocean"
        >>> m2 = m.new_layer("ocean")
        >>> # add features to the layer only if it is activated
        >>> m2.on_layer_activation(f, ocean_color="b", coastline_color="r")
        >>> s = m.util.layer_selector()

        """
        if layer is None:
            layer = self.layer
            m = self
        else:
            layer = str(layer)
            m = self.new_layer(layer)

        def cb(m, layer):
            func(m=m, **kwargs)

        self.BM.on_layer(func=cb, layer=layer, persistent=persistent, m=m)

    def set_extent(self, extents, crs=None):
        """
        Set the extent (x0, x1, y0, y1) of the map in the given coordinate system.

        Parameters
        ----------
        extents : array-like
            The extent in the given crs (x0, x1, y0, y1).
        crs : a crs identifier, optional
            The coordinate-system in which the extent is evaluated.

            - if None, epsg=4326 (e.g. lon/lat projection) is used

            The default is None.

        """
        # just a wrapper to make sure that previously set extents are not
        # reset when plotting data!

        # ( e.g. once .set_extent is called .plot_map does NOT set the extent!)
        if crs is not None:
            crs = self._get_cartopy_crs(crs)
        else:
            crs = ccrs.PlateCarree()

        self.ax.set_extent(extents, crs=crs)
        self._set_extent_on_plot = False

    def get_extent(self, crs=None):
        """
        Get the extent (x0, x1, y0, y1) of the map in the given coordinate system.

        Parameters
        ----------
        crs : a crs identifier, optional
            The coordinate-system in which the extent is evaluated.

            - if None, the extent is provided in epsg=4326 (e.g. lon/lat projection)

            The default is None.

        Returns
        -------
        extent : The extent in the given crs (x0, x1, y0, y1).

        """

        # fast track if plot-crs is requested
        if crs == self.crs_plot:
            x0, x1, y0, y1 = (*self.ax.get_xlim(), *self.ax.get_ylim())

            bnds = self._crs_boundary_bounds
            # clip the map-extent with respect to the boundary bounds
            # (to avoid returning values outside the crs bounds)
            try:
                x0, x1 = np.clip([x0, x1], bnds[0], bnds[2])
                y0, y1 = np.clip([y0, y1], bnds[1], bnds[3])
            except Exception:
                _log.debug(
                    "EOmaps: Error while trying to clip map extent", exc_info=True
                )
        else:
            if crs is not None:
                crs = self._get_cartopy_crs(crs)
            else:
                crs = self._get_cartopy_crs(4326)

            x0, x1, y0, y1 = self.ax.get_extent(crs=crs)

        return x0, x1, y0, y1

    def join_limits(self, *args):
        """
        Join the x- and y- limits of the maps (crs must be equal!).

        Parameters
        ----------
        *args :
            the axes to join.
        """
        for m in args:
            if m is not self:
                self._join_axis_limits(weakref.proxy(m))

    def _join_axis_limits(self, m):
        if self.ax.projection != m.ax.projection:
            _log.warning(
                "EOmaps: joining axis-limits is only possible for "
                + "axes with the same projection!"
            )
            return

        self.ax._EOmaps_joined_action = False
        m.ax._EOmaps_joined_action = False

        # Declare and register callbacks
        def child_xlims_change(event_ax):
            if event_ax._EOmaps_joined_action is not m.ax:
                m.ax._EOmaps_joined_action = event_ax
                m.ax.set_xlim(event_ax.get_xlim())
            event_ax._EOmaps_joined_action = False

        def child_ylims_change(event_ax):
            if event_ax._EOmaps_joined_action is not m.ax:
                m.ax._EOmaps_joined_action = event_ax
                m.ax.set_ylim(event_ax.get_ylim())
            event_ax._EOmaps_joined_action = False

        def parent_xlims_change(event_ax):
            if event_ax._EOmaps_joined_action is not self.ax:
                self.ax._EOmaps_joined_action = event_ax
                self.ax.set_xlim(event_ax.get_xlim())
            event_ax._EOmaps_joined_action = False

        def parent_ylims_change(event_ax):
            if event_ax._EOmaps_joined_action is not self.ax:
                self.ax._EOmaps_joined_action = event_ax
                self.ax.set_ylim(event_ax.get_ylim())

            event_ax._EOmaps_joined_action = False

        self.ax.callbacks.connect("xlim_changed", child_xlims_change)
        self.ax.callbacks.connect("ylim_changed", child_ylims_change)

        m.ax.callbacks.connect("xlim_changed", parent_xlims_change)
        m.ax.callbacks.connect("ylim_changed", parent_ylims_change)

    def _log_on_event(self, level, msg, event):
        """
        Schedule a log message that will be shown on the next matplotlib event.

        Identical scheduled messages are only shown once per event!

        {'CRITICAL': 50, 'FATAL': 50, 'ERROR': 40, 'WARN': 30, 'WARNING': 30,
         'INFO': 20,  'DEBUG': 10, 'NOTSET': 0}

        Parameters
        ----------
        level : int or str
            The logging level.
        msg : str
            The message.
        event : str
            The event name (e.g. "button_release_event")

        """
        level = _parse_log_level(level)

        messages = self._log_on_event_messages.setdefault(event, [])
        cid = self._log_on_event_cids.setdefault(event, None)

        # don't attach messages if they are already scheduled
        if (level, msg) in messages:
            return

        messages.append((level, msg))

        def log_message(*args, **kwargs):
            cid = self._log_on_event_cids.get(event, None)
            messages = self._log_on_event_messages.get(event, [])

            if cid is not None:
                self.f.canvas.mpl_disconnect(cid)
                self._log_on_event_cids.pop(event, None)

            while len(messages) > 0:
                level, msg = messages.pop(0)
                _log.log(level, msg)

        if cid is None:
            self._log_on_event_cids[event] = self.f.canvas.mpl_connect(
                event, log_message
            )

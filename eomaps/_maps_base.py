# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Base class for Maps objects."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .eomaps import Maps

import logging

_log = logging.getLogger(__name__)

from contextlib import contextmanager, ExitStack
from functools import lru_cache, wraps
from textwrap import fill
import importlib.metadata
import weakref
import gc

import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec, SubplotSpec
from cartopy import crs as ccrs

from pyproj import CRS, Transformer
import numpy as np

from .helpers import _parse_log_level, _proxy, WeakOrderedCollection
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


class LazyCx:
    """
    A contextmanager to temporarily change if methods are executed lazily.

    Examples
    --------

    Set global behavior

    >>> Maps.lazy = True # or False


    Temporarily execute methods lazily:

    >>> with Maps.lazy:
    >>>    m["my_layer"].add_feature.preset.coastline()


    Temporarily execute methods immediately:

    >>> with Maps.lazy(False):
    >>>    m["my_layer"].add_feature.preset.coastline()

    """

    def __init__(self):
        self._lazy = True

    def __call__(self, lazy=True):
        if not isinstance(lazy, bool):
            raise TypeError("lazy must be either True or False.")
        self._lazy = lazy
        return self

    def __enter__(self):
        self._init_lazy = MapsBase._lazy
        MapsBase._lazy = self._lazy

    def __exit__(self, type, value, tb):
        MapsBase._lazy = self._init_lazy


class _MapsMeta(type):
    _use_interactive_mode = None
    _always_on_top = False
    _backend_warning_shown = False

    # a contextmanager to set the "lazy" attribute on all Maps objects
    lazy = LazyCx()

    # allow setting "lazy" without overriding the contextmanager
    def __setattr__(cls, name, value):
        if name == "lazy":
            MapsBase._lazy = value
        else:
            super().__setattr__(name, value)

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
            cls._CompanionMixin__companion_widget_key = companion_widget_key

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


class MultiCaller:
    """
    A class to distribute attribute-access and method calls across
    multiple objects.
    """

    def __init__(self, elements):
        self._elements = elements

    def __call__(self, *args, **kwargs):
        ret = [obj.__call__(*args, **kwargs) for obj in self]
        if ret.count(None) != len(self):
            return ret

    def __dir__(self):
        # to support autocompletion, return public attributes of elements
        return [i for i in dir(self._elements[0]) if not i.startswith("_")]

    @property
    def __doc__(self):
        return self._elements[0].__doc__

    def __getattr__(self, name):
        return MultiCaller([getattr(i, name) for i in self])

    def __getattribute__(self, name):
        if name.startswith("_"):
            return object.__getattribute__(self, name)

        return MultiCaller(
            [getattr(i, name) for i in object.__getattribute__(self, "_elements")]
        )

    def __getitem__(self, name):
        return MultiCaller([i[name] for i in self])

    def __iter__(self):
        return (i for i in self._elements)

    def __len__(self):
        return len(self._elements)

    def __add__(self, value):
        return MultiCaller([*self._elements, value])


class LayerNamespace:
    """
    Accessor to create, access and populate layers on the map.

    `m.l.my_layer` will return a :py:class:`Maps` object on the layer
    named`"my_layer"`.

    - If no :py:class:`Maps` object exists in the LayerNamespace, it will be created.
    - Otherwise, the existing :py:class:`Maps` object is returned
        - To create additional :py:class`Maps` objects on the same layer,
          you can use double-underscores in the name, e.g. "my_layer__a"

    Examples
    --------

    Create a :py:class:`Maps` object on the `"overlay"` layer and populate
    the layer with the "ocean" and "land" features.

    >>> m = Maps()
    >>> m.l.overlay.add_feature.preset.ocean()
    >>> m.l.overlay.add_feature.preset.land()

    """

    def __init__(self, m):
        self._m = m
        self._layers = {}

        # self._ingest_layer(self._m)

    def _ingest_layer(self, m, name=None):
        # don't include the all-layer
        # (it's special and only accessible via m.all)
        if name == "all":
            return

        if name is None:
            name = m.name

        self._layers[name] = m
        super().__setattr__(name, m)

    def _remove_layer(self, layer):
        # NOTE it is important to first delete the attribute and then
        # delete the entry from the dict in order to avoid re-creating
        # the layer when checking for attribute-existence!
        try:
            delattr(self, layer)
        except AttributeError:
            pass
        self._layers.pop(layer, None)

    def __dir__(self):
        return [l for l in self._layers if not l.startswith("**")]

    def __iter__(self):
        return iter(self._layers.values())

    def __len__(self):
        return len(self._layers)

    def __getitem__(self, name):
        # NOTE: convert args to string since layer-names are always strings
        if isinstance(name, tuple):
            return MultiMaps([getattr(self, str(n)) for n in name])
        else:
            return getattr(self, str(name))

    def __repr__(self):
        return fill(
            'LayerNamespace("'
            + '", "'.join(i for i in sorted(self._layers)[:5])
            + '"'
            + (" ..." if len(self._layers) > 5 else "")
            + ")"
        )

    def __setattr__(self, name, value):
        if not name.startswith("_"):
            raise TypeError("LayerNamespace does not allow attribute assignment.")

        super().__setattr__(name, value)

    def __getattribute__(self, name) -> "Maps":
        # private attributes are handled in ordinary manner.
        # only public attribute names will trigger layer-creation!
        if name.startswith("_"):
            return super().__getattribute__(name)

        # get the maps-object associated with the name (create if it does not exist)
        # Note: new_layer calls "LayerNamespace._ingest_layer" to ingest the layer
        m = self._layers.get(name)
        if m is None:
            return self._m.new_layer(name)

        return m


class MapsLayerBase:
    def __init__(self, layer=None, parent=None, *args, **kwargs):

        if parent is None:
            self._parent = self
        else:
            self._parent = _proxy(parent)

        # make sure the used layer-name is valid
        if layer is None:
            layer = "base"

        layer = BlitManager._check_layer_name(layer)

        # the "full" layer-name including sublayer-(__) suffix
        self._name = layer

        # the layer at which the artists should be visible
        # TODO write a proper parser method
        self._layer = layer.split("__", 1)[0]

        super().__init__(*args, **kwargs)

    @property
    def layer(self):
        """Name of the layer at which artists of this Maps-object are visible."""
        return self._layer

    @property
    def name(self):
        """
        The name associated with this Maps-object.

        <visible-layer-name>__<sublayer-id>

        """
        return self._name

    @property
    def parent(self):
        """
        The parent-object to which this Maps-object is connected to.
        """
        return self._parent

    @property
    @wraps(LayerNamespace)
    def l(self):
        """LayerNamespace accessor to create/access layers on the map."""
        return self._l

    def new_layer(
        self,
        layer=None,
        inherit_data=False,
        inherit_classification=False,
        inherit_shape=False,
        **kwargs,
    ):
        """
        Create a new Maps-object that shares the same plot-axes.

        Parameters
        ----------
        layer : str or None
            The name of the layer at which map-features are plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer of the parent object is used.

            The default is None.
        inherit_data, inherit_classification, inherit_shape : bool
            Indicator if the corresponding properties should be inherited from
            the parent Maps-object.

            By default only the shape is inherited.

            For more details, see :py:meth:`Maps.inherit_data` and
            :py:meth:`Maps.inherit_classification`

        Returns
        -------
        eomaps.Maps
            A connected copy of the Maps-object that shares the same plot-axes.

        Examples
        --------
        Create a new Maps-object **on an existing layer**

        >>> from eomaps import Maps
        >>> m = Maps(layer="base")    # m.layer == "base"
        >>> m2 = m.new_layer()        # m2.layer == "base"


        Create a new Maps-object representing a **new layer**

        >>> from eomaps import Maps
        >>> m = Maps(layer="base")           # m.layer == "base"
        >>> m2 = m.new_layer("a new layer")  # m2.layer == "a new layer"


        Create a new layer and immediately delete it after it has been exported.
        (useful to free memory if a lot of layers are be exported)

        >>> from eomaps import Maps
        >>> m = Maps(layer="base")
        >>> with m.new_layer("a new layer") as m2:
        >>>     ...
        >>>     m2.show()                           # make the layer visible
        >>>     m2.savefig(...)                     # save it as an image


        See Also
        --------
        Maps.copy : general way for copying Maps objects

        """

        if layer is None:
            layer = self.layer
        else:
            layer = str(layer)
            if len(layer) == 0:
                raise SyntaxError(
                    "EOmaps: Unable to create a layer with an empty layer-name!"
                )

        _log.debug(f"EOmaps: New layer '{layer}' created.")

        m = self.copy(
            data_specs=False,
            classify_specs=False,
            shape=False,
            ax=self.ax,
            layer=layer,
            parent=self.parent,
        )

        if inherit_data:
            m.inherit_data(self)
        if inherit_classification:
            m.inherit_classification(self)
        if inherit_shape and self._shape_assigned:
            getattr(m.set_shape, self.shape.name)(**self.shape._initargs)

        # make sure the new layer does not attempt to reset the extent if
        # it has already been set on the parent layer
        m._set_extent_on_plot = self._set_extent_on_plot

        # re-initialize all sliders and buttons to include the new layer
        self.parent.util._reinit_widgets()

        # share the companion-widget with the parent
        m._companion_widget = self._companion_widget

        return m


class MapsBase(metaclass=_MapsMeta):
    _lazy = None

    def __init__(
        self,
        crs=None,
        f=None,
        ax=None,
        **kwargs,
    ):
        self._view_transparency = 1
        self._figure_closed = False

        self._artists = WeakOrderedCollection()
        self._bg_artists = WeakOrderedCollection()

        self._layout_editor = None

        self._log_on_event_messages = dict()
        self._log_on_event_cids = dict()

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
        self._after_add_child = list()

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
        self._init_axes(ax=ax, plot_crs=crs, **kwargs)

        if self.name in self._l._layers:
            name = self.layer
            i = 0
            while name in self._l._layers:
                name = f"{self.layer}__{i}"
                i += 1

            print(
                f"The layer name '{self.name}' already exists!\n"
                f"It has been re-named to {name} in the LayerNamespace!"
            )
            self._name = name

        self._l._ingest_layer(self)
        self._add_child(self)

        if self.parent == self:
            # Make sure the figure-background patch is on an explicit layer
            # This is used to avoid having the background patch on each fetched
            # background while maintaining the capability of restoring it
            if self.f.patch not in self._bm._bg_artists["**BG**"]:
                self.f.patch.set_zorder(-2)
                self._bm._bg_artists.add("**BG**", self.f.patch)

            if self.ax.patch not in self._bm._bg_artists["**BG**"]:
                self.ax.patch.set_zorder(-1)
                self._bm._bg_artists.add("**BG**", self.ax.patch)

        # Treat cartopy geo-spines separately in the blit-manager
        # to avoid issues with overlapping spines that are drawn on each layer
        # if multiple layers of a map are combined.
        # (Note: spines need to be visible on each layer in case the layer
        # is viewed on its own, but overlapping spines cause blurry boundaries)
        # TODO find a better way to deal with this!
        self._handle_spines()

        self._crs_plot_cartopy = self._get_cartopy_crs(self._crs_plot)

        if self.parent == self and self.__class__._always_on_top:
            self._set_always_on_top(True)

        super().__init__()

    def add_artist(self, artist):
        artist.set_animated(True)

        # TODO is there a better way to handle axes?
        # NOTE: this is required to avoid consecutive re-draws of axes-artists
        # such as backgrounds, spines etc. during fast executed callbacks (e.g. move)!
        if isinstance(artist, plt.Axes):
            self._bm._managed_axes.add(artist)

        self._artists.add(artist)
        self._bm.run_hook("add_artist")

    def add_bg_artist(self, artist, draw=True):
        artist.set_animated(True)

        # TODO is there a better way to handle axes?
        # NOTE: this is required to avoid consecutive re-draws of axes-artists
        # such as backgrounds, spines etc. during fast executed callbacks (e.g. move)!
        if isinstance(artist, plt.Axes):
            self._bm._managed_axes.add(artist)

        self._bg_artists.add(artist)
        self._bm.run_hook("add_bg_artist")

        if draw:
            self.redraw(self.layer)

    def _remove_artist(self, artist):
        self._artists.remove(artist)

    def remove_artist(self, artist):
        self._remove_artist(artist)
        self._bm.run_hook("remove_artist")
        artist.remove()

    def _remove_bg_artist(self, artist):
        self._bg_artists.remove(artist)

    def remove_bg_artist(self, artist, draw=True):
        self._remove_bg_artist(artist)
        self._bm.run_hook("remove_bg_artist")
        artist.remove()

        if draw:
            self.redraw(self.layer)

    def __mul__(self, value):
        self._view_transparency = value
        return self

    def __rmul__(self, value):
        self._view_transparency = value
        return self

    def __add__(self, value):
        return MultiMaps([self, value])

    # to add support for sum()
    def __radd__(self, value):
        if value == 0:
            return MultiMaps([self])
        else:
            return self.__add__(value)

    def _ipython_key_completions_(self, *args, **kwargs):
        # to allow auto-completion for __getitem__ in ipython
        return list(self.l._layers)

    def __getitem__(self, name) -> "Maps":
        # NOTE: convert args to string since layer-names are always strings
        if isinstance(name, tuple):
            return MultiMaps([getattr(self._l, str(n)) for n in name])
        elif isinstance(name, slice):
            return sum([*self.l][name])
        else:
            return getattr(self._l, str(name))

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
        assert isinstance(self, MapsBase), (
            "EOmaps: using a Maps-object as a context-manager is only possible "
            "if you create a NEW layer (not a Maps-object on an existing layer)!"
        )

        return self

    def __exit__(self, type, value, traceback):
        # all action on Maps-objects must be performed BEFORE cleanup!
        is_parent = self.parent == self
        self.cleanup()
        if is_parent:
            plt.close(self.f)
        gc.collect()

    @property
    def f(self):
        """Matplotlib Figure associated with this Maps-object."""
        # always return the figure of the parent object
        return self._f

    @property
    def ax(self):
        """Cartopy GeoAxes associated with this Maps-object."""
        return self._ax

    @property
    def all(self):
        """
        Get a Maps-object on the "all" layer.

        Use it just as any other Maps-object. (It's the same as `Maps(layer="all")`)

        >>> m.all.cb.click.attach.annotate()

        """
        return self.l["all"]

    def redraw(self, *args, force_data_redraw=False):
        """
        Force a re-draw of cached background layers.

        - Use this at the very end of your code to trigger a final re-draw
          to make sure artists not managed by EOmaps are properly drawn!

        Parameters
        ----------
        forece_data_redraw : bool
            Force a re-draw of already plotted datasets.
            The default is False.

        Note
        ----
        Don't use this to interactively update artists on a map!
        since it will trigger a re-draw background-layers!

        To dynamically re-draw an artist whenever you interact with the map, use:

        >>> m.add_artist(artist)

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
            self._bm._refetch_bg = True
            if force_data_redraw and getattr(self, "_data_manager", None) is not None:
                self._data_manager.last_extent = None

        else:
            # only re-fetch the required layers
            for layer in args:
                self._bm._refetch_layer(layer)
                if (
                    force_data_redraw
                    and getattr(self.l[layer], "_data_manager", None) is not None
                ):
                    self.l[layer]._data_manager.last_extent = None

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
        name = self._bm._get_combined_layer_name(*args)
        if not isinstance(name, str):
            _log.info("EOmaps: All layer-names are converted to strings!")
            name = str(name)

        # check if all layers exist
        existing_layers = self._get_layers(exclude_private=False)
        layers_to_show, _ = self._bm._parse_multi_layer_str(name)

        # don't check private layer-names
        layers_to_show = [i for i in layers_to_show if not i.startswith("_")]
        missing_layers = set(layers_to_show).difference(set(existing_layers))
        if len(missing_layers) > 0:
            public_layers = self._get_layers(exclude_private=True)

            lstr = " - " + "\n - ".join(map(str, public_layers))

            _log.warning(
                'EOmaps: The layers: "'
                + '","'.join(sorted(missing_layers))
                + '" do not (yet?) exist!\n'
                + f"Currently available layers are: \n{lstr}"
            )
            return

        # invoke the bg_layer setter of the blit-manager
        self._bm.bg_layer = name
        self._bm.update()

        # plot a snapshot to jupyter notebook cell if inline backend is used
        if not self._bm._snapshot_on_update and plt.get_backend() in [
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

        self.show_layer(self.layer)

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
        active_layer = self._bm._bg_layer
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
        self._bm.update()

    def _get_layers(self, exclude=None, exclude_private=True):
        # return a list of all (empty and non-empty) layer-names
        layers = self._bm._children.get_layers()

        # exclude private layers
        if exclude_private:
            # for python <3.9 compatibility
            def remove_prefix(text, prefix):
                if text.startswith(prefix):
                    return text[len(prefix) :]
                return text

            layers = {remove_prefix(i, "**inset_") for i in layers}
            layers = {i for i in layers if not i.startswith("**")}
        else:
            layers.extend(("**BG**", "**SPINES**"))

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
                stack.enter_context(self._bm._cx_dont_clear_on_layer_change())

                if len(layer) == 0:
                    layer = [self.layer]

                if layer is not None:
                    layer = self._bm._get_combined_layer_name(*layer)

                # add the figure background patch as the bottom layer
                initial_layer = self._bm.bg_layer

                if transparent is False:
                    showlayer_name = self._bm._get_showlayer_name(
                        layer=layer, transparent=transparent
                    )
                    self.show_layer(showlayer_name)
                    sn = self._get_snapshot()
                    # restore the previous layer
                    self._bm._refetch_layer(showlayer_name)
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
        with self.delay_draw():
            for m in self._bm._children:
                try:
                    m.ax.get_gridspec().update(**kwargs)
                except AttributeError:
                    # TODO fix this properly
                    # ignore gridspecs that don't provide an update method
                    # (like GridSpecFromSubplotSpec)
                    pass
        # after changing margins etc. a redraw is required
        # to fetch the updated background!

        self.redraw()

    @wraps(plt.savefig)
    def savefig(self, *args, refetch_wms=False, rasterize_data=True, **kwargs):
        """Save the figure."""

        dpi = kwargs.get("dpi", None)

        # get the currently visible layer (to restore it after saving is done)
        initial_layer = self._bm.bg_layer

        if plt.get_backend() == "agg":
            # make sure that a draw-event was triggered when using the agg backend
            # (to avoid export-issues with some shapes)
            # TODO properly assess why this is necessary!
            self.f.canvas.draw_idle()

        with ExitStack() as stack:

            # don't clear on layer-changes
            stack.enter_context(self._bm._cx_dont_clear_on_layer_change())

            # add the figure background patch as the bottom layer if transparent=False
            transparent = kwargs.get("transparent", False)
            showlayer_name = self._bm._get_showlayer_name(initial_layer, transparent)
            self.show_layer(showlayer_name)

            redraw = False
            if dpi is not None and dpi != self.f.dpi or "bbox_inches" in kwargs:
                redraw = True

                # clear all cached background layers before saving to make sure they
                # are re-drawn with the correct dpi-settings
                self._bm._refetch_bg = True

            # get all layer names that should be drawn
            savelayers, alphas = self._bm._parse_multi_layer_str(showlayer_name)

            # make sure inset-maps are drawn on top of normal maps
            savelayers.sort(key=lambda x: x.startswith("**inset_"))

            zorder = 0
            for layer, alpha in zip(savelayers, alphas):
                # get all (sorted) artists of a layer
                if layer.startswith("**inset"):
                    artists = self._bm.get_bg_artists(["**inset_all", layer])
                else:
                    if layer.startswith("**"):
                        artists = self._bm.get_bg_artists([layer])
                    else:
                        artists = self._bm.get_bg_artists(["all", layer])

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

            if any(l.startswith("**inset") for l in savelayers):
                if "**inset_all" not in savelayers:
                    savelayers.append("**inset_all")
                    alphas.append(1)
            if "all" not in savelayers:
                savelayers.append("all")
                alphas.append(1)

            # always draw dynamic artists on top of background artists
            for layer, alpha in zip(savelayers, alphas):
                # get all (sorted) artists of a layer
                artists = self._bm.get_artists([layer])

                for a in artists:
                    zorder += 1
                    stack.enter_context(a._cm_set(zorder=zorder, animated=False))

            # hide all artists on non-visible layers
            # for key, val in chain(
            #     self._bm._bg_artists.items(), self._bm._artists.items()
            # ):
            #     if key not in savelayers:
            #         for a in val:
            #             stack.enter_context(a._cm_set(visible=False, animated=True))

            for m in self._bm._children:
                # hide all artists on non-visible layers

                # TODO use proper layer parsing not hard-coding!
                if m.layer not in savelayers:
                    for a in (*m._artists, *m._bg_artists):
                        stack.enter_context(a._cm_set(visible=False, animated=True))

                # re-enable normal axis draw cycle by making axes non-animated.
                # This is needed for backward-compatibility, since saving a figure
                # ignores the animated attribute for axis-children but not for the axis
                # itself. See:
                # https://github.com/matplotlib/matplotlib/issues/26007#issuecomment-1568812089
                stack.enter_context(m.ax._cm_set(animated=False))

            # explicitly set axes to non-animated to re-enable draw cycle
            for a in self._bm._managed_axes:
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
            # cleanup all artists
            for a in (*self._artists, *self._bg_artists):
                try:
                    a.remove()
                except Exception:
                    _log.error(
                        f"EOmaps-cleanup: Problem while trying to remove artist: {a}",
                        exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                    )
            self._artists.clear()
            self._bg_artists.clear()

            # remove the child from the LayerNamespace
            self.l._remove_layer(self.layer)

            self._bm.remove_hook(
                "layer_activation", method=None, permanent=None, layer=self.layer
            )

            # remove the child from the parent Maps object
            self._bm._children.remove(self)

            # disconnect callback on xlim-change (only relevant for parent)
            if self.parent == self:
                try:
                    if hasattr(self, "_cid_xlim"):
                        self.ax.callbacks.disconnect(self._cid_xlim)
                        del self._cid_xlim
                except Exception:
                    _log.error(
                        "EOmaps-cleanup: Problem while clearing xlim-cid",
                        exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                    )

        except Exception:
            _log.error(
                "EOmaps: Cleanup problem!",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

    @property
    def crs_plot(self):
        """The crs used for plotting."""
        return self._crs_plot_cartopy

    @lru_cache()
    def get_crs(self, crs="plot"):
        """
        Get the pyproj CRS instance of a given crs specification.

        Parameters
        ----------
        crs : "in", "out" or a crs definition
            the crs to return

            - if "in" : the crs defined in m.data_specs.crs
            - if "out" or "plot" : the crs used for plotting

        Returns
        -------
        crs : pyproj.CRS
            the pyproj CRS instance

        """
        # check for strings first to avoid expensive equality checking for CRS objects!
        if isinstance(crs, str):
            if crs == "in":
                crs = self.data_specs.crs
            elif crs == "out" or crs == "plot":
                if self.crs_plot == ccrs.PlateCarree():
                    crs = 4326
                else:
                    crs = self.crs_plot

        crs = CRS.from_user_input(crs)
        return crs

    def transform_plot_to_lonlat(self, x, y):
        """
        Transform plot-coordinates to longitude and latitude values.

        Parameters
        ----------
        x, y : float or array-like
            The coordinates values in the coordinate-system of the plot.

        Returns
        -------
        lon, lat : The coordinates transformed to longitude and latitude values.

        """
        return self._transf_plot_to_lonlat.transform(x, y)

    def transform_lonlat_to_plot(self, lon, lat):
        """
        Transform longitude and latitude values to plot coordinates.

        Parameters
        ----------
        lon, lat : float or array-like
            The longitude and latitude values to transform.

        Returns
        -------
        x, y : The coordinates transformed to the plot-coordinate system.

        """
        return self._transf_lonlat_to_plot.transform(lon, lat)

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
            self._f._EOmaps_parent = self
        else:
            if not hasattr(self.parent.f, "_EOmaps_parent"):
                # e.g. in case a explicit figure is provided
                self.parent.f._EOmaps_parent = self.parent._real_self

        if getattr(self.parent, "_bm", None) is not None:
            self._bm = self.parent._bm
        else:
            _log.debug("New BlitManager initialized")
            self._bm = BlitManager(self.f)
            self._bm._bg_layer = self.layer

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
            if ax not in (i.ax for i in self._bm._children):
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

            self._l = LayerNamespace(self)

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

            # use the namespace from the parent map
            self._l = next((m._l for m in self._bm._children if m.ax is ax))

    def _get_snapshot(self, layer=None):
        if layer is None:
            buf = self.f.canvas.print_to_buffer()
            x = np.frombuffer(buf[0], dtype=np.uint8).reshape(buf[1][1], buf[1][0], 4)
        else:
            x = self._bm._get_array(layer)[::-1, ...]
        return x

    def _get_ax_label(self):
        return "map"

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
    def _real_self(self):
        # workaround to obtain a non-weak reference for the parent
        # (e.g. self.parent._real_self is a non-weak ref to parent)
        # see https://stackoverflow.com/a/49319989/9703451
        return self

    def _add_child(self, m):
        self._bm._children.add(m)

        # execute hooks to notify the gui that a new child was added
        for action in self._after_add_child:
            try:
                action()
            except Exception:
                _log.exception("EOmaps: Problem executing 'on_add_child' action:")

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

    def _handle_spines(self):
        # put cartopy spines on a separate layer
        for spine in self.ax.spines.values():
            if spine and spine not in self._bm._bg_artists["**SPINES**"]:
                self._bm._bg_artists.add("**SPINES**", spine)

    def _on_resize(self, event):
        # make sure the background is re-fetched if the canvas has been resized
        # (required for peeking layers after the canvas has been resized
        #  and for webagg and nbagg backends to correctly re-draw the layer)

        self._bm._refetch_bg = True
        self._bm._refetch_blank = True

        # update the figure dimensions in case shading is used.
        # Avoid flushing events during resize
        # TODO
        if hasattr(self, "_update_shade_axis_size"):
            self._update_shade_axis_size(flush=False)

    def _on_close(self, event):
        self._figure_closed = True

        # reset attributes that might use up a lot of memory when the figure is closed
        for m in list(self._bm._children):
            if hasattr(m.f, "_EOmaps_parent"):
                m.f._EOmaps_parent = None

            m.cleanup()

        # run garbage-collection to immediately free memory
        gc.collect

    def _on_xlims_change(self, *args, **kwargs):
        self._bm._refetch_bg = True

    def _on_ylims_change(self, *args, **kwargs):
        self._bm._refetch_bg = True

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

        @wraps(func)
        def cb(layer):
            return func(m=m, **kwargs)

        return self._bm.on_layer(func=cb, layer=layer, persistent=persistent)

    @property
    def on_all_layers(self):
        """
        Return a MultiMaps that executes action on all layers defined
        on the map at the moment of execution.


        >>> from eomaps import Maps
        >>> m = Maps()
        >>> m.l.second.add_title("a second layer")
        >>> m.all_layers.add_feature.preset.coastline()

        """
        return sum([*self.l])

    @lru_cache()
    def _get_nominatim_response(self, q, user_agent=None):
        import requests

        _log.info(f"Querying {q}")
        if user_agent is None:
            version = importlib.metadata.version("eomaps")
            user_agent = f"EOMaps v{version}"

        headers = {
            "User-Agent": user_agent,
        }

        resp = requests.get(
            rf"https://nominatim.openstreetmap.org/search?q={q}&format=json&addressdetails=1&limit=1",
            headers=headers,
        ).json()

        if len(resp) == 0:
            raise TypeError(f"Unable to resolve the location: {q}")

        return resp[0]

    def set_extent_to_location(
        self, location, buffer=0, annotate=False, user_agent=None
    ):
        """
        Set the map-extent based on a given location query.

        The bounding-box is hereby resolved via the OpenStreetMap Nominatim service.

        Note
        ----
        The OSM Nominatim service has a strict usage policy that explicitly
        disallows "heavy usage" (e.g.: an absolute maximum of 1 request per second).

        EOMaps caches requests so using a location multiple times in the same
        session does not cause multiple requests!

        For more details, see:
            https://operations.osmfoundation.org/policies/nominatim/
            https://openstreetmap.org/copyright

        Parameters
        ----------
        location : str
            An arbitrary string used to identify the region of interest.
            (e.g. a country, district, address etc.)

            For example:
                "Austria", "Vienna"
        buffer : float
            Fraction of the found extent added as a buffer.
            The default is 0.
        annotate : bool, optional
            Indicator if an annotation should be added to the center of the identified
            location or not. The default is False.
        user_agent: str, optional
            The user-agent used for the Nominatim request

        Examples
        --------
        >>> m = Maps()
        >>> m.set_extent_to_location("Austria")
        >>> m.add_feature.preset.countries()

        >>> m = Maps(Maps.CRS.GOOGLE_MERCATOR)
        >>> m.set_extent_to_location("Vienna")
        >>> m.add_wms.OpenStreetMap.add_layer.default()

        """
        r = self._get_nominatim_response(location)

        # get bbox of found location
        lon0, lon1, lat0, lat1 = map(float, r["boundingbox"])

        dlon, dlat = lon1 - lon0, lat1 - lat0
        lon0 -= dlon * buffer
        lon1 += dlon * buffer
        lat0 -= dlat * buffer
        lat1 += dlat * buffer

        # set extent to found bbox
        self.set_extent((lat0, lat1, lon0, lon1), crs=ccrs.PlateCarree())

        # add annotation
        if annotate is not False:
            if isinstance(annotate, str):
                text = annotate
            else:
                text = fill(r["display_name"], 20)

            self.add_annotation(
                xy=(r["lon"], r["lat"]), xy_crs=4326, text=text, fontsize=8
            )
        else:
            _log.info(f"Centering Map to:\n    {r['display_name']}")

    def join_limits(self, *args):
        """
        Join the x- and y- limits of the maps (crs must be equal!).

        Parameters
        ----------
        *args :
            the axes to join.
        """
        for m in args:
            if m._real_self is not self:
                self._join_axis_limits(m)

    # a WeakSet holding weak-references to maps that share axes limits
    # (used to make sure limits are only shared once between Maps)
    __joined_limits = weakref.WeakSet()

    def _join_axis_limits(self, m):
        if (m._real_self in self.__joined_limits) or (self in m.__joined_limits):
            # make sure limits are only joined once between maps
            return

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

        self.__joined_limits.add(m)

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

    def _get_always_on_top(self):
        try:
            if "qt" in plt.get_backend().lower():
                from qtpy import QtCore

                w = self.f.canvas.window()
                return bool(w.windowFlags() & QtCore.Qt.WindowStaysOnTopHint)
        except Exception:
            _log.debug("Error while trying to get 'always_on_top' flag")
            return False
        return False

    def _set_always_on_top(self, q):
        # keep pyqt window on top
        try:
            from qtpy import QtCore

            if q:
                # only do this if necessary to avoid flickering
                # see https://stackoverflow.com/a/40007740/9703451
                if not self._get_always_on_top():
                    # in case pyqt is used as backend, also keep the figure on top
                    if "qt" in plt.get_backend().lower():
                        w = self.f.canvas.window()
                        ws = w.size()
                        w.setWindowFlags(
                            w.windowFlags() | QtCore.Qt.WindowStaysOnTopHint
                        )
                        w.resize(ws)
                        w.show()

                    # handle companion-widget (in case it has been activated)
                    self._CompanionMixin__set_always_on_top(q)

            else:
                if self._get_always_on_top():
                    if "qt" in plt.get_backend().lower():
                        w = self.f.canvas.window()
                        ws = w.size()
                        w.setWindowFlags(
                            w.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint
                        )
                        w.resize(ws)
                        w.show()

                    # handle companion-widget (in case it has been activated)
                    self._CompanionMixin__set_always_on_top(q)

        except Exception:
            pass

    @contextmanager
    def delay_draw(self, redraw=True):
        """
        A contextmanager to delay drawing until the context exits.

        This is particularly useful to avoid intermediate draw-events when plotting
        a lot of features or datasets on the currently visible layer.


        Examples
        --------

        >>> m = Maps()
        >>> with m.delay_draw():
        >>>     m.add_feature.preset.coastline()
        >>>     m.add_feature.preset.ocean()
        >>>     m.add_feature.preset.land()

        """
        try:
            self._bm._disable_draw = True
            self._bm._disable_update = True

            yield
        finally:
            self._bm._disable_draw = False
            self._bm._disable_update = False
            if redraw:
                self.redraw()


class MultiMaps(MultiCaller):
    """
    Wrapper around Maps-objects to run methods on multiple Maps objects in one go.
    """

    @wraps(MapsBase.show)
    def show(self, **kwargs):
        layers = [(m._layer, m._view_transparency) for m in self._elements]
        self._elements[0].show_layer(*layers)

    @wraps(MapsBase.snapshot)
    def snapshot(self, *args, **kwargs):
        layers = [(m._layer, m._view_transparency) for m in self._elements]
        self._elements[0].snapshot(*layers, **kwargs)

    @wraps(MapsBase.savefig)
    def savefig(self, *args, **kwargs):
        self.show()
        self._elements[0].savefig(*args, **kwargs)

    def __getattribute__(self, name):
        if name in ("show", "snapshot", "savefig"):
            return object.__getattribute__(self, name)

        return super().__getattribute__(name)

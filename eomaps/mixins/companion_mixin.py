import logging

_log = logging.getLogger(__name__)

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from ..helpers import _key_release_event


class CompanionMixin:
    # the keyboard shortcut to activate the companion-widget
    __companion_widget_key = "w"
    # max. number of layers to show all layers as tabs in the widget
    # (otherwise only recently active layers are shown as tabs)
    _companion_widget_n_layer_tabs = 50

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        try:
            from ..qtcompanion.signal_container import _SignalContainer

            # initialize the signal container (MUST be done before init of the widget!)
            self._signal_container = _SignalContainer()
        except Exception:
            _log.debug("SignalContainer could not be initialized", exc_info=True)
            self._signal_container = None

        # slot for the pyqt widget
        self._companion_widget = None
        # a list of actions that are executed whenever the widget is shown
        self._on_show_companion_widget = []

    @staticmethod
    def _if_companion_exists(f):
        # decorator to run method only if companion-widget has been initialized
        def inner(self, *args, **kwargs):
            if self._companion_widget is None:
                return
            return f(self, *args, **kwargs)

        return inner

    def __on_keypress(self, event):
        # NOTE: callback is only attached to the parent Maps object!
        if event.key == self.__companion_widget_key:
            try:
                self._open_companion_widget((event.x, event.y))
            except Exception:
                _log.exception(
                    "EOmaps: Encountered a problem while trying to open "
                    "the companion widget",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

    def _hide_all_companion_widget_indicators(self):
        # hide companion-widget indicator
        for m in self.BM._children:
            # hide companion-widget indicator
            m._indicate_companion_map(False)

    def _show_all_companion_widget_indicators(self):
        # hide companion-widget indicator
        for m in self.BM._children:
            if (w := getattr(m, "_companion_widget", None)) is not None:
                if w.isVisible():
                    # hide companion-widget indicator
                    m._indicate_companion_map(True)

    @_if_companion_exists
    def __set_always_on_top(self, q):
        from qtpy import QtCore

        cw = self._companion_widget.window()
        cws = cw.size()
        if q:
            cw.setWindowFlags(cw.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        else:
            cw.setWindowFlags(cw.windowFlags() & ~QtCore.Qt.WindowStaysOnTopHint)
        cw.resize(cws)
        cw.show()

    @_if_companion_exists
    def _close_companion_widget(self):
        self._companion_widget.close()

    @_if_companion_exists
    def _show_companion_statusbar_message(self, message, time=2000):
        self._companion_widget.window().statusBar().showMessage(message, time)

    @_if_companion_exists
    def _indicate_companion_map(self, visible):
        if hasattr(self, "_companion_map_indicator"):
            try:
                self.all.remove_artist(self._companion_map_indicator)
            except ValueError:
                # ignore errors resulting from the fact that the artist
                # has already been removed!
                pass
            del self._companion_map_indicator

        # don't draw an indicator if only one map is present in the figure
        if all(m.ax == self.ax for m in self.BM._children):
            return

        if visible:
            path = self.ax.patch.get_path()
            self._companion_map_indicator = mpatches.PathPatch(
                path, fc="none", ec="g", lw=5, zorder=9999
            )

            self.ax.add_artist(self._companion_map_indicator)
            self.all.add_artist(self._companion_map_indicator)

        self.BM.update()

    def _identify_maps_object(self, xy):
        clicked_map = None
        if xy is not None:
            for m in self.BM._children:
                if not m._new_axis_map:
                    # only search for Maps-object that initialized new axes
                    continue

                if m.ax.contains_point(xy):
                    clicked_map = m
                    break

        return clicked_map

    def _open_companion_widget(self, xy=None):
        """
        Open the companion-widget.

        Parameters
        ----------
        xy : tuple, optional
            The click position to identify the relevant Maps-object
            (in figure coordinates).
            If None, the calling Maps-object is used

            The default is None.

        """

        clicked_map = self._identify_maps_object(xy)

        if clicked_map is None:
            _log.error(
                "EOmaps: To activate the 'Companion Widget' you must "
                "position the mouse on top of an EOmaps Map!"
            )
            return

        # hide all other companion-widgets
        for m in self.BM._children:
            if m == clicked_map:
                continue
            if m._companion_widget is not None and m._companion_widget.isVisible():
                m._companion_widget.hide()
                m._indicate_companion_map(False)

        if clicked_map._companion_widget is None:
            clicked_map._init_companion_widget()

        if clicked_map._companion_widget is not None:
            if clicked_map._companion_widget.isVisible():
                clicked_map._companion_widget.hide()
                clicked_map._indicate_companion_map(False)
            else:
                clicked_map._companion_widget.show()
                clicked_map._indicate_companion_map(True)
                # execute all actions that should trigger before opening the widget
                # (e.g. update tabs to show visible layers etc.)
                for f in clicked_map._on_show_companion_widget:
                    f()

                # Do NOT activate the companion widget in here!!
                # Activating the window during the callback steals focus and
                # as a consequence the key-released-event is never triggered
                # on the figure and "w" would remain activated permanently.

                _key_release_event(clicked_map.f.canvas, "w")
                clicked_map._companion_widget.activateWindow()

    def _init_companion_widget(self, show_hide_key="w"):
        """
        Create and show the EOmaps Qt companion widget.

        Note
        ----
        The companion-widget requires using matplotlib with the Qt5Agg backend!
        To activate, use: `plt.switch_backend("Qt5Agg")`

        Parameters
        ----------
        show_hide_key : str or None, optional
            The keyboard-shortcut that is assigned to show/hide the widget.
            The default is "w".
        """
        try:
            from ..qtcompanion.app import MenuWindow

            if self._companion_widget is not None:
                _log.error(
                    "EOmaps: There is already an existing companinon widget for this"
                    " Maps-object!"
                )
                return
            if plt.get_backend().lower() in ["qtagg", "qt5agg"]:
                # only pass parent if Qt is used as a backend for matplotlib!
                self._companion_widget = MenuWindow(m=self, parent=self.f.canvas)
            else:
                self._companion_widget = MenuWindow(m=self)
                self._companion_widget.toggle_always_on_top()
                self._companion_widget.hide()  # hide on init

            # connect any pending signals
            for key, funcs in getattr(self, "_connect_signals_on_init", dict()).items():
                while len(funcs) > 0:
                    self._connect_signal(key, funcs.pop())

            # make sure that we clear the colormap-pixmap cache on startup
            self._emit_signal("cmapsChanged")

        except Exception:
            _log.exception(
                "EOmaps: Unable to initialize companion widget.",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

    def fetch_companion_wms_layers(self, refetch=True):
        """
        Fetch (and cache) WebMap layer names for the companion-widget.

        The cached layers are stored at the following location:

        >>> from eomaps import _data_dir
        >>> print(_data_dir)

        Parameters
        ----------
        refetch : bool, optional
            If True, the layers will be re-fetched and the cache will be updated.
            If False, the cached dict is loaded and returned.
            The default is True.
        """
        from ..qtcompanion.widgets.wms import AddWMSMenuButton

        return AddWMSMenuButton.fetch_all_wms_layers(self, refetch=refetch)

    def _connect_signal(self, name, func):
        parent = self.parent
        widget = parent._companion_widget

        # NOTE: use Maps.config(log_level=5) to get signal log messages!
        if widget is None:
            if not hasattr(parent, "_connect_signals_on_init"):
                parent._connect_signals_on_init = dict()

            parent._connect_signals_on_init.setdefault(name, set()).add(func)

        if widget is not None:
            try:
                getattr(parent._signal_container, name).connect(func)
                _log.log(1, f"Signal connected: {name} ({func.__name__})")

            except Exception:
                _log.log(
                    1,
                    f"There was a problem while trying to connect the function {func} "
                    f"to the signal {name} ",
                    exc_info=True,
                )

    # TODO how to deal with calls on _emit_signal?
    def _emit_signal(self, name, *args):
        parent = self.parent
        widget = parent._companion_widget

        # NOTE: use Maps.config(log_level=5) to get signal log messages!
        if widget is not None:
            try:
                getattr(parent._signal_container, name).emit(*args)
                _log.log(1, f"Signal emitted: {name} {args}")
            except Exception:
                _log.log(
                    1,
                    f"There was a problem while trying to emit the signal {name} "
                    f"with the args {args}",
                    exc_info=True,
                )

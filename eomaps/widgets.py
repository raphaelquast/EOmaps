from abc import abstractmethod
from functools import wraps
from contextlib import contextmanager

import numpy as np
import matplotlib.pyplot as plt

from . import _log
from ._blit_manager import LayerParser

try:
    import ipywidgets
except ImportError:
    _log.exception("EOmaps-widgets are missing the required dependency 'ipywidgets'!")


def _check_backend():
    backend = plt.get_backend()
    if "ipympl" not in backend.lower():
        raise AssertionError(
            "EOmaps-widgets only work with the 'ipympl (widget)' backend! "
            "Make sure you have 'ipympl' installed and use the magic-command "
            "'%matplotlib widget' to switch to the interactive jupyter backend!"
        )


@contextmanager
def _force_full(m):
    """A contextmanager to force a full update of the figure (to avoid glitches)"""
    force_full = getattr(m.BM, "_mpl_backend_force_full", False)

    try:
        m.BM._mpl_backend_force_full = True
        yield
    finally:
        m.BM._mpl_backend_force_full = force_full


# %% Layer Selector Widgets


class _LayerSelectionWidget:
    _description = "LayerSelectionWidget"

    def __init__(self, m, layers=None):
        """
        A widget to switch layers of a given Maps-object.

        Parameters
        ----------
        m : eomaps.Maps
            The Maps-object to use.
        layers : list, optional
            A list of layer-names to use.
            If None, all available layers of the provided Maps-object are used.

            The following options are possible:

            A list of layer-names

            >>> ["layer1", "layer2", ...]

            A list of layer-names and/or layer-names with transparency-assignments

            >>> ["layer1", "layer2", ("layer", 0.4)]

            To provide explict display-names for a layer, pass a list of the form
            `[display-name, <layer-assignment>]`

            >>> [["My Layer", "layer1"],
            >>>  ["My secondl lyer", "layer2"],
            >>>  ["Multiple layers", ("layer1",
            >>>                       ("layer", 0.4))]
            >>> ]

        """
        _check_backend()

        self._m = m
        self._set_layers_options(layers)

    def _set_layers_options(self, layers):
        # _layers is a list of the actual layer-names
        # _options is a list of tuples (name, value) passed to the widget-init

        if layers is None:
            self._layers = self._m._get_layers()
            self._options = [*self._layers]
        else:
            self._layers, self._options = [], []
            for l in layers:
                if isinstance(l, str):
                    self._layers.append(l)
                    self._options.append((l, l))
                elif isinstance(l, tuple):
                    l = self._parse_layer(l)
                    self._layers.append(l)
                    self._options.append((l, l))
                elif isinstance(l, list):
                    self._options.append((l[0], self._parse_layer(l[1])))
                    self._layers.append(self._parse_layer(l[1]))

    @staticmethod
    def _parse_layer(l):
        # check if a single transparent layer is provided
        if isinstance(l, tuple):
            if (
                len(l) == 2
                and isinstance(l[0], str)
                and isinstance(l[1], (int, float, np.number))
            ):
                return LayerParser._get_combined_layer_name(l)
            else:
                return LayerParser._get_combined_layer_name(*l)
        else:
            return l


class _SingleLayerSelectionWidget(_LayerSelectionWidget):
    _description = "Layers"
    _widget_cls = None

    @wraps(_LayerSelectionWidget.__init__)
    def __init__(self, m, layers=None, **kwargs):

        _LayerSelectionWidget.__init__(self, m=m, layers=layers)

        self._set_default_kwargs(kwargs)
        self._widget_cls.__init__(self, options=self._options, **kwargs)

        self.observe(self.handler)

    def _set_default_kwargs(self, kwargs):
        kwargs.setdefault("description", self._description)
        if self._m.BM.bg_layer in self._layers:
            kwargs.setdefault("value", self._m.BM.bg_layer)

    def handler(self, change):
        try:
            if self.value is not None:
                with _force_full(self._m):
                    self._m.show_layer(self.value)
                    self._m.BM.update()

        except Exception:
            _log.error("Problem in LayerSelectionWidget handler...", exc_info=True)


class _MultiLayerSelectionWidget(_SingleLayerSelectionWidget):
    def _set_default_kwargs(self, kwargs):
        kwargs.setdefault("description", self._description)

        if self._m.BM.bg_layer in self._layers:
            kwargs.setdefault("value", (self._m.BM.bg_layer, self._m.BM.bg_layer))
        else:
            kwargs.setdefault("value", (self._layers[0][1],))


class LayerDropdown(_SingleLayerSelectionWidget, ipywidgets.Dropdown):
    _widget_cls = ipywidgets.Dropdown


class LayerSelect(_SingleLayerSelectionWidget, ipywidgets.Select):
    _widget_cls = ipywidgets.Select


class LayerSelectionSlider(_SingleLayerSelectionWidget, ipywidgets.SelectionSlider):
    _widget_cls = ipywidgets.SelectionSlider


class LayerToggleButtons(_SingleLayerSelectionWidget, ipywidgets.ToggleButtons):
    _widget_cls = ipywidgets.ToggleButtons


class LayerRadioButtons(_SingleLayerSelectionWidget, ipywidgets.RadioButtons):
    _widget_cls = ipywidgets.RadioButtons


class LayerSelectionRangeSlider(
    _MultiLayerSelectionWidget, ipywidgets.SelectionRangeSlider
):
    _widget_cls = ipywidgets.SelectionRangeSlider

    def handler(self, change):
        try:
            if self.value is not None:
                i0 = self._layers.index(self.value[0])
                i1 = self._layers.index(self.value[1])
                with _force_full(self._m):
                    if i0 == i1:
                        self._m.show_layer(self.value[0])
                    else:
                        self._m.show_layer(*self._layers[i0 : i1 + 1])
        except Exception:
            _log.error("Problem in MultiLayerSelectionWidget handler...", exc_info=True)


class LayerSelectMultiple(_MultiLayerSelectionWidget, ipywidgets.SelectMultiple):
    _widget_cls = ipywidgets.SelectMultiple

    def handler(self, change):
        try:
            if self.value is not None:
                with _force_full(self._m):
                    self._m.show_layer(*self.value)
        except Exception:
            _log.error("Problem in MultiLayerSelectionWidget handler...", exc_info=True)


# %% Overlay Widgets


class OverlaySlider(ipywidgets.FloatSlider):
    def __init__(self, m, layer, **kwargs):
        """
        A Slider to overlay a selected layer on top of other layers

        Parameters
        ----------
        m : eomaps.Maps
            The Maps-object to use.
        layer : str
            The layer to overlay.
        kwargs:
            Additional kwargs passed to the used `ipywidgets.FloatSlider`.

        """
        self._m = m
        _check_backend()

        self._layer = layer

        kwargs.setdefault("value", 0)
        kwargs.setdefault("min", 0)
        kwargs.setdefault("max", 1)
        kwargs.setdefault("step", 0.01)
        kwargs.setdefault("description", f"Overlay\n'{layer}':")

        super().__init__(**kwargs)

        self._last_value = self.value

        self.observe(self.handler)

    def handler(self, change):
        try:
            layers, alphas = LayerParser._parse_multi_layer_str(self._m.BM.bg_layer)

            # in case the active layer has the overlay on top, strip off the overlay
            # from the active layer!
            if layers[-1] == self._layer and alphas[-1] == self._last_value:
                base = LayerParser._get_combined_layer_name(
                    *zip(layers[:-1], alphas[:-1])
                )
            else:
                base = self._m.BM.bg_layer

            with _force_full(self._m):
                self._m.show_layer(base, (self._layer, self.value))

            self._last_value = self.value
        except Exception:
            _log.error("Problem in OverlaySlider handler...", exc_info=True)


# %% CallbackWidgets


class _CallbackWidget:
    def __init__(self, m, **kwargs):
        self._m = m
        _check_backend()

        self._kwargs = kwargs
        self._cid = None

    @abstractmethod
    def attach_callback(self, **kwargs):
        """Attach the callback to the map and return the cid."""
        return "cid"

    def handler(self, change):
        try:
            if self.value is True and self._cid is None:
                self._cid = self.attach_callback(**self._kwargs)

            if self.value is False and self._cid is not None:
                self._cid = self._m.all.cb.click.remove(self._cid)
        except Exception:
            _log.error("Problem in Checkbox handler...", exc_info=True)


class _CallbackCheckbox(ipywidgets.Checkbox, _CallbackWidget):
    _description = "Callback Checkbox"

    @wraps(_CallbackWidget.__init__)
    def __init__(self, *args, value=False, description=None, **kwargs):
        _CallbackWidget.__init__(self, *args, **kwargs)
        super().__init__(
            value=value,
            description=description if description is not None else self._description,
        )
        self.observe(self.handler)


class ClickAnnotateCheckbox(_CallbackCheckbox):
    _description = "Annotate (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.annotate(**kwargs)


class ClickMarkCheckbox(_CallbackCheckbox):
    _description = "Mark (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.mark(**kwargs)


class ClickPrintToConsoleCheckbox(_CallbackCheckbox):
    _description = "Print (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.print_to_console(**kwargs)


class ClickPeekLayerCheckbox(_CallbackCheckbox):
    _description = "Peek Layer (Click)"

    def __init__(self, *args, layer=None, **kwargs):
        assert (
            layer is not None
        ), "EOmaps: You must specify the layer for the PeekLayerCheckbox!"

        self._description = f"Peek Layer: '{layer}'"

        super().__init__(*args, layer=layer, **kwargs)

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.peek_layer(**kwargs)


# NOTE: pick callbacks are attached to the provided Maps objects,
#       click callback are attached to m.all!
class PickAnnotateCheckbox(_CallbackCheckbox):
    _description = "Annotate (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.annotate(**kwargs)


class PickMarkCheckbox(_CallbackCheckbox):
    _description = "Mark (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.mark(**kwargs)


class PickPrintToConsoleCheckbox(_CallbackCheckbox):
    _description = "Print (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.print_to_console(**kwargs)

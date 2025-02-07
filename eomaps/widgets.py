from contextlib import contextmanager

import numpy as np

from . import _log
from ._blit_manager import LayerParser

try:
    import ipywidgets
except ImportError:
    _log.warning("EOmaps-widgets are missing the required dependency 'ipywidgets'!")


@contextmanager
def _force_full(m):
    """A contextmanager to force a full update of the figure (to avoid glitches)"""
    force_full = getattr(m.BM, "_mpl_backend_force_full", False)

    try:
        m.BM._mpl_backend_force_full = True
        yield
    finally:
        m.BM._mpl_backend_force_full = force_full


from textwrap import dedent, indent


def _add_docstring(prefix="", suffix="", replace_with=None):
    def _add_docstring(cls):

        if replace_with is None and cls.__doc__ is not None:
            doc = f"{prefix}\n{dedent(cls.__doc__)}\n{suffix}"
        elif replace_with is not None:
            doc = f"{prefix}\n{dedent(replace_with.__doc__)}\n{suffix}"
        else:
            doc = f"{prefix}\n{dedent(suffix)}"

        doc = indent(doc, "    ")
        cls.__doc__ = doc
        cls.__init__.__doc__ = doc

        return cls

    return _add_docstring


# %% Layer Selector Widgets


class _LayerSelectionWidget:
    # A widget to switch layers of a given Maps-object.

    """

    For more information on how to customize the widgets, have a look at the
    documentation for Jupyter Widgets (https://ipywidgets.readthedocs.io).

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

        To provide explicit display-names for a layer, pass a list of the form
        `[display-name, <layer-assignment>]`

        >>> [["My Layer", "layer1"],
        >>>  ["My secondl lyer", "layer2"],
        >>>  ["Multiple layers", ("layer1",
        >>>                       ("layer", 0.4))]
        >>> ]

    """

    _description = "Layers"
    _widget_cls = None

    def __init__(self, m, layers=None, **kwargs):
        self._m = m
        self._set_layers_options(layers)

        self._set_default_kwargs(kwargs)
        self._widget_cls.__init__(self, options=self._options, **kwargs)

        if hasattr(self, "change_handler"):
            self.observe(self.change_handler, names="value", type="change")

        # add a callback to update the widget values if the map-layer changes
        if hasattr(self, "_cb_on_layer_change"):
            self._m.BM.on_layer(self._cb_on_layer_change, persistent=True)

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

    @contextmanager
    def _unobserve_change_handler(self):
        try:
            self.unobserve(self.change_handler, names="value", type="change")

            yield
        finally:
            self.observe(self.change_handler, names="value", type="change")


class _SingleLayerSelectionWidget(_LayerSelectionWidget):
    def _set_default_kwargs(self, kwargs):
        kwargs.setdefault("description", self._description)
        if self._m.BM.bg_layer in self._layers:
            kwargs.setdefault("value", self._m.BM.bg_layer)

    def change_handler(self, change):
        try:
            if self.value is not None:
                with _force_full(self._m):
                    self._m.show_layer(self.value)

        except Exception:
            _log.error("Problem in LayerSelectionWidget handler...", exc_info=True)

    def _cb_on_layer_change(self, **kwargs):
        """A callback that is executed on all layer changes to update the widget-value."""
        try:
            layer = self._m.BM.bg_layer
            if layer in self._layers:
                with self._unobserve_change_handler():
                    self.value = layer

        except Exception:
            _log.exception(f"Unable to update widget value to {self._m.BM.bg_layer}")


@_add_docstring(
    "A Dropdown list to select the visible layer.", replace_with=_LayerSelectionWidget
)
class LayerDropdown(_SingleLayerSelectionWidget, ipywidgets.Dropdown):
    _widget_cls = ipywidgets.Dropdown


@_add_docstring(
    "A list-box to select a single visible layer.", replace_with=_LayerSelectionWidget
)
class LayerSelect(_SingleLayerSelectionWidget, ipywidgets.Select):
    _widget_cls = ipywidgets.Select


@_add_docstring(
    "Toggle buttons to select a single visible layer.",
    replace_with=_LayerSelectionWidget,
)
class LayerToggleButtons(_SingleLayerSelectionWidget, ipywidgets.ToggleButtons):
    _widget_cls = ipywidgets.ToggleButtons


@_add_docstring(
    "Radio buttons to select a single visible layer.",
    replace_with=_LayerSelectionWidget,
)
class LayerRadioButtons(_SingleLayerSelectionWidget, ipywidgets.RadioButtons):
    _widget_cls = ipywidgets.RadioButtons


@_add_docstring(
    "A slider to select a single visible layer.", replace_with=_LayerSelectionWidget
)
class LayerSelectionSlider(_SingleLayerSelectionWidget, ipywidgets.SelectionSlider):
    _widget_cls = ipywidgets.SelectionSlider


# %% Multi Selector Widgets


class _MultiLayerSelectionWidget(_LayerSelectionWidget):
    def _set_default_kwargs(self, kwargs):
        kwargs.setdefault("description", self._description)

        if self._m.BM.bg_layer in self._layers:
            kwargs.setdefault("value", (self._m.BM.bg_layer, self._m.BM.bg_layer))


@_add_docstring(
    "A list-box to select multiple visible layers.", replace_with=_LayerSelectionWidget
)
class LayerSelectMultiple(_MultiLayerSelectionWidget, ipywidgets.SelectMultiple):
    _widget_cls = ipywidgets.SelectMultiple

    def change_handler(self, change):
        try:
            if len(self.value) > 0 and None not in self.value:
                with _force_full(self._m):
                    self._m.show_layer(*self.value)
        except Exception:
            _log.error("Problem in MultiLayerSelectionWidget handler...", exc_info=True)

    def _cb_on_layer_change(self, **kwargs):
        """A callback that is executed on all layer changes to update the widget-value."""
        try:
            # Identify all layers that are part of the currently visible layer
            # TODO transparencies are currently ignored (e.g. treated as selected)
            active_layers = self._m.BM._get_active_layers_alphas[0]
            found = [l for l in self._layers if l in active_layers]

            if len(found) > 0:
                with self._unobserve_change_handler():
                    self.value = found

        except Exception:
            _log.exception(f"Unable to update widget value to {self._m.BM.bg_layer}")


@_add_docstring(
    "A range-slider to view a combination of a range of layers.",
    replace_with=_LayerSelectionWidget,
)
class LayerSelectionRangeSlider(
    _MultiLayerSelectionWidget, ipywidgets.SelectionRangeSlider
):
    _widget_cls = ipywidgets.SelectionRangeSlider

    def change_handler(self, change):
        try:
            if len(self.value) > 0 and None not in self.value:
                i0 = self._layers.index(self.value[0])
                i1 = self._layers.index(self.value[1])
                with _force_full(self._m):
                    if i0 == i1:
                        self._m.show_layer(self.value[0])
                    else:
                        self._m.show_layer(*self._layers[i0 : i1 + 1])
        except Exception:
            _log.error("Problem in MultiLayerSelectionWidget handler...", exc_info=True)

    def _cb_on_layer_change(self, **kwargs):
        """A callback that is executed on all layer changes to update the widget-value."""
        try:
            # identify all layers that are part of the currently visible layer
            # TODO transparencies are currently ignored (e.g. treated as selected)
            # TODO properly handle case where intermediate layers are not selected
            #      (right now only start- and stop determines the range independent
            #       of the selected layers in between)
            active_layers = self._m.BM._get_active_layers_alphas[0]
            found_idx = [
                self._layers.index(l) for l in self._layers if l in active_layers
            ]

            if len(found_idx) > 0:
                mi, ma = min(found_idx), max(found_idx)

                with self._unobserve_change_handler():
                    self.value = (self._layers[mi], self._layers[ma])

        except Exception:
            _log.exception(f"Unable to update widget value to {self._m.BM.bg_layer}")


# %% Layer Overlay Widgets


class LayerButton(ipywidgets.Button):
    """
    A Button to show a selected layer.

    Parameters
    ----------
    m : eomaps.Maps
        The Maps-object to use.
    layer : str, list or tuple
        The layer to overlay.
        Can be either a string, a tuple of a layer and a transparency or a list
        of the aforementioned types.

        See :py:meth:`Maps.show_layer` for more details.

    kwargs:
        Additional kwargs passed to the used `ipywidgets.FloatSlider`.

    """

    def __init__(self, m, layer, **kwargs):
        self._m = m
        self._layer = self._parse_layer(layer)

        kwargs.setdefault("description", self._layer)

        super().__init__(**kwargs)
        self.on_click(self.click_handler)

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
        elif isinstance(l, list):
            return LayerParser._get_combined_layer_name(*l)
        else:
            return l

    def click_handler(self, b):
        try:
            self._m.show_layer(self._layer)
        except Exception:
            _log.error("Problem in LayerButton handler...", exc_info=True)


class LayerOverlaySlider(ipywidgets.FloatSlider):
    """
    A Slider to overlay a selected layer on top of other layers.

    Parameters
    ----------
    m : eomaps.Maps
        The Maps-object to use.
    layer : str
        The layer to overlay.
    kwargs:
        Additional kwargs passed to the used `ipywidgets.FloatSlider`.

    """

    def __init__(self, m, layer, **kwargs):
        self._m = m
        self._layer = layer

        kwargs.setdefault("value", 0)
        kwargs.setdefault("min", 0)
        kwargs.setdefault("max", 1)
        kwargs.setdefault("step", 0.01)
        kwargs.setdefault("description", f"Overlay\n'{layer}':")

        super().__init__(**kwargs)

        self._last_value = self.value

        self.observe(self.change_handler, names="value", type="change")

    def change_handler(self, change):
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
    """

    For more information on how to customize the widgets, have a look at the
    documentation for Jupyter Widgets (https://ipywidgets.readthedocs.io).

    Parameters
    ----------
    m : eomaps.Maps
        The Maps-object to use.
    widget_kwargs : dict
        A dict of kwargs passed to the creation of the Jupyter widget.
    kwargs:
        All remaining kwargs are passed to the callback.
        (e.g. m.cb.<method>.<name>(...kwargs...))

    """

    _cid = None
    _widget_cls = None

    def __init__(self, m, widget_kwargs=None, **kwargs):
        self._m = m
        self._kwargs = kwargs

        if widget_kwargs is None:
            widget_kwargs = dict()

        widget_kwargs.setdefault("value", False)
        widget_kwargs.setdefault("description", self._description)

        self._widget_cls.__init__(self, **widget_kwargs)

        self.observe(self.change_handler, names="value", type="change")

    def attach_callback(self, **kwargs):
        """Attach the callback to the map and return the cid."""
        raise NotImplementedError()

    def change_handler(self, change):
        try:
            if self.value is True and self._cid is None:
                self._cid = self.attach_callback(**self._kwargs)

            if self.value is False and self._cid is not None:
                self.remove_callback()
        except Exception:
            _log.error("Problem in Checkbox handler...", exc_info=True)


class _CallbackCheckbox(_CallbackWidget, ipywidgets.Checkbox):
    _description = "Callback Checkbox"
    _widget_cls = ipywidgets.Checkbox


class _ClickCallbackCheckbox(_CallbackCheckbox):
    def remove_callback(self, **kwargs):
        self._m.all.cb.click.remove(self._cid)
        self._cid = None


class _PickCallbackCheckbox(_CallbackCheckbox):
    def remove_callback(self, **kwargs):
        self._m.cb.pick.remove(self._cid)
        self._cid = None


@_add_docstring(
    "Checkbox to toggle the 'click.annotate' callback.", replace_with=_CallbackWidget
)
class ClickAnnotateCheckbox(_ClickCallbackCheckbox):
    _description = "Annotate (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.annotate(**kwargs)


@_add_docstring(
    "Checkbox to toggle the 'click.mark' callback.", replace_with=_CallbackWidget
)
class ClickMarkCheckbox(_ClickCallbackCheckbox):
    _description = "Mark (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.mark(**kwargs)


@_add_docstring(
    "Checkbox to toggle the 'click.print_to_console' callback.",
    replace_with=_CallbackWidget,
)
class ClickPrintToConsoleCheckbox(_ClickCallbackCheckbox):
    _description = "Print (Click)"

    def attach_callback(self, **kwargs):
        return self._m.all.cb.click.attach.print_to_console(**kwargs)


@_add_docstring(
    "Checkbox to toggle the 'click.peek_layer' callback.", replace_with=_CallbackWidget
)
class ClickPeekLayerCheckbox(_ClickCallbackCheckbox):
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
@_add_docstring(
    "Checkbox to toggle the 'pick.annotate' callback.", replace_with=_CallbackWidget
)
class PickAnnotateCheckbox(_PickCallbackCheckbox):
    _description = "Annotate (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.annotate(**kwargs)


@_add_docstring(
    "Checkbox to toggle the 'pick.mark' callback.", replace_with=_CallbackWidget
)
class PickMarkCheckbox(_PickCallbackCheckbox):
    _description = "Mark (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.mark(**kwargs)


@_add_docstring(
    "Checkbox to toggle the 'pick.print_to_console' callback.",
    replace_with=_CallbackWidget,
)
class PickPrintToConsoleCheckbox(_PickCallbackCheckbox):
    _description = "Print (Pick)"

    def attach_callback(self, **kwargs):
        return self._m.cb.pick.attach.print_to_console(**kwargs)

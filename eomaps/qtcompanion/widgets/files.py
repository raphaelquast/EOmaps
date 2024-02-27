# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

import logging

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt, QLocale, Signal
from pathlib import Path
import io
import numpy as np

_log = logging.getLogger(__name__)

from .utils import (
    LineEditComplete,
    InputCRS,
    CmapDropdown,
    show_error_popup,
    to_float_none,
    get_crs,
    str_to_bool,
    GetColorWidget,
    AlphaSlider,
)

from ..base import NewWindow, get_dummy_spacer
from ..common import iconpath


def _none_or_val(val):
    if val == "None":
        return None
    else:
        return val


def _floatstr_to_int(val):
    # pythons int() cannot convert float-strings to integer!
    return int(float(val))


def _identify_radius(r):
    r = r.replace(" ", "")
    try:
        # try to identify tuples
        if r.startswith("(") and r.endswith(")"):
            rx, ry = map(float, r.lstrip("(").rstrip(")").split(","))
        elif r == "None":
            r = None
        else:
            r = float(r)
            rx = ry = r
        return rx, ry
    except:
        return r


def _get_gdf_file_endings():
    try:
        from fiona.drvsupport import vector_driver_extensions

        file_endings = [f".{i}" for i in vector_driver_extensions()]
    except Exception as ex:
        file_endings = []

    return file_endings


class AddColorbarCheckbox(QtWidgets.QCheckBox):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Add Colorbar</h3>"
                "If checked, a colorbar will be added for the data.",
            )


class LayerInput(LineEditComplete):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Layer</h3>"
                "Set the layer at which the dataset should be plotted.",
            )


class XInput(LineEditComplete):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set X Coordinate</h3>"
                "Set the variable that should be used as x-coordinate.",
            )


class YInput(LineEditComplete):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set Y Coordinate</h3>"
                "Set the variable that should be used as Y-coordinate.",
            )


class ParameterInput(LineEditComplete):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set Parameter</h3>"
                "Set the variable that should be used as data.",
            )


class IDInput(LineEditComplete):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set ID</h3>"
                "Set the variable that should be used to identify datapoints.",
            )


class ZorderInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set zorder</h3>"
                "Set the zorder (e.g. the vertical stacking order) that will be "
                "assigned to the artist.",
            )


class VminInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set vmin</h3>"
                "Set the lower boundary that is used for color scaling."
                "(by default the minimal value of the dataset is used)",
            )


class VmaxInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set vmax</h3>"
                "Set the upper boundary that is used for color scaling."
                "(by default the maximal value of the dataset is used)",
            )


class MinMaxUpdateButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set vmin/vmax to data limits</h3>"
                "Identify vmin/vmax from the selected dataset.",
            )


class ShapeSelector(QtWidgets.QFrame):
    _ignoreargs = ["shade_hook", "agg_hook"]

    # special treatment of arguments
    _argspecials = dict(
        aggregator=_none_or_val,
        mask_radius=_none_or_val,
        radius=_identify_radius,
        n=_none_or_val,
        maxsize=_floatstr_to_int,
    )

    _argtypes = dict(
        radius=(float, str),
        radius_crs=(int, str),
        n=(int,),
        mesh=(str_to_bool,),
        masked=(str_to_bool,),
        mask_radius=(float,),
        flat=(str_to_bool,),
        aggregator=(str,),
    )

    def __init__(self, *args, m=None, default_shape="shade_points", **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m
        self.shape = default_shape

        self.layout = QtWidgets.QVBoxLayout()
        self.options = QtWidgets.QVBoxLayout()

        self.shape_selector = QtWidgets.QComboBox()
        for i in self.m.set_shape._shp_list:
            self.shape_selector.addItem(i)

        label = QtWidgets.QLabel("Shape:")
        self.shape_selector.activated[str].connect(self.shape_changed)
        shapesel = QtWidgets.QHBoxLayout()
        shapesel.addWidget(label)
        shapesel.addWidget(self.shape_selector)

        self.layout.addLayout(shapesel)
        self.layout.addLayout(self.options)

        self.setLayout(self.layout)

        self.shape_selector.setCurrentIndex(self.shape_selector.findText(self.shape))
        self.shape_changed(self.shape)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set Plot Shape</h3>"
                "Set the plot-shape that is used to visualize the dataset."
                "<br><br>"
                "<b>NOTE:</b> Some shapes require more computational effort than "
                "others! Checkout the docs on how to choose the shape that fits "
                "your needs!",
            )

    def set_shape(self, shape):
        self.shape_selector.setCurrentIndex(self.shape_selector.findText(shape))
        self.shape_changed(shape)

    def argparser(self, key, val):
        special = self._argspecials.get(key, None)
        if special is not None:
            return special(val)

        convtype = self._argtypes.get(key, (str,))

        for t in convtype:
            try:
                convval = t(val)
            except ValueError:
                continue

            return convval

        _log.warning(f"EOmaps: value-conversion for {key} = {val} did not succeed!")
        return val

    @property
    def shape_args(self):

        out = dict(shape=self.shape)
        for key, val in self.paraminputs.items():
            out[key] = self.argparser(key, val.text())

        return out

    def shape_changed(self, s):
        self.shape = s

        import inspect

        signature = inspect.signature(getattr(self.m.set_shape, s))

        self.clear_item(self.options)

        self.options = QtWidgets.QVBoxLayout()

        self.paraminputs = dict()
        for key, val in signature.parameters.items():

            paramname, paramdefault = val.name, val.default

            if paramname in self._ignoreargs:
                continue

            param = QtWidgets.QHBoxLayout()
            name = QtWidgets.QLabel(paramname)
            valinput = QtWidgets.QLineEdit(str(paramdefault))

            param.addWidget(name)
            param.addWidget(valinput)

            self.paraminputs[paramname] = valinput

            self.options.addLayout(param)

        self.layout.addLayout(self.options)

    def clear_item(self, item):
        if hasattr(item, "layout"):
            if callable(item.layout):
                layout = item.layout()
        else:
            layout = None

        if hasattr(item, "widget"):
            if callable(item.widget):
                widget = item.widget()
        else:
            widget = None

        if widget:
            widget.setParent(None)
        elif layout:
            for i in reversed(range(layout.count())):
                self.clear_item(layout.itemAt(i))


class PlotFileWidget(QtWidgets.QWidget):

    file_endings = None
    default_shape = "shade_points"

    def __init__(
        self,
        *args,
        m=None,
        close_on_plot=True,
        attach_tab_after_plot=True,
        tab=None,
        window_title="Plot File",
        **kwargs,
    ):
        """
        A widget to add a layer from a file
        """
        super().__init__(*args, **kwargs)

        self.m = m
        self.tab = tab
        self.window_title = window_title

        self.attach_tab_after_plot = attach_tab_after_plot
        self.close_on_plot = close_on_plot

        self.m2 = None

        self.file_path = None

        self.b_plot = QtWidgets.QPushButton("Plot!", self)
        self.b_plot.clicked.connect(self.b_plot_file)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self.file_info = QtWidgets.QLabel()
        self.file_info.setWordWrap(True)
        self.file_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll.setWidget(self.file_info)

        # add colorbar checkbox
        self.cb_colorbar = AddColorbarCheckbox("Add colorbar")

        # layer
        self.layer_label = QtWidgets.QLabel("<b>Layer:</b>")
        self.layer = LayerInput()
        self.layer.setPlaceholderText(str(self.m.BM.bg_layer))

        setlayername = QtWidgets.QWidget()
        layername = QtWidgets.QHBoxLayout()
        layername.addWidget(self.layer_label)
        layername.addWidget(self.layer)
        setlayername.setLayout(layername)

        # shape selector (with shape options)
        self.shape_selector = ShapeSelector(m=self.m, default_shape=self.default_shape)

        self.setStyleSheet(
            """
            ShapeSelector{
                border:1px dashed;
                }
            """
        )

        # colormaps
        self.cmaps = CmapDropdown()

        validator = QtGui.QDoubleValidator()
        # make sure the validator uses . as separator
        validator.setLocale(QLocale("en_US"))

        # vmin / vmax
        vminlabel, vmaxlabel = QtWidgets.QLabel("vmin="), QtWidgets.QLabel("vmax=")
        self.vmin, self.vmax = VminInput(), VmaxInput()
        self.vmin.setValidator(validator)
        self.vmax.setValidator(validator)

        self.minmaxupdate = MinMaxUpdateButton("🗘")
        self.minmaxupdate.clicked.connect(self.do_update_vals)

        minmaxlayout = QtWidgets.QHBoxLayout()
        minmaxlayout.setAlignment(Qt.AlignLeft)
        minmaxlayout.addWidget(vminlabel)
        minmaxlayout.addWidget(self.vmin)
        minmaxlayout.addWidget(vmaxlabel)
        minmaxlayout.addWidget(self.vmax)
        minmaxlayout.addWidget(self.minmaxupdate, Qt.AlignRight)

        options = QtWidgets.QVBoxLayout()
        options.addWidget(self.cb_colorbar)
        options.addWidget(setlayername)
        options.addWidget(self.shape_selector)
        options.addWidget(self.cmaps)
        options.addLayout(minmaxlayout)
        options.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        optionwidget = QtWidgets.QWidget()
        optionwidget.setLayout(options)

        optionscroll = QtWidgets.QScrollArea()
        optionscroll.setWidgetResizable(True)
        optionscroll.setMinimumWidth(200)
        optionscroll.setWidget(optionwidget)

        options_split = QtWidgets.QSplitter(Qt.Horizontal)
        options_split.addWidget(scroll)
        options_split.addWidget(optionscroll)
        options_split.setSizes((500, 300))

        self.options_layout = QtWidgets.QHBoxLayout()
        self.options_layout.addWidget(options_split)

        self.x = XInput("x")
        self.y = YInput("y")
        self.parameter = ParameterInput("param")
        self.ID = IDInput("ID")
        self.crs = InputCRS()

        # update info-text with respect to the selected columns
        self.x.textChanged.connect(self.update_info_text)
        self.y.textChanged.connect(self.update_info_text)
        self.parameter.textChanged.connect(self.update_info_text)
        self.ID.textChanged.connect(self.update_info_text)

        tx = QtWidgets.QLabel("<b>x:</b>")
        ty = QtWidgets.QLabel("<b>y:</b>")
        tparam = QtWidgets.QLabel("<b>parameter:</b>")
        tcrs = QtWidgets.QLabel("<b>crs:</b>")
        self.tID = QtWidgets.QLabel("<b>ID:</b>")

        plotargs = QtWidgets.QHBoxLayout()
        plotargs.addWidget(self.tID)
        plotargs.addWidget(self.ID)
        plotargs.addWidget(tx)
        plotargs.addWidget(self.x)
        plotargs.addWidget(ty)
        plotargs.addWidget(self.y)
        plotargs.addWidget(tparam)
        plotargs.addWidget(self.parameter)
        plotargs.addWidget(tcrs)
        plotargs.addWidget(self.crs)

        plotargs.addWidget(self.b_plot)

        self.title = QtWidgets.QLabel("<b>Set plot variables:</b>")
        withtitle = QtWidgets.QVBoxLayout()
        withtitle.addWidget(self.title)
        withtitle.addLayout(plotargs)
        withtitle.setAlignment(Qt.AlignBottom)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.addLayout(self.options_layout, stretch=1)
        self.layout.addLayout(withtitle)

        self.setLayout(self.layout)

        self._file_handle = None

    def get_info_text(self):
        return "???"

    def update_info_text(self):
        try:
            self.file_info.setText(self.get_info_text())
        except Exception:
            self.file_info.setText("???")

    def get_layer(self):
        layer = self.layer.text()
        if layer == "":
            layer = self.layer.placeholderText()

        return layer

    def open_file(self, file_path=None):
        self._open_filehandle(file_path)

        if file_path is not None:
            self.file_path = file_path

        if self.file_endings is not None:
            if file_path.suffix.lower() not in self.file_endings:
                self.file_info.setText(
                    f"the file {self.file_path.name} is not a valid file"
                )
                self.file_path = None
                return

        self.do_open_file(file_path)

        self.file_info.setText(self.get_info_text())

        self.layer.set_complete_vals(
            [file_path.name]
            + [i for i in self.m._get_layers() if not i.startswith("_")]
        )

        self.newwindow = NewWindow(
            m=self.m,
            title=self.window_title,
            on_close=self._close_filehandle,
        )

        self.newwindow.statusBar().showMessage(str(self.file_path))

        self.newwindow.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )

        self.newwindow.layout.addWidget(self)
        self.newwindow.resize(800, 500)
        # self.newwindow.setWindowModality(Qt.ApplicationModal) make the popup blocking
        self.newwindow.show()

        self.newwindow.on_close

    def b_plot_file(self):
        try:
            self.do_plot_file()

            # fetch the min/max values if no explicit values were provided
            vmin, vmax = self.vmin.text(), self.vmax.text()
            if vmin != "" and vmax != "":
                pass
            else:
                self.do_update_vals()
                if vmin != "":
                    self.vmin.setText(vmin)
                if vmax != "":
                    self.vmax.setText(vmax)

        except Exception:
            import traceback

            show_error_popup(
                text="There was an error while trying to plot the data!",
                title="Error",
                details=traceback.format_exc(),
            )
            return

        try:
            if self.close_on_plot:
                self.newwindow.close()

            if self.attach_tab_after_plot:
                self.attach_as_tab()
        finally:
            self._close_filehandle()

    def do_open_file(self):
        file_path = Path(QtWidgets.QFileDialog.getOpenFileName()[0])

        return (
            file_path,
            f"The file {file_path.stem} has\n {file_path.stat().st_size} bytes.",
        )

    def _open_filehandle(self, file_path):
        self._file_handle = open(file_path, "r")

    def _close_filehandle(self):

        if self._file_handle is not None:
            try:
                self._file_handle.close()
            except Exception as ex:
                _log.error(
                    "EOmaps: encountered a problem while closing the file.",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

        self._file_handle = None

    def do_plot_file(self):
        self.file_info.setText("Implement `.do_plot_file()` to plot the data!")

    def do_update_vals(self):
        return

    def attach_as_tab(self):
        if self.tab is None:
            return

        if self.file_path is not None:
            name = self.file_path.name
        else:
            return

        if len(name) > 15:
            name = (
                self.file_path.stem[:6]
                + "..."
                + self.file_path.stem[-3:]
                + self.file_path.suffix
            )
        self.tab.addTab(self, name)

        tabindex = self.tab.indexOf(self)

        self.tab.setCurrentIndex(tabindex)
        self.tab.setTabToolTip(tabindex, str(self.file_path))

        self.title.setText("<b>Variables used for plotting:</b>")

        self.layer.setEnabled(False)
        self.x.setEnabled(False)
        self.y.setEnabled(False)
        self.parameter.setEnabled(False)
        self.crs.setEnabled(False)
        self.ID.setEnabled(False)

        # self.vmin.setReadOnly(True)
        # self.vmax.setReadOnly(True)
        self.vmin.setCursorPosition(0)
        self.vmin.setEnabled(False)
        self.vmax.setCursorPosition(0)
        self.vmax.setEnabled(False)

        self.minmaxupdate.setEnabled(False)
        self.cmaps.setEnabled(False)
        self.shape_selector.setEnabled(False)
        self.layer.setEnabled(False)
        self.cb_colorbar.setEnabled(False)

        self.b_plot.close()


class PlotXarrayWidget(PlotFileWidget):
    def __init__(self, *args, window_title="Plot GeoTIFF FIle", **kwargs):

        super().__init__(*args, **kwargs)

        # hide ID inputs... not supported for GeoTIFF
        self.tID.hide()
        self.ID.hide()

        self.default_sel_args = dict()

    def get_crs(self):
        return get_crs(self.crs.text())

    def _open_filehandle(self, file_path):
        import xarray as xar

        self._file_handle = xar.open_dataset(file_path, mask_and_scale=False)

    def get_info_text(self):
        f = self._file_handle
        import xarray as xar

        try:
            selargs = self.get_sel_args()
            usef = f[self.parameter.text()].sel(**selargs)
            s = usef.__repr__()
            return s
        except Exception:
            return f.__repr__()

    def attach_as_tab(self, *args, **kwargs):
        super().attach_as_tab(*args, **kwargs)

        for key, val in self.sel_inputs.items():
            val["inp"].setEnabled(False)

    def get_sel_args(self):
        # use isVisibleTo to avoid issues
        # (see https://stackoverflow.com/a/40174748/9703451)
        s = dict()
        for key, val in self.sel_inputs.items():
            sel = val["inp"].text()
            if val["inp"].isVisibleTo(self) and sel != "":
                # convert to the correct dtype
                sel = np.array(sel).astype(val["dtype"])

                s[key] = sel
        return s

    def do_update_vals(self):
        f = self._file_handle

        try:

            vals = f[self.parameter.text()]
            if hasattr(vals, "_FillValue"):
                vals = vals.where(vals != vals._FillValue)
            vmin = vals.min()
            vmax = vals.max()

            self.vmin.setText(str(float(vmin)))
            self.vmax.setText(str(float(vmax)))
        except Exception:
            import traceback

            show_error_popup(
                text="There was an error while trying to update the values.",
                title="Unable to update values.",
                details=traceback.format_exc(),
            )

    def get_sel_layout(self, f):
        self.sel_title = QtWidgets.QLabel("<b>Select index-labels to plot:</b>")

        layout = QtWidgets.QHBoxLayout()
        dims = list(f.dims)

        self.sel_inputs = dict()
        # get completion values
        for d in dims:
            vals = f[d].values.astype(str)

            label = QtWidgets.QLabel(f"{d}:")
            inp = LineEditComplete()
            inp.set_complete_vals(vals)

            if d in self.default_sel_args:
                inp.setText(str(self.default_sel_args[d]))

            inp.textChanged.connect(self.update_info_text)

            layout.addWidget(label)
            layout.addWidget(inp)

            self.sel_inputs[d] = dict(inp=inp, label=label, dtype=f[d].dtype)

        self.x.textEdited.connect(self.deactivate_sel_cb)
        self.x.completer().activated.connect(self.deactivate_sel_cb)
        self.y.textEdited.connect(self.deactivate_sel_cb)
        self.y.completer().activated.connect(self.deactivate_sel_cb)
        self.parameter.textEdited.connect(self.deactivate_sel_cb)
        self.parameter.completer().activated.connect(self.deactivate_sel_cb)
        self.deactivate_sel_cb()
        layout.addWidget(get_dummy_spacer())

        sel_layout = QtWidgets.QVBoxLayout()
        sel_layout.addWidget(self.sel_title)
        sel_layout.addLayout(layout)

        return sel_layout

    def deactivate_sel_cb(self):
        selected_dims = [self.x.text(), self.y.text()]

        try:
            param_dims = self._file_handle[self.parameter.text()].dims
        except Exception:
            param_dims = None

        for d in self.sel_inputs:
            if d in selected_dims or (param_dims is not None and d not in param_dims):
                self.sel_inputs[d]["label"].hide()
                self.sel_inputs[d]["inp"].hide()
            else:
                self.sel_inputs[d]["label"].show()
                self.sel_inputs[d]["inp"].show()

            if any(i["inp"].isVisibleTo(self) for i in self.sel_inputs.values()):
                self.sel_title.show()
            else:
                self.sel_title.hide()

    def do_plot_file(self):
        f = self._file_handle

        if f is None:
            return

        m2 = self.m.new_layer_from_file.NetCDF(
            f,
            shape=self.shape_selector.shape_args,
            coastline=False,
            layer=self.get_layer(),
            coords=(self.x.text(), self.y.text()),
            parameter=self.parameter.text(),
            data_crs=self.get_crs(),
            sel=self.get_sel_args(),
            cmap=self.cmaps.currentText(),
            vmin=to_float_none(self.vmin.text()),
            vmax=to_float_none(self.vmax.text()),
        )

        if self.cb_colorbar.isChecked():
            m2.add_colorbar()

        m2.show_layer(m2.layer)

        self.m2 = m2


class PlotGeoTIFFWidget(PlotXarrayWidget):

    file_endings = (".tif", ".tiff")

    def __init__(self, *args, window_title="Plot GeoTIFF FIle", **kwargs):

        super().__init__(*args, **kwargs)

        # hide ID inputs... not supported for GeoTIFF
        self.tID.hide()
        self.ID.hide()
        self.default_sel_args = dict(band=1)

    def do_open_file(self, file_path):
        f = self._file_handle

        coords = list(f.coords)
        variables = list(f.variables)

        crs = f.rio.crs
        if crs is not None:
            self.crs.setText(crs.to_string())
        self.parameter.setText(next((i for i in variables if i not in coords)))

        self.x.setText("x")
        self.y.setText("y")

        # set default layer-name to current layer if a single layer is selected,
        # else use the filename
        use_layer = self.m.BM.bg_layer
        if "|" in use_layer:
            use_layer = self.file_path.stem
        else:
            use_layer = use_layer.split("{")[0].strip()

        self.layer.setPlaceholderText(use_layer)

        # set values for autocompletion
        cols = sorted(set(variables + coords))
        self.x.set_complete_vals(cols)
        self.y.set_complete_vals(cols)
        self.parameter.set_complete_vals(cols)

        sel_layout = self.get_sel_layout(f)
        self.layout.addLayout(sel_layout)

        # update info text
        self.update_info_text()


class PlotNetCDFWidget(PlotXarrayWidget):

    file_endings = (".nc",)

    def __init__(self, *args, **kwargs):

        super().__init__(*args, window_title="Plot NetCDF FIle", **kwargs)

        # hide ID inputs... not (yet) supported for NetCDF
        self.tID.hide()
        self.ID.hide()

    def do_open_file(self, file_path):
        f = self._file_handle

        coords = list(f.coords)
        variables = list(f.variables)

        if len(coords) >= 2:
            self.x.setText(coords[0])
            self.y.setText(coords[1])

        # set values for autocompletion
        cols = sorted(set(variables + coords))
        self.x.set_complete_vals(cols)
        self.y.set_complete_vals(cols)

        self.x.setText("?")
        self.y.setText("?")

        # check if coordinate variable-names can be identified
        cols_lower = [i.casefold() for i in cols]
        for c0, c1 in [
            ("x", "y"),
            ("lon", "lat"),
            ("longitude", "latitude"),
        ]:
            if (c0.casefold() in cols_lower) and (c1.casefold() in cols_lower):
                col0 = cols[cols_lower.index(c0)]
                col1 = cols[cols_lower.index(c1)]

                self.x.setText(col0)
                self.y.setText(col1)
                break

        self.parameter.set_complete_vals(cols)
        self.parameter.setText(
            next((i for i in variables if (i != self.x.text() and i != self.y.text())))
        )

        sel_layout = self.get_sel_layout(f)
        self.layout.addLayout(sel_layout)

        # set default layer-name to current layer if a single layer is selected,
        # else use the filename
        use_layer = self.m.BM.bg_layer
        if "|" in use_layer:
            use_layer = self.file_path.stem
        else:
            use_layer = use_layer.split("{")[0].strip()

        self.layer.setPlaceholderText(use_layer)

        # update info text
        self.update_info_text()


class PlotCSVWidget(PlotFileWidget):

    default_shape = "ellipses"
    file_endings = ".csv"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, window_title="Plot CSV FIle", **kwargs)

    def get_crs(self):
        return get_crs(self.crs.text())

    def _open_filehandle(self, file_path):
        import pandas as pd

        self._data = pd.read_csv(file_path)

    def _close_filehandle(self):
        del self._data
        pass

    def do_open_file(self, file_path):
        df = self._data

        if len(df) > 50000:
            # use "shade_points" as default shape if more than 50000 columns are found
            self.shape_selector.set_shape("shade_points")

        cols = df.columns

        # set values for autocompletion
        self.x.set_complete_vals(cols)
        self.y.set_complete_vals(cols)
        self.parameter.set_complete_vals(cols)
        self.ID.set_complete_vals(cols)

        if len(cols) == 3:

            if "lon" in cols:
                self.x.setText("lon")
            elif "x" in cols:
                self.x.setText("x")
            else:
                self.x.setText(cols[0])

            if "lat" in cols:
                self.y.setText("lat")
            elif "y" in cols:
                self.y.setText("x")
            else:
                self.y.setText(cols[1])

            self.parameter.setText(cols[2])

            # if there are only 3 columns there is no column left to use as ID!
            self.ID.setText("")
            self.ID.setPlaceholderText("index")
            self.ID.setEnabled(False)
            # self.ID.hide()
            # self.tID.hide()

        if len(cols) > 3:
            self.ID.setText("")
            self.ID.setPlaceholderText("index")
            self.ID.setEnabled(True)

            if "lon" in cols:
                self.x.setText("lon")
            elif "x" in cols:
                self.x.setText("x")
            else:
                self.x.setText(cols[1])

            if "lat" in cols:
                self.y.setText("lat")
            elif "y" in cols:
                self.y.setText("y")
            else:
                self.y.setText(cols[2])

            self.parameter.setText(cols[3])

        # set default layer-name to current layer if a single layer is selected,
        # else use the filename
        use_layer = self.m.BM.bg_layer
        if "|" in use_layer:
            use_layer = self.file_path.stem
        else:
            use_layer = use_layer.split("{")[0].strip()

        self.layer.setPlaceholderText(use_layer)

    def get_info_text(self):
        import pandas as pd

        cols = dict()

        ID = self.ID.text()
        if self.ID.isVisibleTo(self) and len(ID) > 0 and ID != "index":
            cols["ID"] = ID
            show_index = False
        else:
            show_index = True

        cols["x"] = self.x.text()
        cols["y"] = self.y.text()
        cols["parameter"] = self.parameter.text()

        try:
            usecols = list(cols.keys())
            usevals = list(cols.values())

            df = self._data[usevals]
            init_cols = df.columns
            df.columns = [f"{usecols[i]}: {val}" for i, val in enumerate(usevals)]
            info = df.to_html(index=show_index, max_rows=100, max_cols=10)
            df.columns = init_cols
            return info
        except:
            try:
                return self._data._repr_html_()
            except Exception:
                return self._data.__repr__()

    def do_plot_file(self):
        if self.file_path is None:
            return

        ID = self.ID.text()
        if self.ID.isVisibleTo(self) and len(ID) > 0 and ID != "index":
            read_kwargs = dict(index_col=ID)
        else:
            read_kwargs = dict()

        m2 = self.m.new_layer_from_file.CSV(
            self.file_path,
            shape=self.shape_selector.shape_args,
            coastline=False,
            layer=self.get_layer(),
            parameter=self.parameter.text(),
            x=self.x.text(),
            y=self.y.text(),
            data_crs=self.get_crs(),
            cmap=self.cmaps.currentText(),
            vmin=to_float_none(self.vmin.text()),
            vmax=to_float_none(self.vmax.text()),
            read_kwargs=read_kwargs,
        )

        if self.cb_colorbar.isChecked():
            m2.add_colorbar()

        m2.show_layer(m2.layer)

        self.m2 = m2

    def do_update_vals(self):
        try:
            df = self._data

            vmin = df[self.parameter.text()].min()
            vmax = df[self.parameter.text()].max()

            self.vmin.setText(str(float(vmin)))
            self.vmax.setText(str(float(vmax)))

        except Exception:
            import traceback

            show_error_popup(
                text="There was an error while trying to update the values.",
                title="Unable to update values.",
                details=traceback.format_exc(),
            )


class PlotGeoDataFrameWidget(QtWidgets.QWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.file_endings = _get_gdf_file_endings()

        self.m = m

        self.file_path = None

        self.plot_props = dict()

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self.file_info = QtWidgets.QLabel()
        self.file_info.setWordWrap(True)
        # self.file_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.file_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll.setWidget(self.file_info)

        b_plot = QtWidgets.QPushButton("Plot")
        b_plot.clicked.connect(self.plot_file)

        # color
        self.colorselector = GetColorWidget()
        self.colorselector.cb_colorselected = self.update_on_color_selection

        # alpha of facecolor
        self.alphaslider = AlphaSlider(Qt.Horizontal)
        self.alphaslider.set_alpha_stylesheet()
        self.alphaslider.valueChanged.connect(
            lambda i: self.colorselector.set_alpha(i / 100)
        )
        self.alphaslider.valueChanged.connect(self.update_props)

        # linewidth
        self.linewidthslider = AlphaSlider(Qt.Horizontal)
        self.linewidthslider.set_linewidth_stylesheet()

        self.linewidthslider.valueChanged.connect(
            lambda i: self.colorselector.set_linewidth(i / 10)
        )
        self.linewidthslider.valueChanged.connect(self.update_props)

        # zorder
        self.zorder = ZorderInput("10")
        validator = QtGui.QIntValidator()
        self.zorder.setValidator(validator)
        self.zorder.setMaximumWidth(30)
        self.zorder.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        self.zorder.textChanged.connect(self.update_props)

        zorder_label = QtWidgets.QLabel("zorder: ")
        zorder_label.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )

        zorder_layout = QtWidgets.QHBoxLayout()
        zorder_layout.addWidget(zorder_label)
        zorder_layout.addWidget(self.zorder)
        zorder_layout.setAlignment(Qt.AlignRight | Qt.AlignCenter)

        # layer
        layerlabel = QtWidgets.QLabel("Layer:")
        self.layer = LayerInput()

        setlayername = QtWidgets.QWidget()
        layername = QtWidgets.QHBoxLayout()
        layername.addWidget(layerlabel)
        layername.addWidget(self.layer)
        layername.addLayout(zorder_layout)
        setlayername.setLayout(layername)

        self.alphaslider.setValue(50)
        self.linewidthslider.setValue(10)

        # -----------------------

        props = QtWidgets.QGridLayout()
        props.addWidget(self.colorselector, 0, 0, 2, 1)
        props.addWidget(self.alphaslider, 0, 1)
        props.addWidget(self.linewidthslider, 1, 1)
        # props.addLayout(zorder_layout, 0, 2)
        # set stretch factor to expand the color-selector first
        props.setColumnStretch(0, 1)
        props.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        options = QtWidgets.QVBoxLayout()
        options.addLayout(props)
        options.addWidget(setlayername)
        options.addWidget(b_plot, 0, Qt.AlignRight)
        options.setAlignment(Qt.AlignLeft | Qt.AlignTop)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(scroll)
        layout.addLayout(options)

        self.setLayout(layout)

    def plot_file(self):
        if self.file_path is None:
            return

        layer = self.layer.text()
        if layer == "":
            layer = self.layer.placeholderText()

        self.m.add_gdf(
            self.file_path,
            **self.plot_props,
            layer=layer,
        )
        self.window().close()

    def do_open_file(self, file_path=None):
        try:
            import geopandas as gpd
        except ImportError:
            _log.error(
                "EOmaps: missing required dependency 'geopandas' to open the file."
            )
            return
        self.file_path = file_path
        self.gdf = gpd.read_file(self.file_path)

        self.file_info.setText(self.gdf.__repr__())

        # set default layer-name to current layer if a single layer is selected,
        # else use the filename
        use_layer = self.m.BM.bg_layer
        if "|" in use_layer:
            use_layer = self.file_path.stem
        else:
            use_layer = use_layer.split("{")[0].strip()

        self.layer.setPlaceholderText(use_layer)

    def open_file(self, file_path=None):
        if self.file_endings is not None:
            if file_path.suffix.lower() not in self.file_endings:
                self.file_info.setText(
                    f"the file {self.file_path.name} is not a valid file"
                )
                self.file_path = None
                return

        self.do_open_file(file_path)

        self.update_props()
        self.layer.set_complete_vals(
            [file_path.name]
            + [i for i in self.m._get_layers() if not i.startswith("_")]
        )

        self.newwindow = NewWindow(m=self.m, title="Plot ShapeFile")
        self.newwindow.statusBar().showMessage(str(self.file_path))

        self.newwindow.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )

        self.newwindow.layout.addWidget(self)
        # self.window.resize(800, 500)
        self.newwindow.show()

    def update_on_color_selection(self):
        self.update_alphaslider()
        self.update_props()

    def update_alphaslider(self):
        # to always round up to closest int use -(-x//1)
        self.alphaslider.setValue(int(-(-self.colorselector.alpha * 100 // 1)))

    def update_props(self):
        if self.zorder.text():
            zorder = int(self.zorder.text())

        self.plot_props.update(
            dict(
                facecolor=self.colorselector.facecolor.getRgbF(),
                edgecolor=self.colorselector.edgecolor.getRgbF(),
                linewidth=self.linewidthslider.alpha * 5,
                zorder=zorder,
                # alpha = self.alphaslider.alpha,   # don't specify alpha! it interferes with the alpha of the colors!
            )
        )


class OpenDataStartTab(QtWidgets.QWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m

        icon = iconpath / "open.png"
        self.b_str = (
            f"<img src={icon} height=20 "
            "style='display: inline; vertical-align:bottom;'>"
            "</img>"
        )
        self.t1 = QtWidgets.QLabel()
        # self.t1.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
        self.t1.setText(
            f"<h3>Click on {self.b_str} or DRAG & DROP to plot data from files!</h3>"
            "<p>"
            "Supported filetypes:"
            "<ul>"
            "<li>NetCDF: <code>[.nc]<code></li>"
            "<li>GeoTIFF: <code>[.tif, .tiff]<code></li>"
            "<li>CSV: <code>[.csv]<code></li>"
            "<li>Shapefile: <code>[.shp]<code></li>"
            "</ul>"
        )

        layout = QtWidgets.QVBoxLayout()
        layout.addSpacing(10)
        layout.addWidget(self.t1)

        layout.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        self.setLayout(layout)

        self.setAcceptDrops(True)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Plot Data from Files</h3>"
                f"Click on {self.b_str} or simply drag-and-drop one of the "
                "supported filetypes to get a popup window where you can specify how "
                "you want to visualize the data."
                "<p>"
                "Supported filetypes:"
                "<ul>"
                "<li>NetCDF: <code>[.nc]<code></li>"
                "<li>GeoTIFF: <code>[.tif, .tiff]<code></li>"
                "<li>CSV: <code>[.csv]<code></li>"
                "<li>Shapefile: <code>[.shp]<code></li>"
                "</ul>"
                "<b>NOTE:</b> This capability is primarily intended as an easy way to "
                "get a <i>quick-look</i> at some data for comparison. It does not "
                "provide access to all plotting features of EOmaps!"
                "<p>"
                "Some additional notes:"
                "<ul>"
                "<li>Make sure that the projection of the data-coordinates "
                "has been identified correctly prior to plotting!</li>"
                "<li>Be aware that re-projecting large datasets might take quite some "
                "time and can require a lot of memory!</li>"
                "</ul>",
            )


class OpenFileTabs(QtWidgets.QTabWidget):
    openNewFile = Signal()

    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m
        self.openNewFile.connect(
            lambda *args, **kwargs: self.new_file_tab(file_path=None)
        )

        self.gdf_file_endings = _get_gdf_file_endings()

        self.starttab = OpenDataStartTab(m=self.m)

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_handler)

        self.addTab(self.starttab, "NEW")
        # don't show the close button for this tab
        self.tabBar().setTabButton(self.count() - 1, self.tabBar().RightSide, None)

        self.setStyleSheet(
            """
            QTabWidget::pane {
              border: 0px;
              top:0px;
              background: rgb(200, 200, 200);
              border-radius: 10px;
            }

            QTabBar::tab {
              background: rgb(220, 220, 220);
              border: 0px;
              padding: 3px;
              padding-bottom: 6px;
              margin-left: 10px;
              margin-bottom: -2px;
              border-radius: 4px;
            }

            QTabBar::tab:selected {
              background: rgb(200, 200, 200);
              border: 0px;
              margin-bottom: -2px;
            }
            """
        )

    def close_handler(self, index):
        widget = self.widget(index)

        path = widget.file_path

        self._msg = QtWidgets.QMessageBox(self)
        self._msg.setIcon(QtWidgets.QMessageBox.Question)
        self._msg.setText(
            f"Do you really want to REMOVE the dataset \n\n '{path}' \n\n"
            "from the map?"
        )
        self._msg.setWindowTitle("Remove dataset?")

        self._msg.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        self._msg.buttonClicked.connect(lambda: self.do_close_tab(index))

        self._msg.show()

    def do_close_tab(self, index):
        # TODO create a proper method to completely clear a Maps-object from a map
        if self._msg.standardButton(self._msg.clickedButton()) != self._msg.Yes:
            return

        widget = self.widget(index)
        try:
            if widget.m2.coll in self.m.BM._bg_artists[widget.m2.layer]:
                self.m.BM.remove_bg_artist(widget.m2.coll, layer=widget.m2.layer)
                widget.m2.coll.remove()
        except Exception:
            _log.error("EOmaps_companion: unable to remove dataset artist.")

        widget.m2.cleanup()

        # redraw if the layer was currently visible
        if widget.m2.layer in self.m.BM.bg_layer:
            self.m.redraw(widget.m2.layer)

        del widget.m2

        self.removeTab(index)

        # emit a "dataPlotted" signal to update dropdowns etc.
        self.m._emit_signal("dataPlotted")

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()

            if len(urls) > 1:
                self.window().statusBar().showMessage(
                    "Dropping more than 1 file is not supported!"
                )
                e.accept()  # if we ignore the event, dragLeaveEvent is also ignored!
            else:
                self.window().statusBar().showMessage("DROP IT!")
                e.accept()
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self.window().statusBar().clearMessage()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if len(urls) > 1:
            return

        self.new_file_tab(urls[0].toLocalFile())

    def new_file_tab(self, file_path=None):
        if file_path is None:
            file_path = Path(
                QtWidgets.QFileDialog.getOpenFileName(
                    filter=(
                        "Supported Files (*.nc *.tif *tiff *.csv *.shp);;" "all (*)"
                    )
                )[0]
            )
            # in case no file is selected, don't raise an error!
            if len(file_path.name) == 0:
                return
        elif isinstance(file_path, str):
            file_path = Path(file_path)

        global plc
        ending = file_path.suffix.lower()
        if ending in [".nc"]:
            plc = PlotNetCDFWidget(m=self.m, tab=self)
        elif ending in [".csv"]:
            plc = PlotCSVWidget(m=self.m, tab=self)
        elif ending in [".tif", ".tiff"]:
            plc = PlotGeoTIFFWidget(m=self.m, tab=self)
        elif ending in self.gdf_file_endings:
            plc = PlotGeoDataFrameWidget(m=self.m)
        else:
            _log.error(f"EOmaps: Unknown file extension '{ending}'")
            self.window().statusBar().showMessage(
                f"ERROR: Unknown file extension {ending}", 5000
            )
            show_error_popup(
                text=f"Unknown file extension {ending}.",
                title="Unknown file extension.",
                details=(
                    "Supported file extensions: "
                    f"{['.tiff', '.netcdf', *self.gdf_file_endings]}"
                ),
            )

            return

        self.window().statusBar().clearMessage()

        try:
            plc.open_file(file_path)
        except Exception:
            import traceback

            _log.error(f"EOmaps Error: Unable to open file {file_path}")
            self.window().statusBar().showMessage(
                "ERROR: File could not be opened...", 5000
            )

            show_error_popup(
                text="There was an error while trying to open the file.",
                title="Unable to open file.",
                details=traceback.format_exc(),
            )

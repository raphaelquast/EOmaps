from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QLocale
from pathlib import Path
import io

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

from ..base import NewWindow


def _none_or_val(val):
    if val == "None":
        return None
    else:
        return val


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


class ShapeSelector(QtWidgets.QFrame):
    _ignoreargs = ["shade_hook", "agg_hook"]

    # special treatment of arguments
    _argspecials = dict(
        aggregator=_none_or_val,
        mask_radius=_none_or_val,
        radius=_identify_radius,
        n=_none_or_val,
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

    def __init__(self, *args, m=None, default_shape="shade_raster", **kwargs):
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

        print(f"WARNING value-conversion for {key} = {val} did not succeed!")
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
    default_shape = "shade_raster"

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

        Parameters
        ----------
        *args : TYPE
            DESCRIPTION.
        m : TYPE, optional
            DESCRIPTION. The default is None.
        **kwargs : TYPE
            DESCRIPTION.

        Returns
        -------
        None.

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
        self.cb_colorbar = QtWidgets.QCheckBox("Add colorbar")

        # layer
        self.layer_label = QtWidgets.QLabel("<b>Layer:</b>")
        self.layer = LineEditComplete()
        self.layer.setPlaceholderText(str(self.m.BM.bg_layer))

        setlayername = QtWidgets.QWidget()
        layername = QtWidgets.QHBoxLayout()
        layername.addWidget(self.layer_label)
        layername.addWidget(self.layer)
        setlayername.setLayout(layername)

        # shape selector (with shape options)
        self.shape_selector = ShapeSelector(m=self.m, default_shape=self.default_shape)
        self.setStyleSheet("ShapeSelector{border:1px dashed;}")

        # colormaps
        self.cmaps = CmapDropdown()

        validator = QtGui.QDoubleValidator()
        # make sure the validator uses . as separator
        validator.setLocale(QLocale("en_US"))

        # vmin / vmax
        vminlabel, vmaxlabel = QtWidgets.QLabel("vmin="), QtWidgets.QLabel("vmax=")
        self.vmin, self.vmax = QtWidgets.QLineEdit(), QtWidgets.QLineEdit()
        self.vmin.setValidator(validator)
        self.vmax.setValidator(validator)

        self.minmaxupdate = QtWidgets.QPushButton("🗘")
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

        self.x = LineEditComplete("x")
        self.y = LineEditComplete("y")
        self.parameter = LineEditComplete("param")
        self.ID = LineEditComplete("ID")
        self.crs = InputCRS()

        tx = QtWidgets.QLabel("x:")
        ty = QtWidgets.QLabel("y:")
        tparam = QtWidgets.QLabel("parameter:")
        tcrs = QtWidgets.QLabel("crs:")
        self.tID = QtWidgets.QLabel("ID:")

        plotargs = QtWidgets.QHBoxLayout()
        plotargs.addWidget(tx)
        plotargs.addWidget(self.x)
        plotargs.addWidget(ty)
        plotargs.addWidget(self.y)
        plotargs.addWidget(tparam)
        plotargs.addWidget(self.parameter)
        plotargs.addWidget(tcrs)
        plotargs.addWidget(self.crs)
        plotargs.addWidget(self.tID)
        plotargs.addWidget(self.ID)

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

    def get_layer(self):
        layer = self.layer.text()
        if layer == "":
            layer = self.layer.placeholderText()

        return layer

    def open_file(self, file_path=None):
        info = self.do_open_file(file_path)

        if self.file_endings is not None:
            if file_path.suffix.lower() not in self.file_endings:
                self.file_info.setText(
                    f"the file {self.file_path.name} is not a valid file"
                )
                self.file_path = None
                return

        if file_path is not None:
            self.file_path = file_path

        if info is not None:
            self.file_info.setText(info)

        self.layer.set_complete_vals(
            [file_path.name]
            + [i for i in self.m._get_layers() if not i.startswith("_")]
        )

        self.newwindow = NewWindow(m=self.m, title=self.window_title)
        self.newwindow.statusBar().showMessage(str(self.file_path))

        self.newwindow.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )

        self.newwindow.layout.addWidget(self)
        self.newwindow.resize(800, 500)
        self.newwindow.show()

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

        if self.close_on_plot:
            self.newwindow.close()

        if self.attach_tab_after_plot:
            self.attach_as_tab()

    def do_open_file(self):
        file_path = Path(QtWidgets.QFileDialog.getOpenFileName()[0])

        return (
            file_path,
            f"The file {file_path.stem} has\n {file_path.stat().st_size} bytes.",
        )

    def do_plot_file(self):
        self.file_info.setText("Implement `.do_plot_file()` to plot the data!")

    def do_update_vals(self):
        return

    def attach_as_tab(self):
        if self.tab is None:
            return

        if self.file_path is not None:
            name = self.file_path.stem
        else:
            return

        if len(name) > 10:
            name = name[:7] + "..."
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


class PlotGeoTIFFWidget(PlotFileWidget):

    file_endings = (".tif", ".tiff")

    def __init__(self, *args, window_title="Plot GeoTIFF FIle", **kwargs):

        super().__init__(*args, **kwargs)

        # hide ID inputs... not supported for GeoTIFF
        self.tID.hide()
        self.ID.hide()

    def get_crs(self):
        return get_crs(self.crs.text())

    def do_open_file(self, file_path):
        import xarray as xar

        with xar.open_dataset(file_path, mask_and_scale=False) as f:
            import io

            info = io.StringIO()
            f.info(info)

            coords = list(f.coords)
            variables = list(f.variables)

            crs = f.rio.crs
            if crs is not None:
                self.crs.setText(crs.to_string())
            self.parameter.setText(next((i for i in variables if i not in coords)))

        self.x.setText("x")
        self.y.setText("y")

        # set layer-name to filename by default
        self.layer.setPlaceholderText(file_path.stem)

        # set values for autocompletion
        cols = sorted(set(variables + coords))
        self.x.set_complete_vals(cols)
        self.y.set_complete_vals(cols)
        self.parameter.set_complete_vals(cols)

        return info.getvalue()

    def do_plot_file(self):
        if self.file_path is None:
            return

        m2 = self.m.new_layer_from_file.GeoTIFF(
            self.file_path,
            shape=self.shape_selector.shape_args,
            coastline=False,
            layer=self.get_layer(),
            cmap=self.cmaps.currentText(),
            vmin=to_float_none(self.vmin.text()),
            vmax=to_float_none(self.vmax.text()),
            data_crs=self.get_crs(),
        )

        if self.cb_colorbar.isChecked():
            m2.add_colorbar()

        m2.show_layer(m2.layer)

        self.m2 = m2

    def do_update_vals(self):
        import xarray as xar

        try:
            with xar.open_dataset(self.file_path) as f:
                vmin = f[self.parameter.text()].min()
                vmax = f[self.parameter.text()].max()

                self.vmin.setText(str(float(vmin)))
                self.vmax.setText(str(float(vmax)))

        except Exception:
            import traceback

            show_error_popup(
                text="There was an error while trying to update the values.",
                title="Unable to update values.",
                details=traceback.format_exc(),
            )


class PlotNetCDFWidget(PlotFileWidget):

    file_endings = ".nc"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, window_title="Plot NetCDF FIle", **kwargs)

        # hide ID inputs... not (yet) supported for NetCDF
        self.tID.hide()
        self.ID.hide()

        l = QtWidgets.QHBoxLayout()

        self.sel_title = QtWidgets.QLabel("<b>Select index-labels to plot:</b>")

        l.addWidget(self.sel_title)

        withtitle = QtWidgets.QWidget()
        withtitlelayout = QtWidgets.QVBoxLayout()
        withtitlelayout.addLayout(l)
        withtitle.setLayout(withtitlelayout)

        withtitle.setMaximumHeight(60)

        self.layout.addWidget(withtitle)

    def _deactivate_sel_factory(self, d):
        def cb():
            selected_dims = [self.x.text(), self.y.text()]
            if d in selected_dims:
                self.sel_inputs[d]["label"].hide()
                self.sel_inputs[d]["inp"].hide()

            else:
                self.sel_inputs[d]["label"].show()
                self.sel_inputs[d]["inp"].show()

            if any(i["inp"].isVisible() for i in self.sel_inputs.values()):
                self.sel_title.show()
            else:
                self.sel_title.hide()

        return cb

    def get_sel_layout(self, f):

        layout = QtWidgets.QHBoxLayout()
        dims = list(f.dims)

        self.sel_inputs = dict()
        # get completion values
        for d in dims:
            vals = f[d].values.astype(str)

            label = QtWidgets.QLabel(f"{d}:")
            inp = LineEditComplete()
            inp.set_complete_vals(vals)

            layout.addWidget(label)
            layout.addWidget(inp)

            self.sel_inputs[d] = dict(inp=inp, label=label, dtype=f[d].dtype)

            deactivate_func = self._deactivate_sel_factory(d)
            deactivate_func()

            self.x.textEdited.connect(deactivate_func)
            self.x.completer().activated.connect(deactivate_func)
            self.y.textEdited.connect(deactivate_func)
            self.y.completer().activated.connect(deactivate_func)

        return layout

    def get_sel_args(self):

        s = dict()

        for key, val in self.sel_inputs.items():
            sel = val["inp"].text()
            if val["inp"].isVisible() and sel != "":
                # convert to the correct dtype
                import numpy as np

                sel = np.array(sel).astype(val["dtype"])

                s[key] = sel
        return s

    def get_crs(self):
        return get_crs(self.crs.text())

    def do_open_file(self, file_path):
        import xarray as xar

        with xar.open_dataset(file_path, mask_and_scale=False) as f:

            info = io.StringIO()
            f.info(info)

            coords = list(f.coords)
            variables = list(f.variables)

            if len(coords) >= 2:
                self.x.setText(coords[0])
                self.y.setText(coords[1])

            # set values for autocompletion
            cols = sorted(set(variables + coords))
            self.x.set_complete_vals(cols)
            self.y.set_complete_vals(cols)

            if "lon" in cols:
                self.x.setText("lon")
            elif "x" in cols:
                self.x.setText("x")
            else:
                self.x.setText(cols[0])

            if "lat" in cols:
                self.y.setText("lat")
            elif "y" in cols:
                self.y.setText("y")
            else:
                self.x.setText(cols[1])

            self.parameter.set_complete_vals(cols)
            self.parameter.setText(
                next(
                    (
                        i
                        for i in variables
                        if (i != self.x.text() and i != self.y.text())
                    )
                )
            )

            sel_layout = self.get_sel_layout(f)
            self.layout.addLayout(sel_layout)

        # set layer-name to filename by default
        self.layer.setPlaceholderText(file_path.stem)

        return info.getvalue()

    def do_update_vals(self):
        import xarray as xar

        try:
            with xar.open_dataset(self.file_path) as f:
                vmin = f[self.parameter.text()].min()
                vmax = f[self.parameter.text()].max()

                self.vmin.setText(str(float(vmin)))
                self.vmax.setText(str(float(vmax)))

        except Exception:
            import traceback

            show_error_popup(
                text="There was an error while trying to update the values.",
                title="Unable to update values.",
                details=traceback.format_exc(),
            )

    def do_plot_file(self):
        if self.file_path is None:
            return

        import xarray as xar

        with xar.open_dataset(self.file_path) as f:
            selargs = self.get_sel_args()
            usef = f.sel(**self.get_sel_args())
            if len(selargs) > 0:
                self.file_info.setText(usef.__repr__())

            m2 = self.m.new_layer_from_file.NetCDF(
                usef,
                shape=self.shape_selector.shape_args,
                coastline=False,
                layer=self.get_layer(),
                coords=(self.x.text(), self.y.text()),
                parameter=self.parameter.text(),
                data_crs=self.get_crs(),
                # sel=self.get_sel_args(),
                cmap=self.cmaps.currentText(),
                vmin=to_float_none(self.vmin.text()),
                vmax=to_float_none(self.vmax.text()),
            )

        if self.cb_colorbar.isChecked():
            m2.add_colorbar()

        m2.show_layer(m2.layer)

        self.m2 = m2


class PlotCSVWidget(PlotFileWidget):

    default_shape = "ellipses"
    file_endings = ".csv"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, window_title="Plot CSV FIle", **kwargs)

    def get_crs(self):
        return get_crs(self.crs.text())

    def do_open_file(self, file_path):
        import pandas as pd

        df = pd.read_csv(file_path)

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
            else:
                self.x.setText(cols[0])

            if "lat" in cols:
                self.y.setText("lat")
            else:
                self.x.setText(cols[1])

            self.parameter.setText(cols[2])

            # if there are only 3 columns there is no column left to use as ID!
            self.ID.hide()
            self.tID.hide()

        if len(cols) > 3:

            self.ID.setText(cols[0])

            if "lon" in cols:
                self.x.setText("lon")
            else:
                self.x.setText(cols[1])

            if "lat" in cols:
                self.y.setText("lat")
            else:
                self.x.setText(cols[2])

            self.parameter.setText(cols[3])

        # set layer-name to filename by default
        self.layer.setPlaceholderText(file_path.stem)

        return df.__repr__()

    def do_plot_file(self):
        if self.file_path is None:
            return

        ID = self.ID.text()
        if self.ID.isVisible() and ID != "":
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
            import pandas as pd

            df = pd.read_csv(self.file_path)

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


class PlotShapeFileWidget(QtWidgets.QWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m
        self.file_endings = [".shp"]

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
        self.alphaslider.valueChanged.connect(
            lambda i: self.colorselector.set_alpha(i / 100)
        )
        self.alphaslider.valueChanged.connect(self.update_props)

        # linewidth
        self.linewidthslider = AlphaSlider(Qt.Horizontal)
        self.linewidthslider.valueChanged.connect(
            lambda i: self.colorselector.set_linewidth(i / 10)
        )
        self.linewidthslider.valueChanged.connect(self.update_props)

        # zorder
        self.zorder = QtWidgets.QLineEdit("10")
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
        self.layer = LineEditComplete()
        self.layer.setPlaceholderText(str(self.m.BM.bg_layer))

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
        self.file_path = file_path

        import geopandas as gpd

        self.gdf = gpd.read_file(self.file_path)

        self.file_info.setText(self.gdf.__repr__())

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

        self.t1 = QtWidgets.QLabel()
        # self.t1.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
        self.t1.setText(
            "<h3>Open or DRAG & DROP files!</h3>"
            "<p>"
            "Supported filetypes:"
            "<ul>"
            "<li>NetCDF: <code>[.nc]<code></li>"
            "<li>GeoTIFF: <code>[.tif, .tiff]<code></li>"
            "<li>CSV: <code>[.csv]<code></li>"
            "<li>Shapefile: <code>[.shp]<code></li>"
            "</ul>"
        )

        self.open_button = QtWidgets.QPushButton("Open File")

        layout = QtWidgets.QVBoxLayout()
        layout.addSpacing(10)
        layout.addWidget(self.t1)
        layout.addSpacing(10)
        layout.addWidget(self.open_button)

        layout.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        self.setLayout(layout)

        self.setAcceptDrops(True)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Plot Data from Files</h3>"
                "Click on the 'Open File' button or simply drag-and-drop one of the "
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
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m

        self.starttab = OpenDataStartTab(m=self.m)
        self.starttab.open_button.clicked.connect(
            lambda: self.new_file_tab(file_path=None)
        )

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_handler)

        self.addTab(self.starttab, "NEW")
        # don't show the close button for this tab
        self.tabBar().setTabButton(self.count() - 1, self.tabBar().RightSide, None)

    def close_handler(self, index):
        widget = self.widget(index)

        path = widget.file_path

        self._msg = QtWidgets.QMessageBox(self)
        self._msg.setIcon(QtWidgets.QMessageBox.Question)
        self._msg.setText(f"Do you really want to close the dataset \n\n '{path}'?")
        self._msg.setWindowTitle("Close dataset?")

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
            print("EOmaps_companion: unable to remove dataset artist.")

        widget.m2.cleanup()

        # make sure all temporary pick-artists have been cleared
        widget.m2.BM._clear_temp_artists("pick")
        # redraw if the layer was currently visible
        self.m.redraw(widget.m2.layer)

        del widget.m2

        self.removeTab(index)

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
        elif ending in [".shp"]:
            plc = PlotShapeFileWidget(m=self.m)
        else:
            self.window().statusBar().showMessage(
                f"Unknown file extension {ending}", 5000
            )
            return

        self.window().statusBar().clearMessage()

        try:
            plc.open_file(file_path)
        except Exception:
            self.window().statusBar().showMessage("File could not be opened...", 5000)
            import traceback

            show_error_popup(
                text="There was an error while trying to open the file.",
                title="Unable to open file.",
                details=traceback.format_exc(),
            )

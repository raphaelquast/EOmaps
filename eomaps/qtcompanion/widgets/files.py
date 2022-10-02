from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QLocale
from pathlib import Path

from .utils import (
    LineEditComplete,
    InputCRS,
    CmapDropdown,
    show_error_popup,
    to_float_none,
    get_crs,
    str_to_bool,
)

from ..base import NewWindow


class ShapeSelector(QtWidgets.QWidget):
    _ignoreargs = ["shade_hook", "agg_hook"]

    _argspecials = dict(aggregator={"None": None}, mask_radius={"None": None})

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

    def argparser(self, key, val):
        special = self._argspecials.get(key, None)
        if special and val in special:
            return special[val]

        convtype = self._argtypes.get(key, (str,))

        for t in convtype:
            try:
                convval = t(val)
            except ValueError:
                continue

            return convval

        print(r"WARNING value-conversion for {key} = {val} did not succeed!")
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
        parent=None,
        close_on_plot=True,
        attach_tab_after_plot=True,
        tab=None,
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

        self.parent = parent
        self.tab = tab
        self.attach_tab_after_plot = attach_tab_after_plot
        self.close_on_plot = close_on_plot

        self.m2 = None
        self.cid_annotate = None

        self.file_path = None

        self.b_plot = QtWidgets.QPushButton("Plot!", self)
        self.b_plot.clicked.connect(self.b_plot_file)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        self.file_info = QtWidgets.QLabel()
        self.file_info.setWordWrap(True)
        # self.file_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.file_info.setTextInteractionFlags(Qt.TextSelectableByMouse)
        scroll.setWidget(self.file_info)

        self.cb1 = QtWidgets.QCheckBox("Annotate on click")
        self.cb1.stateChanged.connect(self.b_add_annotate_cb)

        self.cb2 = QtWidgets.QCheckBox("Add colorbar")
        self.cb2.stateChanged.connect(self.b_add_colorbar)

        self.blayer = QtWidgets.QCheckBox()
        self._blayer_text = ""
        self.blayer.stateChanged.connect(self.b_layer_checkbox)
        self.t1_label = QtWidgets.QLabel("Layer:")
        self.t1 = QtWidgets.QLineEdit()
        self.t1.setPlaceholderText(str(self.m.BM.bg_layer))

        self.shape_selector = ShapeSelector(m=self.m, default_shape=self.default_shape)

        self.setlayername = QtWidgets.QWidget()
        layername = QtWidgets.QHBoxLayout()
        layername.addWidget(self.blayer)
        layername.addWidget(self.t1_label)
        layername.addWidget(self.t1)
        self.setlayername.setLayout(layername)

        self.cmaps = CmapDropdown()

        validator = QtGui.QDoubleValidator()
        # make sure the validator uses . as separator
        validator.setLocale(QLocale("en_US"))

        vminlabel = QtWidgets.QLabel("vmin=")
        self.vmin = QtWidgets.QLineEdit()
        self.vmin.setValidator(validator)
        vmaxlabel = QtWidgets.QLabel("vmax=")
        self.vmax = QtWidgets.QLineEdit()
        self.vmax.setValidator(validator)

        minmaxupdate = QtWidgets.QPushButton("🗘")
        minmaxupdate.clicked.connect(self.do_update_vals)

        minmaxlayout = QtWidgets.QHBoxLayout()
        minmaxlayout.setAlignment(Qt.AlignLeft)
        minmaxlayout.addWidget(vminlabel)
        minmaxlayout.addWidget(self.vmin)
        minmaxlayout.addWidget(vmaxlabel)
        minmaxlayout.addWidget(self.vmax)
        minmaxlayout.addWidget(minmaxupdate, Qt.AlignRight)

        options = QtWidgets.QVBoxLayout()
        options.addWidget(self.cb1)
        options.addWidget(self.cb2)
        options.addWidget(self.setlayername)
        options.addWidget(self.shape_selector)
        options.addWidget(self.cmaps)
        options.addLayout(minmaxlayout)

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

        self.crs = InputCRS()

        tx = QtWidgets.QLabel("x:")
        ty = QtWidgets.QLabel("y:")
        tparam = QtWidgets.QLabel("parameter:")
        tcrs = QtWidgets.QLabel("crs:")

        plotargs = QtWidgets.QHBoxLayout()
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

    @property
    def m(self):
        return self.parent.m

    def get_layer(self):
        layer = self.m.BM.bg_layer

        if self.blayer.isChecked():
            layer = self.t1.text()
            if len(layer) == 0 and self.file_path is not None:
                layer = self.file_path.stem
                self.t1.setText(layer)

        return layer

    def b_layer_checkbox(self):
        if self.blayer.isChecked():
            self.t1.setReadOnly(False)
            if len(self.t1.text()) == 0 and self.file_path is not None:
                layer = self.file_path.stem
                self.t1.setText(layer)
        else:
            self.t1.setReadOnly(True)
            self.t1.setText("")

    def b_add_colorbar(self):
        if self.m2 is None:
            return

        if self.cb2.isChecked():
            cb = self.m2.add_colorbar()
            cb[2].patch.set_color("none")
            cb[3].patch.set_color("none")
        else:
            try:
                self.m2._remove_colorbar()
            except:
                pass

    def b_add_annotate_cb(self):
        if self.m2 is None:
            return

        if self.cb1.isChecked():
            if self.cid_annotate is None:
                self.cid_annotate = self.m2.cb.pick.attach.annotate()
        else:
            if self.cid_annotate is not None:
                self.m2.cb.pick.remove(self.cid_annotate)
                self.cid_annotate = None

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
            if self.blayer.isChecked():
                self.t1.setText(file_path.stem)
            self.file_path = file_path

        if info is not None:
            self.file_info.setText(info)

        self.window = NewWindow(parent=self.parent)
        self.window.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )

        self.window.layout.addWidget(self)
        self.window.resize(800, 500)
        self.window.show()

    def b_plot_file(self):
        try:
            self.do_plot_file()
        except Exception:
            import traceback

            show_error_popup(
                text="There was an error while trying to plot the data!",
                title="Error",
                details=traceback.format_exc(),
            )
            return

        if self.close_on_plot:
            self.window.close()

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

        self.t1.setReadOnly(True)
        self.x.setReadOnly(True)
        self.y.setReadOnly(True)
        self.parameter.setReadOnly(True)
        self.crs.setReadOnly(True)
        self.vmin.setReadOnly(True)
        self.vmax.setReadOnly(True)

        self.cmaps.setEnabled(False)
        self.shape_selector.setEnabled(False)
        self.setlayername.setEnabled(False)
        self.b_plot.close()


class PlotGeoTIFFWidget(PlotFileWidget):

    file_endings = (".tif", ".tiff")

    def do_open_file(self, file_path):
        import xarray as xar

        with xar.open_dataset(file_path) as f:
            import io

            info = io.StringIO()
            f.info(info)

            coords = list(f.coords)
            variables = list(f.variables)

            self.crs.setText(f.rio.crs.to_string())
            self.parameter.setText(next((i for i in variables if i not in coords)))

        self.x.setText("x")
        self.y.setText("y")

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
        )

        m2.cb.pick.attach.annotate(modifier=1)

        m2.show_layer(m2.layer)

        self.m2 = m2
        # check if we want to add an annotation
        self.b_add_annotate_cb()

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

        super().__init__(*args, **kwargs)

        l = QtWidgets.QHBoxLayout()
        self.sel = QtWidgets.QLineEdit("")

        tsel = QtWidgets.QLabel("isel:")

        l.addWidget(tsel)
        l.addWidget(self.sel)

        withtitle = QtWidgets.QWidget()
        withtitlelayout = QtWidgets.QVBoxLayout()

        withtitlelayout.addLayout(l)

        withtitle.setLayout(withtitlelayout)
        withtitle.setMaximumHeight(60)

        self.layout.addWidget(withtitle)

    def get_crs(self):
        return get_crs(self.crs.text())

    def get_sel(self):
        import ast

        try:
            sel = self.sel.text()
            if len(sel) == 0:
                return

            return ast.literal_eval("{'date':1}")
        except Exception:
            import traceback

            show_error_popup(
                text=f"{sel} is not a valid selection",
                title="Invalid selection args",
                details=traceback.format_exc(),
            )

    def do_open_file(self, file_path):
        import xarray as xar

        with xar.open_dataset(file_path) as f:
            import io

            info = io.StringIO()
            f.info(info)

            coords = list(f.coords)
            variables = list(f.variables)
            if len(coords) >= 2:
                self.x.setText(coords[0])
                self.y.setText(coords[1])

            self.parameter.setText(next((i for i in variables if i not in coords)))

            # set values for autocompletion
            cols = sorted(set(variables + coords))
            self.x.set_complete_vals(cols)
            self.y.set_complete_vals(cols)

            if "lon" in cols:
                self.x.setText("lon")
            else:
                self.x.setText(cols[0])

            if "lat" in cols:
                self.y.setText("lat")
            else:
                self.x.setText(cols[1])

            self.parameter.set_complete_vals(cols)

        return info.getvalue()

    def do_update_vals(self):
        import xarray as xar

        try:
            with xar.open_dataset(self.file_path) as f:
                isel = self.get_sel()
                if isel is not None:
                    vmin = f.isel(**isel)[self.parameter.text()].min()
                    vmax = f.isel(**isel)[self.parameter.text()].max()
                else:
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

        m2 = self.m.new_layer_from_file.NetCDF(
            self.file_path,
            shape=self.shape_selector.shape_args,
            coastline=False,
            layer=self.get_layer(),
            coords=(self.x.text(), self.y.text()),
            parameter=self.parameter.text(),
            data_crs=self.get_crs(),
            isel=self.get_sel(),
            cmap=self.cmaps.currentText(),
            vmin=to_float_none(self.vmin.text()),
            vmax=to_float_none(self.vmax.text()),
        )

        m2.cb.pick.attach.annotate(modifier=1)

        m2.show_layer(m2.layer)

        self.m2 = m2
        # check if we want to add an annotation
        self.b_add_annotate_cb()


class PlotCSVWidget(PlotFileWidget):

    default_shape = "ellipses"
    file_endings = ".csv"

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

    def get_crs(self):
        return get_crs(self.crs.text())

    def do_open_file(self, file_path):
        import pandas as pd

        head = pd.read_csv(file_path, nrows=50)
        cols = head.columns

        # set values for autocompletion
        self.x.set_complete_vals(cols)
        self.y.set_complete_vals(cols)
        self.parameter.set_complete_vals(cols)

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
        if len(cols) > 3:

            if "lon" in cols:
                self.x.setText("lon")
            else:
                self.x.setText(cols[1])

            if "lat" in cols:
                self.y.setText("lat")
            else:
                self.x.setText(cols[2])

            self.parameter.setText(cols[3])

        return head.__repr__()

    def do_plot_file(self):
        if self.file_path is None:
            return

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
        )

        m2.show_layer(m2.layer)

        self.m2 = m2

        # check if we want to add an annotation
        self.b_add_annotate_cb()

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


class OpenDataStartTab(QtWidgets.QWidget):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.t1 = QtWidgets.QLabel()
        self.t1.setAlignment(Qt.AlignBottom | Qt.AlignCenter)
        self.set_std_text()

        self.b1 = self.FileButton("Open File", tab=parent, txt=self.t1)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.b1, 0, 0)
        layout.addWidget(self.t1, 3, 0)

        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

        self.setAcceptDrops(True)

    def set_std_text(self):
        self.t1.setText(
            "\n"
            + "Open or DRAG & DROP files!\n\n"
            + "Currently supported filetypes are:\n"
            + "    NetCDF | GeoTIFF | CSV"
        )

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.accept()
            self.t1.setText("DROP IT!")
        else:
            e.ignore()
            self.set_std_text()

    def dragLeaveEvent(self, e):
        self.set_std_text()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if len(urls) > 1:
            return

        self.b1.new_file_tab(urls[0].toLocalFile())

    class FileButton(QtWidgets.QPushButton):
        def __init__(self, *args, tab=None, txt=None, **kwargs):
            super().__init__(*args, **kwargs)
            self.tab = tab
            self.clicked.connect(lambda: self.new_file_tab())
            self.txt = txt

        @property
        def m(self):
            return self.tab.m

        def new_file_tab(self, file_path=None):

            if self.txt:
                self.txt.setText("")

            if file_path is None:
                file_path = Path(QtWidgets.QFileDialog.getOpenFileName()[0])
            elif isinstance(file_path, str):
                file_path = Path(file_path)

            global plc
            ending = file_path.suffix.lower()
            if ending in [".nc"]:
                plc = PlotNetCDFWidget(parent=self.tab.parent, tab=self.tab)
            elif ending in [".csv"]:
                plc = PlotCSVWidget(parent=self.tab.parent, tab=self.tab)
            elif ending in [".tif", ".tiff"]:
                plc = PlotGeoTIFFWidget(parent=self.tab.parent, tab=self.tab)
            else:
                print("unknown file extension")

            try:
                plc.open_file(file_path)
            except Exception:
                if self.txt:
                    self.txt.setText("File could not be opened...")
                import traceback

                show_error_popup(
                    text="There was an error while trying to open the file.",
                    title="Unable to open file.",
                    details=traceback.format_exc(),
                )


class OpenFileTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.parent = parent

        t1 = OpenDataStartTab(parent=self)
        self.addTab(t1, "NEW")

    @property
    def m(self):
        return self.parent.m

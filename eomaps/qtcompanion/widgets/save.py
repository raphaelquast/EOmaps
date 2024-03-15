# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt, Slot


class FiletypeComboBox(QtWidgets.QComboBox):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Export file format</h3>"
                "Set the file-format for the export."
                "<p>"
                "<b>NOTE:</b> The current value is also used for clipboard-export!"
                " (<code>ctrl+c</code>)",
            )


class DpiInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Export DPI</h3>"
                "Set the DPI used for exporting images."
                "<p>"
                "<b>NOTE:</b> The current value is also used for clipboard-export!"
                " (<code>ctrl+c</code>)",
            )


class TransparentCheckBox(QtWidgets.QCheckBox):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Frame transparency</h3>"
                "Toggle the transparency of the axis-frame."
                "<p>"
                "If checked, the map will be exported with a transparent background."
                "<p>"
                "<b>NOTE:</b> The current value is also used for clipboard-export!"
                " (<code>ctrl+c</code>)",
            )


class TightBboxCheckBox(QtWidgets.QCheckBox):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Export figure with a tight bbox</h3>"
                "If checked, the exported figure will use the smallest "
                "bounding-box that contains all artists. "
                "The input-box can be used to add a padding (in inches) on all sides."
                "<p>"
                "<b>NOTE:</b> The current value is also used for clipboard-export!"
                " (<code>ctrl+c</code>)",
            )


class TightBboxInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Tight Bbox padding</h3>"
                "Set the padding (in inches) that is added to each side of the "
                "figure when exporting it with a tight bounding-box"
                "<p>"
                "<b>NOTE:</b> The current value is also used for clipboard-export!"
                " (<code>ctrl+c</code>)",
            )


class RefetchWMSCheckBox(QtWidgets.QCheckBox):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Re-fetch WebMap services</h3>"
                "Toggle re-fetching WebMap services on figure-export."
                "<p>"
                "If checked, all WebMap services will be re-fetched with respect to "
                "the export-dpi before saving the figure. "
                "<p>"
                "NOTE: For high dpi-exports, this can result in a very large number of "
                "tiles that need to be fetched from the server. "
                "If the request is too large, the server might refuse it and the final "
                "image can have gaps (or no wms-tiles at all)!"
                "<p>"
                "<b>NOTE:</b> The current value is also used for clipboard-export!"
                " (<code>ctrl+c</code>)",
            )


class RasterizeCheckBox(QtWidgets.QCheckBox):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Rasterize datasets on vector export</h3>"
                "Toggle if data is rasterized (True) or treated as vector (False) "
                "when exporting the figure to vector-formats (svg, pdf, eps)."
                "<p>"
                "If checked, datasets will appear as rasterized images in the exported "
                "vector file (to avoid creating very large files for big datasets)."
                "<p>"
                "<b>NOTE:</b> The current value is also used for clipboard-export!"
                " (<code>ctrl+c</code>)",
            )


class SaveButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Save the figure</h3>"
                "Open a file-dialog to save the figure to disk."
                "<p>"
                "<b>NOTE:</b> The current value is also used for clipboard-export!"
                " (<code>ctrl+c</code>)",
            )


class SaveFileWidget(QtWidgets.QFrame):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        b1 = SaveButton("Save")
        width = b1.fontMetrics().boundingRect(b1.text()).width()
        b1.setFixedWidth(width + 30)

        b1.clicked.connect(self.save_file)

        self.available_filetypes = self.m.f.canvas.get_supported_filetypes()

        # filetype
        self.filetype_dropdown = FiletypeComboBox()
        for i in self.available_filetypes:
            self.filetype_dropdown.addItem(i)
        self.filetype_dropdown.setCurrentIndex(self.filetype_dropdown.findText("png"))
        self.filetype_dropdown.activated.connect(self.update_clipboard_kwargs)

        # dpi
        self.dpi_label = QtWidgets.QLabel("DPI:")
        width = self.dpi_label.fontMetrics().boundingRect(self.dpi_label.text()).width()
        self.dpi_label.setFixedWidth(width + 5)

        self.dpi_input = DpiInput()
        self.dpi_input.setMaximumWidth(50)
        validator = QtGui.QIntValidator()
        self.dpi_input.setValidator(validator)
        self.dpi_input.setText("100")
        self.dpi_input.textChanged.connect(self.update_clipboard_kwargs)

        # transparent
        self.transp_cb = TransparentCheckBox()
        transp_label = QtWidgets.QLabel("Transparent\nBackground")
        width = transp_label.fontMetrics().boundingRect("Transparent").width()
        transp_label.setFixedWidth(width + 5)
        self.transp_cb.stateChanged.connect(self.update_clipboard_kwargs)

        # refetch WebMap services
        self.refetch_cb = RefetchWMSCheckBox()
        refetch_label = QtWidgets.QLabel("Re-fetch\nWebMaps")
        width = transp_label.fontMetrics().boundingRect("Re-fetch").width()
        refetch_label.setFixedWidth(width + 5)
        self.refetch_cb.stateChanged.connect(self.update_clipboard_kwargs)

        # tight bbox
        self.tightbbox_cb = TightBboxCheckBox()
        tightbbox_label = QtWidgets.QLabel("Tight\nBbox")
        width = tightbbox_label.fontMetrics().boundingRect("Tight").width()
        tightbbox_label.setFixedWidth(width + 5)

        self.tightbbox_input = TightBboxInput()
        self.tightbbox_input.setMaximumWidth(50)
        validator = QtGui.QDoubleValidator()
        self.tightbbox_input.setValidator(validator)
        self.tightbbox_input.setText("0.1")
        self.tightbbox_input.setVisible(False)
        self.tightbbox_cb.stateChanged.connect(self.tight_cb_callback)

        self.tightbbox_cb.stateChanged.connect(self.update_clipboard_kwargs)
        self.tightbbox_input.textChanged.connect(self.update_clipboard_kwargs)

        # rasterize data
        self.rasterize_cb = RasterizeCheckBox()
        self.rasterize_label = QtWidgets.QLabel("Rasterize\nDatasets")
        width = self.rasterize_label.fontMetrics().boundingRect("Rasterize").width()
        self.rasterize_label.setFixedWidth(width + 5)

        # only show rasterize question on relevant filetypes
        self.filetype_dropdown.currentIndexChanged.connect(self.rasterize_cb_callback)

        # ------------ LAYOUT ------------

        save_label = QtWidgets.QLabel(
            "<b>Export:</b><br>" "<small>[<code>ctrl + c</code>]</small>"
        )

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(save_label)

        layout.addWidget(self.filetype_dropdown)

        layout.addWidget(self.dpi_label)
        layout.addWidget(self.dpi_input)

        layout.addWidget(self.rasterize_cb)
        layout.addWidget(self.rasterize_label)

        layout.addStretch()

        layout.addWidget(self.transp_cb)
        layout.addWidget(transp_label)

        layout.addWidget(self.refetch_cb)
        layout.addWidget(refetch_label)

        layout.addWidget(self.tightbbox_cb)
        layout.addWidget(tightbbox_label)

        layout.addWidget(self.tightbbox_input)
        layout.addWidget(b1)

        layout.setAlignment(Qt.AlignBottom)

        self.setLayout(layout)
        self.setStyleSheet(
            """
            SaveFileWidget{
                border: 0px solid rgb(200,200,200);
                border-radius: 10px;
                background-color: rgb(200,200,200);
                };
            """
        )

        # set current widget export parameters as copy-to-clipboard args
        self.m._connect_signal("clipboardKwargsChanged", self.set_export_props)

        # set export props to current state of Maps._clipboard_kwargs
        self.set_export_props()

    @Slot()
    def tight_cb_callback(self):
        if self.tightbbox_cb.isChecked():  # e.g. checked
            self.tightbbox_input.setVisible(True)
        else:
            self.tightbbox_input.setVisible(False)

    @Slot()
    def rasterize_cb_callback(self, *args, **kwargs):
        if self.filetype_dropdown.currentText() in ["svg", "pdf", "eps"]:
            self.rasterize_cb.setVisible(True)
            self.rasterize_label.setVisible(True)
        else:
            self.rasterize_cb.setVisible(False)
            self.rasterize_label.setVisible(False)

    @Slot()
    def save_file(self):
        selected_filetype = self.filetype_dropdown.currentText()

        filetype_filter = ";;".join(
            (f"{val} *.{key}" for key, val in self.available_filetypes.items())
        )
        selected_filter = (
            f"{self.available_filetypes[selected_filetype]} *.{selected_filetype}"
        )

        savepath, _ = QtWidgets.QFileDialog.getSaveFileName(
            self,
            caption="Export EOmaps Figure.",
            filter=filetype_filter,
            initialFilter=selected_filter,
            directory=f"EOmaps_figure.{selected_filetype}",
        )

        if savepath is not None and savepath != "":

            kwargs = dict()
            if self.tightbbox_cb.isChecked():
                kwargs["bbox_inches"] = "tight"
                kwargs["pad_inches"] = float(self.tightbbox_input.text())

            self.m.savefig(
                savepath,
                dpi=int(self.dpi_input.text()),
                transparent=self.transp_cb.isChecked(),
                refetch_wms=self.refetch_cb.isChecked(),
                **kwargs,
            )

    @Slot()
    def update_clipboard_kwargs(self, *args, **kwargs):
        clipboard_kwargs = dict(
            format=self.filetype_dropdown.currentText(),
            dpi=int(self.dpi_input.text()),
            transparent=self.transp_cb.isChecked(),
            refetch_wms=self.refetch_cb.isChecked(),
            rasterize_data=self.rasterize_cb.isChecked(),
        )

        if self.tightbbox_cb.isChecked():
            clipboard_kwargs["bbox_inches"] = "tight"
            clipboard_kwargs["pad_inches"] = float(self.tightbbox_input.text())

        # use private setter to avoid triggering callbacks on set
        self.m._set_clipboard_kwargs(**clipboard_kwargs)

    @Slot()
    def set_export_props(self, *args, **kwargs):
        # callback that is triggered on Maps.set_clipboard_kwargs

        clipboard_kwargs = self.m.__class__._clipboard_kwargs

        filetype = clipboard_kwargs.get("format", "png")
        i = self.filetype_dropdown.findText(filetype)
        if i != -1:
            self.filetype_dropdown.setCurrentIndex(i)

        dpi = clipboard_kwargs.get("dpi", 100)
        self.dpi_input.setText(str(dpi))

        transparent = clipboard_kwargs.get("transparent", False)
        self.transp_cb.setChecked(transparent)

        rasterize = clipboard_kwargs.get("rasterize_data", True)
        self.rasterize_cb.setChecked(rasterize)

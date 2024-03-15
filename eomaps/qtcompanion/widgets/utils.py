# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

from qtpy import QtWidgets, QtGui
from qtpy.QtCore import Qt, QRectF, QSize, Slot, Signal
from eomaps import Maps
from functools import lru_cache

import matplotlib.pyplot as plt


@lru_cache()
def get_cmap_pixmaps():
    # cache the pixmaps for matplotlib colormaps
    # Note: the cache must be cleared if new colormaps are registered!
    # (emit the cmapsChanged signal of MenuWindow to clear the cache)
    cmap_pixmaps = list()
    for cmap in sorted(plt.cm._colormaps()):
        pixmap = QtGui.QPixmap()
        pixmap.loadFromData(plt.cm.get_cmap(cmap)._repr_png_(), "png")
        label = QtGui.QIcon()
        label.addPixmap(pixmap, QtGui.QIcon.Normal, QtGui.QIcon.On)
        label.addPixmap(pixmap, QtGui.QIcon.Normal, QtGui.QIcon.Off)
        label.addPixmap(pixmap, QtGui.QIcon.Disabled, QtGui.QIcon.On)
        label.addPixmap(pixmap, QtGui.QIcon.Disabled, QtGui.QIcon.Off)
        cmap_pixmaps.append((label, cmap))

    return cmap_pixmaps


def str_to_bool(val):
    return val == "True"


def to_float_none(s):
    if len(s) > 0:
        return float(s.replace(",", "."))
    else:
        return None


def show_error_popup(text=None, info=None, title=None, details=None):
    global msg
    msg = QtWidgets.QMessageBox()
    msg.setIcon(QtWidgets.QMessageBox.Critical)

    if text:
        msg.setText(text)
    if info:
        msg.setInformativeText(info)
    if title:
        msg.setWindowTitle(title)
    if details:
        msg.setDetailedText(details)

    msg.setStandardButtons(QtWidgets.QMessageBox.Ok)
    msg.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)

    msg.show()


def get_crs(crs):

    try:
        if crs.startswith("Maps.CRS."):

            crsname = crs[9:]
            crs = getattr(Maps.CRS, crsname)
            if callable(crs):
                crs = crs()
        else:
            try:
                crs = int(crs)
            except Exception:
                pass

        # try if we can identify the crs
        Maps.get_crs(Maps, crs)
    except Exception:
        import traceback

        show_error_popup(
            text=f"{crs} is not a valid crs specifier",
            title="Unable to identify crs",
            details=traceback.format_exc(),
        )
    return crs


class LineEditComplete(QtWidgets.QLineEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._options = None

        self.installEventFilter(self)

    def set_complete_vals(self, options):
        self._options = options
        completer = QtWidgets.QCompleter(self._options)
        self.setCompleter(completer)

    def mousePressEvent(self, event):
        super().mousePressEvent(event)
        if self._options is not None:
            # set the completion-prefix to ensure all options are shown
            self.completer().setCompletionPrefix("")
            self.completer().complete()


class InputCRS(LineEditComplete):
    def __init__(self, *args, **kwargs):
        """
        A QtWidgets.QLineEdit widget with autocompletion for available CRS
        """
        super().__init__(*args, **kwargs)
        ignore = ["Projection"]
        self.crs_options = [
            key
            for key, val in Maps.CRS.__dict__.items()
            if not key.startswith("_")
            and (isinstance(val, Maps.CRS.ABCMeta) or isinstance(val, Maps.CRS.CRS))
            and key not in ignore
        ]
        self.set_complete_vals(self.crs_options)
        self.setPlaceholderText("4326")

    def text(self):
        t = super().text()
        if len(t) == 0:
            t = self.placeholderText()

        if t in self.crs_options:
            t = "Maps.CRS." + t

        return t

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>CRS</h3>"
                "Set the coordinate reference system of the coordinates (x, y)."
                "<ul>"
                "<li>A name of a crs accessible via <code>Maps.CRS</code></li>"
                "<li>An EPSG code</li>"
                "<li>A PROJ or WKT string</li>"
                "</ul>",
            )


class CmapDropdown(QtWidgets.QComboBox):
    def __init__(self, *args, startcmap="viridis", **kwargs):
        super().__init__(*args, **kwargs)

        self.setIconSize(QSize(100, 15))
        self.view().setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        for label, cmap in get_cmap_pixmaps():
            self.addItem(label, cmap)

        self.setStyleSheet("combobox-popup: 0;")
        self.setMaxVisibleItems(10)
        idx = self.findText(startcmap)
        if idx != -1:
            self.setCurrentIndex(idx)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Colormap</h3>"
                "Set the colormap that should be used when plotting the data.",
            )

    def wheelEvent(self, e):
        # ignore mouse-wheel events to disable changing the colormap with the mousewheel
        pass


class GetColorWidget(QtWidgets.QFrame):
    def __init__(
        self,
        facecolor="#ff0000",
        edgecolor="#000000",
        linewidth=1,
        alpha=1,
        tooltip=None,
        helptext=None,
    ):
        """
        A widget that indicates a selected color (and opens a popup to change the
        color on click)

        Parameters
        ----------
        facecolor : str
            The initial facecolor to use.
        edgecolor : str
            The initial edgecolor to use.

        Attributes
        -------
        facecolor, edgecolor:
            The QColor object of the currently assigned facecolor/edgecolor.
            To get the hex-string, use    the  ".name()" property.

        """

        if tooltip is None:
            self._tooltip = (
                "<b>click</b>: set facecolor <br> <b>alt + click</b>: set edgecolor"
            )
        else:
            self._tooltip = tooltip

        if helptext is None:
            self._helptext = (
                "<h3>Facecolor / Edgecolor</h3>"
                "<ul><li><b>click</b> to set the facecolor</li>"
                "<li><b>alt+click</b> to set the edgecolor</li></ul>"
            )
        else:
            self._helptext = helptext

        super().__init__()

        if isinstance(facecolor, str):
            self.facecolor = QtGui.QColor(facecolor)
        else:
            self.facecolor = QtGui.QColor(*facecolor)
        if isinstance(edgecolor, str):
            self.edgecolor = QtGui.QColor(edgecolor)
        else:
            self.edgecolor = QtGui.QColor(*edgecolor)

        self.linewidth = linewidth
        self.alpha = alpha

        self.setMinimumSize(15, 15)
        self.setMaximumSize(100, 100)

        self.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

        self.setToolTip(self._tooltip)

        self.setStyleSheet(
            """QToolTip {
            font-family: "SansSerif";
            font-size:10;
            background-color: rgb(53, 53, 53);
            color: white;
            border: none;
            }
            """
        )

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(e.globalPos(), self._helptext)

    def resizeEvent(self, e):
        # make frame rectangular
        self.setMaximumHeight(self.width())

    def paintEvent(self, e):
        super().paintEvent(e)
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        size = self.size()

        if self.linewidth > 0.01:
            painter.setPen(
                QtGui.QPen(self.edgecolor, 1.1 * self.linewidth, Qt.SolidLine)
            )
        else:
            painter.setPen(
                QtGui.QPen(self.facecolor, 1.1 * self.linewidth, Qt.SolidLine)
            )

        painter.setBrush(QtGui.QBrush(self.facecolor, Qt.SolidPattern))

        w, h = size.width(), size.height()
        s = min(min(0.9 * h, 0.9 * w), 100)
        rect = QRectF(w / 2 - s / 2, h / 2 - s / 2, s, s)
        painter.drawRoundedRect(rect, s / 5, s / 5)

        # painter.setFont(QtGui.QFont("Arial", 7))
        # painter.drawText(0, 0, w, h, Qt.AlignCenter,
        #                  f"α:  {self.alpha:.2f}" + "\n" + f"lw: {self.linewidth:.2f}")

    def mousePressEvent(self, event):
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if event.buttons() & (bool(modifiers == Qt.AltModifier)):
            self.set_edgecolor_dialog()
        else:
            self.set_facecolor_dialog()

    def cb_colorselected(self):
        # a general callback that will always be connected to .colorSelected
        pass

    def set_facecolor_dialog(self):
        self._dialog = QtWidgets.QColorDialog()
        self._dialog.setWindowTitle("Select facecolor")
        self._dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
        self._dialog.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, on=True)
        self._dialog.colorSelected.connect(self.set_facecolor)
        self._dialog.colorSelected.connect(self.cb_colorselected)
        self._dialog.setCurrentColor(QtGui.QColor(self.facecolor))
        self._dialog.open()

    def set_edgecolor_dialog(self):
        self._dialog = QtWidgets.QColorDialog()
        self._dialog.setWindowTitle("Select edgecolor")
        self._dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
        self._dialog.setOption(QtWidgets.QColorDialog.ShowAlphaChannel, on=True)
        self._dialog.colorSelected.connect(self.set_edgecolor)
        self._dialog.colorSelected.connect(self.cb_colorselected)
        self._dialog.setCurrentColor(QtGui.QColor(self.edgecolor))
        self._dialog.open()

    def set_facecolor(self, color):
        if isinstance(color, str):
            color = QtGui.QColor(color)
        elif isinstance(color, (list, tuple)):
            color = QtGui.QColor(*color)

        self.alpha = color.alpha() / 255

        color = QtGui.QColor(*color.getRgb()[:3], int(self.alpha * 255))

        self.facecolor = color
        self.update()

    def set_edgecolor(self, color):
        if isinstance(color, str):
            color = QtGui.QColor(color)
        elif isinstance(color, (list, tuple)):
            color = QtGui.QColor(*color)

        self.edgecolor = color
        self.update()

    def set_linewidth(self, linewidth):
        self.linewidth = linewidth
        self.update()

    def set_alpha(self, alpha):
        self.alpha = alpha
        self.set_facecolor(
            QtGui.QColor(*self.facecolor.getRgb()[:3], int(self.alpha * 255))
        )


class AlphaSlider(QtWidgets.QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.alpha = 1
        self._style = ""

        self.setRange(0, 100)
        self.setSingleStep(1)
        self.setTickInterval(10)
        self.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.setValue(100)

        # self.setMinimumWidth(50)
        # self.setMaximumWidth(300)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.MinimumExpanding, QtWidgets.QSizePolicy.Minimum
        )

        self.valueChanged.connect(self.value_changed)

        s = 14
        self.setStyleSheet(
            f"""
            QToolTip {{
               font-family: "SansSerif";
               font-size:10;
               background-color: rgb(53, 53, 53);
               color: white;
               border: none;
               }}
            QSlider::handle:horizontal {{
                background-color: rgba(0,0,0,255);
                border: none;
                border-radius: {s/2}px;
                height: {s}px;
                width: {s}px;
                margin: -{s//2}px 0;
                padding: -{s//2}px 0px;
            }}
            QSlider::groove:horizontal {{
                border-radius: 1px;
                height: 1px;
                margin: 5px;
                background-color: rgba(0,0,0,50);
            }}
            QSlider::groove:horizontal:hover {{
                background-color: rgba(0,0,0,255);
            }}

            """
        )

    def enterEvent(self, e):
        if self.window().showhelp is True:
            if self._style == "linewidth":
                QtWidgets.QToolTip.showText(
                    e.globalPos(),
                    "<h3>Linewidth</h3> Set the linewidth of the shape boundary.",
                )
            elif self._style == "alpha":
                QtWidgets.QToolTip.showText(
                    e.globalPos(),
                    "<h3>Transparency</h3> Set the transparency of the facecolor.",
                )

    def set_stylesheet(self):
        if self._style == "linewidth":
            self.set_linewidth_stylesheet()
        elif self._style == "alpha":
            self.set_alpha_stylesheet()

    @Slot(int)
    def value_changed(self, i):
        self.alpha = i / 100
        self.set_stylesheet()

    def set_linewidth_stylesheet(self):
        self._style = "linewidth"

        self.setStyleSheet(
            """
            QSlider::handle:horizontal {
                background-color: black;
                border: none;
                border-radius: 0px;
                height: 10px;
                width: 5px;
                margin: -10px 0;
                padding: -10px 0px;
            }
            QSlider::groove:horizontal {
                border-radius: 1px;
                height: 1px;
                margin: 5px;
                background-color: rgba(0,0,0,50);
            }
            QSlider::groove:horizontal:hover {
                background-color: rgba(0,0,0,255);
            }
            """
        )

    def set_alpha_stylesheet(self):
        self._style = "alpha"
        a = self.alpha * 255
        s = 12
        self.setStyleSheet(
            f"""
            QSlider::handle:horizontal {{
                background-color: rgba(0,0,0,{a});
                border: 1px solid black;
                border-radius: {s//2}px;
                height: {s}px;
                width: {s}px;
                margin: -{s//2}px 0px;
                padding: -{s//2}px 0px;
            }}
            QSlider::groove:horizontal {{
                border-radius: 1px;
                height: 1px;
                margin: 5px;
                background-color: rgba(0,0,0,50);
            }}
            QSlider::groove:horizontal:hover {{
                background-color: rgba(0,0,0,255);
            }}
            """
        )


class ColorWithSlidersWidget(QtWidgets.QWidget):
    colorSelected = Signal()
    alpha_slider_scale = 100
    linewidth_slider_scale = 10

    def __init__(
        self,
        *args,
        facecolor="red",
        edgecolor="black",
        linewidth=1,
        alpha=0.5,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)

        self.color = GetColorWidget(
            facecolor=facecolor, edgecolor=edgecolor, linewidth=linewidth, alpha=alpha
        )
        self.color.cb_colorselected = self.color_selected
        self.color.setMaximumWidth(60)

        self.alphaslider = AlphaSlider(Qt.Horizontal)
        self.alphaslider.set_alpha_stylesheet()
        self.alphaslider.valueChanged.connect(self.set_alpha_with_slider)
        self.alphaslider.setValue(int(alpha * self.alpha_slider_scale))

        self.linewidthslider = AlphaSlider(Qt.Horizontal)
        self.linewidthslider.set_linewidth_stylesheet()
        self.linewidthslider.valueChanged.connect(self.set_linewidth_with_slider)
        self.linewidthslider.setValue(int(linewidth * self.linewidth_slider_scale))

        layout_sliders = QtWidgets.QVBoxLayout()
        layout_sliders.addWidget(self.alphaslider)
        layout_sliders.addWidget(self.linewidthslider)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(self.color)
        layout.addLayout(layout_sliders)
        self.setLayout(layout)

    @property
    def facecolor(self):
        return self.color.facecolor

    @property
    def edgecolor(self):
        return self.color.edgecolor

    @property
    def linewidth(self):
        return self.color.linewidth

    @property
    def alpha(self):
        return self.color.alpha

    @Slot(int)
    def set_alpha_with_slider(self, i):
        self.color.set_alpha(i / self.alpha_slider_scale)
        self.colorSelected.emit()

    @Slot(int)
    def set_linewidth_with_slider(self, i):
        self.color.set_linewidth(i / self.linewidth_slider_scale)
        self.colorSelected.emit()

    def color_selected(self):
        self.colorSelected.emit()

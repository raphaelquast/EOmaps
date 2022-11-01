from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, QRectF, QSize, pyqtSlot
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

    def wheelEvent(self, e):
        # ignore mouse-wheel events to disable changing the colormap with the mousewheel
        pass


class GetColorWidget(QtWidgets.QFrame):
    def __init__(self, facecolor="#ff0000", edgecolor="#000000", linewidth=1, alpha=1):
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

        self.setToolTip(
            "<b>click</b>: set facecolor <br> <b>alt + click</b>: set edgecolor"
        )

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
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Facecolor / Edgecolor</h3>"
                "<ul><li><b>click</b> to set the facecolor</li>"
                "<li><b>alt+click</b> to set the edgecolor</li></ul>",
            )

    def resizeEvent(self, e):
        # make frame rectangular
        self.setMaximumHeight(self.width())

    def paintEvent(self, e):
        super().paintEvent(e)
        painter = QtGui.QPainter(self)

        painter.setRenderHints(QtGui.QPainter.HighQualityAntialiasing)
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

        self.alpha = color.alpha() / 255

        color = QtGui.QColor(*color.getRgb()[:3], int(self.alpha * 255))

        self.facecolor = color
        self.update()

    def set_edgecolor(self, color):
        if isinstance(color, str):
            color = QtGui.QColor(color)

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


class EditLayoutButton(QtWidgets.QPushButton):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m

        self.clicked.connect(self.callback)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Layout Editor</h3>"
                "Toggle the EOmaps LayoutEditor to re-arrange the position and size"
                "of the axes in the figure."
                "<ul>"
                "<li>Pick axes with the mouse to drag the position.</li>"
                "<li>Use the scroll-wheel while an axis is picked (e.g. green) to "
                "change the size of the axis</li>"
                "<li>Press <b>escape</b> to exit the LayoutEditor</li>"
                "</ul>",
            )

    @pyqtSlot()
    def callback(self):
        if not self.m.parent._layout_editor._modifier_pressed:
            self.m.parent.edit_layout()
        else:
            self.m.parent._layout_editor._undo_draggable()


class AlphaSlider(QtWidgets.QSlider):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.alpha = 1

        self.setRange(0, 100)
        self.setSingleStep(1)
        self.setTickInterval(10)
        self.setTickPosition(QtWidgets.QSlider.TicksBothSides)
        self.setValue(100)

        # self.setMinimumWidth(50)
        self.setMaximumWidth(300)
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

    @pyqtSlot(int)
    def value_changed(self, i):
        self.alpha = i / 100

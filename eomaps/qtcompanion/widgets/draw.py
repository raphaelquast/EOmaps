# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

import logging

from qtpy import QtWidgets
from qtpy.QtCore import Qt, Slot, Signal

from .utils import ColorWithSlidersWidget

_log = logging.getLogger(__name__)


class SaveButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Save Polygons</h3> Save the created polygons as "
                "geo-coded shapefile.",
            )


class RemoveButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Remove Polygons</h3> Successivlely remove the most recently "
                "created polygons from the map.",
            )


class PolyButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setCheckable(True)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            name = self.text()
            if name == "Polygon":
                txt = (
                    "<h3>Draw a Polygon</h3>"
                    "Draw an arbitrary polygon on the map."
                    "<ul>"
                    "<li><b>right click</b> on the map to add new points to the "
                    "polygon (or move the mouse while pressing the right button)</li>"
                    "<li><b>left click</b> to undo previously drawn points</li>"
                    "<li><b>middle click</b> to finish drawing</li>"
                    "</ul>"
                )
            elif name == "Rectangle":
                txt = (
                    "<h3>Draw a Rectangle</h3>"
                    "Draw a rectangle on the map."
                    "<ul>"
                    "<li><b>right click</b> on the map to set the center point of "
                    "the rectangle</li>"
                    "<li><b>move</b> the mouse to set the size</li>"
                    "<li><b>middle click</b> to finish drawing</li>"
                    "</ul>"
                )

            elif name == "Circle":
                txt = (
                    "<h3>Draw a Circle</h3>"
                    "Draw a circle on the map."
                    "<ul>"
                    "<li><b>right click</b> on the map to set the center point of "
                    "the circle</li>"
                    "<li><b>move</b> the mouse to set the size</li>"
                    "<li><b>middle click</b> to finish drawing</li>"
                    "</ul>"
                )
            else:
                txt = ""

            txt += (
                "The shape will be added to the "
                "<b><font color=#c80000>currently selected tab</font></b> "
                "in the tab-bar below."
                "<p>"
                "NOTE: this is not necessarily the visible layer!"
            )

            QtWidgets.QToolTip.showText(e.globalPos(), txt)


class DrawerTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_handler)

        w = self._get_new_drawer()
        self.addTab(w, "0")
        self.update_tab_icon(w=w)

        # a tab that is used to create new tabs
        newtabwidget = QtWidgets.QWidget()
        newtablayout = QtWidgets.QHBoxLayout()
        l = QtWidgets.QLabel("Click on <b>+</b> to open a new drawer tab!")
        newtablayout.addWidget(l)
        newtabwidget.setLayout(newtablayout)

        self.addTab(newtabwidget, "+")
        # don't show the close button for this tab
        self.tabBar().setTabButton(self.count() - 1, self.tabBar().RightSide, None)

        self.tabBarClicked.connect(self.tabbar_clicked)
        self.setCurrentIndex(0)

        self.setStyleSheet(
            """
            QTabWidget::pane {
              border: 0px;
              top:0px;
              background: rgb(150, 150, 150);
              border-radius: 10px;
            }

            QTabBar::tab {
              background: rgb(185, 185, 185);
              border: 0px;
              padding: 3px;
              padding-bottom: 6px;
              padding-left: 6px;
              padding-right: 6px;
              margin-left: 10px;
              margin-bottom: -2px;
              border-radius: 4px;
              font-weight: normal;
            }

            QTabBar::tab:selected {
              background: rgb(150, 150, 150);
              border: 0px;
              margin-bottom: -2px;
              font-weight: normal;
            }
            """
        )

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Draw Shape Tabs</h3>"
                "Each tab represents a ShapeDrawer that can be used to draw shapes "
                "on the map."
                "<p>"
                "Click on '+' to create a new tab."
                "<p>"
                "The tabs can be used to collect shapes that are intended to be "
                "saved to individual files. If a tab is closed, all associated shapes"
                "are removed from the map.",
            )

    @Slot(int)
    def tabbar_clicked(self, index):
        if self.tabText(index) == "+":
            w = self._get_new_drawer()
            self.insertTab(self.count() - 1, w, "0")
            self.update_tab_icon(w=w)

    @Slot(int)
    def close_handler(self, index):
        curridx = self.currentIndex()
        drawerwidget = self.widget(index)

        try:
            while len(drawerwidget.drawer._artists) > 0:
                drawerwidget.drawer.remove_last_shape()
        except Exception:
            _log.error(
                "EOmaps: Encountered some problems while clearing the drawer!",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

        self.m.BM.update()

        self.removeTab(index)
        if index == curridx:
            self.setCurrentIndex(index - 1)

    def _get_new_drawer(self):
        w = DrawerWidget(m=self.m)

        def cb():
            npoly = len(w.drawer._artists)
            idx = self.indexOf(w)
            self.setTabText(idx, str(npoly))

        w.drawer._on_new_poly.append(cb)
        w.drawer._on_poly_remove.append(cb)
        w.colorSelected.connect(self.update_tab_icon)
        return w

    def set_layer(self, layer):
        for i in range(self.count()):
            if self.tabText(i) != "+":
                self.widget(i).set_layer(layer)

    @Slot()
    def update_tab_icon(self, w=None):
        if w is None:
            w = self.sender()
        self.setTabIcon(self.indexOf(w), w.get_tab_icon())


class DrawerWidget(QtWidgets.QWidget):

    colorSelected = Signal()

    _polynames = {
        "Polygon": "polygon",
        "Rectangle": "rectangle",
        "Circle": "circle",
    }

    def __init__(self, *args, m=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.m = m

        self.save_button = SaveButton("  Save Polygons  ")
        self.save_button.setMaximumSize(self.save_button.sizeHint())
        self.save_button.setEnabled(False)

        self.remove_button = RemoveButton("Remove")
        self.remove_button.setMaximumSize(self.remove_button.sizeHint())
        self.remove_button.setEnabled(False)

        self.cancel_button = RemoveButton("Cancel")
        self.cancel_button.setMaximumSize(self.cancel_button.sizeHint())
        self.cancel_button.setEnabled(False)

        self._new_drawer()

        self.save_button.clicked.connect(self.save_shapes)
        self.remove_button.clicked.connect(self.remove_last_shape)
        self.cancel_button.clicked.connect(self.cancel_draw)

        self.polybuttons = []
        for name, poly in self._polynames.items():
            poly_b = PolyButton(name.center(15))
            poly_b.clicked.connect(self.draw_shape_callback(poly=poly))
            poly_b.setMaximumWidth(100)
            self.polybuttons.append(poly_b)

        b_layout = QtWidgets.QVBoxLayout()
        b_layout.setContentsMargins(0, 0, 0, 0)
        b_layout.setSpacing(2)

        for b in self.polybuttons:
            b_layout.addWidget(b)

        save_layout = QtWidgets.QVBoxLayout()
        save_layout.addWidget(self.save_button)
        save_layout.addWidget(self.remove_button)
        save_layout.addWidget(self.cancel_button)

        self.colorselector = ColorWithSlidersWidget(linewidth=1)
        self.colorselector.colorSelected.connect(lambda: self.colorSelected.emit())
        self.colorselector.layout().setContentsMargins(0, 0, 0, 0)

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(b_layout)
        layout.addLayout(save_layout)
        layout.addWidget(self.colorselector)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.setLayout(layout)

        self.m._connect_signal("drawFinished", self.uncheck_polybuttons)
        self.m._connect_signal("drawAborted", self.uncheck_polybuttons)
        self.m._connect_signal("drawStarted", self.check_polybuttons)

        self.setStyleSheet(
            """
            QPushButton {
                border: 1px solid rgb(140, 140, 140);
                border-radius: 4px;
                padding: 4px;
                background-color: rgb(220, 220, 220);
            }
            QPushButton:hover {
                background-color: rgb(210, 210, 210);
                font-weight: bold;
            }
            QPushButton:disabled {
                background-color: rgb(180, 180, 180);
            }
            PolyButton {
                border-radius: 5px;
                border-width: 1px;
                border-style: solid;
                border-color: rgb(100, 100, 100);
                background-color: rgb(220, 220, 220);
                padding: 3px
                }

            PolyButton:pressed {
                background-color: rgb(150, 150, 150);
                }

            PolyButton:hover:!pressed {
                background-color: rgb(180, 180, 180);
                font-weight: bold;
                }

            PolyButton:checked {
                background-color: rgb(180, 0, 0);
                border-color: rgb(100, 0, 0);
                font-weight: bold;
                }
            """
        )

    def check_polybuttons(self, poly):
        for b in self.polybuttons:
            if b.text().strip() == poly:
                b.setChecked(True)
        self.cancel_button.setEnabled(True)

    def uncheck_polybuttons(self):
        for b in self.polybuttons:
            b.setChecked(False)
        self.cancel_button.setEnabled(False)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Draw Shapes on the Map</h3>"
                "A widget to draw simple shapes on the map."
                "<p>"
                "<ul>"
                "<li>use the <b>left</b> mouse button to <b>draw</b> points</li>"
                "<li>use the <b>right</b> mouse button to <b>erase</b> points</li>"
                "<li>use the <b>middle</b> mouse button to <b>finish</b> drawing</li>"
                "</ul>"
                "<p>"
                "For <b>circles</b> and <b>rectangles</b> the first click determines "
                "the center-point, and the size is determined by the position of the "
                "mouse when clicking the middle mouse button."
                "<p>"
                "For <b>polygons</b>, points can be added by successively clicking on "
                "the map with the left mouse button (or by holding the button and "
                "dragging the mouse). The polygon is finalized by clicking the "
                "middle mouse button."
                "<p>"
                "For any shape, the added points can be undone by successively "
                "clicking the right mouse button.",
            )

    def draw_shape_callback(self, poly):
        @Slot()
        def cb():
            s = self.sender()
            for b in self.polybuttons:
                if s is b:
                    b.setChecked(True)
                else:
                    b.setChecked(False)

            getattr(self.drawer, poly)(
                facecolor=self.colorselector.facecolor.getRgbF(),
                edgecolor=self.colorselector.edgecolor.getRgbF(),
                linewidth=self.colorselector.linewidth,
            )

        return cb

    @Slot()
    def _new_poly_cb(self):
        # callback executed on creation of a new polygon
        npoly = len(self.drawer._artists)
        if npoly > 0:
            self.save_button.setEnabled(True)
            self.remove_button.setEnabled(True)
        else:
            self.save_button.setEnabled(False)
            self.remove_button.setEnabled(False)

        if npoly == 0:
            txt = f"Save Polygons".center(20)
        elif npoly == 1:
            txt = f"Save {npoly} Polygon".center(20)
        else:
            txt = f"Save {npoly} Polygons".center(20)

        self.save_button.setText(txt)
        self.save_button.setFixedSize(self.save_button.sizeHint())

    @Slot()
    def save_shapes(self):
        try:
            save_path, widget = QtWidgets.QFileDialog.getSaveFileName(
                caption="Save Shapes",
                directory="shapes.shp",
                filter="Shapefiles (*.shp)",
            )
            if save_path is not None and len(save_path) > 0:
                self.drawer.save_shapes(save_path)
                # after saving the polygons, start with a new drawer
                self._new_drawer()
        except Exception:
            _log.error(
                "EOmaps: Encountered a problem while trying to save " "drawn shapes...",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

    @Slot()
    def remove_last_shape(self):
        try:
            self.drawer.remove_last_shape()
            # update to make sure the changes are reflected on the map immediately
            self.m.BM.update()
        except Exception:
            _log.error(
                "EOmaps: Encountered a problem while trying to remove "
                "the last drawn shape...",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

    @Slot()
    def cancel_draw(self):
        self.drawer._finish_drawing()

    def _new_drawer(self):
        self.drawer = self.m.draw.new_drawer()
        self.save_button.setEnabled(False)
        self.remove_button.setEnabled(False)

        self.drawer._on_new_poly.append(self._new_poly_cb)
        self.drawer._on_poly_remove.append(self._new_poly_cb)

    def set_layer(self, layer):
        self.drawer.set_layer(layer)

    @Slot()
    def get_tab_icon(self):
        from qtpy import QtGui
        from qtpy.QtCore import QRectF

        canvas = QtGui.QPixmap(20, 20)
        canvas.fill(Qt.transparent)

        painter = QtGui.QPainter(canvas)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        painter.setBrush(QtGui.QBrush(self.colorselector.facecolor, Qt.SolidPattern))

        if self.colorselector.linewidth > 0.01:
            painter.setPen(
                QtGui.QPen(
                    self.colorselector.edgecolor,
                    0.5 * self.colorselector.linewidth,
                    Qt.SolidLine,
                )
            )
        else:
            painter.setPen(
                QtGui.QPen(
                    self.colorselector.facecolor,
                    0.5 * self.colorselector.linewidth,
                    Qt.SolidLine,
                )
            )

        rect = QRectF(2.5, 2.5, 15, 15)
        painter.drawRoundedRect(rect, 5, 5)
        painter.end()

        icon = QtGui.QIcon(canvas)

        return icon

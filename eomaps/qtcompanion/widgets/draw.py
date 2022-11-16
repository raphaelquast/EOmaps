from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot

from .utils import GetColorWidget, AlphaSlider
from .editor import AddAnnotationInput


class TransparencySlider(AlphaSlider):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Transparency</h3> Set the transparency of the facecolor.",
            )


class LineWidthSlider(AlphaSlider):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Linewidth</h3> Set the linewidth of the shape boundary.",
            )


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

    @pyqtSlot(int)
    def tabbar_clicked(self, index):
        if self.tabText(index) == "+":
            w = self._get_new_drawer()
            self.insertTab(self.count() - 1, w, "0")

    @pyqtSlot(int)
    def close_handler(self, index):
        curridx = self.currentIndex()
        drawerwidget = self.widget(index)

        try:
            while len(drawerwidget.drawer._artists) > 0:
                drawerwidget.drawer.remove_last_shape()
        except Exception:
            print("EOmaps: Encountered some problems while clearing the drawer!")

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

        return w

    def set_layer(self, layer):
        for i in range(self.count()):
            if self.tabText(i) != "+":
                self.widget(i).set_layer(layer)


class DrawerWidget(QtWidgets.QWidget):

    _polynames = {
        "Polygon": "polygon",
        "Rectangle": "rectangle",
        "Circle": "circle",
    }

    def __init__(self, m=None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.m = m

        self.save_button = SaveButton("  Save Polygons  ")
        self.save_button.setMaximumSize(self.save_button.sizeHint())
        self.save_button.setEnabled(False)

        self.remove_button = RemoveButton("Remove")
        self.remove_button.setMaximumSize(self.remove_button.sizeHint())
        self.remove_button.setEnabled(False)

        self._new_drawer()

        self.save_button.clicked.connect(self.save_shapes)
        self.remove_button.clicked.connect(self.remove_last_shape)

        polybuttons = []
        for name, poly in self._polynames.items():
            poly_b = PolyButton(name)
            poly_b.clicked.connect(self.draw_shape_callback(poly=poly))
            poly_b.setMaximumWidth(100)
            polybuttons.append(poly_b)

        self.colorselector = GetColorWidget()

        self.alphaslider = TransparencySlider(Qt.Horizontal)
        self.alphaslider.valueChanged.connect(self.set_alpha_with_slider)
        self.alphaslider.setValue(50)

        self.linewidthslider = LineWidthSlider(Qt.Horizontal)
        self.linewidthslider.valueChanged.connect(self.set_linewidth_with_slider)
        self.linewidthslider.setValue(20)

        save_layout = QtWidgets.QVBoxLayout()
        save_layout.addWidget(self.save_button)
        save_layout.addWidget(self.remove_button)

        b_layout = QtWidgets.QVBoxLayout()
        for b in polybuttons:
            b_layout.addWidget(b)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.colorselector, 0, 0, 2, 1)
        layout.addWidget(self.alphaslider, 0, 1)
        layout.addWidget(self.linewidthslider, 1, 1)
        layout.addLayout(b_layout, 0, 2, 2, 1)
        layout.addLayout(save_layout, 0, 3, 2, 1)

        layout.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        self.setLayout(layout)

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
        @pyqtSlot()
        def cb():
            self.window().hide()
            self.m.f.canvas.show()
            self.m.f.canvas.activateWindow()

            getattr(self.drawer, poly)(
                facecolor=self.colorselector.facecolor.getRgbF(),
                edgecolor=self.colorselector.edgecolor.getRgbF(),
                linewidth=self.linewidthslider.alpha * 10,
            )

        return cb

    @pyqtSlot()
    def _new_poly_cb(self):
        # callback executed on creation of a new polygon
        npoly = len(self.drawer._artists)
        if npoly > 0:
            self.save_button.setEnabled(True)
            self.remove_button.setEnabled(True)
        else:
            self.save_button.setEnabled(False)
            self.remove_button.setEnabled(False)

        if npoly == 1:
            txt = f"Save {npoly} Polygon"
        else:
            txt = f"Save {npoly} Polygons"

        self.save_button.setText(txt)

    @pyqtSlot()
    def save_shapes(self):
        save_path, widget = QtWidgets.QFileDialog.getSaveFileName(
            caption="Save Shapes", directory="shapes.shp", filter="Shapefiles (*.shp)"
        )
        if save_path is not None and len(save_path) > 0:
            self.drawer.save_shapes(save_path)
            # after saving the polygons, start with a new drawer
            self._new_drawer()

    @pyqtSlot()
    def remove_last_shape(self):
        self.drawer.remove_last_shape()
        # update to make sure the changes are reflected on the map immediately
        self.m.BM.update()

    @pyqtSlot(int)
    def set_alpha_with_slider(self, i):
        self.colorselector.set_alpha(i / 100)

    @pyqtSlot(int)
    def set_linewidth_with_slider(self, i):
        self.colorselector.set_linewidth(i / 10)

    def _new_drawer(self):
        self.drawer = self.m.draw.new_drawer()
        self.save_button.setEnabled(False)
        self.remove_button.setEnabled(False)

        self.drawer._on_new_poly.append(self._new_poly_cb)
        self.drawer._on_poly_remove.append(self._new_poly_cb)

    def set_layer(self, layer):
        self.drawer.set_layer(layer)

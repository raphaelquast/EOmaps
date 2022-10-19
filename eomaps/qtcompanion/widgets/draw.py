from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

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
                    "The shape will be added to the <b>currently selected tab</b> "
                    "in the tab-bar below."
                    "<p>"
                    "NOTE: this is not necessarily the visible layer!",
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
                    "The shape will be added to the <b>currently selected tab</b> "
                    "in the tab-bar below."
                    "<p>"
                    "NOTE: this is not necessarily the visible layer!",
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
                    "The shape will be added to the <b>currently selected tab</b> "
                    "in the tab-bar below."
                    "<p>"
                    "NOTE: this is not necessarily the visible layer!",
                )
            else:
                txt = ""

            QtWidgets.QToolTip.showText(e.globalPos(), txt)


class DrawerWidget(QtWidgets.QWidget):

    _polynames = {
        "Polygon": "polygon",
        "Rectangle": "rectangle",
        "Circle": "circle",
    }

    def __init__(self, m=None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.m = m

        polybuttons = []
        for name, poly in self._polynames.items():
            poly_b = PolyButton(name)
            poly_b.clicked.connect(self.draw_shape_callback(poly=poly))
            poly_b.setMaximumWidth(100)
            polybuttons.append(poly_b)

        self.colorselector = GetColorWidget()

        self.alphaslider = TransparencySlider(Qt.Horizontal)
        self.alphaslider.valueChanged.connect(
            lambda i: self.colorselector.set_alpha(i / 100)
        )
        self.alphaslider.setValue(50)

        self.linewidthslider = LineWidthSlider(Qt.Horizontal)
        self.linewidthslider.valueChanged.connect(
            lambda i: self.colorselector.set_linewidth(i / 10)
        )
        self.linewidthslider.setValue(20)

        self.save_button = SaveButton("Save 999 Polygons")
        self.save_button.setMaximumSize(self.save_button.sizeHint())
        self.save_button.clicked.connect(self.save_polygons)
        self.save_button.setVisible(False)

        self.remove_button = RemoveButton("Remove")
        self.remove_button.setMaximumSize(self.remove_button.sizeHint())
        self.remove_button.clicked.connect(self.remove_last_poly)
        self.remove_button.setVisible(False)

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

        self._new_poly()

    def set_layer(self, layer):
        self.new_poly.set_layer(layer)

    def _on_new_poly(self):
        npoly = len(self.new_poly.gdf)
        if npoly > 0:
            self.save_button.setVisible(True)
            self.remove_button.setVisible(True)
        else:
            self.save_button.setVisible(False)
            self.remove_button.setVisible(False)

        if npoly == 1:
            txt = f"Save {len(self.new_poly.gdf)} Polygon"
        else:
            txt = f"Save {len(self.new_poly.gdf)} Polygons"

        self.save_button.setText(txt)

        self.window().show()

    def _new_poly(self, save_path=None):
        self.save_path = save_path
        self.new_poly = self.m.util.draw.new_poly(savepath=self.save_path)
        self.save_button.setVisible(False)
        self.remove_button.setVisible(False)

        self.new_poly.on_new_poly.append(self._on_new_poly)

    def remove_last_poly(self):
        if len(self.new_poly.gdf) == 0:
            return

        ID = self.new_poly.gdf.index[-1]
        a = self.new_poly._artists.pop(ID)
        self.m.BM.remove_bg_artist(a)
        a.remove()

        self.new_poly.gdf = self.new_poly.gdf.drop(ID)
        self.m.redraw()

        # update button text and visibility (same as if a new poly was created)
        self._on_new_poly()

    def save_polygons(self):
        save_path, widget = QtWidgets.QFileDialog.getSaveFileName(
            caption="Save Shapes", directory="shapes.shp", filter="Shapefiles (*.shp)"
        )
        if save_path is not None and len(save_path) > 0:
            self.new_poly.gdf.to_file(save_path)
            self._new_poly(self.save_path)

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

    def set_poly_type(self, s):
        self._use_poly_type = self._polynames[s]

    def draw_shape_callback(self, poly):
        def cb():
            self.window().hide()
            self.m.figure.f.canvas.show()
            self.m.figure.f.canvas.setFocus()

            getattr(self.new_poly, poly)(
                facecolor=self.colorselector.facecolor.getRgbF(),
                edgecolor=self.colorselector.edgecolor.getRgbF(),
                linewidth=self.linewidthslider.alpha * 10,
            )

        return cb

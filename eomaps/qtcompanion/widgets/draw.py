from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from .utils import GetColorWidget, AlphaSlider


class DrawerWidget(QtWidgets.QWidget):

    _polynames = {
        "Polygon": "polygon",
        "Rectangle": "rectangle",
        "Circle": "circle",
    }

    def __init__(self, m=None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.m = m
        self.new_poly = self.m.util.draw.new_poly()
        self.shapeselector = QtWidgets.QComboBox()

        self.shapeselector.setMinimumWidth(50)
        self.shapeselector.setMaximumWidth(200)

        names = list(self._polynames)
        self._use_poly_type = self._polynames[names[0]]
        for key in names:
            self.shapeselector.addItem(key)
        self.shapeselector.activated[str].connect(self.set_poly_type)

        b1 = QtWidgets.QPushButton("Draw!")
        b1.clicked.connect(self.draw_shape_callback)

        self.colorselector = GetColorWidget()

        self.alphaslider = AlphaSlider(Qt.Horizontal)
        self.alphaslider.valueChanged.connect(
            lambda i: self.colorselector.set_alpha(i / 100)
        )
        self.alphaslider.setValue(100)

        self.linewidthslider = AlphaSlider(Qt.Horizontal)
        self.linewidthslider.valueChanged.connect(
            lambda i: self.colorselector.set_linewidth(i / 10)
        )
        self.linewidthslider.setValue(20)

        layout = QtWidgets.QGridLayout()

        layout.addWidget(self.colorselector, 0, 0, 2, 1)
        layout.addWidget(self.alphaslider, 0, 1)
        layout.addWidget(self.linewidthslider, 1, 1)

        layout.addWidget(self.shapeselector, 0, 2)
        layout.addWidget(b1, 1, 2)

        layout.setAlignment(Qt.AlignCenter)
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

    def set_poly_type(self, s):
        self._use_poly_type = self._polynames[s]

    def draw_shape_callback(self):
        self.window().hide()
        self.m.figure.f.canvas.show()
        self.m.figure.f.canvas.setFocus()

        getattr(self.new_poly, self._use_poly_type)(
            facecolor=self.colorselector.facecolor.getRgbF(),
            edgecolor=self.colorselector.edgecolor.getRgbF(),
            # alpha=self.alphaslider.alpha,
            linewidth=self.linewidthslider.alpha * 10,
        )

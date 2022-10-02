from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from .utils import GetColorWidget, AlphaSlider


class DrawerWidget(QtWidgets.QWidget):

    _polynames = {
        "Polygon": "polygon",
        "Rectangle": "rectangle",
        "Circle": "circle",
    }

    def __init__(self, parent=None):

        super().__init__()

        self.parent = parent

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

    def set_poly_type(self, s):
        self._use_poly_type = self._polynames[s]

    def draw_shape_callback(self):

        p = self.m.util.draw.new_poly()
        getattr(p, self._use_poly_type)(
            facecolor=self.colorselector.facecolor.name(),
            edgecolor=self.colorselector.edgecolor.name(),
            alpha=self.alphaslider.alpha,
            linewidth=self.linewidthslider.alpha * 10,
        )

    @property
    def m(self):
        return self.parent.m

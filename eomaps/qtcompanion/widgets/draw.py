from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt

from .utils import GetColorWidget, AlphaSlider
from .editor import AddAnnotationInput


class DrawerWidget(QtWidgets.QWidget):

    _polynames = {
        "Polygon": "polygon",
        "Rectangle": "rectangle",
        "Circle": "circle",
    }

    def __init__(self, m=None, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.m = m
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
        self.alphaslider.setValue(50)

        self.linewidthslider = AlphaSlider(Qt.Horizontal)
        self.linewidthslider.valueChanged.connect(
            lambda i: self.colorselector.set_linewidth(i / 10)
        )
        self.linewidthslider.setValue(20)

        self.savepath_label = QtWidgets.QLabel()
        self.savepath_button = QtWidgets.QPushButton("Set Savepath")
        self.savepath_button.clicked.connect(self.set_savepath)
        self.savepath_clear_button = QtWidgets.QToolButton()
        self.savepath_clear_button.setText("x")
        self.savepath_clear_button.clicked.connect(self.clear_savepath)

        savepath_layout = QtWidgets.QHBoxLayout()
        savepath_layout.addWidget(self.savepath_button)
        savepath_layout.addWidget(self.savepath_clear_button)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.colorselector, 0, 0, 2, 1)
        layout.addWidget(self.alphaslider, 0, 1)
        layout.addWidget(self.linewidthslider, 1, 1)
        layout.addWidget(self.shapeselector, 0, 2)
        layout.addWidget(b1, 1, 2)
        layout.addLayout(savepath_layout, 2, 0)
        layout.addWidget(self.savepath_label, 2, 1, 1, 2)

        layout.setAlignment(Qt.AlignCenter)
        self.setLayout(layout)

        self.new_poly = self.m.util.draw.new_poly()

    def set_savepath(self):
        save_path, widget = QtWidgets.QFileDialog.getSaveFileName(
            caption="Save Shapes", directory="shapes.shp", filter="Shapefiles (*.shp)"
        )
        if len(save_path) > 0:
            self.save_path = save_path
            self.new_poly = self.m.util.draw.new_poly(savepath=self.save_path)
            self.savepath_label.setText(
                "<b>Shapefiles are saved to:</b><br>" + save_path
            )

    def clear_savepath(self):
        self.save_path = None
        self.new_poly = self.m.util.draw.new_poly()
        self.savepath_label.setText("")

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

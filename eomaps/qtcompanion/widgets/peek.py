from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QSize, pyqtSlot

from .layer import AutoUpdatePeekLayerDropdown, AutoUpdateLayerMenuButton
from ..common import iconpath

peek_methods = (
    "top",
    "bottom",
    "left",
    "right",
    "rectangle",
    "square",
    "circle",
    "ellipse",
)
peek_icons = dict()
for method in peek_methods:
    peek_icons[method] = QtGui.QIcon(str(iconpath / f"peek_{method}.png"))
    peek_icons[method + "_active"] = QtGui.QIcon(
        str(iconpath / f"peek_{method}_active.png")
    )


class RectangleSlider(QtWidgets.QSlider):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Peek-Rectangle Size</h3> Set the size of the peek-rectangle.",
            )


class TransparencySlider(QtWidgets.QSlider):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Peek-Overlay Transparency</h3>"
                "Set the transparency of the peek-overlay.",
            )


class ButtonWidget(QtWidgets.QWidget):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Peek-Method</h3>"
                "Set the method that is used to overlay the peek-layer."
                "<ul>"
                "<li><b>up/down/left/right:</b> show the layer from the map-boundary to the "
                "mouse-position</li>"
                "<li><b>rectangle:</b> show a rectangular region of the layer centered "
                "at the mouse-position. <br>"
                "(click twice to toggle between using a rectangular or square region!)"
                "</li></ul>",
            )


class PeekMethodButtons(QtWidgets.QWidget):
    methodChanged = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._method = "?"
        self.rectangle_size = 1
        self.how = (self.rectangle_size, self.rectangle_size)
        self.alpha = 1
        self.shape = "rectangular"

        self.buttons = dict()
        self.rect_button = (
            QtWidgets.QStackedWidget()
        )  # stacked buttons for rectangle/square
        self.round_button = (
            QtWidgets.QStackedWidget()
        )  # stacked buttons for ellipse/circle

        for method in peek_methods:
            b = QtWidgets.QToolButton()
            b.setIcon(peek_icons[method])
            b.setIconSize(QSize(12, 12))
            b.setAutoRaise(True)
            b.clicked.connect(self.button_clicked(method))
            self.buttons[method] = b

            if method in ("rectangle", "square"):
                self.rect_button.addWidget(b)

            if method in ("ellipse", "circle"):
                self.round_button.addWidget(b)

        self.rectangle_slider = RectangleSlider(Qt.Horizontal)
        self.rectangle_slider.valueChanged.connect(self.rectangle_sider_value_changed)
        self.rectangle_slider.setRange(2, 100)
        self.rectangle_slider.setSingleStep(1)
        self.rectangle_slider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.rectangle_slider.setValue(50)
        self.rectangle_slider.setMinimumWidth(50)
        sp = self.rectangle_slider.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.rectangle_slider.setSizePolicy(sp)
        self.set_rectangle_slider_stylesheet()

        self.alphaslider = TransparencySlider(Qt.Horizontal)
        self.alphaslider.valueChanged.connect(self.alpha_changed)
        self.alphaslider.setRange(0, 100)
        self.alphaslider.setSingleStep(1)
        self.alphaslider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.alphaslider.setValue(100)
        self.alphaslider.setMinimumWidth(50)

        # -------------------------

        buttonlayout = QtWidgets.QHBoxLayout()
        buttonlayout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        buttonlayout.addWidget(self.buttons["top"])
        buttonlayout.addWidget(self.buttons["bottom"])
        buttonlayout.addWidget(self.buttons["right"])
        buttonlayout.addWidget(self.buttons["left"])
        buttonlayout.addWidget(self.rect_button)
        buttonlayout.addWidget(self.round_button)

        buttons = ButtonWidget()
        buttons.setLayout(buttonlayout)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(buttons)
        layout.addWidget(self.rectangle_slider)
        layout.addWidget(self.alphaslider)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignCenter)

        self.setLayout(layout)

        self.methodChanged.connect(self.method_changed)

        self.methodChanged.emit("square")
        self.rect_button.setCurrentWidget(self.buttons["square"])
        self.round_button.setCurrentWidget(self.buttons["circle"])

    def button_clicked(self, method):
        @pyqtSlot()
        def cb():
            if method == "square":
                if self._method == "square":
                    m = "rectangle"
                    self.rect_button.setCurrentWidget(self.buttons["rectangle"])
                else:
                    m = method
                    self.rect_button.setCurrentWidget(self.buttons[method])
            elif method == "rectangle":
                if self._method == "rectangle":
                    m = "square"
                    self.rect_button.setCurrentWidget(self.buttons["square"])
                else:
                    m = method
                    self.rect_button.setCurrentWidget(self.buttons[method])
            elif method == "circle":
                if self._method == "circle":
                    m = "ellipse"
                    self.round_button.setCurrentWidget(self.buttons["ellipse"])
                else:
                    m = method
                    self.round_button.setCurrentWidget(self.buttons[method])
            elif method == "ellipse":
                if self._method == "ellipse":
                    m = "circle"
                    self.round_button.setCurrentWidget(self.buttons["circle"])
                else:
                    m = method
                    self.round_button.setCurrentWidget(self.buttons[method])

            else:
                m = method
            self.methodChanged.emit(m)

        return cb

    @pyqtSlot(int)
    def rectangle_sider_value_changed(self, i):
        self.rectangle_size = i / 100
        if self._method in ["rectangle", "square", "circle", "ellipse"]:
            self.methodChanged.emit(self._method)
        else:
            self.methodChanged.emit("rectangle")

        self.set_rectangle_slider_stylesheet()

    def set_rectangle_slider_stylesheet(self):
        s = 5 + self.rectangle_size * 15
        border = (
            "2px solid black"
            if self.rectangle_size < 0.99
            else "2px solid rgb(200,200,200)"
        )

        self.rectangle_slider.setStyleSheet(
            f"""
            QSlider::handle:horizontal {{
                background-color: rgb(200,200,200);
                border: {border};
                height: {s}px;
                width: {s}px;
                margin: -{s/2}px 0;
                padding: -{s/2}px 0px;
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

    def set_alpha_slider_stylesheet(self):
        a = self.alpha * 255
        s = 12
        self.alphaslider.setStyleSheet(
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

    @pyqtSlot(int)
    def alpha_changed(self, i):
        self.alpha = i / 100
        self.methodChanged.emit(self._method)
        self.set_alpha_slider_stylesheet()

    @pyqtSlot(str)
    def method_changed(self, method):
        self._method = method

        for key, val in self.buttons.items():
            if key == method:
                val.setIcon(peek_icons[f"{key}_active"])
            else:
                val.setIcon(peek_icons[f"{key}"])

        if method == "rectangle":
            self.shape = "rectangular"
            self.rectangle_slider.show()
            if self.rectangle_size < 0.99:
                self.how = (self.rectangle_size, self.rectangle_size)
            else:
                self.how = "full"
        elif method == "square":
            self.shape = "rectangular"
            self.rectangle_slider.show()
            if self.rectangle_size < 0.99:
                self.how = self.rectangle_size
            else:
                self.how = "full"

        elif method == "ellipse":
            self.rectangle_slider.show()
            if self.rectangle_size < 0.99:
                self.how = (self.rectangle_size, self.rectangle_size)
                self.shape = "round"
            else:
                self.how = "full"
                self.shape = "rectangular"

        elif method == "circle":
            self.rectangle_slider.show()
            if self.rectangle_size < 0.99:
                self.how = self.rectangle_size
                self.shape = "round"
            else:
                self.how = "full"
                self.shape = "rectangular"

        else:
            self.rectangle_slider.hide()
            self.how = method


class ModifierInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Peek Layer Modifier</h3>"
                "Assign a keyboard-modifier to the peek-callback. "
                "If used, the peek-callback will <b>only</b> be executed if the "
                "corresponding button is pressed on the keyboard!",
            )


class PeekLayerWidget(QtWidgets.QWidget):
    def __init__(
        self, *args, m=None, layers=None, exclude=None, how=(0.5, 0.5), **kwargs
    ):
        """
        A dropdown-list that attaches a peek-callback to look at the selected layer

        Parameters
        ----------
        layers : list or None, optional
            If a list is provided, only layers in the list will be used.
            Otherwise the available layers are fetched from the given Maps-object.
            The default is None.
        exclude : list, optional
            A list of layer-names to exclude. The default is None.

        Returns
        -------
        None.

        """
        super().__init__(*args, **kwargs)

        self.m = m
        self._layers = layers
        self._exclude = exclude

        self.cid = None
        self.current_layer = None

        self.layerselector = AutoUpdatePeekLayerDropdown(
            m=self.m, layers=layers, exclude=exclude
        )
        self.layerselector.update_layers()  # do this before attaching the callback!
        self.layerselector.currentIndexChanged[str].connect(self.set_layer_callback)
        self.layerselector.setMinimumWidth(100)

        self.buttons = PeekMethodButtons()
        self.buttons.methodChanged.connect(self.method_changed)

        modifier_label = QtWidgets.QLabel("Modifier:")
        self.modifier = ModifierInput()
        self.modifier.setMaximumWidth(50)
        self.modifier.textChanged.connect(self.method_changed)

        modifier_layout = QtWidgets.QVBoxLayout()
        modifier_layout.addWidget(modifier_label)
        modifier_layout.addWidget(self.modifier)
        modifier_layout.setAlignment(Qt.AlignLeft)
        modifier_widget = QtWidgets.QWidget()
        modifier_widget.setLayout(modifier_layout)

        label = QtWidgets.QLabel("<b>Peek Layer</b>:")
        width = label.fontMetrics().boundingRect(label.text()).width()
        label.setFixedWidth(width + 5)

        selectorlayout = QtWidgets.QVBoxLayout()
        selectorlayout.addWidget(label)
        selectorlayout.addWidget(self.layerselector)
        selectorlayout.setAlignment(Qt.AlignLeft)

        selectorwidget = QtWidgets.QWidget()
        selectorwidget.setLayout(selectorlayout)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(selectorwidget, 0, Qt.AlignLeft)
        layout.addWidget(modifier_widget, 0, Qt.AlignLeft)
        layout.addWidget(self.buttons)
        layout.setAlignment(Qt.AlignLeft)

        self.setLayout(layout)

    @pyqtSlot(str)
    def set_layer_callback(self, l):
        self.remove_peek_cb()
        if self.cid is not None:
            self.current_layer = None

        if l == "":
            self.current_layer = None
            return

        modifier = self.modifier.text().strip()
        if modifier == "":
            modifier = None

        self.cid = self.m.all.cb.click.attach.peek_layer(
            layer=l,
            how=self.buttons.how,
            alpha=self.buttons.alpha,
            modifier=modifier,
            shape=self.buttons.shape,
        )
        self.current_layer = l

    @pyqtSlot(str)
    def method_changed(self, method):
        self.add_peek_cb()

    def add_peek_cb(self):
        if self.current_layer is None:
            return

        self.remove_peek_cb()

        modifier = self.modifier.text()
        if modifier == "":
            modifier = None

        self.cid = self.m.all.cb.click.attach.peek_layer(
            layer=self.current_layer,
            how=self.buttons.how,
            alpha=self.buttons.alpha,
            modifier=modifier,
            shape=self.buttons.shape,
        )

    def remove_peek_cb(self):
        if self.cid is not None:
            if self.cid in self.m.all.cb.click.get.attached_callbacks:
                self.m.all.cb.click.remove(self.cid)
            self.cid = None


# make sure tabs are never larger than 150px
class TabBar(QtWidgets.QTabBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # remove strange line on top of tabs
        # (see https://stackoverflow.com/a/33941638/9703451)
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setElideMode(Qt.ElideRight)

    def tabSizeHint(self, index):
        size = QtWidgets.QTabBar.tabSizeHint(self, index)
        return QSize(min(size.width(), 150), size.height())


class PeekTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        self.setTabBar(TabBar())

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_handler)

        w = PeekLayerWidget(m=self.m)
        self.addTab(w, peek_icons[w.buttons._method], "    ")
        self.setIconSize(QSize(10, 10))
        # update the tab title with the modifier key
        cb = self.settxt_factory(w)
        w.modifier.textChanged.connect(cb)
        w.buttons.methodChanged.connect(cb)
        w.layerselector.currentIndexChanged[str].connect(cb)

        # emit pyqtSignal to set text
        w.buttons.methodChanged.emit(w.buttons._method)

        # a tab that is used to create new tabs
        newtabwidget = QtWidgets.QWidget()
        newtablayout = QtWidgets.QHBoxLayout()
        l = QtWidgets.QLabel("Click on <b>+</b> to open a new peek layer tab!")
        newtablayout.addWidget(l)
        newtabwidget.setLayout(newtablayout)

        self.addTab(newtabwidget, "+")
        # don't show the close button for this tab
        self.tabBar().setTabButton(self.count() - 1, self.tabBar().RightSide, None)

        self.tabBarClicked.connect(self.tabbar_clicked)
        self.setCurrentIndex(0)

    def setTabText(self, index, tip):
        # set ToolTip as well wenn setting the TabText
        super().setTabText(index, tip)
        self.setTabToolTip(index, tip)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Peek Layer Tabs</h3>"
                "Each tab represents a peek-layer callback for the map. "
                "Click on the '+' to create a new tab. "
                "The tabs can be used to specify multiple peek callbacks "
                "to quickly compare several different layers."
                "<p>"
                "Assign <b>modifiers</b> to the individual peek-callbacks to "
                "switch between the peek-callbacks by holding the corresponding keys"
                "on the keyboard.",
            )

    @pyqtSlot(int)
    def tabbar_clicked(self, index):
        if self.tabText(index) == "+":
            w = PeekLayerWidget(m=self.m)
            self.insertTab(self.count() - 1, w, "    ")

            # update the tab title with the modifier key
            cb = self.settxt_factory(w)
            w.modifier.textChanged.connect(cb)
            w.buttons.methodChanged.connect(cb)
            w.layerselector.currentIndexChanged[str].connect(cb)
            # emit pyqtSignal to set text
            w.buttons.methodChanged.emit(w.buttons._method)

    @pyqtSlot(int)
    def close_handler(self, index):
        curridx = self.currentIndex()
        self.widget(index).remove_peek_cb()
        self.removeTab(index)
        if index == curridx:
            self.setCurrentIndex(index - 1)

    def settxt_factory(self, w):
        @pyqtSlot()
        def settxt():
            self.setTabIcon(self.indexOf(w), peek_icons[w.buttons._method])
            mod = w.modifier.text().strip()

            txt = ""
            if mod != "":
                txt += f"[{mod}] "

            tabtext = txt + (w.current_layer if w.current_layer is not None else "")

            self.setTabText(self.indexOf(w), tabtext)

        return settxt

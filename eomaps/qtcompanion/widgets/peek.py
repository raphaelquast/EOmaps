from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal

from .layer import AutoUpdateLayerDropdown, AutoUpdateLayerMenuButton


class PeekMethodButtons(QtWidgets.QWidget):
    methodChanged = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._method = "?"
        self.rectangle_size = 1
        self.how = (self.rectangle_size, self.rectangle_size)
        self.alpha = 1

        self.symbols = dict(
            zip(
                ("🡇", "🡅", "🡆", "🡄", "⛋", "🞑"),
                ("top", "bottom", "left", "right", "rectangle", "square"),
            )
        )

        self.symbols_inverted = {v: k for k, v in self.symbols.items()}

        self.buttons = dict()
        for symbol, method in self.symbols.items():
            b = QtWidgets.QToolButton()
            b.setText(symbol)
            b.setAutoRaise(True)
            b.clicked.connect(self.button_clicked)

            self.buttons[method] = b

        self.slider = QtWidgets.QSlider(Qt.Horizontal)
        self.slider.valueChanged.connect(self.sider_value_changed)
        self.slider.setToolTip("Set rectangle size")
        self.slider.setRange(0, 100)
        self.slider.setSingleStep(1)
        self.slider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.slider.setValue(50)
        self.slider.setMinimumWidth(50)

        self.alphaslider = QtWidgets.QSlider(Qt.Horizontal)
        self.alphaslider.valueChanged.connect(self.alpha_changed)
        self.alphaslider.setToolTip("Set transparency")
        self.alphaslider.setRange(0, 100)
        self.alphaslider.setSingleStep(1)
        self.alphaslider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.alphaslider.setValue(100)
        self.alphaslider.setMinimumWidth(50)

        # -------------------------

        buttons = QtWidgets.QHBoxLayout()
        buttons.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        buttons.addWidget(self.buttons["top"])
        buttons.addWidget(self.buttons["bottom"])
        buttons.addWidget(self.buttons["right"])
        buttons.addWidget(self.buttons["left"])
        buttons.addWidget(self.buttons["rectangle"])
        buttons.addWidget(self.slider, 1)

        layout = QtWidgets.QVBoxLayout()
        layout.addLayout(buttons)
        layout.addWidget(self.alphaslider)

        self.setLayout(layout)

        self.methodChanged.connect(self.method_changed)

        self.methodChanged.emit("square")
        self.buttons["rectangle"].setText(self.symbols_inverted["square"])

    def button_clicked(self):

        sender = self.sender().text()
        if self._method in ["rectangle", "square"]:
            if sender == self.symbols_inverted["square"]:
                method = "rectangle"
                self.buttons["rectangle"].setText(self.symbols_inverted["rectangle"])
            elif sender == self.symbols_inverted["rectangle"]:
                method = "square"
                self.buttons["rectangle"].setText(self.symbols_inverted["square"])
            else:
                method = self.symbols[sender]

        else:
            method = self.symbols[sender]

        self.methodChanged.emit(method)

    def sider_value_changed(self, i):
        self.rectangle_size = i / 100
        if self._method in ["rectangle", "square"]:
            self.methodChanged.emit(self._method)
        else:
            self.methodChanged.emit("rectangle")

    def alpha_changed(self, i):
        self.alpha = i / 100
        self.methodChanged.emit(self._method)

    def method_changed(self, method):
        self._method = method

        for key, val in self.buttons.items():
            if key == method:
                val.setStyleSheet("QToolButton {color: red; }")
            else:
                val.setStyleSheet("")

        if method == "square":
            self.buttons["rectangle"].setStyleSheet("QToolButton {color: red; }")

        if method == "rectangle":
            if self.rectangle_size < 0.99:
                self.how = (self.rectangle_size, self.rectangle_size)
            else:
                self.how = "full"
        elif method == "square":
            if self.rectangle_size < 0.99:
                self.how = self.rectangle_size
            else:
                self.how = "full"
        else:
            self.how = method


class PeekLayerWidget(QtWidgets.QWidget):
    def __init__(
        self, *args, parent=None, layers=None, exclude=None, how=(0.5, 0.5), **kwargs
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

        self.parent = parent
        self._layers = layers
        self._exclude = exclude

        self.cid = None
        self.current_layer = None

        self.layerselector = AutoUpdateLayerDropdown(
            m=self.m, layers=layers, exclude=exclude
        )
        self.layerselector.update_layers()  # do this before attaching the callback!
        self.layerselector.currentIndexChanged[str].connect(self.set_layer_callback)
        self.layerselector.setMinimumWidth(100)

        self.buttons = PeekMethodButtons()
        self.buttons.methodChanged.connect(self.method_changed)

        modifier_label = QtWidgets.QLabel("Modifier:")
        self.modifier = QtWidgets.QLineEdit()
        self.modifier.setMaximumWidth(50)
        self.modifier.textChanged.connect(self.method_changed)

        modifier_layout = QtWidgets.QHBoxLayout()
        modifier_layout.addWidget(modifier_label, 0, Qt.AlignLeft)
        modifier_layout.addWidget(self.modifier, 0, Qt.AlignLeft)
        modifier_widget = QtWidgets.QWidget()
        modifier_widget.setLayout(modifier_layout)

        label = QtWidgets.QLabel("<b>Peek Layer</b>:")
        width = label.fontMetrics().boundingRect(label.text()).width()
        label.setFixedWidth(width + 5)

        selectorlayout = QtWidgets.QVBoxLayout()
        selectorlayout.addWidget(label, 0, Qt.AlignTop)
        selectorlayout.addWidget(self.layerselector, 0, Qt.AlignCenter | Qt.AlignLeft)
        selectorlayout.addWidget(modifier_widget)
        selectorlayout.setAlignment(Qt.AlignTop)

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(selectorlayout)
        layout.addWidget(self.buttons)

        layout.setAlignment(Qt.AlignTop)

        self.setLayout(layout)

    @property
    def m(self):
        return self.parent.m

    def set_layer_callback(self, l):
        self.remove_peek_cb()
        if self.cid is not None:
            self.current_layer = None

        if l == "":
            return

        modifier = self.modifier.text().strip()
        if modifier == "":
            modifier = None

        self.cid = self.m.all.cb.click.attach.peek_layer(
            l, how=self.buttons.how, alpha=self.buttons.alpha, modifier=modifier
        )
        self.current_layer = l

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
            self.current_layer,
            how=self.buttons.how,
            alpha=self.buttons.alpha,
            modifier=modifier,
        )

    def remove_peek_cb(self):
        if self.cid is not None:
            self.m.all.cb.click.remove(self.cid)
            self.cid = None


class PeekTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_handler)

        w = PeekLayerWidget(parent=self.parent)
        self.addTab(w, "    ")

        # update the tab title with the modifier key
        cb = self.settxt_factory(w)
        w.modifier.textChanged.connect(cb)
        w.buttons.methodChanged.connect(cb)
        w.layerselector.currentIndexChanged[str].connect(cb)

        # emit pyqtSignal to set text
        w.buttons.methodChanged.emit(w.buttons._method)

        # a tab that is used to create new tabs
        self.addTab(QtWidgets.QWidget(), "+")
        # don't show the close button for this tab
        self.tabBar().setTabButton(self.count() - 1, self.tabBar().RightSide, None)

        self.tabBarClicked.connect(self.tabbar_clicked)

        self.setCurrentIndex(0)

    def tabbar_clicked(self, index):
        if self.tabText(index) == "+":
            w = PeekLayerWidget(parent=self.parent)
            self.insertTab(self.count() - 1, w, "    ")

            # update the tab title with the modifier key
            cb = self.settxt_factory(w)
            w.modifier.textChanged.connect(cb)
            w.buttons.methodChanged.connect(cb)
            w.layerselector.currentIndexChanged[str].connect(cb)
            # emit pyqtSignal to set text
            w.buttons.methodChanged.emit(w.buttons._method)

    def close_handler(self, index):
        self.widget(index).remove_peek_cb()
        self.removeTab(index)

    def settxt_factory(self, w):
        def settxt():
            self.setTabText(
                self.indexOf(w),
                w.buttons.symbols_inverted.get(w.buttons._method, "")
                + (
                    (" [" + w.modifier.text() + "]: ")
                    if w.modifier.text().strip() != ""
                    else ": "
                )
                + (w.current_layer if w.current_layer is not None else ""),
            )

        return settxt

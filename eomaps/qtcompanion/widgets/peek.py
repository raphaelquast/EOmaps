from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, QSize

from .layer import AutoUpdateLayerDropdown, AutoUpdateLayerMenuButton
from ..common import iconpath

peek_methods = ("top", "bottom", "left", "right", "rectangle", "square")
peek_icons = dict()
for method in peek_methods:
    peek_icons[method] = QtGui.QIcon(str(iconpath / f"peek_{method}.png"))
    peek_icons[method + "_active"] = QtGui.QIcon(
        str(iconpath / f"peek_{method}_active.png")
    )


class PeekMethodButtons(QtWidgets.QWidget):
    methodChanged = pyqtSignal(str)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._method = "?"
        self.rectangle_size = 1
        self.how = (self.rectangle_size, self.rectangle_size)
        self.alpha = 1

        self.buttons = dict()
        self.rect_button = (
            QtWidgets.QStackedWidget()
        )  # stacked buttons for rectangle/square
        for method in peek_methods:
            b = QtWidgets.QToolButton()
            b.setIcon(peek_icons[method])
            b.setIconSize(QSize(12, 12))
            b.setAutoRaise(True)
            b.clicked.connect(self.button_clicked(method))
            self.buttons[method] = b

            if method in ("rectangle", "square"):
                self.rect_button.addWidget(b)

        self.rectangle_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.rectangle_slider.valueChanged.connect(self.rectangle_sider_value_changed)
        self.rectangle_slider.setToolTip("Rectangle size")
        self.rectangle_slider.setRange(2, 100)
        self.rectangle_slider.setSingleStep(1)
        self.rectangle_slider.setTickPosition(QtWidgets.QSlider.NoTicks)
        self.rectangle_slider.setValue(50)
        self.rectangle_slider.setMinimumWidth(50)
        sp = self.rectangle_slider.sizePolicy()
        sp.setRetainSizeWhenHidden(True)
        self.rectangle_slider.setSizePolicy(sp)
        self.set_rectangle_slider_stylesheet()

        self.alphaslider = QtWidgets.QSlider(Qt.Horizontal)
        self.alphaslider.valueChanged.connect(self.alpha_changed)
        self.alphaslider.setToolTip("Overlay transparency")
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
        buttons.addWidget(self.rect_button)
        buttons.addWidget(self.rectangle_slider, 1)

        layout = QtWidgets.QVBoxLayout()

        layout.addLayout(buttons)
        layout.addWidget(self.alphaslider)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignCenter)

        self.setLayout(layout)

        self.methodChanged.connect(self.method_changed)

        self.methodChanged.emit("square")
        self.rect_button.setCurrentWidget(self.buttons["square"])

        # self.buttons["rectangle"].setText(self.symbols_inverted["square"])

    def button_clicked(self, method):
        def cb():
            if method == "square":
                m = "rectangle"
                self.rect_button.setCurrentWidget(self.buttons["rectangle"])
            elif method == "rectangle":
                m = "square"
                self.rect_button.setCurrentWidget(self.buttons["square"])
            else:
                m = method
            self.methodChanged.emit(m)

        return cb

    def rectangle_sider_value_changed(self, i):
        self.rectangle_size = i / 100
        if self._method in ["rectangle", "square"]:
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

    def alpha_changed(self, i):
        self.alpha = i / 100
        self.methodChanged.emit(self._method)
        self.set_alpha_slider_stylesheet()

    def method_changed(self, method):
        self._method = method

        for key, val in self.buttons.items():
            if key == method:
                val.setIcon(peek_icons[f"{key}_active"])
            else:
                val.setIcon(peek_icons[f"{key}"])

        if method == "rectangle":
            self.rectangle_slider.show()
            if self.rectangle_size < 0.99:
                self.how = (self.rectangle_size, self.rectangle_size)
            else:
                self.how = "full"
        elif method == "square":
            self.rectangle_slider.show()
            if self.rectangle_size < 0.99:
                self.how = self.rectangle_size
            else:
                self.how = "full"
        else:
            self.rectangle_slider.hide()
            self.how = method


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

        selectorwidget = QtWidgets.QWidget()
        selectorwidget.setLayout(selectorlayout)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(selectorwidget)
        layout.addWidget(self.buttons)

        layout.setAlignment(Qt.AlignCenter | Qt.AlignLeft)

        self.setLayout(layout)

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
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

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

    def close_handler(self, index):
        curridx = self.currentIndex()
        self.widget(index).remove_peek_cb()
        self.removeTab(index)
        if index == curridx:
            self.setCurrentIndex(index - 1)

    def settxt_factory(self, w):
        def settxt():
            self.setTabIcon(self.indexOf(w), peek_icons[w.buttons._method])
            mod = w.modifier.text().strip()

            txt = ""
            if mod != "":
                txt += f"[{mod}] "

            self.setTabText(
                self.indexOf(w),
                txt + (w.current_layer if w.current_layer is not None else ""),
            )

        return settxt

from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot


class AutoUpdatePeekLayerDropdown(QtWidgets.QComboBox):
    def __init__(
        self,
        *args,
        m=None,
        layers=None,
        exclude=None,
        use_active=False,
        empty_ok=True,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.m = m
        self._layers = layers
        self._exclude = exclude
        self._use_active = use_active
        self._empty_ok = empty_ok

        self.last_layers = []

        self._last_active = None

        self.update_layers()

        self.setSizeAdjustPolicy(self.AdjustToMinimumContentsLengthWithIcon)

        self.activated.connect(self.set_last_active)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Peek Layer</h3>"
                "Select a layer to peek on."
                "<p>"
                "An overlay of the selected layer will be printed on top of the "
                "currently visible layer. The controls on the side can be used to "
                "select the peek-method as well as the transparency of the overlay.",
            )

    @pyqtSlot()
    def set_last_active(self):
        self._last_active = self.currentText()

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.update_layers()
        elif event.button() == Qt.LeftButton:
            self.update_layers()

        super().mousePressEvent(event)

    @property
    def layers(self):
        if self._layers is not None:
            return self._layers
        else:
            return [
                i
                for i in self.m._get_layers(exclude=self._exclude)
                if not str(i).startswith("_")
            ]

    def update_layers(self):
        layers = self.layers
        if set(layers) == set(self.last_layers):
            return

        self.last_layers = layers
        self.clear()

        if self._empty_ok:
            self.addItem("")

        # the QAbstractItemView object that holds the dropdown-items
        view = self.view()
        view.setTextElideMode(Qt.ElideNone)

        for key in layers:
            self.addItem(str(key))
        # set the size of the dropdown to be 10 + the longest item
        view.setFixedWidth(view.sizeHintForColumn(0) + 10)

        if self._use_active:
            # set current index to active layer if _use_active
            currindex = self.findText(str(self.m.BM.bg_layer))
            self.setCurrentIndex(currindex)
        elif self._last_active is not None:
            # set current index to last active layer otherwise
            idx = self.findText(self._last_active)
            if idx != -1:
                self.setCurrentIndex(idx)


class AutoUpdateLayerMenuButton(QtWidgets.QPushButton):
    def __init__(self, *args, m=None, layers=None, exclude=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m
        self._layers = layers
        self._exclude = exclude

        self._last_layers = []

        menu = QtWidgets.QMenu()
        menu.aboutToShow.connect(self.update_layers)
        self.setMenu(menu)

        # update layers on every change of the Maps-object background layer
        self.m.BM.on_layer(self.update_visible_layer, persistent=True)
        # update layers before the widget is shown to make sure they always
        # represent the currently visible layers on startup of the widget
        # (since "update_visible_layer" only triggers if the widget is actually visible)
        self.m._on_show_companion_widget.append(self.update_visible_layer)
        self.update_layers()

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Visible Layer</h3>"
                "Get a dropdown-list of all currently available map-layers."
                "<p>"
                "<ul>"
                "<li><b>click</b> to switch to the selected layer</li>"
                "<li><b>control+click</b> to overlay multiple layers</li>"
                "</ul>"
                "NOTE: The order at which you select layers will determine "
                "the 'stacking' of the layers! (the number [n] in front "
                " of the layer-name indicates the stack-order of the layer.",
            )

    def get_uselayer(self):
        active_layers = []
        for a in self.menu().actions():
            w = a.defaultWidget()

            if isinstance(w, QtWidgets.QCheckBox) and w.isChecked():
                active_layers.append(a.data())

        uselayer = "???"

        if len(active_layers) > 1:
            uselayer = "|".join(active_layers)
        elif len(active_layers) == 1:
            uselayer = active_layers[0]

        return uselayer

    def mousePressEvent(self, event):
        if event.button() == Qt.RightButton:
            self.update_layers()
        elif event.button() == Qt.LeftButton:
            self.update_layers()

        super().mousePressEvent(event)

    @property
    def layers(self):
        if self._layers is not None:
            return self._layers
        else:
            return [
                i
                for i in self.m._get_layers(exclude=self._exclude)
                if not str(i).startswith("_")
            ]

    def update_display_text(self, l):
        # make sure that we don't use too long labels as text
        if len(l) > 50:
            l = f"{len([1 for i in l.split('|') if len(i) > 0])} layers visible"
            # txt = txt[:50] + " ..."

        if "{" in l:  # TODO support transparency
            l = "custom :   " + l
            self.setStyleSheet("QPushButton{color: rgb(200,50,50)}")
        elif "|" in l:
            l = "multi :   " + l
            self.setStyleSheet("QPushButton{color: rgb(200,50,50)}")
        else:
            self.setStyleSheet("QPushButton{color: rgb(50,200,50)}")

        self.setText(l)

    def update_visible_layer(self, *args, **kwargs):
        if not self.isVisible():
            return
        # make sure to re-fetch layers first
        self.update_layers()
        self.update_display_text(self.m.BM._bg_layer)

    @pyqtSlot()
    def actionClicked(self):
        action = self.sender()
        if not isinstance(action, QtWidgets.QWidgetAction):
            # sometimes the sender is the button... ignore those events!
            return

        # check if a keyboard modifier is pressed
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        actionwidget = action.defaultWidget()

        checked_layers = [l for l in self.m.BM.bg_layer.split("|") if l != "_"]
        selected_layer = action.data()
        selected_layers = [l for l in action.data().split("|") if l != "_"]

        # if no relevant modifier is pressed, just select single layers!
        if not (modifiers == Qt.ShiftModifier or modifiers == Qt.ControlModifier):
            self.m.show_layer(selected_layer)
            return

        # if the "all" layer was selected, just select it and no other layer!
        # (workaround since we use a checkbox to avoid closing the menu on click)
        if selected_layer == "all" or "|" in selected_layer:
            if modifiers == Qt.ShiftModifier or modifiers == Qt.ControlModifier:
                self.update_checkstatus()
                return
            else:
                self.m.show_layer(selected_layer)
                return

        if isinstance(actionwidget, QtWidgets.QCheckBox):
            if actionwidget.isChecked():
                for l in selected_layers:
                    if l not in checked_layers:
                        checked_layers.append(l)
            else:
                for l in selected_layers:
                    if l in checked_layers and len(checked_layers) > 1:
                        checked_layers.remove(l)

            uselayer = "???"
            if len(checked_layers) > 1:
                uselayer = "|".join(checked_layers)
            elif len(checked_layers) == 1:
                uselayer = checked_layers[0]

            # collect all checked items and set the associated layer
            if uselayer != "???":
                self.m.show_layer(uselayer)
        else:
            self.m.show_layer(selected_layer)

    def update_checkstatus(self):
        currlayer = str(self.m.BM.bg_layer)

        if "{" in currlayer:  # TODO support transparency
            active_layers = []
        else:
            if "|" in currlayer:
                active_layers = [i for i in currlayer.split("|") if i != "_"]
                active_layers.append(currlayer)
            else:
                active_layers = [currlayer]

        for action in self.menu().actions():
            key = action.data()
            w = action.defaultWidget()
            if isinstance(w, QtWidgets.QCheckBox):
                # temporarily disconnect triggering the action on state-changes
                w.clicked.disconnect(action.trigger)
                if key in active_layers:
                    w.setChecked(True)
                    w.setText(f"[{active_layers.index(key)}]  {key}")
                else:
                    w.setChecked(False)
                    w.setText(key + "        ")  # add space for [n]

                # re connect action trigger
                w.clicked.connect(action.trigger)

    @pyqtSlot()
    def update_layers(self):
        layers = self.layers
        if layers == self._last_layers:
            self.update_checkstatus()
            return

        # only clear and re-draw the whole tabbar if it is necessary
        # (e.g. if the number of layers has changed)
        self.menu().clear()

        for key in layers:
            checkBox = QtWidgets.QCheckBox(key, self.menu())
            # checkBox.setCheckable(False)
            action = QtWidgets.QWidgetAction(self.menu())
            action.setDefaultWidget(checkBox)
            action.setText(key + "        ")
            action.setData(key)

            if key == "all":
                # use a transparent checkbox to avoid closing the menu on click
                checkBox.setStyleSheet(
                    "QCheckBox::indicator {border: none;}"
                    "QCheckBox::indicator::checked {background:rgb(255,50,50)}"
                )
            elif "|" in key:
                # use a transparent checkbox to avoid closing the menu on click
                checkBox.setStyleSheet(
                    "QCheckBox::indicator {border: none;}"
                    "QCheckBox::indicator::checked {background:rgb(50,100,50)}"
                )

            # connect the action of the checkbox to the action of the menu
            checkBox.clicked.connect(action.trigger)
            action.triggered.connect(self.actionClicked)
            self.menu().addAction(action)

            action.triggered.connect(self.menu().show)

        self.update_display_text(self.m.BM._bg_layer)

        self._last_layers = layers
        self.update_checkstatus()

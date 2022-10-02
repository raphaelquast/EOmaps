from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt


class AutoUpdateLayerDropdown(QtWidgets.QComboBox):
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

        # update layers on every change of the Maps-object background layer
        self.m.BM.on_layer(self.update_visible_layer, persistent=True)
        self.update_layers()

        self.setSizeAdjustPolicy(self.AdjustToContents)

        self.activated.connect(self.set_last_active)

    def set_last_active(self):
        self._last_active = self.currentText()

    def update_visible_layer(self, m, l):
        # make sure to re-fetch layers first
        self.update_layers()

        if self._use_active:
            # set current index to active layer if _use_active
            currindex = self.findText(l)
            self.setCurrentIndex(currindex)
        elif self._last_active is not None:
            # set current index to last active layer otherwise
            idx = self.findText(self._last_active)
            if idx != -1:
                self.setCurrentIndex(idx)

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

        for key in layers:
            self.addItem(str(key))

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

        self.checked_layers = []

        menu = QtWidgets.QMenu()
        menu.aboutToShow.connect(self.update_layers)
        self.setMenu(menu)

        # update layers on every change of the Maps-object background layer
        self.m.BM.on_layer(self.update_visible_layer, persistent=True)
        self.update_layers()

        self.setToolTip("Use (control + click) to select multiple layers!")

    def get_uselayer(self):
        active_layers = []
        for a in self.menu().actions():
            w = a.defaultWidget()

            if isinstance(w, QtWidgets.QCheckBox) and w.isChecked():
                active_layers.append(a.text())

        uselayer = "???"

        if len(active_layers) > 1:
            uselayer = "_|" + "|".join(active_layers)
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
        # TODO properly indicate temporary multi-layers
        txt = l.lstrip("_|")
        # make sure that we don't use too long labels as text
        if len(txt) > 50:
            txt = f"{len([1 for i in txt.split('|') if len(i) > 0])} layers visible"
            # txt = txt[:50] + " ..."

        if l.startswith("_"):
            txt = "⧉  " + txt
            self.setStyleSheet("QPushButton{color: rgb(200,50,50)}")
        else:
            self.setStyleSheet("QPushButton{color: rgb(50,200,50)}")

        self.setText(txt)

    def update_visible_layer(self, m, l):
        # make sure to re-fetch layers first
        self.update_layers()

        self.update_display_text(l)

        self.checked_layers = sorted([i for i in l.split("|") if i != "_"])

    def actionClicked(self):
        # check if a keyboard modifier is pressed
        modifiers = QtWidgets.QApplication.keyboardModifiers()

        action = self.sender()
        if not isinstance(action, QtWidgets.QWidgetAction):
            # sometimes the sender is the button... ignore those events!
            return

        actionwidget = action.defaultWidget()
        text = action.text()

        # if no relevant modifier is pressed, just select single layers!
        if not (modifiers == Qt.ShiftModifier or modifiers == Qt.ControlModifier):

            self.m.show_layer(text)
            self.checkorder = [text]
            return

        if isinstance(actionwidget, QtWidgets.QCheckBox):
            if actionwidget.isChecked():
                for l in (i for i in text.split("|") if i != "_"):
                    if l not in self.checked_layers:
                        self.checked_layers.append(l)
            else:
                if text in self.checked_layers:
                    self.checked_layers.remove(text)

            uselayer = "???"
            if len(self.checked_layers) > 1:
                uselayer = "_|" + "|".join(sorted(self.checked_layers))
            elif len(self.checked_layers) == 1:
                uselayer = self.checked_layers[0]

            # collect all checked items and set the associated layer
            if uselayer != "???":
                self.m.show_layer(uselayer)
        else:
            self.m.show_layer(text)
            self.checked_layers = []

    def update_checkstatus(self):
        currlayer = str(self.m.BM.bg_layer)
        if "|" in currlayer:
            active_layers = [i for i in currlayer.split("|") if i != "_"]
        else:
            active_layers = [currlayer]

        for action in self.menu().actions():
            key = action.text()
            w = action.defaultWidget()
            if isinstance(w, QtWidgets.QCheckBox):

                # temporarily disconnect triggering the action on state-changes
                w.stateChanged.disconnect(action.trigger)

                if key in active_layers:
                    w.setChecked(True)
                else:
                    w.setChecked(False)

                # re connect action trigger
                w.stateChanged.connect(action.trigger)

    def update_layers(self):
        layers = self.layers
        if layers == self._last_layers:
            self.update_checkstatus()

            return

        # only clear and re-draw the whole tabbar if it is necessary
        # (e.g. if the number of layers has changed)
        self.menu().clear()

        currlayer = str(self.m.BM.bg_layer)
        if "|" in currlayer:
            active_layers = [i for i in currlayer.split("|") if i != "_"]
        else:
            active_layers = [currlayer]

        for key in layers:
            if key == "all" or "|" in key:
                label = QtWidgets.QLabel(key)
                action = QtWidgets.QWidgetAction(self.menu())
                action.setDefaultWidget(label)
                action.setText(key)

                action.triggered.connect(self.actionClicked)
            else:
                checkBox = QtWidgets.QCheckBox(key, self.menu())
                action = QtWidgets.QWidgetAction(self.menu())
                action.setDefaultWidget(checkBox)
                action.setText(key)

                if key in active_layers:
                    checkBox.setChecked(True)
                else:
                    checkBox.setChecked(False)

                # connect the action of the checkbox to the action of the menu
                checkBox.stateChanged.connect(action.trigger)

                action.triggered.connect(self.actionClicked)

            self.menu().addAction(action)

        self.update_display_text(self.m.BM._bg_layer)

        self._last_layers = layers

# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

from qtpy import QtWidgets
from qtpy.QtCore import Qt, Slot
from ..common import iconpath
from qtpy import QtGui


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

    @Slot()
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
            if key == "all":
                continue
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


class AutoUpdateLayerLabel(QtWidgets.QLabel):
    def __init__(self, *args, m=None, max_length=60, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        self._max_length = max_length

        # update layers on every change of the Maps-object background layer
        self.m.BM.on_layer(self.update, persistent=True)
        self.setText(self.get_text())

        # turn text interaction off to "click through" the label
        self.setTextInteractionFlags(Qt.NoTextInteraction)

    def get_text(self):
        layers, alphas = self.m.BM._get_active_layers_alphas

        prefix = "&nbsp;&nbsp;&nbsp;&nbsp;" "<font color=gray>"
        suffix = "<\font>"

        s = ""
        for i, (l, a) in enumerate(zip(layers, alphas)):
            if len(s) > self._max_length:
                s = f"<b>( {len(layers)} layers visible )</b>"
                break

            if i > 0:
                s += "  |  "

            ls = f"<b>{l}</b>"
            if a < 1:
                ls += " {" + f"{a*100:.0f}%" + "}"

            s += ls

        if len(s) > self._max_length:
            s = s[: self._max_length - 3] + "..."

        return prefix + s + suffix

    def update(self, *args, **kwargs):
        self.setText(self.get_text())


class AutoUpdateLayerMenuButton(QtWidgets.QPushButton):
    def __init__(
        self, *args, m=None, layers=None, exclude=None, auto_text=False, **kwargs
    ):
        super().__init__(*args, **kwargs)

        self.m = m
        self._layers = layers
        self._exclude = exclude
        self._auto_text = auto_text

        self._last_layers = []

        menu = QtWidgets.QMenu()
        menu.setStyleSheet("QMenu { menu-scrollable: 1;}")
        menu.aboutToShow.connect(self.update_layers)
        self.setMenu(menu)

        # update layers on every change of the Maps-object background layer
        self.m.BM.on_layer(self.update_visible_layer, persistent=True)
        # update layers before the widget is shown to make sure they always
        # represent the currently visible layers on startup of the widget
        # (since "update_visible_layer" only triggers if the widget is actually visible)
        self.m._on_show_companion_widget.append(self.update_visible_layer)
        self.update_layers()

        # set font properties before the stylesheet to avoid clipping of bold text!
        font = QtGui.QFont("sans seriv", 8, QtGui.QFont.Bold, False)
        self.setFont(font)
        # self.setText("Layers:")
        # self.layer_button.setText("")
        # self.setIcon(QtGui.QIcon(str(iconpath / "layers.png")))

        self.set_icons(str(iconpath / "layers.png"), str(iconpath / "layers_hover.png"))

        self.setStyleSheet(
            """
            QPushButton {border: 0px;}
            QPushButton::menu-indicator { width: 0; }
            """
        )

        self.toggled.connect(self.swap_icon)

    def set_icons(self, normal_icon=None, hoover_icon=None, checked_icon=None):
        if normal_icon:
            pm = QtGui.QPixmap(normal_icon)
            self.normal_icon = QtGui.QIcon(
                pm.scaled(
                    self.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
            self.setIcon(self.normal_icon)
            self.active_icon = self.normal_icon
        if hoover_icon:
            pm = QtGui.QPixmap(hoover_icon)
            self.hoover_icon = QtGui.QIcon(
                pm.scaled(
                    self.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        if checked_icon:
            pm = QtGui.QPixmap(checked_icon)
            self.checked_icon = QtGui.QIcon(
                pm.scaled(
                    self.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
            )
        else:
            self.checked_icon = self.hoover_icon

    def swap_icon(self, *args, **kwargs):
        if self.normal_icon and self.hoover_icon:
            if self.isChecked():
                self.active_icon = self.checked_icon
            else:
                self.active_icon = self.normal_icon
            self.setIcon(self.active_icon)

    def leaveEvent(self, event):
        if self.active_icon:
            self.setIcon(self.active_icon)

        return super().enterEvent(event)

    def enterEvent(self, e):
        if self.hoover_icon and not self.isChecked():
            self.setIcon(self.hoover_icon)
        else:
            self.setIcon(self.normal_icon)

        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Layer Dropdown Menu</h3>"
                "Get a dropdown-list of all currently available map-layers."
                "<p>"
                "<ul>"
                "<li><b>click</b> to switch to the selected layer</li>"
                "<li><b>control+click</b> to overlay multiple layers</li>"
                "</ul>"
                "The number [n] in front of the layer-name indicates the "
                "stack-order of the layer.",
            )

    def get_uselayer(self):
        active_layers = []
        for a in self.menu().actions():
            w = a.defaultWidget()

            if isinstance(w, QtWidgets.QCheckBox) and w.isChecked():
                active_layers.append(a.data())

        uselayer = "???"

        if len(active_layers) > 1:
            uselayer = self.m.BM._get_combined_layer_name(*active_layers)
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
        if not self._auto_text:
            return
        # make sure that we don't use too long labels as text
        if len(l) > 50:
            l = f"{len([1 for i in l.split('|') if len(i) > 0])} layers visible"
            # txt = txt[:50] + " ..."

        if "{" in l:
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

    @Slot()
    def actionClicked(self):
        action = self.sender()
        if not isinstance(action, QtWidgets.QWidgetAction):
            # sometimes the sender is the button... ignore those events!
            return

        # check if a keyboard modifier is pressed
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        actionwidget = action.defaultWidget()

        # just split here to keep transparency-assignments in tact!
        active_layers = self.m.BM.bg_layer.split("|")

        checked_layers = [l for l in active_layers if l != "_"]
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
                uselayer = self.m.BM._get_combined_layer_name(*checked_layers)
            elif len(checked_layers) == 1:
                uselayer = checked_layers[0]

            # collect all checked items and set the associated layer
            if uselayer != "???":
                self.m.show_layer(uselayer)
        else:
            self.m.show_layer(selected_layer)

    def update_checkstatus(self):
        currlayer = str(self.m.BM.bg_layer)
        layers, alphas = self.m.BM._get_active_layers_alphas
        if "|" in currlayer:
            active_layers = [i for i in layers if not i.startswith("_")]
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

    @Slot()
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

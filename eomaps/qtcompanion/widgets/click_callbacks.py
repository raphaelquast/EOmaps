from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot


class AnnotateButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Annotation (click) callback</h3>"
                "Add a basic annotation if you click anywhere on the map.<p>"
                "The annotation will show lon/lat as well as x/y coordinates of the "
                "used projection.",
            )


class AnnotatePickButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Annotation (pick) callback</h3>"
                "Add a basic annotation if you click on a datapoint of the map.<p>"
                "The closest datapoint to the click-position will be identified and "
                "the annotation will show the picked data-value, the ID and the "
                "coordinates (both original and x/y of the used projection)<p>"
                "NOTE: If more than 1 dataset is present on the layer, the used "
                "dataset is selected via the dropdown-menu!",
            )


class MarkButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Mark (click) callback</h3>"
                "Add a basic mark-callback if you click anywhere on the map.<p>"
                "A marker (geodesic circle) with a red edgecolor will be added to "
                "indicate the clicked location. The radius of the marker can be "
                "adjusted with the input-box (in units of meters)",
            )


class MarkRadiusLineEdit(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>(click) Marker Radius</h3>"
                "Set the radius of the (click) marker (in meters).",
            )


class PickNPointsLineEdit(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Number of points to pick</h3>"
                "Set the number of nearest datapoints to select "
                "when executing 'pick' callbacks<p>"
                "NOTE: If multiple datasets are present on a layer, this is "
                "assigned for each dataset individually!)",
            )


class MarkPickButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Mark (pick) callback</h3>"
                "Add a basic mark-callback if you click on a datapoint of the map.<p>"
                "The closest datapoint to the click-position will be identified and "
                "a marker with a red edgecolor will be added to indicate the point.<p>"
                "NOTE: If more than 1 dataset is present on the layer, the used "
                "dataset is selected via the dropdown-menu!",
            )


class PrintButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Print-To-Console (click) callback</h3>"
                "Print the coordinates (both lon/lat and x/y of the used projection) "
                "to the console if you click anywhere on the map.<p>",
            )


class PrintPickButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Print-To-Console (pick) callback</h3>"
                "The closest datapoint to the click-position will be identified and "
                "the available information of the point will be printed to the "
                "console: the picked data-value, the ID and the coordinates "
                "(both original and x/y of the used projection)<p>"
                "NOTE: If more than 1 dataset is present on the layer, the used "
                "dataset is selected via the dropdown-menu!",
            )


class PickMapDropdown(QtWidgets.QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet("border-style:none;")
        self.setMinimumWidth(150)
        self.setMaximumWidth(400)
        self.setSizeAdjustPolicy(self.AdjustToContents)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Pick Callback Dataset</h3>"
                "If there is more than 1 dataset on the currently visible layer, use "
                "the dropdown to select the dataset you want to pick."
                "<p>"
                "The name represents the following:<br>"
                "ID: [parameter name] ( [layer] )",
            )


class PermanentCheckBox(QtWidgets.QCheckBox):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Permanent Markers / Annotations</h3>"
                "If checked, the markers and annotations created with "
                "the Pick/Click callbacks will be permanent."
                "(e.g. they are not removed on the next click).",
            )


class ClearButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Clear Annotations and Markers</h3>"
                "Remove all (permanent) annotations and markers from the map. <p>"
                "(This does not affect markers and annotations added with "
                "<code>m.add_annotation()</code> or <code>m.add_marker()</code>",
            )


class ClickCallbacks(QtWidgets.QFrame):
    widgetShown = pyqtSignal()

    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.setStyleSheet(
            """
            ClickCallbacks{
                border: 1px solid rgb(200,200,200);
                border-radius: 10px;
                };
            """
        )

        self.m = m

        self._pick_map = self.m

        # NOTE: maps-objects can be weakproxies! so don't use them as keys in a dict!
        self.cids = dict()

        self._kwargs = dict(
            mark=dict(
                shape="geod_circles",
                radius=100000,
                fc="none",
                ec="r",
                n=100,
                # zorder=998,
            ),
            mark_pick=dict(
                fc="none",
                ec="r",
                n=100,
                lw=2,  # zorder=998
            ),
            annotate=dict(),  # zorder=999
            annotate_pick=dict(),  # zorder=999
        )

        self.buttons = dict()

        self.t_click = QtWidgets.QLabel("<b>Click</b> callbacks:")
        self.t_pick = QtWidgets.QLabel("<b>Pick</b> callbacks:")

        # number of points to pick
        # (init before pick map dropdown to update n)
        self.n_points_inp = PickNPointsLineEdit()
        self.n_points_inp.setText(str(self._pick_map.cb.pick._n_ids))
        self.n_points_inp.setMaximumWidth(30)
        validator = QtGui.QIntValidator()
        self.n_points_inp.setValidator(validator)
        self.n_points_inp.textChanged.connect(self.n_points_changed)

        # pick-map dropdown
        self.map_dropdown = PickMapDropdown()
        self.populate_dropdown()
        self.map_dropdown.activated.connect(self.set_pick_map)

        t_dropdown = QtWidgets.QLabel("<b>Dataset:</b>")

        dropdown_layout = QtWidgets.QHBoxLayout()
        dropdown_layout.addWidget(t_dropdown)
        dropdown_layout.addWidget(self.map_dropdown)
        dropdown_layout.addWidget(self.n_points_inp)

        # Annotate
        b_ann = AnnotateButton("Annotate")
        self.buttons["annotate"] = b_ann
        b_ann.clicked.connect(self.button_clicked("annotate"))

        # Print To Console
        b_print = PrintButton("Print To Console")
        self.buttons["print"] = b_print
        b_print.clicked.connect(self.button_clicked("print"))

        # Mark
        b_mark = MarkButton("Mark")
        self.buttons["mark"] = b_mark
        b_mark.clicked.connect(self.button_clicked("mark"))
        self.radius_inp = MarkRadiusLineEdit()
        self.radius_inp.setText(str(self._kwargs["mark"]["radius"]))
        self.radius_inp.setMaximumWidth(80)
        validator = QtGui.QDoubleValidator()
        self.radius_inp.setValidator(validator)
        self.radius_inp.textChanged.connect(self.radius_changed)

        t_rad = QtWidgets.QLabel("Radius [m]:")

        marklayout = QtWidgets.QHBoxLayout()
        marklayout.addWidget(t_rad)
        marklayout.addWidget(self.radius_inp)
        marklayout.addStretch(1)

        # Annotate (PICK)
        b_ann2 = AnnotatePickButton("Annotate")
        self.buttons["annotate_pick"] = b_ann2
        b_ann2.clicked.connect(self.button_clicked("annotate_pick"))

        # Print To Console (PICK)
        b_print2 = PrintPickButton("Print To Console")
        self.buttons["print_pick"] = b_print2
        b_print2.clicked.connect(self.button_clicked("print_pick"))

        # Mark (Pick)
        b_mark2 = MarkPickButton("Mark")
        self.buttons["mark_pick"] = b_mark2
        b_mark2.clicked.connect(self.button_clicked("mark_pick"))

        # checkbox if callbacks are permanent
        self.permanent_cb = PermanentCheckBox("Permanent?")
        self.permanent_cb.stateChanged.connect(self.set_permanent)

        # button to clear permanent annotations/markers
        bclear = ClearButton("Clear")
        bclear.clicked.connect(self.clear_annotations_and_markers)
        bclear.setFixedSize(bclear.sizeHint())

        blayout = QtWidgets.QGridLayout()
        blayout.addWidget(self.t_click, 0, 0)
        blayout.addWidget(self.t_pick, 1, 0)
        blayout.addWidget(b_ann, 0, 1, 1, 1, Qt.AlignLeft)
        blayout.addWidget(b_print, 0, 2, 1, 1, Qt.AlignLeft)
        blayout.addWidget(b_mark, 0, 3, 1, 1, Qt.AlignLeft)
        blayout.addLayout(marklayout, 0, 4, 1, 1, Qt.AlignLeft)
        blayout.addWidget(b_ann2, 1, 1, 1, 1, Qt.AlignLeft)
        blayout.addWidget(b_print2, 1, 2, 1, 1, Qt.AlignLeft)
        blayout.addWidget(b_mark2, 1, 3, 1, 1, Qt.AlignLeft)
        blayout.addLayout(dropdown_layout, 1, 4, 1, 1, Qt.AlignLeft)

        perm_layout = QtWidgets.QVBoxLayout()
        perm_layout.addWidget(self.permanent_cb, Qt.AlignRight)
        perm_layout.addWidget(bclear, Qt.AlignRight)

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(blayout)
        layout.addStretch(1)
        layout.addLayout(perm_layout)

        self.setLayout(layout)

        self.update_buttons()

        # update the buttons on each "show" to make sure "pick" buttons become visible
        # when a dataset is plotted
        self.widgetShown.connect(self.update_buttons)

        self.set_pick_map(0)

        # make sure we re-attach pick-callback on a layer change
        self.m.BM.on_layer(self.on_layer_change, persistent=True)

    def showEvent(self, event):
        self.widgetShown.emit()

    def identify_pick_map(self):
        pickm = list()
        for m in (self.m.parent, *self.m.parent._children):
            if (
                m.coll is not None
                and m.ax == self.m.ax
                and m.layer
                in (
                    "all",
                    m.BM._bg_layer,
                    *m.BM._bg_layer.split("|"),
                )
            ):
                pickm.append(m)
        return pickm

    @pyqtSlot()
    def clear_annotations_and_markers(self):
        # clear all annotations and markers from this axis
        # (irrespective of the visible layer!)
        for m in (self.m.parent, *self.m.parent._children):
            if m.ax == self.m.ax:
                m.cb.click._cb.clear_annotations()
                m.cb.click._cb.clear_markers()
                m.cb.pick._cb.clear_annotations()
                m.cb.pick._cb.clear_markers()

        self.m.BM.update()

    def reattach_pick_callbacks(self):
        # re-attach all "pick" callbacks (e.g. if the pick_map changed)
        for key in ("annotate_pick", "mark_pick", "print_pick"):
            if self.cids.get(key, None) is not None:
                self.attach_callback(key)

    def set_permanent(self):
        self.reattach_pick_callbacks()
        # re-attach click callbacks as well
        for key in ("annotate", "mark", "print"):
            if self.cids.get(key, None) is not None:
                self.attach_callback(key)

    def populate_dropdown(self):
        self.map_dropdown.clear()

        # the QAbstractItemView object that holds the dropdown-items
        view = self.map_dropdown.view()
        view.setTextElideMode(Qt.ElideNone)

        for i, m in enumerate(self.identify_pick_map()):
            if m.data_specs.parameter is not None:
                name = f"{i}: {m.data_specs.parameter}"
            else:
                name = f"{i}"

            if "|" in m.BM.bg_layer:
                if m.layer != m.BM.bg_layer:
                    name += f" ({m.layer})"

            self.map_dropdown.addItem(name, m)

        # use None to keep already selected maps selected!
        self.set_pick_map(None)

        # set the size of the dropdown to be 10 + the longest item
        view.setFixedWidth(view.sizeHintForColumn(0) + 10)

    def set_pick_map(self, index=None):
        maps = self.identify_pick_map()
        if len(maps) == 0:
            self._pick_map = None
            return

        if index is None and self._pick_map is not None and self._pick_map in maps:
            # if a map was already selected (and it is still a valid target, keep it)
            return

        # if not map was explicitly selected, select the first one
        if index is None:
            index = 0

        self._pick_map = self.map_dropdown.itemData(index)
        self.reattach_pick_callbacks()

        # update number of picked points to reflect value of selected dataset
        self.n_points_inp.setText(str(self._pick_map.cb.pick._n_ids))
        self.n_points_changed()

        self.update_buttons()

    def on_layer_change(self, *args, **kwargs):
        # update maps-objects
        self.populate_dropdown()
        self.update_buttons()

    @pyqtSlot()
    def update_buttons(self):
        if self._pick_map is None or self._pick_map.coll is None:
            self.t_pick.setEnabled(False)
            self.map_dropdown.setEnabled(False)
        else:
            self.t_pick.setEnabled(True)
            self.map_dropdown.setEnabled(True)

        for key, val in self.buttons.items():
            if key.endswith("_pick"):
                # set pick-buttons to invisible if no pick_map is found
                if self._pick_map is None or self._pick_map.coll is None:
                    val.setEnabled(False)
                else:
                    val.setEnabled(True)

                if self.cids.get(key, None) is not None:
                    val.setStyleSheet("background-color : rgb(200,100,100);")
                else:
                    val.setStyleSheet("background-color : rgba(200,100,100,50);")
            else:
                if self.cids.get(key, None) is not None:
                    val.setStyleSheet("background-color : rgb(100,150,100);")
                else:
                    val.setStyleSheet("background-color : rgba(100,150,100,50);")

    def remove_callback(self, key):
        mcid = self.cids.get(key, None)
        if mcid is not None:
            m, cid = mcid
            if key.endswith("_pick"):
                # explicitly check if the callback is attached to avoid warnings if
                # the figure is closed while a callback is still attached
                # (this way cleanup might have already removed the callback)
                if cid in m.cb.pick.get.attached_callbacks:
                    m.cb.pick.remove(cid)
            else:
                if cid in m.cb.click.get.attached_callbacks:
                    m.cb.click.remove(cid)
        self.cids[key] = None

        self.m.BM.update()

    def attach_callback(self, key):
        # remove existing callback
        self.remove_callback(key)

        if key == "mark":
            method = self.m.all.cb.click.attach.mark
        elif key == "annotate":
            method = self.m.all.cb.click.attach.annotate
        elif key == "print":
            method = self.m.all.cb.click.attach.print_to_console
        elif key == "mark_pick":
            method = self._pick_map.cb.pick.attach.mark
        elif key == "annotate_pick":
            method = self._pick_map.cb.pick.attach.annotate
        elif key == "print_pick":
            method = self._pick_map.cb.pick.attach.print_to_console

        # check if we want a permanent or temporary annotation/marker
        if key not in ["print", "print_pick"]:
            self._kwargs[key]["permanent"] = self.permanent_cb.isChecked()

        if key.endswith("_pick"):
            self.cids[key] = (self._pick_map, method(**self._kwargs.get(key, dict())))
        else:
            # disable motion callback for permanent markers and annotations
            if key != "print":
                if self.permanent_cb.isChecked():
                    self._kwargs[key]["on_motion"] = False
                else:
                    self._kwargs[key]["on_motion"] = True

            self.cids[key] = (self.m.all, method(**self._kwargs.get(key, dict())))

    @pyqtSlot()
    def radius_changed(self):
        try:
            radius = float(self.radius_inp.text())
        except ValueError:
            return
        self._kwargs["mark"]["radius"] = radius
        self.attach_callback("mark")
        self.update_buttons()

    @pyqtSlot()
    def n_points_changed(self):
        try:
            n = int(self.n_points_inp.text())
        except ValueError:
            return

        self._pick_map.cb.pick.set_props(n)

        self.update_buttons()

    def button_clicked(self, key):
        @pyqtSlot()
        def cb():
            if self.cids.get(key, None) is not None:
                self.remove_callback(key)
            else:
                self.attach_callback(key)
            self.update_buttons()

        return cb

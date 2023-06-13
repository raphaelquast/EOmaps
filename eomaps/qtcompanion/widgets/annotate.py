from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot, pyqtSignal
from .utils import GetColorWidget

from matplotlib.patches import BoxStyle, ArrowStyle
from matplotlib.colors import to_rgba

arrow_styles = ArrowStyle.get_styles()
arrow_styles_reversed = dict(map(reversed, arrow_styles.items()))

box_styles = BoxStyle.get_styles()
box_styles_reversed = dict(map(reversed, box_styles.items()))


class AnnotationTextEdit(QtWidgets.QTextEdit):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMaximumHeight(70)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Annotation Text</h3>"
                "Enter the text that should be displayed as an annotation on the map."
                "<p>"
                "<ul><li>press <b>shift + enter</b> to add the annotation"
                " to the map!</li></ul>"
                "<p>"
                "To enter LaTex symbols and equations, encapsulate the LaTex code in "
                "two $ symbols, e.g.: <code>$\sqrt(x^2)=x$</code>",
            )


class AnnotationDial(QtWidgets.QDial):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setRange(0, 360)
        self.setSingleStep(45)
        self.setWrapping(True)
        self.setMaximumSize(45, 45)
        self.setNotchesVisible(True)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Set Text Position</h3>"
                "Use the dial to set the position of the text-box relative to the "
                "annotated point.",
            )


class RemoveButton(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setText("Remove")

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Undo Annotations</h3>"
                "Successively undo previously added annotations.",
            )


class AnnotateButton(QtWidgets.QToolButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setText("Annotate")

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Add Annotation</h3>"
                "Push this button to add an annotation to the map the next time you "
                "<b>left click</b> on the map."
                "<p>"
                "The annotation will be added to the "
                "<b><font color=#c80000>currently selected tab</font></b> "
                "in the tab-bar below."
                "<p>"
                "NOTE: this is not necessarily the visible layer!",
            )


class EditAnnotationsButton(QtWidgets.QPushButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Make Annotations Editable</h3>"
                "This button will make all (permanent) annotations editable! "
                "<ul>"
                "<li>Click on an annotation to select it for editing</li>"
                "<li>Edit text, patch-color, rotation with the widgets..."
                "<li>Drag the annotation to move the text-box</li>"
                "<li>Hold down <b>shift</b> to resize the text-box</li>"
                "<li>Hold down <b>R</b> to rotate the text-box</li>"
                "<li>Hold down <b>control</b> to move the anchor position</li>"
                "</ul>",
            )


class AddAnnotationInput(QtWidgets.QWidget):
    widgetShown = pyqtSignal()

    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        self.layer = None

        self.annotate_props = dict()
        self._relpos = [0, 0]

        self._last_text_inp = ""

        self.cb_cids = []

        label = QtWidgets.QLabel("Add Annotation\non next click:")
        self.text_inp = AnnotationTextEdit()

        self.text_inp.textChanged.connect(self.update_selected_text)

        self.color = GetColorWidget(facecolor="white", edgecolor="black")
        self.color.cb_colorselected = self.colorselected
        self.color.setMaximumSize(35, 35)

        self.b = AnnotateButton()
        self.b.clicked.connect(self.do_add_annotation)
        self.b.setFixedSize(self.b.sizeHint())

        self.b_rem = RemoveButton()
        self.b_rem.clicked.connect(self.remove_last_annotation)
        self.b_rem.setFixedSize(self.b.sizeHint())

        blayout = QtWidgets.QVBoxLayout()
        blayout.addWidget(self.b, Qt.AlignTop)
        blayout.addWidget(self.b_rem, Qt.AlignTop)

        self.dial = AnnotationDial()
        self.dial.valueChanged.connect(self.dial_value_changed)
        self.dial.setValue(225)

        # button to make annotations editable
        self.edit_annotations = EditAnnotationsButton("Edit Annotations")
        self.edit_annotations.clicked.connect(self.toggle_annotations_editable)

        # drop-down menu to select boxstyle

        self._boxstyle = "round"
        self.boxstyle_dropdown = QtWidgets.QComboBox()
        self.boxstyle_dropdown.addItem("none")

        for i in box_styles:
            self.boxstyle_dropdown.addItem(i)
        self.boxstyle_dropdown.setCurrentIndex(
            self.boxstyle_dropdown.findText(self._boxstyle)
        )
        self.boxstyle_dropdown.activated.connect(self.set_boxstyle)

        # drop-down menu to select arrow style

        self._arrowstyle = "fancy"
        self.arrowstyle_dropdown = QtWidgets.QComboBox()
        self.arrowstyle_dropdown.addItem("none")

        for i in arrow_styles:
            self.arrowstyle_dropdown.addItem(i)
        self.arrowstyle_dropdown.setCurrentIndex(
            self.arrowstyle_dropdown.findText(self._arrowstyle)
        )
        self.arrowstyle_dropdown.activated.connect(self.set_arrowstyle)

        layout = QtWidgets.QVBoxLayout()

        layout_h = QtWidgets.QHBoxLayout()
        layout_h.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout_h.addWidget(self.color)
        layout_h.addWidget(self.dial)
        layout_h.addWidget(self.boxstyle_dropdown)
        layout_h.addWidget(self.arrowstyle_dropdown)

        layout_h.addWidget(self.text_inp)
        layout_h.addLayout(blayout, Qt.AlignTop)

        layout.addLayout(layout_h)
        layout.addWidget(self.edit_annotations)
        self.setLayout(layout)

        self._annotation_active = False

        # update the buttons on each "show"
        self.widgetShown.connect(self.update_buttons)

        self.text_inp.installEventFilter(self)

    def eventFilter(self, widget, event):
        from PyQt5 import QtCore

        if event.type() == QtCore.QEvent.KeyPress and widget is self.text_inp:

            # trigger adding the annotation on SHIFT + ENTER
            if (
                event.key() in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter)
                and event.modifiers() == QtCore.Qt.ShiftModifier
            ):

                self.do_add_annotation()
                return True

            return super().eventFilter(widget, event)

        return super().eventFilter(widget, event)

    def set_boxstyle(self, *args, **kwargs):
        self._boxstyle = self.boxstyle_dropdown.currentText()
        # trigger colorselected to set the patch-props
        self.colorselected()

    def set_arrowstyle(self, *args, **kwargs):
        self._arrowstyle = self.arrowstyle_dropdown.currentText()
        # trigger colorselected to set the arrow-props
        self.colorselected()

    @property
    def selected_annotation(self):
        if self.m._edit_annotations._drag_active:
            return self.m._edit_annotations._last_selected_annotation
        else:
            return None

    def set_edited_annotation_props(self, *args, **kwargs):
        # update dynamically updated props of the annotation to reflect values in the
        # companion widget controls
        ann = self.selected_annotation
        if ann:
            # set the rotation position of the dial
            rotation = ann.get_rotation()
            self.dial.setValue(int(180 - rotation))
            self.dial.repaint()

    def set_selected_annotation_props(self, *args, **kwargs):
        # update the annotation-widget with respect to the properties of the
        # currently selected annotation
        ann = self.selected_annotation
        if ann:
            # put the text of the currently selected annotation in the input-box
            text = ann.get_text()
            self.text_inp.setText(text)
            # color text-input green to indicate that changes are made on an
            # existing annotation
            self.text_inp.setStyleSheet("background-color: rgba(0,200,0,100)")

            # set the rotation position of the dial
            rotation = ann.get_rotation()
            self.dial.setValue(int(180 - rotation))

            patch = ann.get_bbox_patch()

            # set current boxstyle in dropdown
            self._boxstyle = box_styles_reversed.get(
                patch.get_boxstyle().__class__, "none"
            )
            self.boxstyle_dropdown.setCurrentText(self._boxstyle)

            # set patch colors and linewidth
            fc = patch.get_facecolor()
            ec = ann._draggable._init_ec
            lw = patch.get_linewidth()

            self.color.set_facecolor([int(i * 255) for i in to_rgba(fc)])
            self.color.set_edgecolor([int(i * 255) for i in to_rgba(ec)])
            self.color.set_linewidth(lw)

            self.b_rem.setEnabled(True)
            self.b_rem.setStyleSheet("background-color : rgb(100,150,100);")

            if ann.arrow_patch is None:
                self._arrowstyle = "none"
            else:
                self._arrowstyle = ann.arrowprops.get("arrowstyle", "none")

            # set current arrowstyle in dropdown
            self.arrowstyle_dropdown.setCurrentText(self._arrowstyle)

        else:
            self.text_inp.setStyleSheet("background-color: none")
            self.b_rem.setEnabled(False)
            self.b_rem.setStyleSheet("background-color : rgba(100,150,100,50);")

    def update_selected_text(self, *args, **kwargs):
        ann = self.selected_annotation
        if ann:
            text = self.text_inp.toPlainText()
            ann.set_text(text)
            self.m.BM.update(artists=[ann])

    def update_selected_rotation(self, r):
        ann = self.selected_annotation
        if ann:
            # update the rotation of the currently selected annotation
            ann.set_rotation(r)
            self.m.BM.update(artists=[ann])

    def update_selected_patch(self, fc, ec, lw):
        ann = self.selected_annotation
        if ann:
            patch = ann.get_bbox_patch()
            patch.set_facecolor(fc)
            patch.set_edgecolor(ec)
            patch.set_linewidth(lw)

            bbox = self.annotate_props.get("bbox", None)
            if bbox:
                ann.set_bbox(bbox)

            if self._arrowstyle:
                if ann.arrow_patch is not None:
                    arrowprops = self._get_arrowprops()["arrowprops"]
                    if arrowprops is not None:
                        arrowprops = {
                            key: val
                            for key, val in arrowprops.items()
                            if key
                            in [
                                "arrowstyle",
                                "connectionstyle",
                                "fc",
                                "ec",
                                "lw",
                                "facecolor",
                                "edgecolor",
                                "linewidth",
                            ]
                        }
                        ann.arrow_patch.set(**arrowprops)
                    else:
                        ann.arrow_patch.set(arrowstyle=None)

            self.m.BM.update(artists=[ann])

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Add Annotation</h3>"
                "Type some text and press <b>Annotate</b> to add a permanent annotation"
                " the next time you click on the map."
                "<p>"
                "<ul>"
                "<li>Use the <b>dial</b> to set the location of the text "
                "relative to the annotation position.</li>"
                "<li>Click <b>Stop</b> to abort adding an annotation.</li>"
                "</ul>"
                "<p>"
                "NOTE: Annotations are 'dynamic' artists (e.g. artists that do not"
                "require a re-draw of the background-layer) so they will NOT appear"
                "in the list of background-artists!",
            )

    @pyqtSlot(int)
    def dial_value_changed(self, i):
        self.annotate_props["rotation"] = int(180 - i)
        self.annotate_props["horizontalalignment"] = "center"
        self.annotate_props["verticalalignment"] = "center"

        self._relpos = [0.5, 0.5]

        # if edit is active, edit the currently selected annotation
        if self.m._edit_annotations._drag_active:
            self.update_selected_rotation(self.annotate_props["rotation"])

    @pyqtSlot()
    def do_add_annotation(self):
        if self._annotation_active is True:
            self.stop()
        else:
            self.add_annotation(text=self.text_inp.toPlainText())

    @pyqtSlot()
    def remove_last_annotation(self):
        ann = self.selected_annotation
        if ann:
            self.m.BM.remove_artist(ann)
            ann.remove()
            self.m.BM.update()
        else:
            self.window().statusBar().showMessage("There is no annotation to remove!")

    def colorselected(self):
        if self._boxstyle == "none":
            boxstyle = "round"
            fc = self.color.facecolor.getRgbF()
            ec = self.color.edgecolor.getRgbF()
            alpha = 0
            lw = self.color.linewidth
        else:
            boxstyle = self._boxstyle
            fc = self.color.facecolor.getRgbF()
            ec = self.color.edgecolor.getRgbF()
            alpha = self.color.alpha
            lw = self.color.linewidth

        self.annotate_props["bbox"] = dict(
            boxstyle=boxstyle, facecolor=fc, edgecolor=ec, linewidth=lw, alpha=alpha
        )

        self.update_selected_patch(fc, ec, lw)

    def set_layer(self, layer):
        self.stop()
        self.layer = layer

    def stop(self):
        while len(self.cb_cids) > 0:
            self.m.all.cb.click.remove(self.cb_cids.pop())

        self.set_selected_annotation_props()

        self._annotation_active = False
        self.text_inp.setEnabled(True)
        self.b.setText("Annotate")

        self.text_inp.setText(self._last_text_inp)

    def _get_arrowprops(self):
        if self._arrowstyle != "none":
            arrowprops = dict(
                arrowstyle=self._arrowstyle,
                connectionstyle="angle3",
                fc="k",
                ec="k"
                if self._arrowstyle not in ["simple", "fancy", "wedge"]
                else "none",
                relpos=self._relpos.copy(),
            )
            xytext = (20, 20)
        else:
            arrowprops = None
            xytext = (0, 0)

        return dict(arrowprops=arrowprops, xytext=xytext, textcoords="offset pixels")

    def add_annotation(self, text):
        # clear selected annotation to avoid updating text
        self.m._edit_annotations._set_last_selected_annotation(None)

        # self.window().hide()
        self.m.f.canvas.show()
        self.m.f.canvas.activateWindow()

        arrow_props = self._get_arrowprops()

        def cb(pos, **kwargs):
            if len(self.cb_cids) > 0:
                self.m.add_annotation(
                    xy=pos,
                    xy_crs=self.m.crs_plot,
                    text=text,
                    layer=self.layer,
                    permanent=True,
                    **arrow_props,
                    **self.annotate_props,
                )
                self.stop()

        # remove old callback if it is still attached
        self.stop()
        # attach new callback
        self.cb_cids.append(self.m.all.cb.click.attach(cb))
        self.text_inp.setStyleSheet("background-color: rgba(200,0,0,100)")
        self.text_inp.setText(
            "<h3>Click on the map to add the annotation!</h3>"
            "<hl>"
            f"<pre>{text}</pre>"
        )
        self._last_text_inp = text

        self._annotation_active = True
        self.text_inp.setEnabled(False)
        self.b.setText("Stop")

    def showEvent(self, event):
        self.widgetShown.emit()
        super().showEvent(event)

    @property
    def _annotations_editable(self):
        return self.m._edit_annotations._drag_active

    @pyqtSlot()
    def toggle_annotations_editable(self):
        if not self._annotations_editable:
            self.m._edit_annotations(True, print_msg=False)
            self.window().statusBar().showMessage(
                "Annotations editable! "
                "< control >: Move  |  < shift >: Resize  |   < R >: Rotate"
            )
        else:
            self.m._edit_annotations(False)
            self.window().statusBar().showMessage("")

        self.update_buttons()

    @pyqtSlot()
    def update_buttons(self):
        if self._annotations_editable:
            self.edit_annotations.setText(
                "Annotations editable!    "
                "< control >: Move  |  < shift >: Resize  |   < R >: Rotate"
            )
            self.edit_annotations.setStyleSheet("background-color : rgb(100,150,100);")

        else:
            self.edit_annotations.setText("Edit Annotations")
            self.edit_annotations.setStyleSheet(
                "background-color : rgba(100,150,100,50);"
            )

        self.set_selected_annotation_props()

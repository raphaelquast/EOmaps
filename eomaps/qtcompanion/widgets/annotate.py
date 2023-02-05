from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSlot
from .utils import GetColorWidget


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


class AddAnnotationInput(QtWidgets.QWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        self.layer = None

        self.annotate_props = dict()
        self._relpos = [0, 0]

        self.cb_cids = []

        label = QtWidgets.QLabel("Add Annotation\non next click:")
        self.text_inp = AnnotationTextEdit()

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

        layout = QtWidgets.QHBoxLayout()
        layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        layout.addWidget(self.color)
        layout.addWidget(self.dial)
        layout.addWidget(label)
        layout.addWidget(self.text_inp)
        layout.addLayout(blayout, Qt.AlignTop)

        self.setLayout(layout)

        self._annotation_active = False

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
        from math import sin, cos, radians

        d = 50

        i = i
        x, y = -d * sin(radians(i)), -d * cos(radians(i))

        self.annotate_props["xytext"] = (x, y)
        self.annotate_props["textcoords"] = "offset pixels"

        if x < -d / 3:
            self._relpos[0] = 1
            self.annotate_props["horizontalalignment"] = "right"
        elif -d / 3 < x < d / 3:
            self._relpos[0] = 0.5
            self.annotate_props["horizontalalignment"] = "center"
        else:
            self._relpos[0] = 0
            self.annotate_props["horizontalalignment"] = "left"
        if y < -d / 3:
            self._relpos[1] = 1
            self.annotate_props["verticalalignment"] = "top"
        elif -d / 3 < y < d / 3:
            self._relpos[1] = 0.5
            self.annotate_props["verticalalignment"] = "center"
        else:
            self._relpos[1] = 0
            self.annotate_props["verticalalignment"] = "bottom"

    @pyqtSlot()
    def do_add_annotation(self):
        if self._annotation_active is True:
            self.stop()
        else:
            self.add_annotation(text=self.text_inp.toPlainText())

    @pyqtSlot()
    def remove_last_annotation(self):
        if self.m.cb.click.get.permanent_annotations:
            last_ann = self.m.cb.click.get.permanent_annotations.pop(-1)
            self.m.BM.remove_artist(last_ann)
            last_ann.remove()
            self.m.BM.update()
        else:
            self.window().statusBar().showMessage("There is no annotation to remove!")

    def colorselected(self):
        self.annotate_props["bbox"] = dict(
            boxstyle="round",
            facecolor=self.color.facecolor.getRgbF(),
            edgecolor=self.color.edgecolor.getRgbF(),
        )

    def set_layer(self, layer):
        self.stop()
        self.layer = layer

    def stop(self):
        while len(self.cb_cids) > 0:
            self.m.all.cb.click.remove(self.cb_cids.pop())

        self.text_inp.setStyleSheet("background-color: none")
        self._annotation_active = False
        self.text_inp.setEnabled(True)
        self.b.setText("Annotate")

    def add_annotation(self, text):
        self.window().hide()
        self.m.f.canvas.show()
        self.m.f.canvas.activateWindow()

        def cb(pos, **kwargs):
            if len(self.cb_cids) > 0:
                self.m.add_annotation(
                    xy=pos,
                    xy_crs=self.m.crs_plot,
                    text=text,
                    layer=self.layer,
                    permanent=True,
                    arrowprops=dict(
                        arrowstyle="fancy",
                        connectionstyle="angle3",
                        fc="k",
                        ec="none",
                        relpos=self._relpos.copy(),
                    ),
                    **self.annotate_props,
                )
                self.stop()

        # remove old callback if it is still attached
        self.stop()
        # attach new callback
        self.cb_cids.append(self.m.all.cb.click.attach(cb))
        self.text_inp.setStyleSheet("background-color: rgba(200,0,0,100)")
        self._annotation_active = True
        self.text_inp.setEnabled(False)
        self.b.setText("Stop")

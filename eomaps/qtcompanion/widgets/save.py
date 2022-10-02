from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt

from .utils import EditLayoutButton


class SaveFileWidget(QtWidgets.QWidget):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent

        b_edit = EditLayoutButton("Edit layout", m=self.m)
        width = b_edit.fontMetrics().boundingRect(b_edit.text()).width()
        b_edit.setFixedWidth(width + 30)

        b1 = QtWidgets.QPushButton("Save!")
        width = b1.fontMetrics().boundingRect(b1.text()).width()
        b1.setFixedWidth(width + 30)

        b1.clicked.connect(self.save_file)

        # dpi
        l1 = QtWidgets.QLabel("DPI:")
        width = l1.fontMetrics().boundingRect(l1.text()).width()
        l1.setFixedWidth(width + 5)

        self.dpi_input = QtWidgets.QLineEdit()
        self.dpi_input.setMaximumWidth(50)
        validator = QtGui.QIntValidator()
        self.dpi_input.setValidator(validator)
        self.dpi_input.setText("200")

        # transparent
        self.transp_cb = QtWidgets.QCheckBox()
        transp_label = QtWidgets.QLabel("Tranparent")
        width = transp_label.fontMetrics().boundingRect(transp_label.text()).width()
        transp_label.setFixedWidth(width + 5)

        layout = QtWidgets.QHBoxLayout()
        layout.addWidget(b_edit)
        layout.addStretch(1)
        layout.addWidget(l1)
        layout.addWidget(self.dpi_input)
        layout.addWidget(transp_label)
        layout.addWidget(self.transp_cb)

        layout.addWidget(b1)

        layout.setAlignment(Qt.AlignBottom)

        self.setLayout(layout)

    @property
    def m(self):
        return self.parent.m

    def save_file(self):
        savepath = QtWidgets.QFileDialog.getSaveFileName()[0]

        if savepath is not None:
            self.m.savefig(
                savepath,
                dpi=int(self.dpi_input.text()),
                transparent=self.transp_cb.isChecked(),
            )

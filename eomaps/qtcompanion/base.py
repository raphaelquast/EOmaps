from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt

from .common import iconpath


def get_dummy_spacer():
    space = QtWidgets.QWidget()
    space.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
    )
    space.setAttribute(Qt.WA_TransparentForMouseEvents)
    return space


class ToolBar(QtWidgets.QToolBar):
    def __init__(self, *args, m=None, left_widget=None, title=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m

        logo = QtGui.QPixmap(str(iconpath / "logo.png"))
        logolabel = QtWidgets.QLabel()
        logolabel.setMaximumHeight(25)
        logolabel.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        logolabel.setPixmap(
            logo.scaled(logolabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

        b_close = QtWidgets.QToolButton()
        b_close.setAutoRaise(True)
        b_close.setFixedSize(25, 25)
        b_close.setText("🞫")
        b_close.clicked.connect(self.close_button_callback)

        self.b_minmax = QtWidgets.QToolButton()
        self.b_minmax.setAutoRaise(True)
        self.b_minmax.setFixedSize(25, 25)
        self.b_minmax.setText("🗖")
        self.b_minmax.clicked.connect(self.maximize_button_callback)

        if left_widget:
            self.addWidget(left_widget)

        if title is not None:
            titlewidget = QtWidgets.QLabel(f"<b>{title}</b>")
            titlewidget.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.addWidget(get_dummy_spacer())
            self.addWidget(titlewidget)

        self.addWidget(get_dummy_spacer())

        if m is not None:
            from .utils import AutoUpdateLayerMenuButton

            showlayer = AutoUpdateLayerMenuButton(m=self.m)
            self.addWidget(showlayer)
        self.addWidget(logolabel)
        self.addWidget(self.b_minmax)
        self.addWidget(b_close)

        self.setMovable(False)

        self.setStyleSheet(
            "QToolBar{border: none; spacing:5px;}"
            'QToolButton[autoRaise="true"]{text-align:center;}'
            "QPushButton{border:none;}"
        )
        self.setContentsMargins(0, 0, 0, 0)

        self.press_pos = None

    def close_button_callback(self):
        self.window().close()

    def maximize_button_callback(self):
        if not self.window().isMaximized():
            self.window().showMaximized()
            self.b_minmax.setText("🗗")
        else:
            self.window().showNormal()
            self.b_minmax.setText("🗖")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.press_pos = event.pos()

    def mouseReleaseEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.press_pos = None

    def mouseMoveEvent(self, event):
        if not self.press_pos:
            return

        if self.window().isMaximized():
            # minimize the window and position it centered
            self.window().showNormal()
            self.window().move(self.press_pos)
            self.press_pos = QtCore.QPoint(int(self.window().sizeHint().width() / 2), 0)
        else:
            self.window().move(self.window().pos() + (event.pos() - self.press_pos))


class NewWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, m=None, title=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m
        self.setWindowTitle("OpenFile")

        toolbar = ToolBar(title=title)
        self.addToolBar(toolbar)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(5, 20, 5, 5)

        statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(statusBar)

        widget = QtWidgets.QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # make sure that we close all remaining windows if the figure is closed
        self.m.figure.f.canvas.mpl_connect("close_event", self.on_close)

    def on_close(self, e):
        self.close()


class transparentWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_alpha = 0.25
        self.m = m

        # make sure the window does not steal focus from the matplotlib-canvas
        # on show (otherwise callbacks are inactive as long as the window is focused!)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )

        self.transparentQ = QtWidgets.QToolButton()
        self.transparentQ.setStyleSheet("border:none")
        self.transparentQ.setToolTip("Make window semi-transparent.")
        self.transparentQ.setIcon(QtGui.QIcon(str(iconpath / "eye_closed.png")))

        self.toolbar = ToolBar(m=self.m, left_widget=self.transparentQ)
        self.transparentQ.clicked.connect(self.cb_transparentQ)

        self.addToolBar(self.toolbar)

    def cb_transparentQ(self):
        if self.out_alpha == 1:
            self.out_alpha = 0.25
            self.setFocus()
            self.transparentQ.setIcon(QtGui.QIcon(str(iconpath / "eye_closed.png")))

        else:
            self.out_alpha = 1
            self.setFocus()
            self.transparentQ.setIcon(QtGui.QIcon(str(iconpath / "eye_open.png")))

    def focusInEvent(self, e):
        self.setWindowOpacity(1)
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        if not self.isActiveWindow():
            self.setWindowOpacity(self.out_alpha)
        super().focusInEvent(e)

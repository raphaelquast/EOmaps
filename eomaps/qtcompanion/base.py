from PyQt5 import QtWidgets, QtCore, QtGui
from PyQt5.QtCore import Qt, pyqtSlot

from .common import iconpath


def get_dummy_spacer():
    space = QtWidgets.QWidget()
    space.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
    )
    space.setAttribute(Qt.WA_TransparentForMouseEvents)
    return space


class TransparentQToolButton(QtWidgets.QToolButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Toggle window Transparency</h3>"
                "If activated, the companion-widget will get semi-transparent if it "
                "is out of focus.",
            )


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
        b_close.setIcon(QtGui.QIcon(str(iconpath / "close.png")))
        b_close.clicked.connect(self.close_button_callback)

        self.b_minmax = QtWidgets.QToolButton()
        self.b_minmax.setAutoRaise(True)
        self.b_minmax.setFixedSize(25, 25)
        self.b_minmax.setIcon(QtGui.QIcon(str(iconpath / "maximize.png")))
        self.b_minmax.clicked.connect(self.maximize_button_callback)

        self.b_showhelp = QtWidgets.QToolButton()
        self.b_showhelp.setText("?")
        self.b_showhelp.setCheckable(True)
        self.b_showhelp.setAutoRaise(True)
        self.b_showhelp.toggled.connect(self.toggle_show_help)
        self.b_showhelp.setToolTip("Toggle showing help-tooltips.")

        if left_widget:
            self.addWidget(left_widget)

        if title is not None:
            titlewidget = QtWidgets.QLabel(f"<b>{title}</b>")
            titlewidget.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.addWidget(get_dummy_spacer())
            self.addWidget(titlewidget)

        self.addWidget(self.b_showhelp)

        self.addWidget(get_dummy_spacer())

        if m is not None:
            from .widgets.layer import AutoUpdateLayerMenuButton

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
            """
            QToolButton:checked {background-color:rgba(255,50,50, 150);
            border: none;
            border-radius: 5px;}
            """
        )
        self.setContentsMargins(0, 0, 0, 0)

        self.press_pos = None

    @pyqtSlot()
    def toggle_show_help(self):
        if self.b_showhelp.isChecked():
            self.window().showhelp = True
            self.b_showhelp.setText("Click here to hide help tooltips")
        else:
            self.window().showhelp = False
            self.b_showhelp.setText("?")

    @pyqtSlot()
    def close_button_callback(self):
        self.window().close()
        if self.m is not None:
            self.m._indicate_companion_map(False)

    @pyqtSlot()
    def maximize_button_callback(self):
        if not self.window().isMaximized():
            self.window().showMaximized()
            self.b_minmax.setText("🗗")
        else:
            self.window().showNormal()
            self.b_minmax.setText("🗖")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            self.press_pos = event.windowPos().toPoint()

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
            self.window().move(event.globalPos() - self.press_pos)


class NewWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, m=None, title=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m
        self.setWindowTitle("OpenFile")

        self.showhelp = False

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
        self.m.f.canvas.mpl_connect("close_event", self.on_close)

    @pyqtSlot()
    def on_close(self, e):
        self.close()


class transparentWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_alpha = 0.25
        self.m = m

        # get the current PyQt app and connect the focus-change callback
        self.app = QtWidgets.QApplication([]).instance()
        self.app.focusChanged.connect(self.on_window_focus)

        # make sure the window does not steal focus from the matplotlib-canvas
        # on show (otherwise callbacks are inactive as long as the window is focused!)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog  # | Qt.WindowStaysOnTopHint
        )
        self.setFocusPolicy(Qt.ClickFocus)

        self.transparentQ = TransparentQToolButton()
        self.transparentQ.setStyleSheet("border:none")
        self.transparentQ.setIcon(QtGui.QIcon(str(iconpath / "eye_closed.png")))

        self.toolbar = ToolBar(m=self.m, left_widget=self.transparentQ)
        self.transparentQ.clicked.connect(self.cb_transparentQ)

        self.addToolBar(self.toolbar)

    @pyqtSlot()
    def cb_transparentQ(self):
        if self.out_alpha == 1:
            self.out_alpha = 0.25
            self.setFocus()
            self.transparentQ.setIcon(QtGui.QIcon(str(iconpath / "eye_closed.png")))

        else:
            self.out_alpha = 1
            self.setFocus()
            self.transparentQ.setIcon(QtGui.QIcon(str(iconpath / "eye_open.png")))

    @pyqtSlot("QWidget*", "QWidget*")
    def on_window_focus(self, old, new):
        if new is not None:
            if new is self or hasattr(new, "window") and new.window() is self:
                self.setWindowOpacity(1)

                # Uncheck avtive pan/zoom actions of the matplotlib toolbar.
                # This is done to avoid capturing of draw-events during pan/zoom
                # so that draw-events triggered by the companion take effect immediately

                toolbar = getattr(self.m.BM.canvas, "toolbar", None)
                if toolbar is not None:
                    for key in ["pan", "zoom"]:
                        val = toolbar._actions.get(key, None)
                        if val is not None and val.isCheckable() and val.isChecked():
                            val.trigger()
            else:
                self.setWindowOpacity(self.out_alpha)
        else:
            self.setWindowOpacity(1)

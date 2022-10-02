from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, pyqtSignal

from .base import ResizableWindow
from .common import iconpath

from .widgets.peek import PeekTabs
from .widgets.editor import ArtistEditor
from .widgets.wms import AddWMSMenuButton
from .widgets.draw import DrawerWidget
from .widgets.save import SaveFileWidget
from .widgets.files import OpenFileTabs
from .widgets.layer import AutoUpdateLayerMenuButton
from .widgets.utils import get_cmap_pixmaps


class ControlTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, parent=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.parent = parent

        tab1 = QtWidgets.QWidget()
        tab1layout = QtWidgets.QVBoxLayout()

        peektabs = PeekTabs(parent=self.parent)
        tab1layout.addWidget(peektabs)

        try:
            addwms = AddWMSMenuButton(m=self.m, new_layer=True)
        except:
            addwms = QtWidgets.QPushButton("WMS services unavailable")
        tab1layout.addWidget(addwms)

        tab1layout.addStretch(1)
        tab1layout.addWidget(SaveFileWidget(parent=self.parent))

        tab1.setLayout(tab1layout)

        self.tab1 = tab1
        self.tab2 = OpenFileTabs(parent=self.parent)
        self.tab3 = DrawerWidget(parent=self.parent)

        self.tab6 = ArtistEditor(m=self.m)

        self.addTab(self.tab1, "Compare")
        self.addTab(self.tab6, "Edit")
        self.addTab(self.tab2, "Open Files")
        if hasattr(self.m.util, "draw"):  # for future "draw" capabilities
            self.addTab(self.tab3, "Draw Shapes")

        # re-populate artists on tab-change
        self.currentChanged.connect(self.tabchanged)

        self.setAcceptDrops(True)

    def tabchanged(self):
        if self.currentWidget() == self.tab6:
            self.tab6.populate()
            self.tab6.populate_layer()

    @property
    def m(self):
        return self.parent.m

    def dragEnterEvent(self, e):
        # switch to open-file-tab on drag-enter
        # (the open-file-tab takes over from there!)
        self.setCurrentWidget(self.tab2)
        self.tab2.setCurrentIndex(0)


class ToolBar(QtWidgets.QToolBar):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m

        logo = QtGui.QPixmap(str(iconpath / "logo.png"))
        logolabel = QtWidgets.QLabel()
        logolabel.setMaximumHeight(25)
        logolabel.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        logolabel.setPixmap(
            logo.scaled(logolabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

        showlayer = AutoUpdateLayerMenuButton(m=self.m)

        b_close = QtWidgets.QToolButton()
        b_close.setAutoRaise(True)
        b_close.setFixedSize(25, 25)
        b_close.setText("🞫")
        b_close.clicked.connect(self.close_button_callback)

        self.transparentQ = QtWidgets.QToolButton()
        self.transparentQ.setStyleSheet("border:none")
        self.transparentQ.setToolTip("Make window semi-transparent.")
        self.transparentQ.setIcon(QtGui.QIcon(str(iconpath / "eye_closed.png")))

        space = QtWidgets.QWidget()
        space.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

        self.addWidget(self.transparentQ)
        self.addWidget(space)
        self.addWidget(showlayer)
        self.addWidget(logolabel)
        self.addWidget(b_close)

        self.setMovable(False)

        self.setStyleSheet(
            "QToolBar{border: none; spacing:20px;}"
            'QToolButton[autoRaise="true"]{text-align:center; color: red;}'
            "QPushButton{border:none;}"
        )
        self.setContentsMargins(5, 0, 0, 5)

    def close_button_callback(self):
        self.window().close()


class transparentWindow(ResizableWindow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_alpha = 0.25

        # make sure the window does not steal focus from the matplotlib-canvas
        # on show (otherwise callbacks are inactive as long as the window is focused!)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog | Qt.WindowStaysOnTopHint
        )

    def focusInEvent(self, e):
        self.setWindowOpacity(1)
        super().focusInEvent(e)

    def focusOutEvent(self, e):
        if not self.isActiveWindow():
            self.setWindowOpacity(self.out_alpha)
        super().focusInEvent(e)


class MenuWindow(transparentWindow):

    cmapsChanged = pyqtSignal()

    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        # clear the colormaps-dropdown pixmap cache if the colormaps have changed
        # (the pyqtSignal is emmited by Maps-objects if a new colormap is registered)
        self.cmapsChanged.connect(lambda: get_cmap_pixmaps.cache_clear())

        self.toolbar = ToolBar(m=self.m)
        self.toolbar.transparentQ.clicked.connect(self.cb_transparentQ)
        self.addToolBar(self.toolbar)

        tabs = ControlTabs(parent=self)
        tabs.setMouseTracking(True)

        self.setStyleSheet(
            """QToolTip {
                                font-family: "SansSerif";
                                font-size:10;
                                background-color: rgb(53, 53, 53);
                                color: white;
                                border: none;
                                }"""
        )
        self.cb_transparentQ()

        sizegrip = QtWidgets.QSizeGrip(self)

        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.addWidget(tabs)
        menu_layout.addWidget(sizegrip, 0, QtCore.Qt.AlignBottom | QtCore.Qt.AlignRight)

        menu_widget = QtWidgets.QWidget()
        menu_widget.setLayout(menu_layout)

        # prevent context-menu's from appearing to avoid the "hide toolbar"
        # context menu when right-clicking the toolbar
        self.setContextMenuPolicy(Qt.NoContextMenu)

        self.setCentralWidget(menu_widget)

        self.show()

    def cb_transparentQ(self):
        if self.out_alpha == 1:
            self.out_alpha = 0.25
            self.setFocus()
            self.toolbar.transparentQ.setIcon(
                QtGui.QIcon(str(iconpath / "eye_closed.png"))
            )

        else:
            self.out_alpha = 1
            self.setFocus()
            self.toolbar.transparentQ.setIcon(
                QtGui.QIcon(str(iconpath / "eye_open.png"))
            )

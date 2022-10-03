from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, pyqtSignal

from .base import transparentWindow
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
        self.tab_open = OpenFileTabs(parent=self.parent)
        self.tab3 = DrawerWidget(parent=self.parent)

        self.tab_edit = ArtistEditor(m=self.m)

        self.addTab(self.tab1, "Compare")
        self.addTab(self.tab_edit, "Edit")
        self.addTab(self.tab_open, "Open Files")
        if hasattr(self.m.util, "draw"):  # for future "draw" capabilities
            self.addTab(self.tab3, "Draw Shapes")

        # re-populate artists on tab-change
        self.currentChanged.connect(self.tabchanged)

        self.setAcceptDrops(True)

    def tabchanged(self):
        if self.currentWidget() == self.tab_edit:
            self.tab_edit.populate()
            self.tab_edit.populate_layer()

            # activate the currently visible layer in the editor-tabs
            try:
                idx = next(
                    i
                    for i in range(self.tab_edit.tabs.count())
                    if self.tab_edit.tabs.tabText(i) == self.m.BM._bg_layer
                )
                self.tab_edit.tabs.setCurrentIndex(idx)
            except StopIteration:
                pass

    @property
    def m(self):
        return self.parent.m

    def dragEnterEvent(self, e):
        self.tab_open.starttab.dragEnterEvent(e)

    def dragLeaveEvent(self, e):
        self.tab_open.starttab.dragLeaveEvent(e)

    def dropEvent(self, e):
        self.tab_open.starttab.dropEvent(e)


class MenuWindow(transparentWindow):

    cmapsChanged = pyqtSignal()

    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        # clear the colormaps-dropdown pixmap cache if the colormaps have changed
        # (the pyqtSignal is emmited by Maps-objects if a new colormap is registered)
        self.cmapsChanged.connect(lambda: get_cmap_pixmaps.cache_clear())

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

        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.addWidget(tabs)
        menu_widget = QtWidgets.QWidget()
        menu_widget.setLayout(menu_layout)

        statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(statusbar)

        # prevent context-menu's from appearing to avoid the "hide toolbar"
        # context menu when right-clicking the toolbar
        self.setContextMenuPolicy(Qt.NoContextMenu)

        self.setCentralWidget(menu_widget)

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt, pyqtSignal

from .base import transparentWindow

from .widgets.peek import PeekTabs
from .widgets.editor import ArtistEditor
from .widgets.wms import AddWMSMenuButton
from .widgets.save import SaveFileWidget
from .widgets.files import OpenFileTabs
from .widgets.utils import get_cmap_pixmaps
from .widgets.extent import SetExtentToLocation


class ControlTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        tab1 = QtWidgets.QWidget()
        tab1layout = QtWidgets.QVBoxLayout()

        peektabs = PeekTabs(m=self.m)
        tab1layout.addWidget(peektabs)

        try:
            addwms = AddWMSMenuButton(m=self.m, new_layer=True)
        except:
            addwms = QtWidgets.QPushButton("WMS services unavailable")
        tab1layout.addWidget(addwms)

        setextent = SetExtentToLocation(m=self.m)
        tab1layout.addWidget(setextent)

        tab1layout.addStretch(1)
        save = SaveFileWidget(m=self.m)
        tab1layout.addWidget(save)

        tab1.setLayout(tab1layout)

        self.tab1 = tab1
        self.tab_open = OpenFileTabs(m=self.m)

        self.tab_edit = ArtistEditor(m=self.m)

        self.addTab(self.tab1, "Compare")
        self.addTab(self.tab_edit, "Edit")
        self.addTab(self.tab_open, "Open Files")

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

    def dragEnterEvent(self, e):
        self.tab_open.dragEnterEvent(e)

    def dragLeaveEvent(self, e):
        self.tab_open.dragLeaveEvent(e)

    def dropEvent(self, e):
        self.tab_open.dropEvent(e)


class MenuWindow(transparentWindow):

    cmapsChanged = pyqtSignal()

    def __init__(self, *args, m=None, **kwargs):
        # assign m before calling the init of the transparentWindow
        # to show the layer-selector!
        self.m = m

        # indicator if help-tooltips should be displayed or not
        # (toggled by a toolbar checkbox)
        self.showhelp = False

        super().__init__(*args, m=self.m, **kwargs)

        # clear the colormaps-dropdown pixmap cache if the colormaps have changed
        # (the pyqtSignal is emmited by Maps-objects if a new colormap is registered)
        self.cmapsChanged.connect(lambda: get_cmap_pixmaps.cache_clear())

        tabs = ControlTabs(m=self.m)
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

        sh = self.sizeHint()
        self.resize(int(sh.width() * 1.35), sh.height())

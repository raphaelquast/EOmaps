from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QKeySequence

# TODO make sure a QApplication has been instantiated
app = QtWidgets.QApplication.instance()
if app is None:
    # if it does not exist then a QApplication is created
    app = QtWidgets.QApplication([])


from .base import transparentWindow
from .widgets.peek import PeekTabs
from .widgets.editor import ArtistEditor
from .widgets.wms import AddWMSMenuButton
from .widgets.save import SaveFileWidget
from .widgets.files import OpenFileTabs, OpenDataStartTab
from .widgets.utils import get_cmap_pixmaps
from .widgets.extent import SetExtentToLocation
from .widgets.click_callbacks import ClickCallbacks


class OpenFileButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        OpenDataStartTab.enterEvent(self, e)


class Tab1(QtWidgets.QWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        peektabs = PeekTabs(m=self.m)
        setextent = SetExtentToLocation(m=self.m)
        save = SaveFileWidget(m=self.m)

        click_cbs = ClickCallbacks(m=self.m)

        try:
            addwms = AddWMSMenuButton(m=self.m, new_layer=True)
        except:
            addwms = QtWidgets.QPushButton("WMS services unavailable")

        self.open_file_button = OpenFileButton("Open File")
        self.open_file_button.setFixedSize(self.open_file_button.sizeHint())

        l2 = QtWidgets.QHBoxLayout()
        l2.addWidget(addwms)
        l2.addWidget(self.open_file_button)
        l2.addStretch(1)
        l2.addWidget(setextent)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(peektabs)
        layout.addLayout(l2)
        layout.addStretch(1)
        layout.addWidget(click_cbs)
        layout.addWidget(save)

        self.setLayout(layout)


class ControlTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        self.tab1 = Tab1(m=self.m)
        self.tab_open = OpenFileTabs(m=self.m)

        # connect the open-file-button to the button from the "Open Files" tab
        self.tab1.open_file_button.clicked.connect(self.trigger_open_file_button)

        self.tab_edit = ArtistEditor(m=self.m)

        self.addTab(self.tab1, "Compare")
        self.addTab(self.tab_edit, "Edit")
        self.addTab(self.tab_open, "Open Files")

        # re-populate artists on tab-change
        self.currentChanged.connect(self.tabchanged)

        self.setAcceptDrops(True)

    @pyqtSlot()
    def trigger_open_file_button(self):
        self.tab_open.starttab.open_button.clicked.emit()

    @pyqtSlot()
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
        self.cmapsChanged.connect(self.clear_pixmap_cache)

        self.tabs = ControlTabs(m=self.m)
        self.tabs.setMouseTracking(True)

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
        menu_layout.addWidget(self.tabs)
        menu_widget = QtWidgets.QWidget()
        menu_widget.setLayout(menu_layout)

        statusbar = QtWidgets.QStatusBar(self)
        self.setStatusBar(statusbar)

        # prevent context-menu's from appearing to avoid the "hide toolbar"
        # context menu when right-clicking the toolbar
        self.setContextMenuPolicy(Qt.NoContextMenu)

        self.setCentralWidget(menu_widget)

        # sh = self.sizeHint()
        # self.resize(int(sh.width() * 1.35), sh.height())

    def show(self):
        super().show()
        # make sure show/hide shortcut also works if the widget is active
        # we need to re-assign this on show to make sure it is always assigned
        # when the window is shown
        self.shortcut = QtWidgets.QShortcut(QKeySequence("w"), self)
        self.shortcut.setContext(Qt.WindowShortcut)
        self.shortcut.activated.connect(self.toggle_show)
        self.shortcut.activatedAmbiguously.connect(self.toggle_show)

    @pyqtSlot()
    def toggle_show(self):
        if self.isVisible():
            self.hide()
            self.m._indicate_companion_map(False)
        else:
            self.show()
            self.activateWindow()
            self.m._indicate_companion_map(True)

    @pyqtSlot()
    def clear_pixmap_cache(self):
        get_cmap_pixmaps.cache_clear()

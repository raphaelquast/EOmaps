from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize
from PyQt5.QtGui import QKeySequence

# TODO make sure a QApplication has been instantiated
app = QtWidgets.QApplication.instance()
if app is None:
    # if it does not exist then a QApplication is created
    app = QtWidgets.QApplication([])

from .base import AlwaysOnTopWindow
from .widgets.peek import PeekTabs
from .widgets.editor import ArtistEditor
from .widgets.wms import AddWMSMenuButton
from .widgets.save import SaveFileWidget
from .widgets.files import OpenFileTabs, OpenDataStartTab
from .widgets.utils import get_cmap_pixmaps
from .widgets.extent import SetExtentToLocation
from .widgets.click_callbacks import ClickCallbacks

from .widgets.editor import LayerTabBar
from .widgets.utils import EditLayoutButton


class OpenFileButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        OpenDataStartTab.enterEvent(self, e)


class CompareTab(QtWidgets.QWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        peektabs = PeekTabs(m=self.m)

        setextent = SetExtentToLocation(m=self.m)
        self.save_widget = SaveFileWidget(m=self.m)

        # -------------
        self.layer_tabs = LayerTabBar(self.m, populate=True)
        # make sure the tab-widget auto-expands properly
        self.layer_tabs.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Minimum
        )
        self.layer_tabs.setTabsClosable(False)
        # -------------

        self.click_cbs = ClickCallbacks(m=self.m)

        # add wms button
        try:
            addwms = AddWMSMenuButton(m=self.m, new_layer=True)
            addwms.wmsLayerCreated.connect(
                self.layer_tabs.repopulate_and_activate_current
            )
        except:
            addwms = None

        # open file button
        self.open_file_button = OpenFileButton("Open File")
        self.open_file_button.setFixedSize(self.open_file_button.sizeHint())

        # edit layout button
        b_edit = EditLayoutButton("Edit layout", m=self.m)
        width = b_edit.fontMetrics().boundingRect(b_edit.text()).width()
        b_edit.setFixedWidth(width + 30)

        # layer dropdown button
        from .widgets.layer import AutoUpdateLayerMenuButton

        self.layer_button = AutoUpdateLayerMenuButton(m=self.m)

        options_layout = QtWidgets.QHBoxLayout()
        if addwms:
            options_layout.addWidget(addwms)
        options_layout.addWidget(self.open_file_button)
        options_layout.addWidget(b_edit)
        options_layout.addStretch(1)
        options_layout.addWidget(setextent)

        layer_tab_layout = QtWidgets.QHBoxLayout()
        layer_tab_layout.setAlignment(Qt.AlignLeft)
        # layer_tab_layout.addWidget(
        #     QtWidgets.QLabel(
        #         "<b>Layers: </b><br>" "<small><code> [ctrl / shift] </code></small>"
        #     )
        # )
        layer_tab_layout.addWidget(self.layer_button)
        layer_tab_layout.addWidget(self.layer_tabs)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(peektabs)
        layout.addWidget(self.click_cbs)
        layout.addLayout(options_layout)
        layout.addStretch(1)
        layout.addLayout(layer_tab_layout)
        layout.addWidget(self.save_widget)

        self.setLayout(layout)


class ControlTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m

        self.tab_compare = CompareTab(m=self.m)
        self.tab_open = OpenFileTabs(m=self.m)
        self.tab_edit = ArtistEditor(m=self.m)

        # connect the open-file-button to the button from the "Open Files" tab
        self.tab_compare.open_file_button.clicked.connect(self.trigger_open_file_button)
        self.tab_edit.edit_actions.open_file_button.clicked.connect(
            self.trigger_open_file_button
        )

        self.addTab(self.tab_compare, "Compare")
        self.addTab(self.tab_edit, "Edit")
        self.addTab(self.tab_open, "Data")

        # re-populate artists on tab-change
        self.currentChanged.connect(self.tabchanged)

        self.setAcceptDrops(True)

        self.setStyleSheet(
            """
            ControlTabs {
                font-size: 10pt;
                font-weight: bold;
            }

            QTabWidget::pane {
              border: 0px;
              top:0px;
              background: rgb(240, 240, 240);
              border-radius: 10px;
            }

            QTabBar::tab {
              background: rgb(240, 240, 240);
              border: 0px;
              padding: 3px;
              padding-bottom: 6px;
              padding-left: 6px;
              padding-right: 6px;
              margin-left: 10px;
              margin-bottom: -2px;
              border-radius: 4px;
            }

            QTabBar::tab:selected {
              background: rgb(200, 200, 200);
              border:1px solid rgb(150, 150, 150);
              margin-bottom: 2px;
            }
            """
        )

    @pyqtSlot()
    def trigger_open_file_button(self):
        self.tab_open.starttab.open_button.clicked.emit()

    @pyqtSlot()
    def tabchanged(self):

        if self.currentWidget() == self.tab_compare:
            self.tab_compare.layer_tabs.repopulate_and_activate_current()

        elif self.currentWidget() == self.tab_edit:
            self.tab_edit.artist_tabs.repopulate_and_activate_current()

    def dragEnterEvent(self, e):
        self.tab_open.dragEnterEvent(e)

    def dragLeaveEvent(self, e):
        self.tab_open.dragLeaveEvent(e)

    def dropEvent(self, e):
        self.tab_open.dropEvent(e)


class MenuWindow(AlwaysOnTopWindow):

    cmapsChanged = pyqtSignal()
    clipboardKwargsChanged = pyqtSignal()
    annotationSelected = pyqtSignal()
    annotationEdited = pyqtSignal()
    dataPlotted = pyqtSignal()

    def __init__(self, *args, m=None, **kwargs):

        # assign m before calling the init of the AlwaysOnTopWindow
        # to show the layer-selector!
        self.m = m

        # indicator if help-tooltips should be displayed or not
        # (toggled by a toolbar checkbox)
        self.showhelp = False

        super().__init__(*args, m=self.m, **kwargs)

        self.tabs = ControlTabs(m=self.m)
        self.tabs.setMouseTracking(True)

        # self.cb_transparentQ()

        menu_layout = QtWidgets.QVBoxLayout()
        menu_layout.addWidget(self.tabs)
        menu_widget = QtWidgets.QWidget()
        menu_widget.setLayout(menu_layout)

        statusbar = QtWidgets.QStatusBar(self)
        statusbar.addPermanentWidget(QtWidgets.QLabel(f"EOmaps v{self.m.__version__}"))

        self.setStatusBar(statusbar)

        # prevent context-menu's from appearing to avoid the "hide toolbar"
        # context menu when right-clicking the toolbar
        self.setContextMenuPolicy(Qt.NoContextMenu)

        self.setCentralWidget(menu_widget)

        # sh = self.sizeHint()
        # self.resize(int(sh.width() * 1.35), sh.height())

        # clear the colormaps-dropdown pixmap cache if the colormaps have changed
        # (the pyqtSignal is emmited by Maps-objects if a new colormap is registered)
        self.cmapsChanged.connect(self.clear_pixmap_cache)

        # set save-file args to values set as clipboard kwargs
        self.clipboardKwargsChanged.connect(
            self.tabs.tab_compare.save_widget.set_export_props
        )

        self.annotationSelected.connect(
            self.tabs.tab_edit.addannotation.set_selected_annotation_props
        )

        self.annotationEdited.connect(
            self.tabs.tab_edit.addannotation.set_edited_annotation_props
        )

        self.dataPlotted.connect(self.tabs.tab_compare.click_cbs.populate_dropdown)
        self.dataPlotted.connect(self.tabs.tab_compare.click_cbs.update_buttons)

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

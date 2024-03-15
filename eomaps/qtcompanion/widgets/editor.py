# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

import logging
from textwrap import dedent

from qtpy import QtCore, QtWidgets, QtGui
from qtpy.QtCore import Qt, Signal, Slot, QPointF
from qtpy.QtGui import QFont

from matplotlib.colors import to_rgba_array

from ...inset_maps import InsetMaps
from ...helpers import _key_release_event
from ..common import iconpath
from ..base import BasicCheckableToolButton, NewWindow
from .wms import AddWMSMenuButton
from .utils import ColorWithSlidersWidget, GetColorWidget, AlphaSlider
from .annotate import AddAnnotationWidget
from .draw import DrawerTabs
from .files import OpenDataStartTab
from .layer import AutoUpdateLayerMenuButton

_log = logging.getLogger(__name__)


class AddFeaturesMenuButton(QtWidgets.QPushButton):
    FeatureAdded = Signal(str)

    def __init__(self, *args, m=None, sub_menu="preset", **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m
        self._menu_fetched = False

        self.sub_menu = sub_menu
        # the layer to which features are added
        self.layer = None

        self.props = dict(
            # alpha = 1,
            facecolor="r",
            edgecolor="g",
            linewidth=1,
            zorder=0,
        )

        self.setText("●   " + self.sub_menu.capitalize().ljust(8))
        # self.setMaximumWidth(200)

        width = self.fontMetrics().boundingRect(self.text()).width()
        self.setFixedWidth(width + 30)

        self.feature_menu = QtWidgets.QMenu()
        self.feature_menu.setStyleSheet(
            """
            QMenu {
                menu-scrollable: 1;
            }
            """
        )

        self.setStyleSheet(
            """
            QPushButton {
                border: 1px solid rgb(140, 140, 140);
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: rgb(210, 210, 210);
                font-weight: bold;
            }
            """
        )

        self.feature_menu.aboutToShow.connect(self.fetch_menu)

        self.setMenu(self.feature_menu)
        self.clicked.connect(self.show_menu)

    def fetch_menu(self):
        if self._menu_fetched:
            return

        features = getattr(self.m.add_feature, self.sub_menu)

        feature_types = [i for i in dir(features) if not i.startswith("_")]

        def grouped(iterable, splits=2):
            # group objects by prefix (before last underscore)
            levels = dict()

            special_prefixes = ["bathymetry"]
            for i in iterable:
                if i.count("_") >= 2 and i.split("_")[0] not in special_prefixes:
                    prefix = "_".join(i.split("_", 2)[:2])
                else:
                    prefix = i.split("_")[0]

                levels.setdefault(prefix, []).append(i)

            return levels

        feature_types = grouped(sorted(feature_types))

        for feature_group, sub_features in feature_types.items():
            if len(sub_features) == 1:
                feature = sub_features[0]
                action = self.feature_menu.addAction(str(feature))
                action.triggered.connect(
                    self.menu_callback_factory(self.sub_menu, feature)
                )
            else:
                sub_menu = self.feature_menu.addMenu(feature_group)
                for feature in sub_features:
                    action = sub_menu.addAction(str(feature))
                    action.triggered.connect(
                        self.menu_callback_factory(self.sub_menu, feature)
                    )

        self._menu_fetched = True

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>NaturalEarth Features</h3>"
                "Add NaturalEarth features to the map."
                "<p>"
                "The feature will be added to the "
                "<b><font color=#c80000>currently selected tab</font></b> "
                "in the tab-bar below."
                "<p>"
                "NOTE: this is not necessarily the visible layer!",
            )

        super().enterEvent(e)

    @Slot()
    def show_menu(self):
        self.feature_menu.popup(self.mapToGlobal(self.menu_button.pos()))

    def set_layer(self, layer):
        self.layer = layer

    def menu_callback_factory(self, featuretype, feature):
        @Slot()
        def cb():
            # TODO set the layer !!!!
            if self.layer is None:
                layer = self.m.BM.bg_layer
            else:
                layer = self.layer

            if layer.startswith("_") and "|" in layer:
                self.window().statusBar().showMessage(
                    "Adding features to temporary multi-layers is not supported!", 5000
                )

                return
            try:
                f = getattr(getattr(self.m.add_feature, featuretype), feature)
                if featuretype == "preset":
                    f(layer=layer, **f.kwargs)
                else:
                    f(layer=layer, **self.props)

                self.m.f.canvas.draw_idle()
                self.FeatureAdded.emit(str(layer))
            except Exception:
                _log.error(
                    "---- adding the feature",
                    featuretype,
                    feature,
                    "did not work----",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

        return cb


class ZorderInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Zorder</h3>"
                "Set the zorder of the artist (e.g. the vertical stacking "
                "order with respect to other artists on the same layer)",
            )


class RemoveArtistToolButton(QtWidgets.QToolButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Remove Artist</h3>"
                "Remove the artist from the axis. (This <b>can not</b> be undone!)",
            )


class ShowHideToolButton(QtWidgets.QToolButton):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Show/Hide Artist</h3>"
                "Make the corresponding artist visible (eye open) "
                "or invisible (eye closed).",
            )


class LineWidthInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Linewidth</h3>" "Set the linewidth of the corresponding artist.",
            )


class AlphaInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Transparency</h3>" "Set the alpha-transparency of the artist.",
            )


class AddFeatureWidget(QtWidgets.QFrame):
    def __init__(self, m=None):

        super().__init__()
        # self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)

        self.m = m

        self.selectors = [
            AddFeaturesMenuButton(m=self.m, sub_menu="preset"),
            AddFeaturesMenuButton(m=self.m, sub_menu="cultural"),
            AddFeaturesMenuButton(m=self.m, sub_menu="physical"),
        ]
        for s in self.selectors:
            s.clicked.connect(self.update_props)
            s.menu().aboutToShow.connect(self.update_props)

        self.colorselector = ColorWithSlidersWidget(facecolor="#aaaa7f")

        self.zorder = ZorderInput("0")
        validator = QtGui.QIntValidator()
        self.zorder.setValidator(validator)
        self.zorder.setMaximumWidth(30)
        self.zorder.setMaximumHeight(20)
        self.zorder.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )
        self.zorder.textChanged.connect(self.update_props)

        zorder_label = QtWidgets.QLabel("zorder: ")
        zorder_label.setSizePolicy(
            QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        )

        zorder_layout = QtWidgets.QHBoxLayout()
        zorder_layout.addWidget(zorder_label)
        zorder_layout.addWidget(self.zorder, 0)
        zorder_label.setAlignment(Qt.AlignRight | Qt.AlignCenter)

        layout_buttons = QtWidgets.QVBoxLayout()
        for s in self.selectors:
            layout_buttons.addWidget(s)

        layout_buttons.addLayout(zorder_layout)

        layout = QtWidgets.QHBoxLayout()
        layout.addLayout(layout_buttons)
        layout.addWidget(self.colorselector)
        layout.setAlignment(Qt.AlignLeft | Qt.AlignCenter)

        layout_tight = QtWidgets.QVBoxLayout()
        layout_tight.addStretch(1)
        layout_tight.addLayout(layout)
        layout_tight.addStretch(1)

        self.setLayout(layout_tight)

    @Slot()
    def update_props(self):
        # don't specify alpha! it interferes with the alpha of the colors!

        for s in self.selectors:
            s.props.update(
                dict(
                    facecolor=self.colorselector.facecolor.getRgbF(),
                    edgecolor=self.colorselector.edgecolor.getRgbF(),
                    linewidth=self.colorselector.linewidth,
                    zorder=int(self.zorder.text()),
                    # alpha = self.colorselector.alpha,
                )
            )

    def set_linewidth_slider_stylesheet(self):
        self.linewidthslider.setStyleSheet(
            """
            QSlider::handle:horizontal {
                background-color: black;
                border: none;
                border-radius: 0px;
                height: 10px;
                width: 5px;
                margin: -10px 0;
                padding: -10px 0px;
            }
            QSlider::groove:horizontal {
                border-radius: 1px;
                height: 1px;
                margin: 5px;
                background-color: rgba(0,0,0,50);
            }
            QSlider::groove:horizontal:hover {
                background-color: rgba(0,0,0,255);
            }
            """
        )

    def set_alpha_slider_stylesheet(self):
        a = self.alphaslider.alpha * 255
        s = 12
        self.alphaslider.setStyleSheet(
            f"""
            QSlider::handle:horizontal {{
                background-color: rgba(0,0,0,{a});
                border: 1px solid black;
                border-radius: {s//2}px;
                height: {s}px;
                width: {s}px;
                margin: -{s//2}px 0px;
                padding: -{s//2}px 0px;
            }}
            QSlider::groove:horizontal {{
                border-radius: 1px;
                height: 1px;
                margin: 5px;
                background-color: rgba(0,0,0,50);
            }}
            QSlider::groove:horizontal:hover {{
                background-color: rgba(0,0,0,255);
            }}
            """
        )

    def update_alphaslider(self):
        # to always round up to closest int use -(-x//1)
        self.alphaslider.setValue(int(-(-self.colorselector.alpha * 100 // 1)))


class OpenFileButton(QtWidgets.QPushButton):
    def enterEvent(self, e):
        OpenDataStartTab.enterEvent(self, e)


class PlusButton(BasicCheckableToolButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.set_icons(
            normal_icon=str(iconpath / "plus.png"),
            hoover_icon=str(iconpath / "plus_hoover.png"),
        )

        self.setFixedSize(30, 30)
        self.setCheckable(False)

        self.setStyleSheet("PlusButton {border: 0}")


class ArtistInfoDialog(NewWindow):
    def __init__(self, info_text="-", source_code="", **kwargs):
        super().__init__(**kwargs)
        self.info_text = info_text
        self.source_code = source_code

        self.setWindowTitle("Info")
        self.setWindowIcon(QtGui.QIcon(str(iconpath / "info.png")))
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Dialog
        )

        if self.info_text:
            self.info_widget = QtWidgets.QTextBrowser()
            self.info_widget.setOpenExternalLinks(True)
            self.info_widget.setMarkdown(dedent(self.info_text))
            self.info_widget.setStyleSheet(
                """
                QTextBrowser {
                    border-radius: 20px;
                    border: 0px;
                    }
                """
            )

            self.layout.addWidget(self.info_widget)

        code_label = QtWidgets.QLabel("<b>Code to reproduce:</b>")
        self.source_code_widget = QtWidgets.QLabel()
        if self.source_code:
            self.source_code_widget = QtWidgets.QLabel()
            self.source_code_widget.setText(dedent(self.source_code))
            self.source_code_widget.setTextInteractionFlags(Qt.TextSelectableByMouse)
            self.source_code_widget.setWordWrap(True)
            self.source_code_widget.setStyleSheet(
                """
                QLabel {
                    background-color : rgb(220, 220, 220);
                    border-radius: 4px;
                    min-height: 10px;
                    border: 1px solid black;
                    color : black;
                    padding: 2px 2px 2px 2px;
                    }
                """
            )
            self.layout.addWidget(code_label)
            self.layout.addWidget(self.source_code_widget)


_last_info_button = None
_init_size = (450, 300)
_init_pos = None


class ArtistInfoButton(BasicCheckableToolButton):
    def __init__(self, *args, info_text=None, source_code=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.info_text = info_text
        self.source_code = source_code

        self.set_icons(
            normal_icon=str(iconpath / "info.png"),
            hoover_icon=str(iconpath / "info_hoover.png"),
            checked_icon=str(iconpath / "info_checked.png"),
        )

        self.setFixedSize(13, 13)
        self.setCheckable(True)
        self.setStyleSheet("ArtistInfoButton {border: 0}")

        self.clicked.connect(self.on_click)

        # use a lambda here to make sure the closure keeps "self" alive
        # so that we can call "self._on_destroyed()" (otherwise "self" might already
        # be garbage-collected)
        self.destroyed.connect(lambda: self._on_destroyed())

    def _on_destroyed(self):
        # Since buttons are destroyed and re-created on new population of the
        # editor tabs, the widget must be closed to make sure that the
        # button state always indicates the currently active info-artist.
        global _last_info_button
        if _last_info_button is not None:
            _last_info_button._info_widget.close()
            _last_info_button = None

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Map Feature Info</h3>"
                "Click to get a popup that provides additional "
                "information on the feature."
                "<ul>"
                "<li>References / Sources</li>"
                "<li>License-info</li>"
                "<li>Code to reproduce</li>"
                "<li>...</li>"
                "</ul>",
            )

    @Slot()
    def on_click(self, *args, **kwargs):
        global _last_info_button
        global _init_size
        global _init_pos

        if _last_info_button is not None:
            try:
                _init_pos = _last_info_button._info_widget.pos()
                _init_size = (
                    _last_info_button._info_widget.width(),
                    _last_info_button._info_widget.height(),
                )
                _last_info_button.setChecked(False)
                _last_info_button._info_widget.close()
            except Exception:
                _log.debug(
                    "There was a problem while trying to close an info-popup",
                    exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
                )

            _last_info_button = None

        if self.info_text is None and self.source_code is None:
            return

        # remember the last clicked button
        _last_info_button = self

        self._info_widget = ArtistInfoDialog(
            parent=self.window(),
            title="Map Feature Info",
            info_text=self.info_text,
            source_code=self.source_code,
            on_close=lambda: self.setChecked(False),
        )
        self.setChecked(True)
        self._info_widget.show()

        if _init_pos:
            self._info_widget.move(_init_pos)
        if _init_size:
            self._info_widget.resize(*_init_size)


class LayerArtistTabs(QtWidgets.QTabWidget):
    plusClicked = Signal()

    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m
        self.margin_left = 25
        self.margin_right = 60

        # Plus Button
        self.plus_button = PlusButton(self)
        self.plus_button.clicked.connect(self.plusClicked.emit)

        self.layer_button = AutoUpdateLayerMenuButton(self, m=self.m)
        self.layer_button.setFixedWidth(30)

        self.move_plus_button()  # Move to the correct location
        self.move_layer_button()  # Move to the correct location

    def move_plus_button(self, *args, **kwargs):
        """Move the plus button to the correct location."""
        # Set the plus button location in a visible area
        h = self.geometry().top()
        w = self.window().width()

        self.plus_button.move(w - self.margin_right, -3)

    def move_layer_button(self, *args, **kwargs):
        """Move the plus button to the correct location."""
        # Set the plus button location in a visible area
        h = self.geometry().top()

        self.layer_button.move(-5, 2)

    def paintEvent(self, *args, **kwargs):
        # make some space for the + button
        self.tabBar().setFixedWidth(
            self.window().width() - self.margin_left - self.margin_right
        )
        self.tabBar().move(self.margin_left, 0)
        self.move_plus_button()
        self.move_layer_button()
        super().paintEvent(*args, **kwargs)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Background Layers and Artists</h3>"
                "Each tab represents a layer of the map."
                "<ul>"
                "<li>The tab-order represents the stacking order of the layers.</li>"
                "<li><b>drag</b> tabs to change the layer ordering!</li>"
                "</ul>"
                "<ul>"
                "<li><b>click</b> on a tab to select it (to add/remove features)</li>"
                "<li><b>control + click</b> on a tab to make it the visible layer.</li>"
                "<li><b>shift + click</b> on tabs to make multiple layers visible.</li>"
                "</ul>"
                "The tab-entries show all individual <b>background</b> artists of the "
                "selected layer. (background artists are static map-elements that are "
                "only re-drawn on pan/zoom or resize events)"
                "<br>"
                "Features and WebMaps created with the controls above are always "
                "added to the <b>currently selected tab</b>!<br>"
                "(indicated by a <b><font color=#c80000>red border</font></b>)",
            )


class OptionTabs(QtWidgets.QTabWidget):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Add Features / Add Annotations / Draw Shapes</h3>"
                "The tabs provide a set of convenience-functionalities to add basic "
                "features to the map."
                "<ul>"
                "<li><b>Add Features:</b> Add NaturalEarth features to the map.</li>"
                "<li><b>Add Annotations:</b> Add an arrow with a text-annotation "
                "to the map.</li>"
                "<li><b>Draw Shapes:</b> Draw basic shapes on the map and optionally "
                "save the shapes as geo-coded shapefiles.</li>"
                "</ul>",
            )


class LayerTransparencySlider(AlphaSlider):
    _alphas = dict()

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Layer Transparency</h3> Set the global layer transparency.",
            )


class LayerTabBar(QtWidgets.QTabBar):
    _number_of_min_tabs_for_size = 6
    _n_layer_msg_shown = False

    def __init__(self, m=None, populate=False, *args, **kwargs):
        """
        Parameters
        ----------
        m : eomaps.Maps
            the Maps object to use
        populate : bool, optional
            Indicator if the layer-tabs are automatically created or not.

            - Use True if ONLY tabs should be shown
            - Use False if tabs should contain widgets... (then the TabWidget
              will take care of creating tabs)

            The default is False.

        """

        super().__init__(*args, **kwargs)
        self.m = m

        # remove strange line on top of tabs
        # (see https://stackoverflow.com/a/33941638/9703451)
        self.setDrawBase(False)
        self.setExpanding(False)
        self.setElideMode(Qt.ElideRight)

        self._current_tab_idx = None
        self._current_tab_name = None

        self.setMovable(True)
        self.setUsesScrollButtons(True)

        self.tabBarClicked.connect(self.tabchanged)

        self.setTabsClosable(True)
        self.tabCloseRequested.connect(self.close_handler)

        self.tabMoved.connect(self.tab_moved)

        if populate:
            # re-populate tabs if a new layer is created
            # NOTE this is done by the TabWidget if tabs have content!!
            self.populate()
            # re-populate on show to make sure currently active layers are shown
            self.m.BM.on_layer(self.populate_on_layer, persistent=True)
            self.m._after_add_child.append(self.populate)
            self.m._on_show_companion_widget.append(self.populate)

        # set font properties before the stylesheet to avoid clipping of bold text!
        font = QFont("sans seriv", 8, QFont.Bold, False)
        self.setFont(font)

        self.setStyleSheet(
            """
            QTabWidget::pane {
              border: 0px;
              top:0px;
              background: rgb(200, 200, 200);
              border-radius: 10px;
            }

            QTabBar::tab {
              background: rgb(245, 245, 245);
              border: 1px solid black;
              padding: 3px;
              margin-left: 2px;
              margin-bottom: 0px;
              border-radius: 4px;
            }

            QTabBar::tab:selected {
              background: rgb(245, 245, 245);
              border: 1px solid black;
              margin-bottom: 0px;
            }
            """
        )

    def event(self, event):
        # don't show normal tooltips while showhelp is active
        # (they would cause the help-popups to disappear after ~ 1 sec)
        if event.type() == QtCore.QEvent.ToolTip and self.window().showhelp:
            return False

        return super().event(event)

    def mousePressEvent(self, event):
        # TODO a more clean implementation of this would be nice
        # explicitly handle control+click and shift+click events
        # to avoid activating the currently clicked tab
        # (we want to activate the currently active tab which is shifted to the
        # start-position!)
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if (
            modifiers == Qt.ControlModifier
            and event.button() == Qt.MouseButton.LeftButton
        ):

            idx = self.tabAt(event.pos())
            self.tabchanged(idx)
        elif (
            modifiers == Qt.ShiftModifier
            and event.button() == Qt.MouseButton.LeftButton
        ):
            idx = self.tabAt(event.pos())
            self.tabchanged(idx)
        else:
            super().mousePressEvent(event)

    @Slot()
    def get_tab_icon(self, color="red"):
        if isinstance(color, str):
            color = QtGui.QColor(color)
        elif isinstance(color, (list, tuple)):
            color = QtGui.QColor(*color)

        canvas = QtGui.QPixmap(20, 20)
        canvas.fill(Qt.transparent)

        painter = QtGui.QPainter(canvas)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)

        pencolor = QtGui.QColor(color)
        pencolor.setAlpha(100)
        painter.setPen(QtGui.QPen(pencolor, 2, Qt.SolidLine))
        painter.setBrush(QtGui.QBrush(color, Qt.SolidPattern))

        painter.drawEllipse(QPointF(10, 12), 7, 7)
        painter.end()

        icon = QtGui.QIcon(canvas)
        return icon

    # def sizeHint(self):
    #     # make sure the TabBar does not expand the window width
    #     hint = super().sizeHint()
    #     width = self.window().width()
    #     hint.setWidth(width)
    #     return hint

    def minimumTabSizeHint(self, index):
        # the minimum width of the tabs is determined such that at least
        # "_number_of_min_tabs_for_size"  tabs are visible.
        # (e.g. for the elide of long tab-names)

        hint = super().tabSizeHint(index)
        w = int(self.sizeHint().width() / self._number_of_min_tabs_for_size)
        hint.setWidth(w)
        return hint

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Layer Tabs</h3>"
                "Select, combine and re-arrange layers of the map. "
                "<ul>"
                "<li><b>ctrl + click:</b> make selected layer visible</li>"
                "<li><b>shift + click:</b> select multiple layers </li>"
                "<li><b>drag:</b> change the layer stacking-order. "
                "</ul>",
            )

    def repopulate_and_activate_current(self, *args, **kwargs):
        self.populate()

        # activate the currently visible layer tab
        try:
            idx = next(
                i for i in range(self.count()) if self.tabText(i) == self.m.BM._bg_layer
            )
            self.setCurrentIndex(idx)
        except StopIteration:
            pass

    @Slot()
    def tab_moved(self):
        # get currently active layers
        active_layers, alphas = self.m.BM._get_active_layers_alphas

        # get the name of the layer that was moved
        layer = self.tabText(self.currentIndex())
        if layer not in active_layers:
            return

        # get the current ordering of visible layers
        ntabs = self.count()
        layer_order = []
        for i in range(ntabs):
            txt = self.tabText(i)
            if txt in active_layers:
                layer_order.append(txt)

        # set the new layer-order
        if active_layers != layer_order:  # avoid recursions
            alpha_order = [alphas[active_layers.index(i)] for i in layer_order]
            self.m.show_layer(*zip(layer_order, alpha_order))

    @Slot(int)
    def close_handler(self, index):
        layer = self.tabText(index)

        self._msg = QtWidgets.QMessageBox(self)
        self._msg.setIcon(QtWidgets.QMessageBox.Question)

        self._msg.setWindowIcon(QtGui.QIcon(str(iconpath / "info.png")))

        self._msg.setText(f"Do you really want to delete the layer '{layer}'")
        self._msg.setWindowTitle(f"Delete layer: '{layer}'?")

        self._msg.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        self._msg.buttonClicked.connect(self.get_close_tab_cb(index))

        _ = self._msg.show()

    def get_close_tab_cb(self, index):
        @Slot()
        def cb():
            self._do_close_tab(index)

        return cb

    def _do_close_tab(self, index):

        if self._msg.standardButton(self._msg.clickedButton()) != self._msg.Yes:
            return

        layer = self.tabText(index)

        if self.m.layer == layer:
            _log.error("EOmaps: The base-layer cannot be deleted!")
            return

        # get currently active layers
        active_layers, alphas = self.m.BM._get_active_layers_alphas

        # cleanup the layer and remove any artists etc.
        for m in list(self.m._children):
            if layer == m.layer:
                m.cleanup()
                m.BM._bg_layers.pop(layer, None)

        # in case the layer was visible, try to activate a suitable replacement
        if layer in active_layers:
            # if possible, show the currently active multi-layer but without
            # the deleted layer
            layer_idx = active_layers.index(layer)
            active_layers.pop(layer_idx)
            alphas.pop(layer_idx)

            if len(active_layers) > 0:
                try:
                    self.m.show_layer(*zip(active_layers, alphas))
                except Exception:
                    pass
            else:
                # otherwise switch to the first available layer
                try:
                    switchlayer = next(
                        (
                            i
                            for i in self.m.BM._bg_artists
                            if layer not in self.m.BM._parse_multi_layer_str(i)[0]
                        )
                    )
                    self.m.show_layer(switchlayer)
                except StopIteration:
                    # don't allow deletion of last layer
                    _log.error("EOmaps: Unable to delete the last available layer!")
                    return

        if layer in list(self.m.BM._bg_artists):
            for a in self.m.BM._bg_artists[layer]:
                self.m.BM.remove_bg_artist(a)
                a.remove()
            del self.m.BM._bg_artists[layer]

        if layer in self.m.BM._bg_layers:
            del self.m.BM._bg_layers[layer]

        # also remove the layer from any layer-change/layer-activation triggers
        # (e.g. to deal with not-yet-fetched WMS services)

        for permanent, d in self.m.BM._on_layer_activation.items():
            if layer in d:
                del d[layer]

        for permanent, d in self.m.BM._on_layer_change.items():
            if layer in d:
                del d[layer]

        self.populate()

    def color_active_tab(self, m=None, layer=None, adjust_order=True):
        # defaultcolor = self.palette().color(self.foregroundRole())
        defaultcolor = QtGui.QColor(100, 100, 100)
        activecolor = QtGui.QColor(50, 150, 50)  # QtGui.QColor(0, 128, 0)
        multicolor = QtGui.QColor(50, 150, 50)  # QtGui.QColor(0, 128, 0)

        # get currently active layers
        active_layers, alphas = self.m.BM._get_active_layers_alphas

        for i in range(self.count()):
            selected_layer = self.tabText(i)
            color = activecolor if len(active_layers) == 1 else multicolor
            if selected_layer in active_layers:
                idx = active_layers.index(selected_layer)
                self.setTabTextColor(i, color)

                if alphas[idx] < 1:
                    color = QtGui.QColor(color)
                    color.setAlpha(int(alphas[idx] * 100))

                self.setTabIcon(i, self.get_tab_icon(color))
            else:
                self.setTabTextColor(i, defaultcolor)
                self.setTabIcon(i, QtGui.QIcon())

            if layer == selected_layer:
                self.setTabTextColor(i, activecolor)

        if adjust_order:
            # --- adjust the sort-order of the tabs to the order of the visible layers
            # disconnect tab_moved callback to avoid recursions
            self.tabMoved.disconnect(self.tab_moved)
            # to avoid issues with non-existent and private layers (e.g. the background
            # layer on savefig etc.) use the following strategy:
            # - go through the layers in reverse
            # - move each found layer to the position 0
            for cl in active_layers[::-1]:
                for i in range(self.count()):
                    layer = self.tabText(i)
                    if layer == cl:
                        self.moveTab(i, 0)
            # re-connect tab_moved callback
            self.tabMoved.connect(self.tab_moved)

    @Slot()
    def populate_on_layer(self, *args, **kwargs):
        lastlayer = getattr(self, "_last_populated_layer", "")
        currlayer = self.m.BM.bg_layer
        # only populate if the current layer is not part of the last set of layers
        # (e.g. to allow show/hide of selected layers without removing the tabs)
        if not self.m.BM._layer_is_subset(currlayer, lastlayer):
            self.populate(*args, **kwargs)
            self._last_populated_layer = currlayer
        else:
            # still update tab colors  (e.g. if layers are removed from multi)
            self.color_active_tab()

    @Slot()
    def populate(self, *args, **kwargs):
        if not self.isVisible():
            return

        self._current_tab_idx = self.currentIndex()
        self._current_tab_name = self.tabText(self._current_tab_idx)

        alllayers = set(self.m._get_layers())
        nlayers = len(alllayers)
        max_n_layers = self.m._companion_widget_n_layer_tabs
        if nlayers > max_n_layers:
            if not LayerTabBar._n_layer_msg_shown:
                _log.info(
                    "EOmaps-companion: The map has more than "
                    f"{max_n_layers} layers... only last active layers "
                    "are shown in the layer-tabs!"
                )
                LayerTabBar._n_layer_msg_shown = True

            # if more than max_n_layers layers are available, show only active tabs to
            # avoid performance issues when too many tabs are created
            alllayers = [i for i in self.m.BM._bg_layer.split("|") if i in alllayers]
            for i in range(self.count(), -1, -1):
                self.removeTab(i)
        else:
            # go through the layers in reverse and remove any no longer existing layers
            existing_layers = set()
            for i in range(self.count(), -1, -1):
                layer = self.tabText(i)
                # remove all tabs that do not represent existing layers of the map
                if layer not in alllayers:
                    self.removeTab(i)
                else:
                    existing_layers.add(layer)

            # pop all existing layers from the alllayers set (no need to re-create them)
            alllayers.difference_update(existing_layers)

        for i, layer in enumerate(sorted(alllayers)):

            layout = QtWidgets.QGridLayout()
            layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

            if layer.startswith("_"):  # or "|" in layer:
                # make sure the currently opened tab is always added (even if empty)
                if layer != self._current_tab_name:
                    # don't show empty layers
                    continue

            self.addTab(layer)
            self.setTabToolTip(i, layer)

            if layer == "all" or layer == self.m.layer:
                # don't show the close button for this tab
                self.setTabButton(self.count() - 1, self.RightSide, None)

        self.color_active_tab()

        # try to restore the previously opened tab
        self.set_current_tab_by_name(self._current_tab_name)

    @Slot(str)
    def set_current_tab_by_name(self, layer):
        if layer is None:
            layer = self.m.BM.bg_layer

        found = False
        ntabs = self.count()
        if ntabs > 0 and layer != "":
            for i in range(ntabs):
                if self.tabText(i) == layer:
                    self.setCurrentIndex(i)
                    found = True
                    break

            if found is False:
                self.setCurrentIndex(0)

    @Slot(int)
    def tabchanged(self, index):
        # TODO
        # modifiers are only released if the canvas has focus while the event happens!!
        # (e.g. button is released but event is not fired on the canvas)
        # see https://stackoverflow.com/q/60978379/9703451

        # simply calling  canvas.setFocus() does not work!

        # for w in QtWidgets.QApplication.topLevelWidgets():
        #     if w.inherits('QMainWindow'):
        #         w.canvas.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        #         w.canvas.setFocus()
        #         w.raise_()
        #         _log.debug("raising", w, w.canvas)

        layer = self.tabText(index)
        if len(layer) == 0:
            return

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            if layer != "":
                self.m.show_layer(
                    (layer, LayerTransparencySlider._alphas.get(layer, 1))
                )
                # TODO this is a workaround since modifier-releases are not
                # forwarded to the canvas if it is not in focus
                _key_release_event(self.m.f.canvas, "control")

        elif modifiers == Qt.ShiftModifier:
            # The all layer should not be combined with other layers...
            # (it is already visible anyways)
            if layer == "all" and "|" in layer:
                return

            # get currently active layers
            active_layers, alphas = self.m.BM._get_active_layers_alphas

            for x in (
                i for i in self.m.BM._parse_multi_layer_str(layer)[0] if i != "_"
            ):
                if x not in active_layers:
                    active_layers.append(x)
                    alphas.append(LayerTransparencySlider._alphas.get(layer, 1))
                else:
                    idx = active_layers.index(x)
                    active_layers.pop(idx)
                    alphas.pop(idx)

            if len(active_layers) >= 1:
                self.m.show_layer(*zip(active_layers, alphas))
            else:
                self.m.show_layer(
                    (layer, LayerTransparencySlider._alphas.get(layer, 1))
                )
            # TODO this is a workaround since modifier-releases are not
            # forwarded to the canvas if it is not in focus
            _key_release_event(self.m.f.canvas, "shift")

        # make sure to reflect the layer-changes in the tab-colors (and positions)
        self.color_active_tab()

        self.set_current_tab_by_name(layer)


class ArtistEditorTabs(LayerArtistTabs):
    def __init__(self, m=None):
        super().__init__(m=m)

        self.setTabBar(LayerTabBar(m=self.m))

        # re-populate tabs if a new layer is created
        self.populate()
        self.m._after_add_child.append(self.populate)
        self.m.BM.on_layer(self.populate_on_layer, persistent=True)

        self.currentChanged.connect(self.populate_layer)
        self.m.BM._on_add_bg_artist.append(self.populate)
        self.m.BM._on_remove_bg_artist.append(self.populate)

        self.m._on_show_companion_widget.append(self.populate)
        self.m._on_show_companion_widget.append(self.populate_layer)

        self.plusClicked.connect(self.new_layer_button_clicked)

        self.setStyleSheet(
            """
            QTabWidget::pane {
                border: 0px;
                top:0px;
                background: rgb(240, 240, 240);
                border-radius: 10px;
            }
            QScrollArea {border:0px}
            """
        )

    def new_layer_button_clicked(self, *args, **kwargs):
        inp = QtWidgets.QInputDialog(self)
        inp.setWindowIcon(QtGui.QIcon(str(iconpath / "plus.png")))
        inp.setWindowFlags(inp.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        inp.setInputMode(QtWidgets.QInputDialog.TextInput)
        inp.setFixedSize(200, 100)

        inp.setWindowTitle("New Layer")
        inp.setLabelText("Name:")

        if inp.exec_() == QtWidgets.QDialog.Accepted:
            # use .strip to remove any trailing spaces
            layer = inp.textValue().strip()
            # only create layers if at least 1 character has been provided
            if len(layer) > 0:
                self.m.new_layer(layer)

        inp.deleteLater()

    def repopulate_and_activate_current(self, *args, **kwargs):
        self.populate()

        # activate the currently visible layer tab
        try:
            idx = next(
                i for i in range(self.count()) if self.tabText(i) == self.m.BM._bg_layer
            )
            self.setCurrentIndex(idx)

        except StopIteration:
            pass

        self.populate_layer()

    def _get_artist_layout(self, a, layer):
        # label
        try:
            name = a.get_label()
            if len(name) == 0:
                name = str(a)

        except Exception:
            name = str(a)

        # for artists that should not show up in the editor
        if name.startswith("__EOmaps_exclude"):
            return [(None, None)]
        elif name.startswith("__EOmaps_deactivate"):
            name = name[20:].strip()
            deactivated = True
        else:
            deactivated = False

        if len(name) > 80:
            label = QtWidgets.QLabel(name[:76] + "... >")
            label.setToolTip(name)
        else:
            label = QtWidgets.QLabel(name)

        label.setStyleSheet(
            "border-radius: 5px;"
            "border-style: solid;"
            "border-width: 1px;"
            "border-color: rgba(0, 0, 0,100);"
            "padding-left: 10px;"
        )
        label.setAlignment(Qt.AlignLeft)
        label.setMaximumHeight(25)

        # remove
        b_r = RemoveArtistToolButton()
        b_r.setText("🞪")
        b_r.setAutoRaise(True)
        b_r.setStyleSheet("QToolButton {color: red;}")
        b_r.clicked.connect(self.remove(artist=a, layer=layer))

        # show / hide
        b_sh = ShowHideToolButton()
        b_sh.setAutoRaise(True)

        if a in self.m.BM._hidden_artists:
            b_sh.setIcon(QtGui.QIcon(str(iconpath / "eye_closed.png")))
        else:
            b_sh.setIcon(QtGui.QIcon(str(iconpath / "eye_open.png")))

        b_sh.clicked.connect(self.show_hide(artist=a, layer=layer))

        # zorder
        b_z = ZorderInput()
        b_z.setMinimumWidth(30)
        b_z.setMaximumWidth(30)
        validator = QtGui.QIntValidator()
        b_z.setValidator(validator)
        b_z.setText(str(a.get_zorder()))
        b_z.returnPressed.connect(self.set_zorder(artist=a, layer=layer, widget=b_z))

        # # alpha
        # alpha = a.get_alpha()
        # if alpha is not None:
        #     b_a = AlphaInput()

        #     b_a.setMinimumWidth(25)
        #     b_a.setMaximumWidth(50)

        #     validator = QtGui.QDoubleValidator(0.0, 1.0, 3)
        #     validator.setLocale(QtCore.QLocale("en_US"))

        #     b_a.setValidator(validator)
        #     b_a.setText(str(alpha))
        #     b_a.returnPressed.connect(self.set_alpha(artist=a, layer=layer, widget=b_a))
        # else:
        #     b_a = None

        # # linewidth
        # try:
        #     lw = a.get_linewidth()
        #     if isinstance(lw, list) and len(lw) > 1:
        #         pass
        #     else:
        #         lw = lw[0]

        #     if lw is not None:
        #         b_lw = LineWidthInput()

        #         b_lw.setMinimumWidth(25)
        #         b_lw.setMaximumWidth(50)
        #         validator = QtGui.QDoubleValidator(0, 100, 3)
        #         validator.setLocale(QtCore.QLocale("en_US"))

        #         b_lw.setValidator(validator)
        #         b_lw.setText(str(lw))
        #         b_lw.returnPressed.connect(
        #             self.set_linewidth(artist=a, layer=layer, widget=b_lw)
        #         )
        #     else:
        #         b_lw = None
        # except Exception:
        #     b_lw = None

        # # color
        # try:
        #     facecolor = to_rgba_array(a.get_facecolor())
        #     edgecolor = to_rgba_array(a.get_edgecolor())
        #     if facecolor.shape[0] != 1:
        #         facecolor = (0, 0, 0, 0)
        #         use_cmap = True
        #     else:
        #         facecolor = (facecolor.squeeze() * 255).astype(int).tolist()
        #         use_cmap = False

        #     if edgecolor.shape[0] != 1:
        #         edgecolor = (0, 0, 0, 0)
        #     else:
        #         edgecolor = (edgecolor.squeeze() * 255).astype(int).tolist()

        #     b_c = GetColorWidget(facecolor=facecolor, edgecolor=edgecolor)
        #     b_c.cb_colorselected = self.set_color(
        #         artist=a, layer=layer, colorwidget=b_c
        #     )
        #     b_c.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)

        #     b_c.setSizePolicy(
        #         QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
        #     )
        #     b_c.setMaximumWidth(25)

        # except Exception:
        #     b_c = None
        #     use_cmap = True
        #     pass

        # # cmap
        # from .utils import CmapDropdown

        # if use_cmap is True:
        #     try:
        #         cmap = a.get_cmap()
        #         b_cmap = CmapDropdown(startcmap=cmap.name)
        #         b_cmap.activated.connect(
        #             self.set_cmap(artist=a, layer=layer, widget=b_cmap)
        #         )
        #     except Exception:
        #         b_cmap = None
        #         pass
        # else:
        #     b_cmap = None

        # button to show artist info popup
        info_text = getattr(a, "_EOmaps_info", None)
        source_code = getattr(a, "_EOmaps_source_code", None)
        if info_text or source_code:
            b_info = ArtistInfoButton(info_text=info_text, source_code=source_code)
        else:
            b_info = None

        layout = []
        if not deactivated:
            layout.append((b_sh, 0))  # show hide

        layout.append((b_z, 2))  # zorder

        layout.append((label, 3))  # title

        if b_info is not None:
            layout.append((b_info, 4))  # info button

        if not deactivated:
            layout.append((b_r, 7))  # remove

        if deactivated:
            for w in layout:
                w[0].setEnabled(False)

        return layout

    @Slot()
    def populate_on_layer(self, *args, **kwargs):
        lastlayer = getattr(self, "_last_populated_layer", "")

        # only populate if the current layer is not part of the last set of layers
        # (e.g. to allow show/hide of selected layers without removing the tabs)
        if not self.m.BM._layer_visible(lastlayer):
            self._last_populated_layer = self.m.BM.bg_layer
            self.populate(*args, **kwargs)
        else:
            # TODO check why adjusting the tab-order causes recursions if multiple
            # layers are selected (and the transparency of a sub-layer is changed)
            self.tabBar().color_active_tab(adjust_order=False)

    @Slot()
    def populate(self, *args, **kwargs):
        if not self.isVisible():
            return

        tabbar = self.tabBar()
        self._current_tab_idx = self.currentIndex()
        self._current_tab_name = self.tabText(self._current_tab_idx)

        # go through the layers in reverse and remove any no longer existing layers
        alllayers = set(self.m._get_layers())
        nlayers = len(alllayers)
        max_n_layers = self.m._companion_widget_n_layer_tabs
        if nlayers > max_n_layers:
            if not LayerTabBar._n_layer_msg_shown:
                _log.info(
                    "EOmaps-companion: The map has more than "
                    f"{max_n_layers} layers... only last active layers "
                    "are shown in the layer-tabs!"
                )
                LayerTabBar._n_layer_msg_shown = True

            # if more than max_n_layers layers are available, show only active tabs to
            # avoid performance issues when too many tabs are created
            alllayers = self.m.BM._get_active_layers_alphas[0]
            for i in range(self.count(), -1, -1):
                self.removeTab(i)
        else:
            existing_layers = set()
            for i in range(self.count(), -1, -1):
                layer = self.tabText(i)
                # remove all tabs that do not represent existing layers of the map
                if layer not in alllayers:
                    self.removeTab(i)
                else:
                    existing_layers.add(layer)

            # pop all existing layers from the alllayers set (no need to re-create them)
            alllayers.difference_update(existing_layers)

        for i, layer in enumerate(sorted(alllayers)):

            layout = QtWidgets.QGridLayout()
            layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

            if layer.startswith("_"):  # or "|" in layer:
                # make sure the currently opened tab is always added (even if empty)
                if layer != self._current_tab_name:
                    # don't show empty layers
                    continue

            # use a QStackedWidget as tab-widget so contents can be switched dynamically
            tabwidget = QtWidgets.QStackedWidget()

            self.addTab(tabwidget, layer)
            self.setTabToolTip(i, layer)

            if layer == "all" or layer == self.m.layer:
                # don't show the close button for this tab
                tabbar.setTabButton(self.count() - 1, tabbar.RightSide, None)

        tabbar.color_active_tab()

        # try to restore the previously opened tab
        tabbar.set_current_tab_by_name(self._current_tab_name)

    def get_layer_alpha(self, layer):
        layers, alphas = self.m.BM._get_active_layers_alphas
        if layer in layers:
            idx = layers.index(layer)
            alpha = alphas[idx]
            LayerTransparencySlider._alphas[layer] = alpha

        elif layer in LayerTransparencySlider._alphas:
            # use last set alpha value for the layer
            alpha = LayerTransparencySlider._alphas[layer]
        else:
            alpha = 1
        return alpha

    @Slot()
    def populate_layer(self, layer=None):
        if not self.isVisible():
            return

        if layer is None:
            layer = self.tabText(self.currentIndex())

        # make sure we fetch artists of inset-maps from the layer with
        # the "__inset_" prefix
        if isinstance(self.m, InsetMaps) and not layer.startswith("__inset_"):
            layer = "__inset_" + layer
        widget = self.currentWidget()

        if widget is None:
            # ignore events without tabs (they happen on re-population of the tabs)
            return

        edit_layout = QtWidgets.QGridLayout()
        edit_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # make sure that we don't create an empty entry !
        # TODO the None check is to address possible race-conditions
        # with Maps objects that have no axes defined.
        if layer in self.m.BM._bg_artists and self.m.ax is not None:
            artists = [
                a for a in self.m.BM.get_bg_artists(layer) if a.axes is self.m.ax
            ]
        else:
            artists = []

        for i, a in enumerate(artists):
            for art, pos in self._get_artist_layout(a, layer):
                if art is not None:
                    edit_layout.addWidget(art, i, pos)

        # ------------------------ layer-actions menu
        # button to add WebMap services to the currently selected layer
        try:
            self.addwms = AddWMSMenuButton(m=self.m, new_layer=False, layer=layer)
            self.addwms.wmsLayerCreated.connect(self.populate_layer)
        except Exception:
            self.addwms = None

        # slider to set the global layer transparency
        self.layer_transparency_slider = LayerTransparencySlider(Qt.Horizontal)
        self.layer_transparency_slider.set_alpha_stylesheet()
        self.layer_transparency_slider.setValue(int(self.get_layer_alpha(layer) * 100))
        layer_transparency_label = QtWidgets.QLabel("<b>Layer Transparency:</b>")

        def update_layerslider(alpha):
            self.set_layer_alpha(layer, alpha / 100)
            LayerTransparencySlider._alphas[layer] = alpha / 100

        self.layer_transparency_slider.valueChanged.connect(update_layerslider)

        layer_actions_layout = QtWidgets.QHBoxLayout()
        if self.addwms is not None:
            layer_actions_layout.addWidget(self.addwms)

        spacer = QtWidgets.QSpacerItem(50, 1)
        layer_actions_layout.addItem(spacer)

        layer_actions_layout.addWidget(layer_transparency_label)
        layer_actions_layout.addWidget(self.layer_transparency_slider, 1)
        # ------------------------

        # a separator line
        separator = QtWidgets.QFrame()
        separator.setFrameShape(QtWidgets.QFrame.HLine)
        separator.setFixedHeight(1)
        separator.setStyleSheet("background-color: rgb(150,150,150)")

        # scroll area for the artists
        edit_widget = QtWidgets.QWidget()
        edit_widget.setLayout(edit_layout)

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(edit_widget)

        layout = QtWidgets.QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addLayout(layer_actions_layout)

        for text in self.m.BM._pending_webmaps.get(layer, []):
            layout.addWidget(QtWidgets.QLabel(f"<b>PENDING WebMap</b>: {text}"))

        layout.addWidget(scroll)
        layout.addStretch(1)

        tabwidget = QtWidgets.QWidget()
        tabwidget.setLayout(layout)

        while widget.count() > 0:
            widget.removeWidget(widget.widget(0))

        widget.addWidget(tabwidget)
        widget.setCurrentWidget(tabwidget)

    # --------

    def set_color(self, artist, layer, colorwidget):
        def cb():
            artist.set_fc(colorwidget.facecolor.getRgbF())
            artist.set_edgecolor(colorwidget.edgecolor.getRgbF())

            self.m.BM._refetch_layer(layer)
            self.m.BM.update()

        return cb

    def _do_remove(self, artist, layer):
        if self._msg.standardButton(self._msg.clickedButton()) != self._msg.Yes:
            return

        self.m.BM.remove_bg_artist(artist, layer)
        try:
            artist.remove()
        except Exception:
            _log.error(
                "EOmaps: There was an error while trying to remove the artist",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

        # explicit treatment for gridlines
        grids = self.m.parent._grid._gridlines
        for g in grids:
            if artist == g._coll:
                g.remove()

        self.populate_layer(layer)
        self.m.redraw(layer)

    def remove(self, artist, layer):
        @Slot()
        def cb():
            self._msg = QtWidgets.QMessageBox(self)

            self._msg.setIcon(QtWidgets.QMessageBox.Question)
            self._msg.setWindowTitle("Delete artist?")
            self._msg.setText(
                "Do you really want to delete the following artist "
                + f"from the layer '{layer}'?\n\n"
                + f"    '{artist.get_label()}'"
            )

            self._msg.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            self._msg.buttonClicked.connect(lambda: self._do_remove(artist, layer))
            self._msg.show()

        return cb

    def show_hide(self, artist, layer):
        @Slot()
        def cb():
            if artist in self.m.BM._hidden_artists:
                self.m.BM._hidden_artists.remove(artist)
                artist.set_visible(True)
            else:
                self.m.BM._hidden_artists.add(artist)
                artist.set_visible(False)

            self.m.redraw(layer)
            self.populate_layer(layer)

        return cb

    def set_zorder(self, artist, layer, widget):
        @Slot()
        def cb():
            val = widget.text()
            if len(val) > 0:
                artist.set_zorder(int(val))

            self.m.redraw(layer)

        return cb

    def set_alpha(self, artist, layer, widget):
        @Slot()
        def cb():
            val = widget.text()
            if len(val) > 0:
                artist.set_alpha(float(val.replace(",", ".")))

            self.m.redraw(layer)

        return cb

    def set_linewidth(self, artist, layer, widget):
        @Slot()
        def cb():
            val = widget.text()
            if len(val) > 0:
                artist.set_linewidth(float(val.replace(",", ".")))

            self.m.redraw(layer)

        return cb

    def set_cmap(self, artist, layer, widget):
        @Slot()
        def cb():
            val = widget.currentText()
            if len(val) > 0:
                artist.set_cmap(val)

            self.m.redraw(layer)

        return cb

    @Slot()
    def set_layer_alpha(self, layer, alpha):
        layers, alphas = self.m.BM._get_active_layers_alphas
        if layer in layers:
            idx = layers.index(layer)
            alphas[idx] = alpha

        self.m.show_layer(*zip(layers, alphas))


class ArtistEditor(QtWidgets.QWidget):
    def __init__(self, *args, m=None, show_editor=False, **kwargs):

        super().__init__()

        self.m = m

        self.artist_tabs = ArtistEditorTabs(m=self.m)

        self.artist_tabs.tabBar().setStyleSheet(
            """
            QTabBar::tab {
              background: rgb(220, 220, 220);
              border: 0px solid black;
              padding: 1px;
              padding-bottom: 6px;
              margin: 0px;
              margin-left: 2px;
              margin-bottom: -3px;
              border-radius: 4px;
            }

            QTabBar::tab:selected {
              background: rgb(150, 150, 150);
              border: 2px solid darkred;
              margin-bottom: -3px;
            }
            """
        )

        self.addfeature = AddFeatureWidget(m=self.m)
        self.addannotation = AddAnnotationWidget(m=self.m)
        self.draw = DrawerTabs(m=self.m)

        # add a margin to the top of the drawer widget
        d = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.draw)
        layout.setContentsMargins(0, 5, 0, 0)
        d.setLayout(layout)

        # make sure the layer is properly set
        self.set_layer()

        self.option_tabs = OptionTabs()
        self.option_tabs.addTab(self.addfeature, "Add Features")
        self.option_tabs.addTab(self.addannotation, "Add Annotations")
        self.option_tabs.addTab(d, "Draw Shapes")

        # set font properties before the stylesheet to avoid clipping of bold text!
        font = QFont("sans seriv", 8, QFont.Bold, False)
        self.option_tabs.setFont(font)

        self.option_tabs.setStyleSheet(
            """
            QTabWidget::pane {
              border: 0px;
              top:0px;
              background: rgb(200, 200, 200);
              border-radius: 10px;
            }

            QTabBar::tab {
              background: rgb(220, 220, 220);
              border: 0px;
              padding: 5px;
              padding-bottom: 6px;
              margin-left: 10px;
              margin-bottom: -2px;
              border-radius: 4px;
              font-weight: normal;
            }

            QTabBar::tab:selected {
              background: rgb(200, 200, 200);
              border: 0px;
              margin-bottom: -2px;
              font-weight: bold;
            }
            """
        )

        # repopulate the layer if features or webmaps are added
        for s in self.addfeature.selectors:
            s.FeatureAdded.connect(self.artist_tabs.populate_layer)

        option_widget = QtWidgets.QWidget()
        option_layout = QtWidgets.QVBoxLayout()
        option_layout.addWidget(self.option_tabs)

        option_widget.setLayout(option_layout)

        splitter = QtWidgets.QSplitter(Qt.Vertical)
        splitter.addWidget(option_widget)
        splitter.addWidget(self.artist_tabs)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        splitter.setStyleSheet(
            """
            QSplitter::handle {
                background: rgb(220,220,220);
                margin: 1px;
                margin-left: 20px;
                margin-right: 20px;
                height:1px;
                }
            QSplitter::handle:pressed {
                background: rgb(180,180,180);
            }
            """
        )

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)

        self.setLayout(layout)

        # connect a callback to update the layer of the feature-button
        # with respect to the currently selected layer-tab
        self.artist_tabs.tabBar().currentChanged.connect(self.set_layer)

    @Slot()
    def set_layer(self):
        layer = self.artist_tabs.tabText(self.artist_tabs.currentIndex())
        for s in self.addfeature.selectors:
            s.set_layer(layer)
        if self.draw is not None:
            self.draw.set_layer(layer)

        self.addannotation.set_layer(layer)

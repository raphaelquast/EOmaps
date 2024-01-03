# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

import logging
from weakref import WeakSet

from qtpy import QtWidgets, QtCore, QtGui
from qtpy.QtCore import Qt, Slot

from .common import iconpath

_log = logging.getLogger(__name__)


def get_dummy_spacer():
    space = QtWidgets.QWidget()
    space.setSizePolicy(
        QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
    )
    space.setAttribute(Qt.WA_TransparentForMouseEvents)
    return space


class BasicCheckableToolButton(QtWidgets.QToolButton):
    def __init__(
        self,
        *args,
        normal_icon=None,
        hoover_icon=None,
        checked_icon=None,
        tooltip=None,
        **kwargs,
    ):
        """
        Basic tool button with a hoover state

        Parameters
        ----------
        normal_icon : str, optional
            Path to the normal icon. The default is None.
        hoover_icon : str, optional
            Path to the hoover icon. The default is None.
        checked_icon : str, optional
            Path to the checked icon. If None, the hoover icon is used! The default is None.
        kwargs :
            additional kwargs passed to QToolButton.
        """

        super().__init__(*args, **kwargs)

        self.setStyleSheet(
            """
            BasicCheckableToolButton { border: 0px};
            """
        )

        self.setCheckable(True)
        self.setAutoRaise(False)
        self.setFixedSize(25, 25)

        self.normal_icon = None
        self.hoover_icon = None
        self.checked_icon = None

        self.set_icons(normal_icon, hoover_icon, checked_icon)

        self.toggled.connect(self.swap_icon)

        self.setStyleSheet(
            """
            QToolButton {
                border: 0px;
                border-radius: 4px;
                padding: 4px;
            }
            QToolButton:hover {
                background-color: rgb(210, 210, 210);
            }

            """
        )

    def set_icons(
        self, normal_icon=None, hoover_icon=None, checked_icon=None, size=None
    ):
        if size is None:
            size = self.size()
        else:
            size = QtCore.QSize(*size)

        if normal_icon:
            pm = QtGui.QPixmap(normal_icon)

            self.normal_icon = QtGui.QIcon(
                pm.scaled(
                    size,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
            )
            self.setIcon(self.normal_icon)
            self.active_icon = self.normal_icon
        if hoover_icon:
            pm = QtGui.QPixmap(hoover_icon)
            self.hoover_icon = QtGui.QIcon(
                pm.scaled(
                    size,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
            )
        if checked_icon:
            pm = QtGui.QPixmap(checked_icon)
            self.checked_icon = QtGui.QIcon(
                pm.scaled(
                    size,
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
            )
        else:
            self.checked_icon = self.hoover_icon

    def enterEvent(self, event):
        if self.isCheckable():
            if self.hoover_icon and not self.isChecked():
                self.setIcon(self.hoover_icon)
            else:
                self.setIcon(self.normal_icon)
        else:
            if self.hoover_icon:
                self.setIcon(self.hoover_icon)

        return super().enterEvent(event)

    def leaveEvent(self, event):
        if self.active_icon:
            self.setIcon(self.active_icon)

        return super().enterEvent(event)

    def swap_icon(self, *args, **kwargs):
        if self.normal_icon and self.hoover_icon:
            if self.isChecked():
                self.active_icon = self.checked_icon
            else:
                self.active_icon = self.normal_icon
            self.setIcon(self.active_icon)

    def sizeHint(self):
        # to keep checked button centered
        hint = super().sizeHint()
        if hint.width() & 1:
            hint.setWidth(hint.width() + 1)
        if hint.height() & 1:
            hint.setHeight(hint.height() + 1)
        return hint


class HelpButton(BasicCheckableToolButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setToolTip("Toggle showing help-tooltips.")
        self.setFixedSize(30, 30)

        self.set_icons(
            normal_icon=str(iconpath / "info.png"),
            hoover_icon=str(iconpath / "info_hoover.png"),
            checked_icon=str(iconpath / "info_checked.png"),
            size=(17, 17),
        )


class AlwaysOnTopToolButton(BasicCheckableToolButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.setFixedSize(30, 30)

        self.set_icons(
            normal_icon=str(iconpath / "eye_closed.png"),
            hoover_icon=str(iconpath / "eye_open.png"),
            checked_icon=str(iconpath / "eye_open.png"),
        )

    def enterEvent(self, event):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                event.globalPos(),
                "<h3>Keep plot window on top</h3>"
                "If activated, the figure will remain <b>always on top</b> of other"
                " applications",
            )

        return super().enterEvent(event)


class OpenFileButton(BasicCheckableToolButton):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCheckable(False)

        self.setFixedSize(30, 30)
        self.set_icons(
            normal_icon=str(iconpath / "open.png"),
            hoover_icon=str(iconpath / "open_hover.png"),
        )

    def enterEvent(self, e):
        super().enterEvent(e)

        self.window().tabs.tab_open.starttab.enterEvent(e)


class EditLayoutButton(BasicCheckableToolButton):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.setFixedSize(30, 30)

        self.m = m
        self.clicked.connect(self.callback)

        self.m._connect_signal(
            "layoutEditorActivated", lambda *args: self.setChecked(True)
        )
        self.m._connect_signal(
            "layoutEditorDeactivated", lambda *args: self.setChecked(False)
        )

        self.set_icons(
            normal_icon=str(iconpath / "edit_layout.png"),
            hoover_icon=str(iconpath / "edit_layout_hover.png"),
            checked_icon=str(iconpath / "edit_layout_active.png"),
        )

    def enterEvent(self, e):
        super().enterEvent(e)

        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Layout Editor</h3>"
                "Toggle the EOmaps LayoutEditor to re-arrange the position and size "
                "of the axes in the figure."
                "<ul>"
                "<li><b>Right-click</b> on axes with the mouse to select them (hold "
                "down 'shift' to select multiple axes).</li>"
                "<li><b>Drag</b> axes (or use the <b>arrow-keys</b>) to adjust "
                "their position</li>"
                "<li>Use the <b>scroll-wheel</b> (or the <b>+/- keys</b>) to adjust "
                "their size</li>"
                "<li>Hold down <b>'h'</b> or <b>'v'</b> key to adjust "
                "horizontal/vertical size.<br>"
                "(maps always keep their aspect-ratio!)</li>"
                "<li>Hold down <b>'control'</b> to adjust the colorbar/histogram size."
                "<li>Press <b>control + z</b> to undo the last step</li>"
                "<li>Press <b>control + y</b> to redo the last undone step</li>"
                "<li>Press <b>escape</b> to exit the LayoutEditor</li>"
                "</ul>",
            )

    @Slot()
    def callback(self):
        if not self.m.parent._layout_editor._modifier_pressed:
            self.m.parent.edit_layout()
        else:
            self.m.parent._layout_editor._undo_draggable()


class ToolBar(QtWidgets.QToolBar):
    def __init__(
        self,
        *args,
        m=None,
        left_widget=None,
        title=None,
        on_close=None,
        layers="text",
        add_buttons=False,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        self.m = m

        self._on_close = on_close

        logo = QtGui.QPixmap(str(iconpath / "logo.png"))
        logolabel = QtWidgets.QLabel()
        logolabel.setMaximumHeight(25)
        logolabel.setAlignment(Qt.AlignBottom | Qt.AlignRight)
        logolabel.setPixmap(
            logo.scaled(logolabel.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

        b_close = QtWidgets.QToolButton()
        b_close.setAutoRaise(True)
        b_close.setFixedSize(22, 22)
        b_close.setIcon(QtGui.QIcon(str(iconpath / "close.png")))
        b_close.clicked.connect(self.close_button_callback)

        self.b_minmax = QtWidgets.QToolButton()
        self.b_minmax.setAutoRaise(True)
        self.b_minmax.setFixedSize(22, 22)
        self.b_minmax.setIcon(QtGui.QIcon(str(iconpath / "maximize.png")))
        self.b_minmax.clicked.connect(self.maximize_button_callback)

        self.b_showhelp = HelpButton()
        self.b_showhelp.toggled.connect(self.toggle_show_help)

        if add_buttons:
            self.b_open = OpenFileButton()
            self.b_open.clicked.connect(self.open_file_button_callback)

            self.b_edit = EditLayoutButton(m=self.m)

        if left_widget:
            self.addWidget(left_widget)

        self.addWidget(self.b_showhelp)

        if title is not None:
            titlewidget = QtWidgets.QLabel(f"<b>{title}</b>")
            titlewidget.setAttribute(Qt.WA_TransparentForMouseEvents)
            self.addWidget(get_dummy_spacer())
            self.addWidget(titlewidget)

        if add_buttons:
            self.addWidget(self.b_open)
            self.addWidget(self.b_edit)
        if m is not None:
            if layers == "dropdown":
                from .widgets.layer import AutoUpdateLayerMenuButton

                showlayer = AutoUpdateLayerMenuButton(m=self.m)
                self.addWidget(showlayer)
            elif layers == "text":
                from .widgets.layer import AutoUpdateLayerLabel

                showlayer = AutoUpdateLayerLabel(
                    m=self.m,
                )
                self.addWidget(get_dummy_spacer())
                self.addWidget(showlayer)

        self.addWidget(get_dummy_spacer())

        self.addWidget(logolabel)
        self.addWidget(self.b_minmax)
        self.addWidget(b_close)

        self.setMovable(False)

        self.setStyleSheet(
            """
            QToolBar {
                border: none;
                spacing:5px;
            }
            """
        )

        self.setContentsMargins(0, 0, 0, 0)

        self.press_pos = None

    @Slot()
    def toggle_show_help(self):
        if self.b_showhelp.isChecked():
            self.window().showhelp = True
            # self.b_showhelp.setText("Click to hide help tooltips")
        else:
            self.window().showhelp = False
            # self.b_showhelp.setText("?")

    @Slot()
    def close_button_callback(self):
        self.window().close()
        if self.m is not None:
            self.m._indicate_companion_map(False)

        if self._on_close is not None:
            self._on_close()

    @Slot()
    def open_file_button_callback(self):
        self.window().tabs.tab_open.openNewFile.emit()

    @Slot()
    def maximize_button_callback(self):
        if not self.window().isMaximized():
            self.window().showMaximized()
            self.b_minmax.setText("🗗")
        else:
            self.window().showNormal()
            self.b_minmax.setText("🗖")

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.LeftButton:
            try:
                self.press_pos = event.windowPos().toPoint()
            except Exception:
                # for PyQt6 compatibility
                self.press_pos = event.scenePosition().toPoint()

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


_windows_to_close = WeakSet()


class NewWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, m=None, title=None, on_close=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.m = m
        self.setWindowTitle("OpenFile")

        self.showhelp = False

        self.toolbar = ToolBar(title=title, on_close=on_close)
        self.addToolBar(self.toolbar)

        self.layout = QtWidgets.QVBoxLayout()
        self.layout.setContentsMargins(5, 20, 5, 5)

        statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(statusBar)

        widget = QtWidgets.QWidget()
        widget.setLayout(self.layout)
        self.setCentralWidget(widget)

        # make sure that we close all remaining windows if the figure is closed
        if self.m is not None:
            self.m.f.canvas.mpl_connect("close_event", self.on_close)

        self.setStyleSheet(
            """
            NewWindow{
                border: 1px solid gray;
                }
            """
        )

        _windows_to_close.add(self)

    @Slot()
    def on_close(self, e):
        self.close()


class AlwaysOnTopWindow(QtWidgets.QMainWindow):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.out_alpha = 0.25
        self.m = m

        # get the current PyQt app and connect the focus-change callback
        self.app = QtWidgets.QApplication([]).instance()

        # make sure the window does not steal focus from the matplotlib-canvas
        # on show (otherwise callbacks are inactive as long as the window is focused!)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlags(
            Qt.FramelessWindowHint | Qt.Dialog  # | Qt.WindowStaysOnTopHint
        )
        self.setFocusPolicy(Qt.ClickFocus)

        self.on_top = AlwaysOnTopToolButton()

        self.toolbar = ToolBar(
            m=self.m, left_widget=self.on_top, layers="text", add_buttons=True
        )
        self.on_top.clicked.connect(self.toggle_always_on_top)

        self.addToolBar(self.toolbar)

    @Slot()
    def toggle_always_on_top(self, *args, **kwargs):
        q = self.m._get_always_on_top()

        if q:
            self.m._set_always_on_top(False)
            self.on_top.setChecked(False)
        else:
            self.m._set_always_on_top(True)
            self.on_top.setChecked(True)

    def closeEvent(*args, **kwargs):
        global _windows_to_close
        for w in _windows_to_close:
            try:
                w.close()
            except Exception:
                _log.debug(f"There was a problem while trying to close the window {w}")

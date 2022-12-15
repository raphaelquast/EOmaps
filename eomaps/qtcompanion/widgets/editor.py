from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtCore import Qt, pyqtSignal, pyqtSlot, QSize

from matplotlib.colors import to_rgba_array

from ..common import iconpath
from .wms import AddWMSMenuButton
from .utils import GetColorWidget, AlphaSlider
from .annotate import AddAnnotationInput
from .draw import DrawerTabs


class AddFeaturesMenuButton(QtWidgets.QPushButton):
    def __init__(self, *args, m=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m
        self._menu_fetched = False

        # the layer to which features are added
        self.layer = None

        self.props = dict(
            # alpha = 1,
            facecolor="r",
            edgecolor="g",
            linewidth=1,
            zorder=0,
        )

        self.setText("Add Feature")
        # self.setMaximumWidth(200)

        width = self.fontMetrics().boundingRect(self.text()).width()
        self.setFixedWidth(width + 30)

        self.feature_menu = QtWidgets.QMenu()
        self.feature_menu.setStyleSheet("QMenu { menu-scrollable: 1;}")
        self.feature_menu.aboutToShow.connect(self.fetch_menu)

        self.setMenu(self.feature_menu)
        self.clicked.connect(self.show_menu)

    def fetch_menu(self):
        if self._menu_fetched:
            return

        feature_types = [i for i in dir(self.m.add_feature) if not i.startswith("_")]

        for featuretype in feature_types:
            try:
                sub_menu = self.feature_menu.addMenu(featuretype)

                sub_features = [
                    i
                    for i in dir(getattr(self.m.add_feature, featuretype))
                    if not i.startswith("_")
                ]
                for feature in sub_features:
                    action = sub_menu.addAction(str(feature))
                    action.triggered.connect(
                        self.menu_callback_factory(featuretype, feature)
                    )
            except:
                print("there was a problem with the NaturalEarth feature", featuretype)
                continue

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

    @pyqtSlot()
    def show_menu(self):
        self.feature_menu.popup(self.mapToGlobal(self.menu_button.pos()))

    def set_layer(self, layer):
        self.layer = layer

    def menu_callback_factory(self, featuretype, feature):
        @pyqtSlot()
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

                self.m.BM.update()
            except Exception:
                import traceback

                print(
                    "---- adding the feature", featuretype, feature, "did not work----"
                )
                print(traceback.format_exc())

        return cb


class ZorderInput(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Zorder</h3> Set the zorder of the artist (e.g. the vertical "
                "stacking order with respect to other artists in the figure)",
            )


class TransparencySlider(AlphaSlider):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Facecolor Transparency</h3> "
                "Set the transparency for the facecolor of the feature.",
            )


class LinewidthSlider(AlphaSlider):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(), "<h3>Linewidth</h3> Set the linewidth of the feature"
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
                "Make the corresponding artist visible (eye open) or invisible (eye closed).",
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
        self.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)

        self.m = m

        self.selector = AddFeaturesMenuButton(m=self.m)
        self.selector.clicked.connect(self.update_props)

        self.colorselector = GetColorWidget(facecolor="#aaaa7f")
        self.colorselector.cb_colorselected = self.update_on_color_selection

        self.alphaslider = TransparencySlider(Qt.Horizontal)
        self.alphaslider.valueChanged.connect(self.set_alpha_with_slider)
        self.alphaslider.valueChanged.connect(self.update_props)

        self.linewidthslider = LinewidthSlider(Qt.Horizontal)
        self.linewidthslider.valueChanged.connect(self.set_linewidth_with_slider)
        self.linewidthslider.valueChanged.connect(self.update_props)
        self.set_linewidth_slider_stylesheet()

        self.zorder = ZorderInput("0")
        validator = QtGui.QIntValidator()
        self.zorder.setValidator(validator)
        self.zorder.setMaximumWidth(30)
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
        zorder_layout.addWidget(self.zorder)
        zorder_label.setAlignment(Qt.AlignRight | Qt.AlignCenter)

        layout = QtWidgets.QGridLayout()
        layout.addWidget(self.colorselector, 0, 0, 2, 1)
        layout.addWidget(self.alphaslider, 0, 1)
        layout.addWidget(self.linewidthslider, 1, 1)
        layout.addLayout(zorder_layout, 0, 2)
        layout.addWidget(self.selector, 1, 2)

        # set stretch factor to expand the color-selector first
        layout.setColumnStretch(0, 1)

        layout.setAlignment(Qt.AlignCenter | Qt.AlignTop)
        self.setLayout(layout)

        # do this at the end to ensure everything has already been set up properly
        self.alphaslider.setValue(100)
        self.linewidthslider.setValue(20)

        self.update_props()

    @pyqtSlot(int)
    def set_alpha_with_slider(self, i):
        self.colorselector.set_alpha(i / 100)

    @pyqtSlot(int)
    def set_linewidth_with_slider(self, i):
        self.colorselector.set_linewidth(i / 10)

    @pyqtSlot()
    def update_props(self):
        self.set_alpha_slider_stylesheet()

        self.selector.props.update(
            dict(
                facecolor=self.colorselector.facecolor.getRgbF(),
                edgecolor=self.colorselector.edgecolor.getRgbF(),
                linewidth=self.linewidthslider.alpha * 5,
                zorder=int(self.zorder.text()),
                # alpha = self.alphaslider.alpha,   # don't specify alpha! it interferes with the alpha of the colors!
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

    def update_on_color_selection(self):
        self.update_alphaslider()
        self.update_props()

    def update_alphaslider(self):
        # to always round up to closest int use -(-x//1)
        self.alphaslider.setValue(int(-(-self.colorselector.alpha * 100 // 1)))


class NewLayerLineEdit(QtWidgets.QLineEdit):
    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>New Layer</h3>"
                "Enter a layer-name and press <b>enter</b> to create "
                "a new (empty) layer on the map!"
                "<p>"
                "NTOE: The tab of the new layer will be activated once the layer is "
                "created, but it is NOT automatically set as the visible layer!",
            )


class NewLayerWidget(QtWidgets.QFrame):
    NewLayerCreated = pyqtSignal(str)

    def __init__(self, *args, m=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.m = m

        new_layer_label = QtWidgets.QLabel("<b>Create a new layer:</b>")
        self.new_layer_name = NewLayerLineEdit()
        self.new_layer_name.setMaximumWidth(300)
        self.new_layer_name.setPlaceholderText("my_layer")

        self.new_layer_name.returnPressed.connect(self.new_layer)

        try:
            self.addwms = AddWMSMenuButton(m=self.m, new_layer=False)
        except:
            self.addwms = None

        newlayer = QtWidgets.QHBoxLayout()
        newlayer.setAlignment(Qt.AlignLeft)

        if self.addwms is not None:
            newlayer.addWidget(self.addwms)
        newlayer.addStretch(1)
        newlayer.addWidget(new_layer_label)
        newlayer.addWidget(self.new_layer_name)

        # addfeature = AddFeatureWidget(m=self.m)

        layout = QtWidgets.QVBoxLayout()
        # layout.addWidget(addfeature)
        layout.addLayout(newlayer)
        self.setLayout(layout)

    @pyqtSlot()
    def new_layer(self):
        # use .strip() to make sure the layer does not start or end with whitespaces
        layer = self.new_layer_name.text().strip()
        if len(layer) == 0:
            QtWidgets.QToolTip.showText(
                self.mapToGlobal(self.new_layer_name.pos()),
                "Type a layer-name and press return!",
            )
            return

        m2 = self.m.new_layer(layer)
        self.NewLayerCreated.emit(layer)
        # self.m.show_layer(layer)

        return m2


class LayerArtistTabs(QtWidgets.QTabWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        stylesheet = """
            QTabWidget::pane { /* The tab widget frame */
                border-top: 0px solid rgb(100,100,100);
            }

            QTabWidget::tab-bar {
                left: 5px; /* move to the right by 5px */
            }

            QTabBar::tab {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #E1E1E1, stop: 0.4 #DDDDDD,
                                            stop: 0.5 #D8D8D8, stop: 1.0 #D3D3D3);
                border-bottom-color: none;
                border-top-left-radius: 2px;
                border-top-right-radius: 2px;
                min-width: 50px;
                padding: 1px;
                margin: 1px;
            }

            QTabBar::tab:selected, QTabBar::tab:hover {
                border: 1px solid black;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                                            stop: 0 #fafafa, stop: 0.4 #f4f4f4,
                                            stop: 0.5 #e7e7e7, stop: 1.0 #fafafa);
            }

            QTabBar::tab:selected {
                padding: 0px;
                border: 2px solid rgb(200,0,0);
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                border-bottom-color: rgb(100,100,100); /* same as pane color */
            }

            QTabBar::tab:!selected {
                border: 1px solid rgb(200,200,200);
                margin-top: 4px; /* make non-selected tabs look smaller */
            }
            """

        self.setStyleSheet(stylesheet)

    def enterEvent(self, e):
        if self.window().showhelp is True:
            QtWidgets.QToolTip.showText(
                e.globalPos(),
                "<h3>Background Layers and Artists</h3>"
                "Each tab represents a layer of the map."
                "The tab-entries show all individual <b>background</b> artists of the "
                "selected layer. (background artists are static map-elements that are "
                "only re-drawn on pan/zoom or resize events)"
                "<ul>"
                "<li><b>control+click</b> on a tab to make it the visible layer.</li>"
                "<li><b>shift+click</b> on tabs to make multiple layers visible.</li>"
                "</ul>"
                "Feature and WebMap artists created with the controls above are always "
                "added to the "
                "<b>currently selected tab</b>!<br>"
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


# make sure tabs are never larger than 150px
class TabBar(QtWidgets.QTabBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # remove strange line on top of tabs
        # (see https://stackoverflow.com/a/33941638/9703451)
        self.setStyleSheet(
            " QTabBar { "
            "qproperty-drawBase: 0; "
            "}"
            " QTabBar::tab { "
            "padding-left: 0px; "
            "}"
        )

        self.setElideMode(Qt.ElideRight)

    def tabSizeHint(self, index):
        size = QtWidgets.QTabBar.tabSizeHint(self, index)
        return QSize(min(size.width(), 150), size.height())


class ArtistEditor(QtWidgets.QWidget):
    def __init__(self, m=None):

        super().__init__()

        self.m = m
        self._hidden_artists = dict()

        self.tabs = LayerArtistTabs()
        self.tabs.setTabBar(TabBar())
        self.tabs.setMovable(True)
        self.tabs.setUsesScrollButtons(True)

        self.option_tabs = OptionTabs()

        self.newlayer = NewLayerWidget(m=self.m)
        self.newlayer.new_layer_name.returnPressed.connect(self.populate)
        # re-populate layers on new layer creation
        self.newlayer.NewLayerCreated.connect(self.populate)
        # set active tab to the new tab on layer creation
        self.newlayer.NewLayerCreated[str].connect(self.set_current_tab_by_name)

        self.addfeature = AddFeatureWidget(m=self.m)
        self.addannotation = AddAnnotationInput(m=self.m)

        self.option_tabs.addTab(self.addfeature, "Add Features")
        self.option_tabs.addTab(self.addannotation, "Add Annotations")

        self.draw = DrawerTabs(m=self.m)
        self.option_tabs.addTab(self.draw, "Draw Shapes")

        option_widget = QtWidgets.QWidget()
        option_layout = QtWidgets.QVBoxLayout()
        option_layout.addWidget(self.option_tabs)
        option_layout.addWidget(self.newlayer)
        option_widget.setLayout(option_layout)

        splitter = QtWidgets.QSplitter(Qt.Vertical)
        splitter.addWidget(option_widget)
        splitter.addWidget(self.tabs)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(splitter)

        self.setLayout(layout)

        self.populate()

        self.tabs.tabBarClicked.connect(self.tabchanged)
        self.tabs.currentChanged.connect(self.populate_layer)
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_handler)

        self._current_tab_idx = None
        self._current_tab_name = None

        self.m.BM.on_layer(self.color_active_tab, persistent=True)

        self.m.BM._on_add_bg_artist.append(self.populate)
        self.m.BM._on_remove_bg_artist.append(self.populate)
        # connect a callback to update the layer of the feature-button
        # with respect to the currently selected layer-tab
        self.tabs.currentChanged.connect(self.set_layer)
        self.set_layer()

    @pyqtSlot()
    def set_layer(self):
        layer = self.tabs.tabText(self.tabs.currentIndex())
        self.addfeature.selector.set_layer(layer)
        if self.draw is not None:
            self.draw.set_layer(layer)

        if self.newlayer.addwms is not None:
            self.newlayer.addwms.set_layer(layer)

        self.addannotation.set_layer(layer)

    @pyqtSlot(int)
    def close_handler(self, index):
        layer = self.tabs.tabText(index)

        self._msg = QtWidgets.QMessageBox(self)
        self._msg.setIcon(QtWidgets.QMessageBox.Question)
        self._msg.setText(f"Do you really want to delete the layer '{layer}'")
        self._msg.setWindowTitle(f"Delete layer: '{layer}'?")

        self._msg.setStandardButtons(
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
        )
        self._msg.buttonClicked.connect(self.get_close_tab_cb(index))

        _ = self._msg.show()

    def get_close_tab_cb(self, index):
        @pyqtSlot()
        def cb():
            self._do_close_tab(index)

        return cb

    def _do_close_tab(self, index):

        if self._msg.standardButton(self._msg.clickedButton()) != self._msg.Yes:
            return

        layer = self.tabs.tabText(index)

        if self.m.layer == layer:
            print("can't delete the base-layer")
            return

        for m in list(self.m._children):
            if layer == m.layer:
                m.cleanup()
                m.BM._bg_layers.pop(layer, None)

        if self.m.BM._bg_layer == layer:
            try:
                switchlayer = next((i for i in self.m.BM._bg_artists if i != layer))
                self.m.show_layer(switchlayer)
            except StopIteration:
                # don't allow deletion of last layer
                print("you cannot delete the last available layer!")
                return

        if layer in list(self.m.BM._bg_artists):
            for a in self.m.BM._bg_artists[layer]:
                self.m.BM.remove_bg_artist(a)
                a.remove()
            del self.m.BM._bg_artists[layer]

        if layer in self.m.BM._bg_layers:
            del self.m.BM._bg_layers[layer]

        # also remove not-yet-fetched WMS services!
        if layer in self.m.BM._on_layer_activation:
            del self.m.BM._on_layer_activation[layer]

        self.populate()

    def color_active_tab(self, m=None, l=None):

        defaultcolor = self.tabs.palette().color(self.tabs.foregroundRole())
        activecolor = QtGui.QColor(50, 200, 50)
        multicolor = QtGui.QColor(200, 50, 50)

        for i in range(self.tabs.count()):
            layer = self.tabs.tabText(i)

            active_layers = set(self.m.BM._bg_layer.split("|"))
            active_layers.add(self.m.BM._bg_layer)

            color = activecolor if len(active_layers) == 1 else multicolor
            if layer in active_layers:
                self.tabs.tabBar().setTabTextColor(i, color)
            else:
                self.tabs.tabBar().setTabTextColor(i, defaultcolor)

            if l == layer:
                self.tabs.tabBar().setTabTextColor(i, activecolor)

    def _get_artist_layout(self, a, layer):
        # label
        name = str(a)
        if len(name) > 50:
            label = QtWidgets.QLabel(name[:46] + "... >")
            label.setToolTip(name)
        else:
            label = QtWidgets.QLabel(name)
        label.setStyleSheet(
            "border-radius: 5px;"
            "border-style: solid;"
            "border-width: 1px;"
            "border-color: rgba(0, 0, 0,100);"
        )
        label.setAlignment(Qt.AlignCenter)
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

        # #b_sh.setStyleSheet("background-color : #79a76e")
        if a in self._hidden_artists.get(layer, []):
            b_sh.setIcon(QtGui.QIcon(str(iconpath / "eye_closed.png")))
        else:
            b_sh.setIcon(QtGui.QIcon(str(iconpath / "eye_open.png")))

        b_sh.clicked.connect(self.show_hide(artist=a, layer=layer))

        # zorder
        b_z = ZorderInput()
        b_z.setMinimumWidth(25)
        b_z.setMaximumWidth(25)
        validator = QtGui.QIntValidator()
        b_z.setValidator(validator)
        b_z.setText(str(a.get_zorder()))
        b_z.returnPressed.connect(self.set_zorder(artist=a, layer=layer, widget=b_z))

        # alpha
        alpha = a.get_alpha()
        if alpha is not None:
            b_a = AlphaInput()

            b_a.setMinimumWidth(25)
            b_a.setMaximumWidth(50)

            validator = QtGui.QDoubleValidator(0.0, 1.0, 3)
            validator.setLocale(QtCore.QLocale("en_US"))

            b_a.setValidator(validator)
            b_a.setText(str(alpha))
            b_a.returnPressed.connect(self.set_alpha(artist=a, layer=layer, widget=b_a))
        else:
            b_a = None

        # linewidth
        try:
            lw = a.get_linewidth()
            if isinstance(lw, list) and len(lw) > 1:
                pass
            else:
                lw = lw[0]

            if lw is not None:
                b_lw = LineWidthInput()

                b_lw.setMinimumWidth(25)
                b_lw.setMaximumWidth(50)
                validator = QtGui.QDoubleValidator(0, 100, 3)
                validator.setLocale(QtCore.QLocale("en_US"))

                b_lw.setValidator(validator)
                b_lw.setText(str(lw))
                b_lw.returnPressed.connect(
                    self.set_linewidth(artist=a, layer=layer, widget=b_lw)
                )
            else:
                b_lw = None
        except Exception:
            b_lw = None

        # color
        try:
            facecolor = to_rgba_array(a.get_facecolor())
            edgecolor = to_rgba_array(a.get_edgecolor())
            if facecolor.shape[0] != 1:
                facecolor = (0, 0, 0, 0)
                use_cmap = True
            else:
                facecolor = (facecolor.squeeze() * 255).astype(int).tolist()
                use_cmap = False

            if edgecolor.shape[0] != 1:
                edgecolor = (0, 0, 0, 0)
            else:
                edgecolor = (edgecolor.squeeze() * 255).astype(int).tolist()

            b_c = GetColorWidget(facecolor=facecolor, edgecolor=edgecolor)
            b_c.cb_colorselected = self.set_color(
                artist=a, layer=layer, colorwidget=b_c
            )
            b_c.setFrameStyle(QtWidgets.QFrame.StyledPanel | QtWidgets.QFrame.Plain)

            b_c.setSizePolicy(
                QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Minimum
            )
            b_c.setMaximumWidth(25)

        except:
            b_c = None
            use_cmap = True
            pass

        # cmap
        from .utils import CmapDropdown

        if use_cmap is True:
            try:
                cmap = a.get_cmap()
                b_cmap = CmapDropdown(startcmap=cmap.name)
                b_cmap.activated.connect(
                    self.set_cmap(artist=a, layer=layer, widget=b_cmap)
                )
            except:
                b_cmap = None
                pass
        else:
            b_cmap = None

        layout = []
        layout.append((b_sh, 0))  # show hide
        if b_c is not None:
            layout.append((b_c, 1))  # color
        layout.append((b_z, 2))  # zorder

        layout.append((label, 3))  # title
        if b_lw is not None:
            layout.append((b_lw, 4))  # linewidth

        if b_a is not None:
            layout.append((b_a, 5))  # alpha

        if b_cmap is not None:
            layout.append((b_cmap, 6))  # cmap

        layout.append((b_r, 7))  # remove

        return layout

    @pyqtSlot()
    def populate_layer(self):
        layer = self.tabs.tabText(self.tabs.currentIndex())
        widget = self.tabs.currentWidget()

        if widget is None:
            # ignore events without tabs (they happen on re-population of the tabs)
            return

        layout = QtWidgets.QGridLayout()
        layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

        # make sure that we don't create an empty entry !
        if layer in self.m.BM._bg_artists:
            artists = [a for a in self.m.BM._bg_artists[layer] if a.axes is self.m.ax]
        else:
            artists = []

        for i, a in enumerate(
            sorted((*artists, *self._hidden_artists.get(layer, [])), key=str)
        ):

            a_layout = self._get_artist_layout(a, layer)
            for art, pos in a_layout:
                layout.addWidget(art, i, pos)

        tabwidget = QtWidgets.QWidget()
        tabwidget.setLayout(layout)

        widget.setWidget(tabwidget)

    @pyqtSlot()
    def populate(self):
        self._current_tab_idx = self.tabs.currentIndex()
        self._current_tab_name = self.tabs.tabText(self._current_tab_idx)

        alllayers = sorted(list(self.m._get_layers()))
        self.tabs.clear()

        self.tabwidgets = dict()
        for i, layer in enumerate(alllayers):

            layout = QtWidgets.QGridLayout()
            layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)

            if layer.startswith("_"):  # or "|" in layer:
                # make sure the currently opened tab is always added (even if empty)
                if layer != self._current_tab_name:
                    # don't show empty layers
                    continue

            scroll = QtWidgets.QScrollArea()
            scroll.setWidgetResizable(True)

            self.tabs.addTab(scroll, layer)
            self.tabs.setTabToolTip(i, layer)

            if layer == "all" or layer == self.m.layer:
                tabbar = self.tabs.tabBar()
                # don't show the close button for this tab
                tabbar.setTabButton(self.tabs.count() - 1, tabbar.RightSide, None)

        # try to restore the previously opened tab
        self.set_current_tab_by_name(self._current_tab_name)

        self.color_active_tab()

    @pyqtSlot(str)
    def set_current_tab_by_name(self, layer):
        found = False
        ntabs = self.tabs.count()
        if ntabs > 0 and self._current_tab_name != "":
            for i in range(ntabs):
                if self.tabs.tabText(i) == layer:
                    self.tabs.setCurrentIndex(i)
                    found = True
                    break

            if found is False:
                print(f"Unable to activate the tab '{self._current_tab_name}'!")
                self.tabs.setCurrentIndex(0)

    @pyqtSlot(int)
    def tabchanged(self, index):
        # TODO
        # modifiers are only released if the canvas has focus while the event happens!!
        # (e.g. button is released but event is not fired on the canvas)
        # see https://stackoverflow.com/questions/60978379/why-alt-modifier-does-not-trigger-key-release-event-the-first-time-you-press-it

        # simply calling  canvas.setFocus() does not work!

        # for w in QtWidgets.QApplication.topLevelWidgets():
        #     if w.inherits('QMainWindow'):
        #         w.canvas.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)
        #         w.canvas.setFocus()
        #         w.raise_()
        #         print("raising", w, w.canvas)

        layer = self.tabs.tabText(index)

        modifiers = QtWidgets.QApplication.keyboardModifiers()
        if modifiers == Qt.ControlModifier:
            if layer != "":
                self.m.show_layer(layer)
                # TODO this is a workaround since modifier-releases are not
                # forwarded to the canvas if it is not in focus
                self.m.f.canvas.key_release_event("control")

        elif modifiers == Qt.ShiftModifier:
            # The all layer should not be combined with other layers...
            # (it is already visible anyways)
            if layer == "all" or "|" in layer:
                return
            currlayers = [i for i in self.m.BM._bg_layer.split("|") if i != "_"]

            for l in (i for i in layer.split("|") if i != "_"):
                if l not in currlayers:
                    currlayers.append(l)
                else:
                    currlayers.remove(l)

            if len(currlayers) > 1:
                uselayer = "|".join(sorted(currlayers))

                self.m.show_layer(uselayer)
            elif len(currlayers) == 1:
                self.m.show_layer(currlayers[0])
            else:
                self.m.show_layer(layer)
            # TODO this is a workaround since modifier-releases are not
            # forwarded to the canvas if it is not in focus
            self.m.f.canvas.key_release_event("shift")

    def set_color(self, artist, layer, colorwidget):
        def cb():
            artist.set_fc(colorwidget.facecolor.getRgbF())
            artist.set_edgecolor(colorwidget.edgecolor.getRgbF())

            self.m.redraw()

        return cb

    def _do_remove(self, artist, layer):
        if self._msg.standardButton(self._msg.clickedButton()) != self._msg.Yes:
            return

        self.m.BM.remove_bg_artist(artist, layer)

        if artist in self._hidden_artists.get(layer, []):
            self._hidden_artists[layer].remove(artist)

        artist.remove()

        self.populate()
        self.m.redraw()

    def remove(self, artist, layer):
        @pyqtSlot()
        def cb():
            self._msg = QtWidgets.QMessageBox(self)
            self._msg.setIcon(QtWidgets.QMessageBox.Question)
            self._msg.setWindowTitle(f"Delete artist?")
            self._msg.setText(
                "Do you really want to delete the following artist"
                + f"from the layer '{layer}'?\n\n"
                + f"    '{artist}'"
            )

            self._msg.setStandardButtons(
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No
            )
            self._msg.buttonClicked.connect(lambda: self._do_remove(artist, layer))
            ret = self._msg.show()

        return cb

    def show_hide(self, artist, layer):
        @pyqtSlot()
        def cb():
            if artist in self.m.BM._bg_artists[layer]:
                self._hidden_artists.setdefault(layer, []).append(artist)
                self.m.BM.remove_bg_artist(artist, layer=layer)
                artist.set_visible(False)
            else:
                if layer in self._hidden_artists:
                    try:
                        self._hidden_artists[layer].remove(artist)
                    except ValueError:
                        print("could not find hidden artist in _hidden_artists list")
                        pass

                try:
                    self.m.BM.add_bg_artist(artist, layer=layer)
                except:
                    print("problem unhiding", artist, "from layer", layer)

            self.m.redraw()

        return cb

    def set_zorder(self, artist, layer, widget):
        @pyqtSlot()
        def cb():
            val = widget.text()
            if len(val) > 0:
                artist.set_zorder(int(val))

            self.m.redraw()

        return cb

    def set_alpha(self, artist, layer, widget):
        @pyqtSlot()
        def cb():
            val = widget.text()
            if len(val) > 0:
                artist.set_alpha(float(val.replace(",", ".")))

            self.m.redraw()

        return cb

    def set_linewidth(self, artist, layer, widget):
        @pyqtSlot()
        def cb():
            val = widget.text()
            if len(val) > 0:
                artist.set_linewidth(float(val.replace(",", ".")))

            self.m.redraw()

        return cb

    def set_cmap(self, artist, layer, widget):
        @pyqtSlot()
        def cb():
            val = widget.currentText()
            if len(val) > 0:
                artist.set_cmap(val)

            self.m.redraw()

        return cb

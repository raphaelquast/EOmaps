from PyQt5 import QtWidgets


class WMS_GEBCO:
    layer_prefix = "GEBCO_"
    name = "GEBCO"

    def __init__(self, m=None):
        self.m = m
        self.wmslayers = [
            key
            for key in self.m.add_wms.GEBCO.add_layer.__dict__.keys()
            if not (key in ["m"] or key.startswith("_"))
        ]

    def do_add_layer(self, wmslayer, layer):
        getattr(self.m.add_wms.GEBCO.add_layer, wmslayer)(layer=layer)


class WMS_NASA_GIBS:
    layer_prefix = "NASA_GIBS_"
    name = "NASA_GIBS"

    def __init__(self, m=None):
        self.m = m

        if self.m.get_crs(3857) == m.crs_plot:
            self.usewms = self.m.add_wms.NASA_GIBS.EPSG_3857
        elif self.m.get_crs(3031) == m.crs_plot:
            self.usewms = self.m.add_wms.NASA_GIBS.EPSG_3031
        elif self.m.get_crs(3413) == m.crs_plot:
            self.usewms = self.m.add_wms.NASA_GIBS.EPSG_3413
        elif self.m.get_crs(4326) == m.crs_plot:
            self.usewms = self.m.add_wms.NASA_GIBS.EPSG_4326
        else:
            self.usewms = self.m.add_wms.NASA_GIBS.EPSG_3857

        self.wmslayers = [
            key
            for key in self.usewms.add_layer.__dict__.keys()
            if not (key in ["m"] or key.startswith("_"))
        ]

    def do_add_layer(self, wmslayer, layer):
        getattr(self.usewms.add_layer, wmslayer)(layer=layer)


class WMS_OSM:
    layer_prefix = "OSM_"
    name = "OpenStreetMap"

    def __init__(self, m=None):
        self.m = m
        self.wmslayers = [
            key
            for key in self.m.add_wms.OpenStreetMap.add_layer.__dict__.keys()
            if not (key in ["m"] or key.startswith("_"))
        ]

    def do_add_layer(self, wmslayer, layer):
        getattr(self.m.add_wms.OpenStreetMap.add_layer, wmslayer)(layer=layer)


class WMS_S2_cloudless:
    layer_prefix = "S2_"
    name = "S2 cloudless"

    def __init__(self, m=None):
        self.m = m
        wmslayers = sorted(self.m.add_wms.S2_cloudless.layers)

        if self.m.crs_plot == self.m.CRS.GOOGLE_MERCATOR:
            wmslayers = [i for i in wmslayers if i.endswith("3857")]
        else:
            wmslayers = [i for i in wmslayers if not i.endswith("3857")]

        self.wmslayers = wmslayers

    def do_add_layer(self, wmslayer, layer):
        getattr(self.m.add_wms.S2_cloudless.add_layer, wmslayer)(layer=layer)


class WMS_ESA_WorldCover:
    layer_prefix = ""
    name = "ESA WorldCover"

    def __init__(self, m=None):
        self.m = m
        self.wmslayers = [
            key
            for key in self.m.add_wms.ESA_WorldCover.layers
            if (key.startswith("WORLDCOVER") or key.startswith("COP"))
        ]

    def do_add_layer(self, wmslayer, layer):
        getattr(self.m.add_wms.ESA_WorldCover.add_layer, wmslayer)(layer=layer)


class WMS_S1GBM:
    layer_prefix = "S1GBM_"
    name = "S1GBM"

    def __init__(self, m=None):
        self.m = m
        self.wmslayers = ["vv", "vh"]

    def do_add_layer(self, wmslayer, layer):
        getattr(self.m.add_wms.S1GBM.add_layer, wmslayer)(layer=layer)


class AddWMSMenuButton(QtWidgets.QPushButton):
    def __init__(self, *args, m=None, new_layer=False, show_layer=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m
        self._new_layer = new_layer
        self._show_layer = show_layer

        self.wms_dict = {
            "OpenStreetMap": WMS_OSM,
            "S2 Cloudless": WMS_S2_cloudless,
            "ESA WorldCover": WMS_ESA_WorldCover,
            "S1GBM:": WMS_S1GBM,
            "GEBCO:": WMS_GEBCO,
            "NASA GIBS:": WMS_NASA_GIBS,
        }

        if self._new_layer:
            self.setText("Create new WebMap Layer")
        else:
            self.setText("Add WebMap Service")

        width = self.fontMetrics().boundingRect(self.text()).width()
        self.setFixedWidth(width + 30)

        self.feature_menu = QtWidgets.QMenu()
        self.feature_menu.setStyleSheet("QMenu { menu-scrollable: 1;}")
        self.feature_menu.aboutToShow.connect(self.populate_menu)

        self.setMenu(self.feature_menu)
        self.clicked.connect(
            lambda: self.feature_menu.popup(self.mapToGlobal(self.menu_button.pos()))
        )

    def populate_menu(self):
        self.sub_menus = dict()
        for wmsname in self.wms_dict:
            self.sub_menus[wmsname] = self.feature_menu.addMenu(wmsname)
            self.sub_menus[wmsname].aboutToShow.connect(self.populate_submenu)

        self.feature_menu.aboutToShow.disconnect()

    def populate_submenu(self):
        if not isinstance(self.sender(), QtWidgets.QMenu):
            return

        wmsname = self.sender().title()

        try:
            wmsclass = self.wms_dict[wmsname]
            wms = wmsclass(m=self.m)
            sub_features = wms.wmslayers
            for wmslayer in sub_features:
                action = self.sub_menus[wmsname].addAction(wmslayer)
                action.triggered.connect(self.menu_callback_factory(wms, wmslayer))
        except:
            self.window().statusBar().showMessage(
                "There was a problem while fetching the WMS layer: " + wmsname
            )

        self.sub_menus[wmsname].aboutToShow.disconnect()

    def menu_callback_factory(self, wms, wmslayer):
        layer = self.m.BM.bg_layer
        if layer.startswith("_") and "|" in layer:
            self.window().statusBar().showMessage(
                "Adding features to temporary multi-layers is not supported!", 3000
            )
            return

        def wms_cb():
            if self._new_layer:
                layer = wms.name + "_" + wmslayer
                # indicate creation of new layer in statusbar
                self.window().statusBar().showMessage(
                    f"New WebMap layer '{layer}' created!", 2000
                )

            else:
                layer = self.m.BM.bg_layer
                if layer.startswith("_") and "|" in layer:
                    self.window().statusBar().showMessage(
                        "Adding features to temporary multi-layers is not supported!",
                        3000,
                    )

                layer = self.m.BM._bg_layer

            wms.do_add_layer(wmslayer, layer=layer)

            if self._show_layer:
                self.m.show_layer(layer)

        return wms_cb

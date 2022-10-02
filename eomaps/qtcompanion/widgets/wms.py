from PyQt5 import QtWidgets


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
        self.wmslayers = sorted(self.m.add_wms.S2_cloudless.layers)

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
    def __init__(self, *args, m=None, new_layer=False, **kwargs):
        super().__init__(*args, **kwargs)

        self.m = m
        self._new_layer = new_layer

        wms_dict = {
            "OpenStreetMap": WMS_OSM,
            "S2 Cloudless": WMS_S2_cloudless,
            "ESA WorldCover": WMS_ESA_WorldCover,
            "S1GBM:": WMS_S1GBM,
        }

        if self._new_layer:
            self.setText("Create new WebMap Layer")
        else:
            self.setText("Add WebMap Service")

        width = self.fontMetrics().boundingRect(self.text()).width()
        self.setFixedWidth(width + 30)

        feature_menu = QtWidgets.QMenu()
        feature_menu.setStyleSheet("QMenu { menu-scrollable: 1;}")

        for wmsname, wmsclass in wms_dict.items():
            try:
                wms = wmsclass(m=self.m)
                sub_menu = feature_menu.addMenu(wmsname)

                sub_features = wms.wmslayers
                for wmslayer in sub_features:
                    action = sub_menu.addAction(wmslayer)
                    action.triggered.connect(self.menu_callback_factory(wms, wmslayer))
            except:
                print("there was a problem while fetching the WMS layer", wmsname)
        self.setMenu(feature_menu)
        self.clicked.connect(
            lambda: feature_menu.popup(self.mapToGlobal(self.menu_button.pos()))
        )

    def menu_callback_factory(self, wms, wmslayer):
        if self.m.BM.bg_layer.startswith("_"):
            print(
                "Adding features to temporary multi-layers is not supported!"
                "Create a specific multi-layer (e.g. 'layer1|layer2' first!"
            )
            return

        def wms_cb():
            if self._new_layer:
                layer = wms.name + "_" + wmslayer
            else:
                layer = self.m.BM._bg_layer

            wms.do_add_layer(wmslayer, layer=layer)

            if self._new_layer:
                self.m.show_layer(layer)

        return wms_cb

import matplotlib as mpl

mpl.rcParams["toolbar"] = "None"

import unittest
import warnings

from eomaps import Maps
import matplotlib.pyplot as plt
from matplotlib.backend_bases import MouseEvent
import requests
import xml


def button_press_event(canvas, x, y, button, dblclick=False, guiEvent=None):
    canvas._button = button
    s = "button_press_event"
    mouseevent = MouseEvent(
        s, canvas, x, y, button, canvas._key, dblclick=dblclick, guiEvent=guiEvent
    )
    canvas.callbacks.process(s, mouseevent)


def button_release_event(canvas, x, y, button, guiEvent=None):
    s = "button_release_event"
    event = MouseEvent(s, canvas, x, y, button, canvas._key, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)
    canvas._button = None


def scroll_event(canvas, x, y, step, guiEvent=None):
    s = "scroll_event"
    event = MouseEvent(s, canvas, x, y, step=step, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)


def motion_notify_event(canvas, x, y, guiEvent=None):
    s = "motion_notify_event"
    event = MouseEvent(s, canvas, x, y, guiEvent=guiEvent)
    canvas.callbacks.process(s, event)


class TestWMS(unittest.TestCase):
    def setUp(self):
        pass

    def test_WMS_OSM(self):
        try:
            m = Maps(Maps.CRS.GOOGLE_MERCATOR)
            m.add_wms.OpenStreetMap.add_layer.default()
            plt.close(m.f)
        except requests.exceptions.ConnectionError:
            warnings.warn("Encountered a connection error for OSM")
        except requests.exceptions.ConnectTimeout:
            warnings.warn("Encountered a connection timeout for OSM")

    def test_WMS_S1GBM(self):
        try:
            m = Maps(Maps.CRS.GOOGLE_MERCATOR)
            m.add_wms.S1GBM.add_layer.vv()
            plt.close(m.f)
        except requests.exceptions.ConnectionError:
            warnings.warn("Encountered a connection error for S1GBM")
        except requests.exceptions.ConnectTimeout:
            warnings.warn("Encountered a connection timeout for S1GBM")

    def test_WMS_ESA_WorldCover(self):
        try:
            m = Maps(Maps.CRS.GOOGLE_MERCATOR)
            m.add_feature.preset.coastline()
            ESA_layer = m.add_wms.ESA_WorldCover.add_layer.WORLDCOVER_2020_MAP
            ESA_layer.set_extent_to_bbox()
            ESA_layer.info

            ESA_layer()

            plt.close(m.f)
        except requests.exceptions.ConnectionError:
            warnings.warn("Encountered a connection error for ESA_WorldCover")
        except requests.exceptions.ConnectTimeout:
            warnings.warn("Encountered a connection timeout for ESA_WorldCover")

    def test_ArcGIS_REST_API(self):
        try:
            m = Maps(Maps.CRS.GOOGLE_MERCATOR)
            m.add_feature.preset.ocean(ec="k", zorder=100)
            hillshade = m.add_wms.ESRI_ArcGIS.Elevation.Elevation_World_Hillshade
            hillshade.add_layer.xyz_layer()
            plt.close(m.f)
        except requests.exceptions.ConnectionError:
            warnings.warn("Encountered a connection error for ArcGIS_REST_API")
        except requests.exceptions.ConnectTimeout:
            warnings.warn("Encountered a connection timeout for ArcGIS_REST_API")

    def test_WMS_legend_capabilities_NASA_GIBS(self):
        try:
            m = Maps(4326)
            m.add_feature.preset.coastline()

            # use a layer that provides a legend
            NASA_layer = (
                m.add_wms.NASA_GIBS.EPSG_4326.add_layer.AIRS_L2_Cloud_Top_Height_Night
            )
            NASA_layer.set_extent_to_bbox()

            NASA_layer.info

            NASA_layer(transparent=True)
            NASA_layer.add_legend()

            legax = m.f.axes[-1]
            leg_cpos = (
                (legax.bbox.x0 + legax.bbox.x1) / 2,
                (legax.bbox.y0 + legax.bbox.y1) / 2,
            )

            # pick up the the legend (e.g. click on it)
            button_press_event(m.f.canvas, *leg_cpos, 1, False)

            # resize the legend
            scroll_event(m.f.canvas, *leg_cpos, 20, False)

            # move the legend
            motion_notify_event(
                m.f.canvas,
                (m.ax.bbox.x0 + m.ax.bbox.x1) / 2,
                (m.ax.bbox.y0 + m.ax.bbox.y1) / 2,
                None,
            )

            # release the legend
            button_press_event(m.f.canvas, 0, 0, 1, False)
            plt.close(m.f)
        except requests.exceptions.ConnectionError:
            warnings.warn("Encountered a connection error for NASA_GIBS")
        except requests.exceptions.ConnectTimeout:
            warnings.warn("Encountered a connection timeout for NASA_GIBS")
        except xml.etree.ElementTree.ParseError:
            warnings.warn("Encountered a ParseError for NASA_GIBS legend")

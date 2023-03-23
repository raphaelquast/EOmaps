import matplotlib as mpl

mpl.rcParams["toolbar"] = "None"

import unittest
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from eomaps import Maps
from pathlib import Path


class TestFromFile(unittest.TestCase):
    def setUp(self):
        self.csvpath = Path(__file__).parent / "_testdata" / "testfile.csv"
        self.tiffpath = Path(__file__).parent / "_testdata" / "testfile.tif"
        self.netcdfpath = Path(__file__).parent / "_testdata" / "testfile.nc"
        pass

    def test_CSV(self):
        data = Maps.read_file.CSV(
            self.csvpath, x="x", y="y", parameter="data", crs=4326
        )
        m = Maps.from_file.CSV(
            self.csvpath, x="x", y="y", parameter="data", data_crs=4326
        )

        m2 = m.new_layer_from_file.CSV(
            self.csvpath,
            x="x",
            y="y",
            parameter="data",
            data_crs=4326,
            layer="second",
            cmap="cividis",
            extent=(-20, 20, -56, 78),
        )
        m.show_layer(m2.layer)

        plt.close("all")

    def test_GeoTIFF(self):
        data = Maps.read_file.GeoTIFF(self.tiffpath)
        m = Maps.from_file.GeoTIFF(self.tiffpath)

        m2 = m.new_layer_from_file.GeoTIFF(
            self.tiffpath,
            layer="second",
            cmap="cividis",
            shape="shade_points",
            extent=(7, 9, 41, 42),
        )
        m.show_layer(m2.layer)
        plt.close("all")

    def test_NetCDF(self):
        data = Maps.read_file.NetCDF(self.netcdfpath, data_crs=4326)
        m = Maps.from_file.NetCDF(
            self.netcdfpath, data_crs=4326, shape="voronoi_diagram"
        )

        m2 = m.new_layer_from_file.NetCDF(
            self.netcdfpath,
            layer="second",
            cmap="cividis",
            shape="shade_raster",
            data_crs=4326,
            extent=((7, 9, 41, 42), 4326),
        )
        m.show_layer(m2.layer)
        plt.close("all")

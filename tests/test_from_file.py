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
        )
        m2.show()

    def test_GeoTIFF(self):
        data = Maps.read_file.GeoTIFF(self.tiffpath)
        m = Maps.from_file.GeoTIFF(self.tiffpath)

        m2 = m.new_layer_from_file.GeoTIFF(
            self.tiffpath, layer="second", cmap="cividis", shape="shade_points"
        )
        m2.show()

    def test_NetCDF(self):
        data = Maps.read_file.NetCDF(self.netcdfpath, data_crs=4326)
        m = Maps.from_file.NetCDF(
            self.netcdfpath, data_crs=4326, shape="voronoi_diagram"
        )

        m2 = m.new_layer_from_file.NetCDF(
            self.netcdfpath,
            layer="second",
            cmap="cividis",
            shape="shade_points",
            data_crs=4326,
        )

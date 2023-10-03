import unittest
from pathlib import Path
import matplotlib.pyplot as plt
from eomaps import Maps


class TestRasterAggregation(unittest.TestCase):
    def setUp(self):
        self.tiffpath = Path(__file__).parent / "_testdata" / "testfile.tif"
        self.extent = (
            7.989179329607744,
            8.492294242279327,
            40.50104703441937,
            40.87109579596078,
        )

    def test_raster_aggregation(self):
        for agg in [
            "mean",
            "sum",
            "min",
            "max",
            "first",
            "last",
            "median",
            "spline",
            "fast_mean",
            "fast_sum",
        ]:

            m = Maps.from_file.GeoTIFF(
                self.tiffpath,
                shape=dict(shape="raster", maxsize=1e3, aggregator=agg),
                vmin=-2000,
                vmax=0,
            )
            m.set_extent(self.extent)
            m.add_title(agg)
            m.f.canvas.draw()
        plt.close("all")

    def test_raster_aggregation_reprojected(self):
        for agg in [
            "mean",
            "sum",
            "min",
            "max",
            "first",
            "last",
            "median",
            "spline",
            "fast_mean",
            "fast_sum",
        ]:

            m = Maps.from_file.GeoTIFF(
                self.tiffpath,
                plot_crs=3857,
                shape=dict(shape="raster", maxsize=2e3, aggregator=agg),
                vmin=-2000,
                vmax=0,
            )
            m.add_title(agg)
            m.set_extent(self.extent)
            m.f.canvas.draw()
        plt.close("all")

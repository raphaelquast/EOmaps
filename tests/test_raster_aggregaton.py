import unittest
from pathlib import Path
import matplotlib.pyplot as plt
from eomaps import Maps


class TestRasterAggregation(unittest.TestCase):
    def setUp(self):
        self.tiffpath = Path(__file__).parent / "_testdata" / "testfile.tif"
        self.netcdfpath = Path(__file__).parent / "_testdata" / "testfile.nc"

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
            for valid_fraction in (0, 0.5):
                m = Maps.from_file.GeoTIFF(
                    self.tiffpath,
                    shape=dict(shape="raster", maxsize=1e2, aggregator=agg),
                    # shape=dict(shape="shade_raster"),
                    vmin=-2000,
                    vmax=0,
                )
                m.set_extent(self.extent)
                m.add_title(agg)

                m = Maps.from_file.NetCDF(
                    self.netcdfpath,
                    data_crs=4326,
                    shape=dict(shape="raster", maxsize=1e2, aggregator=agg),
                )
                m.set_extent(self.extent)
                m.add_title(agg)

                m.f.canvas.draw()

            plt.close("all")

    def _test_raster_aggregation_reprojected(self):
        for agg in [
            "mean",
            "sum",
            "min",
            "max",
            "std",
            "first",
            "last",
            "median",
            "spline",
            "fast_mean",
            "fast_sum",
        ]:
            for valid_fraction in (0, 0.5):

                m = Maps.from_file.GeoTIFF(
                    self.tiffpath,
                    plot_crs=3857,
                    shape=dict(shape="raster", maxsize=2e3, aggregator=agg),
                    vmin=-2000,
                    vmax=0,
                )
                m.add_title(agg)
                m.set_extent(self.extent)

                m = Maps.from_file.NetCDF(
                    self.netcdfpath,
                    plot_crs=3857,
                    data_crs=4326,
                    shape=dict(shape="raster", maxsize=1e2, aggregator=agg),
                )
                m.set_extent(self.extent)
                m.add_title(agg)

                m.f.canvas.draw()
            plt.close("all")

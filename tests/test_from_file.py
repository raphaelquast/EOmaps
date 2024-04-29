import pytest
from eomaps import Maps
from pathlib import Path

paths = {
    "CSV": Path(__file__).parent / "_testdata" / "testfile.csv",
    "GeoTIFF": Path(__file__).parent / "_testdata" / "testfile.tif",
    "NetCDF": Path(__file__).parent / "_testdata" / "testfile.nc",
}

read_args = {
    "CSV": dict(x="x", y="y", parameter="data", crs=4326),
    "NetCDF": dict(data_crs=4326),
}

plot_args = {
    "CSV": dict(x="x", y="y", parameter="data", data_crs=4326),
    "NetCDF": dict(data_crs=4326),
}

style_args = {
    "CSV": dict(cmap="cividis", shape="ellipses"),
    "GeoTIFF": dict(shape="raster", extent=(7, 9, 41, 42)),
    "NetCDF": dict(shape="voronoi_diagram"),
}


@pytest.mark.parametrize("method", ["CSV", "GeoTIFF", "NetCDF"])
def test_read_file(method):
    _ = getattr(Maps.read_file, method)(paths[method], **read_args.get(method, {}))


@pytest.mark.parametrize("method", ["CSV", "GeoTIFF", "NetCDF"])
@pytest.mark.mpl_image_compare()
def test_from_file(method):
    m = getattr(Maps.from_file, method)(
        paths[method], **plot_args.get(method, {}), **style_args.get(method, {})
    )
    m.add_feature.preset.coastline()
    m.add_gridlines(lw=2, auto_n=5)
    return m


@pytest.mark.parametrize("method", ["CSV", "GeoTIFF", "NetCDF"])
@pytest.mark.mpl_image_compare()
def test_new_layer_from_file(method):

    m = Maps(Maps.CRS.Mollweide(), layer="all")
    m.add_feature.preset.coastline()
    m.add_gridlines(lw=2, auto_n=5)

    m2 = getattr(m.new_layer_from_file, method)(
        paths[method],
        **plot_args.get(method, {}),
        **style_args.get(method, {}),
        layer="second",
    )
    m.show_layer(m2.layer)

    return m

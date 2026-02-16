import pytest
from eomaps import Maps


@pytest.mark.parametrize("reproject", ["gpd", "cartopy"])
@pytest.mark.parametrize("clip", ["crs", "crs_bounds", "extent"])
def test_gdf_reproject(reproject, clip):

    m = Maps(3035)
    m.set_extent(
        (5.2197051759523285, 15.049503639569611, 38.13009442774602, 43.90360564611554)
    )
    gdf = m.add_feature.physical.coastline.get_gdf()

    m.add_gdf(gdf, reproject=reproject, clip=clip)

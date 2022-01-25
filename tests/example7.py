# EOmaps example 7: Using geopandas - interactive shapes!

from eomaps import Maps, MapsGrid
from cartopy.feature import shapereader
import geopandas as gpd
import pandas as pd
import numpy as np

# ----------- create some example-data
lon, lat = np.meshgrid(np.linspace(-180, 180, 25), np.linspace(-90, 90, 25))
data = pd.DataFrame(
    dict(lon=lon.flat, lat=lat.flat, data=np.sqrt(lon ** 2 + lat ** 2).flat)
)

# ----------- load some data from NaturalEarth and put in in a geopandas.GeoDataFrame
path = shapereader.natural_earth(
    resolution="10m", category="cultural", name="admin_0_countries"
)
r = shapereader.Reader(path)
gdf = gpd.GeoDataFrame(
    dict(name=[i.attributes["NAME_EN"] for i in r.records()]),
    geometry=[*r.geometries()],
    crs=4326,
)

# -----------  define a callback to color picked objects
def cb(self, ind, **kwargs):
    if ind is not None:
        # get the selected geometry and re-project it to the desired crs
        geom = self.cb.pick["countries"].data.loc[[ind]].geometry
        # add the geometry to the map
        art = self.figure.ax.add_geometries(
            geom, self.figure.ax.projection, fc="r", alpha=0.75
        )
        # make the geometry temporary (e.g. remove it on the next pick event)
        self.cb.pick["countries"].add_temporary_artist(art, layer=2)


# -----------  define a callback to get the name of the picked object
def txt(m, ID, val, pos, ind):
    if ind is not None:
        return gdf.loc[ind]["name"]


# ----------- setup some maps objects and assign datasets and the plot-crs
mg = MapsGrid(1, 2)
mg.m_0_0.set_data(data=data.sample(100), xcoord="lon", ycoord="lat", crs=4326)
mg.m_0_0.plot_specs.crs = 4326

mg.m_0_1.set_data(data=data, xcoord="lon", ycoord="lat", crs=4326)
mg.m_0_1.plot_specs.crs = Maps.CRS.Orthographic(45, 45)

mg.add_feature.preset.ocean()

for m in mg:
    # plot the attached dataset and attach callbacks to it
    m.set_shape.rectangles(radius=3, radius_crs=4326)
    m.plot_map(alpha=0.75, ec=(1, 1, 1, 0.5), pick_distance=25, colorbar=False)

    m.cb.pick.attach.mark(
        permanent=False, shape="rectangles", fc="none", ec="b", lw=2, layer=1
    )

    # plot a geopandas GeoDataFrame and attach some callbacks to it
    m.add_gdf(
        gdf,
        picker_name="countries",
        fc="none",
        lw=0.5,
        zorder=10,
    )
    m.cb.pick["countries"].attach(cb)
    m.cb.pick["countries"].attach.annotate(text=txt)


mg.share_pick_events()  # share default pick events
mg.share_pick_events("countries")  # share the events of the "countries" picker
mg.f.set_figheight(6)
mg.f.tight_layout()

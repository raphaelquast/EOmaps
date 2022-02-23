try:
    from equi7grid import equi7grid

    equ7_OK = True
except ImportError:
    equ7_OK = False

from pathlib import Path

from shapely.geometry import shape
import shapefile

from cartopy import crs as ccrs
from pyproj import CRS


class Equi7Grid_projection(ccrs.Projection):
    """
    Equi7Grid projection for cartopy.

    >>> m = Maps(Equi7Grid_projection("EU"))
    >>> m.add_feature.preset.coastline()
    >>> m.ax.add_geometries([m.ax.projection.equi7_zone_polygon],
    >>>                     m.ax.projection, fc="none", ec="r")

    possible subgrid's are:
        - "EU": Europe
        - "AF": Africa
        - "AS": Asia
        - "NA": North-America
        - "SA": South-America
        - "OC": Oceania
        - "AN": Antarctica

    See https://github.com/TUW-GEO/Equi7Grid for details.
    """

    subgrids = ["EU", "AF", "AS", "NA", "SA", "OC", "AN"]

    def __init__(self, subgrid="EU", *args, **kwargs):
        assert equ7_OK, (
            "EOmaps: Missing dependency for Equi7Grid_projection: 'equi7grid'."
            + "To install, use `pip install equi7grid`"
        )

        equi7path = Path(equi7grid.__file__)

        shppath = (
            equi7path.parent
            / "grids"
            / subgrid
            / "PROJ"
            / f"EQUI7_V14_{subgrid}_PROJ_ZONE.shp"
        )

        self.subgrid = subgrid

        self.wkt = CRS.from_wkt(equi7grid.Equi7Grid._static_data[self.subgrid]["wkt"])

        with shapefile.Reader(str(shppath)) as r:
            projpoly = shape(r.shape())

        b = projpoly.bounds
        proj4params = self.wkt

        super().__init__(proj4params, *args, **kwargs)

        self._boundary = projpoly.boundary.envelope.boundary
        self.bounds = [b[0], b[2], b[1], b[3]]

        self.equi7_zone_polygon = projpoly

    @property
    def boundary(self):
        return self._boundary

    @classmethod
    def _pyproj_crs_generator(cls):
        # return a generator that yields Equi7Grid pyproj CRS instances
        # (used to properly identify Equi7Grid crs as cartopy crs)
        if not equ7_OK:
            return
        for subgrid in cls.subgrids:
            yield (
                subgrid,
                CRS.from_wkt(equi7grid.Equi7Grid._static_data[subgrid]["wkt"]),
            )

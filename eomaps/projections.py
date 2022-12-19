from cartopy import crs as ccrs
from pyproj import CRS

# fmt: off
equi7_wkt = {
       'AF': 'PROJCS["Azimuthal_Equidistant",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Azimuthal_Equidistant"],PARAMETER["latitude_of_center",8.5],PARAMETER["longitude_of_center",21.5],PARAMETER["false_easting",5621452.01998],PARAMETER["false_northing",5990638.42298],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
       'AN': 'PROJCS["Azimuthal_Equidistant",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Azimuthal_Equidistant"],PARAMETER["latitude_of_center",-90],PARAMETER["longitude_of_center",0],PARAMETER["false_easting",3714266.97719],PARAMETER["false_northing",3402016.50625],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
       'AS': 'PROJCS["Azimuthal_Equidistant",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Azimuthal_Equidistant"],PARAMETER["latitude_of_center",47],PARAMETER["longitude_of_center",94],PARAMETER["false_easting",4340913.84808],PARAMETER["false_northing",4812712.92347],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
       'EU': 'PROJCS["Azimuthal_Equidistant",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Azimuthal_Equidistant"],PARAMETER["latitude_of_center",53],PARAMETER["longitude_of_center",24],PARAMETER["false_easting",5837287.81977],PARAMETER["false_northing",2121415.69617],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
       'NA': 'PROJCS["Azimuthal_Equidistant",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Azimuthal_Equidistant"],PARAMETER["latitude_of_center",52],PARAMETER["longitude_of_center",-97.5],PARAMETER["false_easting",8264722.17686],PARAMETER["false_northing",4867518.35323],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
       'OC': 'PROJCS["Azimuthal_Equidistant",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Azimuthal_Equidistant"],PARAMETER["latitude_of_center",-19.5],PARAMETER["longitude_of_center",131.5],PARAMETER["false_easting",6988408.5356],PARAMETER["false_northing",7654884.53733],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]',
       'SA': 'PROJCS["Azimuthal_Equidistant",GEOGCS["WGS 84",DATUM["WGS_1984",SPHEROID["WGS 84",6378137,298.257223563,AUTHORITY["EPSG","7030"]],AUTHORITY["EPSG","6326"]],PRIMEM["Greenwich",0],UNIT["Degree",0.0174532925199433]],PROJECTION["Azimuthal_Equidistant"],PARAMETER["latitude_of_center",-14],PARAMETER["longitude_of_center",-60.5],PARAMETER["false_easting",7257179.23559],PARAMETER["false_northing",5592024.44605],UNIT["metre",1,AUTHORITY["EPSG","9001"]],AXIS["Easting",EAST],AXIS["Northing",NORTH]]'
       }

equi7_bounds = {
    'AF': [1.2543052434921265e-05, 11480904.712667901,
           2.4167820811271667e-06, 9364439.712266332],
    'AN': [-4.377216100692749e-08, 9708998.50615953,
           6.062444299459457e-06, 8723837.623274699],
    'AS': [1.897849142551422e-05, 11571909.44067226,
           -2.6971101760864258e-06, 9675694.372909721],
    'EU': [1.7520040273666382e-05, 8229145.40230763,
           -2.760905772447586e-06, 5588300.082247556],
    'NA': [1.2945383787155151e-05, 13311049.338409482,
           1.0095536708831787e-06, 9813819.228253476],
    'OC': [1.851562410593033e-05, 18717928.292316865,
           1.7517246305942535e-05, 12188756.619997777],
    'SA': [7.836148142814636e-06, 11687457.98940951,
           7.897615432739258e-06, 10511084.6923448]
    }
# fmt: on


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

    subgrids = list(equi7_wkt)

    def __init__(self, subgrid="EU", *args, **kwargs):
        self.subgrid = subgrid

        self.wkt = equi7_wkt[self.subgrid]
        super().__init__(self.wkt, *args, **kwargs)

        self.bounds = equi7_bounds[self.subgrid]

    @classmethod
    def _pyproj_crs_generator(cls):
        # return a generator that yields Equi7Grid pyproj CRS instances
        # (used to properly identify Equi7Grid crs as cartopy crs)
        for subgrid in cls.subgrids:
            yield (
                subgrid,
                CRS.from_wkt(equi7_wkt[subgrid]),
            )


ccrs.Equi7Grid_projection = Equi7Grid_projection

ccrs.Equi7_EU = Equi7Grid_projection("EU")
ccrs.Equi7_AF = Equi7Grid_projection("AF")
ccrs.Equi7_AS = Equi7Grid_projection("AS")
ccrs.Equi7_NA = Equi7Grid_projection("NA")
ccrs.Equi7_SA = Equi7Grid_projection("SA")
ccrs.Equi7_OC = Equi7Grid_projection("OC")
ccrs.Equi7_AN = Equi7Grid_projection("AN")

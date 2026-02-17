import logging

_log = logging.getLogger(__name__)

from difflib import get_close_matches
from pathlib import Path

import numpy as np
import matplotlib.path as mpath

from ..cb_container import GeoDataFramePicker
from ..helpers import _get_rect_poly_verts, register_modules, progressbar


class GeopandasMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def __lazy_attrs(self):
        # list of attributes that support lazy-evaluation
        return [i for i in dir(GeopandasMixin) if not i.startswith("_")]

    def _make_rect_poly(self, x0, y0, x1, y1, crs=None, npts=100):
        """
        Return a geopandas.GeoDataFrame with a rectangle in the given crs.

        Parameters
        ----------
        x0, y0, y1, y1 : float
            the boundaries of the shape
        npts : int, optional
            The number of points used to draw the polygon-lines. The default is 100.
        crs : any, optional
            a coordinate-system identifier.  (e.g. output of `m.get_crs(crs)`)
            The default is None.

        Returns
        -------
        gdf : geopandas.GeoDataFrame
            the geodataframe with the shape and crs defined

        """
        (gpd,) = register_modules("geopandas")

        from shapely.geometry import Polygon

        verts = _get_rect_poly_verts(x0=x0, y0=y0, x1=x1, y1=y1, npts=npts)
        gdf = gpd.GeoDataFrame(geometry=[Polygon(verts)])
        gdf.set_crs(crs, inplace=True)

        return gdf

    def add_gdf(
        self,
        gdf,
        picker_name=None,
        pick_method="contains",
        val_key=None,
        layer=None,
        temporary_picker=None,
        clip=False,
        reproject="gpd",
        verbose=False,
        only_valid=False,
        set_extent=False,
        permanent=True,
        **kwargs,
    ):
        """
        Plot a `geopandas.GeoDataFrame` on the map.

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame, str or pathlib.Path
            A GeoDataFrame that should be added to the plot.

            If a string (or pathlib.Path) is provided, it is identified as the path to
            a file that should be read with `geopandas.read_file(gdf)`.

        picker_name : str or None
            A unique name that is used to identify the pick-method.

            If a `picker_name` is provided, a new pick-container will be
            created that can be used to pick geometries of the GeoDataFrame.

            The container can then be accessed via:
            >>> m.cb.pick__<picker_name>
            or
            >>> m.cb.pick[picker_name]
            and it can be used in the same way as `m.cb.pick...`

        pick_method : str or callable
            if str :
                The operation that is executed on the GeoDataFrame to identify
                the picked geometry.
                Possible values are:

                - "contains":
                  pick a geometry only if it contains the clicked point
                  (only works with polygons! (not with lines and points))
                - "centroids":
                  pick the closest geometry with respect to the centroids
                  (should work with any geometry whose centroid is defined)

                The default is "centroids"

            if callable :
                A callable that is used to identify the picked geometry.
                The call-signature is:

                >>> def picker(artist, mouseevent):
                >>>     # if the pick is NOT successful:
                >>>     return False, dict()
                >>>     ...
                >>>     # if the pick is successful:
                >>>     return True, dict(ID, pos, val, ind)

                The default is "contains"

        val_key : str
            The dataframe-column used to identify values for pick-callbacks.
            The default is the value provided via `column=...` or None.
        layer : int, str or None
            The name of the layer at which the dataset will be plotted.

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer assigned to the Maps-object is used (e.g. `m.layer`)

            The default is None.
        temporary_picker : str, optional
            The name of the picker that should be used to make the geometry
            temporary (e.g. remove it after each pick-event)
        clip : str or False
            This feature can help with re-projection issues for non-global crs.
            (see example below)

            Indicator if geometries should be clipped prior to plotting or not.

            - if "crs": clip with respect to the boundary-shape of the crs
            - if "crs_bounds" : clip with respect to a rectangular crs boundary
            - if "extent": clip with respect to the current extent of the plot-axis.

            >>> mg = MapsGrid(2, 3, crs=3035)
            >>> mg.m_0_0.add_feature.preset.ocean(use_gpd=True)
            >>> mg.m_0_1.add_feature.preset.ocean(use_gpd=True, clip="crs")
            >>> mg.m_0_2.add_feature.preset.ocean(use_gpd=True, clip="extent")
            >>> mg.m_1_0.add_feature.preset.ocean(use_gpd=False)
            >>> mg.m_1_1.add_feature.preset.ocean(use_gpd=False, clip="crs")
            >>> mg.m_1_2.add_feature.preset.ocean(use_gpd=False, clip="extent")

        reproject : str, optional
            Similar to "clip" this feature mainly addresses issues in the way how
            re-projected geometries are displayed in certain coordinate-systems.
            (see example below)

            - if "gpd": re-project geometries geopandas
            - if "cartopy": re-project geometries with cartopy (slower but more robust)

            The default is "gpd".

            >>> mg = MapsGrid(2, 1, crs=Maps.CRS.Stereographic())
            >>> mg.m_0_0.add_feature.preset.ocean(reproject="gpd")
            >>> mg.m_1_0.add_feature.preset.ocean(reproject="cartopy")

        verbose : bool, optional
            Indicator if a progressbar should be printed when re-projecting
            geometries with "use_gpd=False". The default is False.
        only_valid : bool, optional
            - If True, only valid geometries (e.g. `gdf.is_valid`) are plotted.
            - If False, all geometries are attempted to be plotted
              (this might result in errors for infinite geometries etc.)

            The default is True
        set_extent: bool, optional
            - if True, set map extent to the extent of the geometries with +-5% margin.
            - if float, use the value as margin (0-1).

            The default is True.
        permanent : bool, optional
            If True, all created artists are added as "permanent" background
            artists. If  False, artists are added as dynamic artists.
            The default is True.
        kwargs :
            all remaining kwargs are passed to `geopandas.GeoDataFrame.plot(**kwargs)`

        Returns
        -------
        new_artists : matplotlib.Artist
            The matplotlib-artists added to the plot

        """
        (gpd,) = register_modules("geopandas")

        if val_key is None:
            val_key = kwargs.get("column", None)

        gdf = self._handle_gdf(
            gdf,
            val_key=val_key,
            only_valid=only_valid,
            clip=clip,
            reproject=reproject,
            verbose=verbose,
        )

        # plot gdf and identify newly added collections
        # (geopandas always uses collections)
        colls = [id(i) for i in self.ax.collections]
        artists, prefixes = [], []

        # drop all invalid geometries
        if only_valid:
            valid = gdf.is_valid
            n_invald = np.count_nonzero(~valid)
            gdf = gdf[valid]
            if len(gdf) == 0:
                _log.error("EOmaps: GeoDataFrame contains only invalid geometries!")
                return
            elif n_invald > 0:
                _log.warning(
                    "EOmaps: {n_invald} invalid GeoDataFrame geometries are ignored!"
                )

        if set_extent:
            extent = np.array(
                [
                    gdf.bounds["minx"].min(),
                    gdf.bounds["maxx"].max(),
                    gdf.bounds["miny"].min(),
                    gdf.bounds["maxy"].max(),
                ]
            )

            if isinstance(set_extent, (int, float, np.number)):
                margin = set_extent
            else:
                margin = 0.05

            dx = extent[1] - extent[0]
            dy = extent[3] - extent[2]

            d = max(dx, dy) * margin
            extent[[0, 2]] -= d
            extent[[1, 3]] += d

            self.set_extent(extent, crs=gdf.crs)

        for geomtype, geoms in gdf.groupby(gdf.geom_type):
            gdf.plot(ax=self.ax, aspect=self.ax.get_aspect(), **kwargs)
            artists = [i for i in self.ax.collections if id(i) not in colls]
            for i in artists:
                prefixes.append(f"_{i.__class__.__name__.replace('Collection', '')}")

        if picker_name is not None:
            if isinstance(pick_method, str):
                picker_cls = GeoDataFramePicker(
                    gdf=gdf, pick_method=pick_method, val_key=val_key
                )
                picker = picker_cls.get_picker()
            elif callable(pick_method):
                picker = pick_method
                picker_cls = None
            else:
                _log.error(
                    "EOmaps: The provided pick_method is invalid."
                    "Please provide either a string or a function."
                )
                return

            if len(artists) > 1:
                log_names = [picker_name + prefix for prefix in np.unique(prefixes)]
                _log.warning(
                    "EOmaps: Multiple geometry types encountered in `m.add_gdf`. "
                    + "The pick containers are re-named to"
                    + f"{log_names}"
                )
            else:
                prefixes = [""]

            for artist, prefix in zip(artists, prefixes):
                # make the newly added collection pickable
                self.cb.add_picker(picker_name + prefix, artist, picker=picker)
                # attach the re-projected GeoDataFrame to the pick-container
                self.cb.pick[picker_name + prefix].data = gdf
                self.cb.pick[picker_name + prefix].val_key = val_key
                self.cb.pick[picker_name + prefix]._picker_cls = picker_cls

        if layer is None:
            layer = self.layer

        if temporary_picker is not None:
            if temporary_picker == "default":
                for art, prefix in zip(artists, prefixes):
                    self.cb.pick.add_temporary_artist(art)
            else:
                for art, prefix in zip(artists, prefixes):
                    self.cb.pick[temporary_picker].add_temporary_artist(art)
        else:
            for art, prefix in zip(artists, prefixes):
                art.set_label(f"EOmaps GeoDataframe ({prefix.lstrip('_')}, {len(gdf)})")
                if permanent is True:
                    self.l[layer].add_bg_artist(art)
                else:
                    self.l[layer].add_artist(art)
        return artists

    def _handle_gdf(
        self,
        gdf,
        val_key=None,
        only_valid=True,
        clip=False,
        reproject="gpd",
        verbose=False,
    ):
        (gpd,) = register_modules("geopandas")

        if isinstance(gdf, (str, Path)):
            gdf = gpd.read_file(gdf)

        if only_valid:
            gdf = gdf[gdf.is_valid]

        try:
            # explode the GeoDataFrame to avoid picking multi-part geometries
            gdf = gdf.explode(index_parts=False)
        except Exception:
            # geopandas sometimes has problems exploding geometries...
            # if it does not work, just continue with the Multi-geometries!
            _log.error("EOmaps: Exploding geometries did not work!")
            pass

        if clip:
            gdf = self._clip_gdf(gdf, clip)
        if reproject == "gpd":
            gdf = gdf.to_crs(self.crs_plot)
        elif reproject == "cartopy":
            # optionally use cartopy's re-projection routines to re-project
            # geometries

            cartopy_crs = self._get_cartopy_crs(gdf.crs)
            if self.ax.projection != cartopy_crs:
                geoms = gdf.geometry
                if len(geoms) > 0:
                    proj_geoms = []

                    if verbose:
                        for g in progressbar(geoms, "EOmaps: re-projecting... ", 20):
                            proj_geoms.append(
                                self.ax.projection.project_geometry(g, cartopy_crs)
                            )
                    else:
                        for g in geoms:
                            proj_geoms.append(
                                self.ax.projection.project_geometry(g, cartopy_crs)
                            )
                    gdf = gdf.set_geometry(proj_geoms)
                    gdf = gdf.set_crs(self.ax.projection, allow_override=True)
                gdf = gdf[~gdf.is_empty]
        else:
            raise AssertionError(
                f"EOmaps: '{reproject}' is not a valid reproject-argument."
            )

        return gdf

    def _clip_gdf(self, gdf, how="crs"):
        """
        Clip the shapes of a GeoDataFrame with respect to the given boundaries.

        Parameters
        ----------
        gdf : geopandas.GeoDataFrame
            The GeoDataFrame containing the geometries.
        how : str, optional
            Identifier how the clipping should be performed.

            - clipping with geopandas:
              - "crs" : use the actual crs boundary polygon
              - "crs_bounds" : use the boundary-envelope of the crs
              - "extent" : use the current plot-extent

            The default is "crs".

        Returns
        -------
        gdf
            A GeoDataFrame with the clipped geometries

        """
        (gpd,) = register_modules("geopandas")

        if how == "crs" or how == "crs_invert":
            clip_shp = gpd.GeoDataFrame(
                geometry=[self.ax.projection.domain], crs=self.crs_plot
            ).to_crs(gdf.crs)
        elif how == "extent" or how == "extent_invert":
            self._bm.update()
            x0, x1, y0, y1 = self.get_extent(crs=self.crs_plot)
            clip_shp = self._make_rect_poly(x0, y0, x1, y1, self.crs_plot).to_crs(
                gdf.crs
            )
        elif how == "crs_bounds" or how == "crs_bounds_invert":
            x0, x1, y0, y1 = self.get_extent(crs=self.crs_plot)
            clip_shp = self._make_rect_poly(
                *self.crs_plot.boundary.bounds, self.crs_plot
            ).to_crs(gdf.crs)
        else:
            raise TypeError(f"EOmaps: '{how}' is not a valid clipping method")

        clip_shp = clip_shp.buffer(0)  # use this to make sure the geometry is valid

        # add 1% of the extent-diameter as buffer
        bnd = clip_shp.boundary.bounds
        d = np.sqrt((bnd.maxx - bnd.minx) ** 2 + (bnd.maxy - bnd.miny) ** 2)
        clip_shp = clip_shp.buffer(d / 100)

        # clip the geo-dataframe with the buffered clipping shape
        clipgdf = gdf.clip(clip_shp)

        return clipgdf

    def _set_gdf_path_boundary(self, gdf, set_extent=True):
        geom = gdf.to_crs(self.crs_plot).union_all()
        if "Polygon" in geom.geom_type:
            geom = geom.boundary

        if geom.geom_type == "MultiLineString":
            boundary_linestrings = geom.geoms
        elif geom.geom_type == "LineString":
            boundary_linestrings = [geom]
        else:
            raise TypeError(
                f"Geometries of type {geom.type} cannot be used as map-boundary."
            )

        vertices, codes = [], []
        for g in boundary_linestrings:
            x, y = g.xy
            codes.extend(
                [mpath.Path.MOVETO, *[mpath.Path.LINETO] * len(x), mpath.Path.CLOSEPOLY]
            )
            vertices.extend([(x[0], y[0]), *zip(x, y), (x[-1], y[-1])])

        path = mpath.Path(vertices, codes)

        self.ax.set_boundary(path, self.ax.transData)
        if set_extent:
            x0, y0 = np.min(vertices, axis=0)
            x1, y1 = np.max(vertices, axis=0)

            self.set_extent([x0, x1, y0, y1], gdf.crs)

    def _get_country_frame(self, countries, scale=50):
        """
        Get the map-frame to one (or more) country boarders defined by
        the NaturalEarth admin_0_countries dataset.

        For more details, see:

            https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-0-countries/

        Parameters
        ----------
        countries : str or list of str
            The countries who should be included in the map-frame.
        scale : int, optional
            The scale factor of the used NaturalEarth dataset.
            One of 10, 50, 110.
            The default is 50.
        """
        countries = [i.lower() for i in np.atleast_1d(countries)]
        gdf = self.add_feature.cultural.admin_0_countries.get_gdf(scale=scale)
        names = gdf.NAME.str.lower().values

        q = np.isin(names, countries)

        if np.count_nonzero(q) == len(countries):
            return gdf[q]
        else:
            for c in countries:
                if c not in names:
                    print(
                        f"Unable to identify the country '{c}'. "
                        f"Fid you mean {get_close_matches(c, gdf.NAME)}"
                    )

import logging

_log = logging.getLogger(__name__)

from itertools import repeat, chain, pairwise
from functools import wraps
from pathlib import Path
import weakref

from pyproj import CRS
import numpy as np

import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

from ..ne_features import NaturalEarthFeatures
from ..grid import GridFactory
from ..helpers import _TransformedBoundsLocator, _get_rect_poly_verts
from ..compass import Compass
from ..scalebar import ScaleBar

try:
    from .._webmap import _cx_refetch_wms_on_size_change
    from ..webmap_containers import WebMapContainer
except ImportError as ex:
    _log.error(f"EOmaps: Unable to import dependencies required for WebMaps: {ex}")
    _cx_refetch_wms_on_size_change = None
    WebMapContainer = None


class AddMixin:
    add_feature = NaturalEarthFeatures

    if WebMapContainer is not None:
        _preferred_wms_service = "wms"
        add_wms = WebMapContainer

    def __init__(self, *args, **kwargs):
        if WebMapContainer is not None:
            self.add_wms = self.add_wms(weakref.proxy(self))
            self._wms_legend = dict()

        self.add_feature = self.add_feature(weakref.proxy(self))

        if self.parent == self:
            self._grid = GridFactory(self)

        # a set to hold references to the compass objects
        self._compass = set()

        super().__init__(*args, **kwargs)

    @property
    def __lazy_attrs(self):
        # list of attributes that support lazy-evaluation
        return [i for i in dir(AddMixin) if not i.startswith("_")]

    @wraps(GridFactory.add_grid)
    def add_gridlines(self, *args, **kwargs):
        """Add gridlines to the Map."""
        return self.parent._grid.add_grid(m=self, *args, **kwargs)

    @wraps(Compass.__call__)
    def add_compass(self, *args, **kwargs):
        """Add a compass (or north-arrow) to the map."""
        c = Compass(weakref.proxy(self))
        c(*args, **kwargs)
        # store a reference to the object (required for callbacks)!
        self._compass.add(c)
        return c

    @wraps(ScaleBar.__init__)
    def add_scalebar(
        self,
        pos=None,
        rotation=0,
        scale=None,
        n=10,
        preset=None,
        autoscale_fraction=0.25,
        auto_position=(0.8, 0.25),
        scale_props=None,
        patch_props=None,
        label_props=None,
        line_props=None,
        layer=None,
        size_factor=1,
        pickable=True,
    ):
        """Add a scalebar to the map."""
        s = ScaleBar(
            m=self,
            preset=preset,
            scale=scale,
            n=n,
            autoscale_fraction=autoscale_fraction,
            auto_position=auto_position,
            scale_props=scale_props,
            patch_props=patch_props,
            label_props=label_props,
            line_props=line_props,
            layer=layer,
            size_factor=size_factor,
        )

        # add the scalebar to the map at the desired position
        s._add_scalebar(pos=pos, azim=rotation, pickable=pickable)
        self.BM.update()
        return s

    def add_logo(
        self,
        filepath=None,
        position="lr",
        size=0.12,
        pad=0.1,
        layer=None,
        fix_position=False,
        **kwargs,
    ):
        """
        Add a small image (png, jpeg etc.) to the map.

        The position of the image is dynamically updated if the plot is resized or
        zoomed.

        Parameters
        ----------
        filepath : str, optional
            if str: The path to the image-file.
            The default is None in which case an EOmaps logo is added to the map.
        position : str, optional
            The position of the logo.
            - "ul", "ur" : upper left, upper right
            - "ll", "lr" : lower left, lower right
            The default is "lr".
        size : float, optional
            The size of the logo as a fraction of the axis-width.
            The default is 0.15.
        pad : float, tuple optional
            Padding between the axis-edge and the logo as a fraction of the logo-width.
            If a tuple is passed, (x-pad, y-pad)
            The default is 0.1.
        layer : str or None, optional
            The layer at which the logo should be visible.
            If None, the logo will be added to ALL layers and will be drawn on
            top of ALL background artists. The default is None.
        fix_position : bool, optional
            If True, the relative position of the logo (with respect to the map-axis)
            is fixed (and dynamically updated on zoom / resize events)

            NOTE: If True, the logo can NOT be moved with the layout_editor!
            The default is False.
        kwargs :
            Additional kwargs are passed to plt.imshow
        """
        if layer is None:
            # TODO ensure that logos are plotted on top of spines!
            layer = "**SPINES**"

        if filepath is None:
            filepath = Path(__file__).parent.parent / "logo.png"

        im = mpl.image.imread(filepath)

        # replace default rgba colors of transparent regions with the
        # color used by the axes background patch
        try:
            from matplotlib.colors import to_rgb

            im[..., :3][im[..., 3] == 0] = to_rgb(self.ax.patch.get_facecolor())
            print("YAY")
        except Exception as ex:
            _log.debug(
                "Encountered a problem while trying to adjust color of "
                f"transparent logo regions with axes background color: {ex}",
            )

        def getpos(pos):
            s = size
            if isinstance(pad, tuple):
                pwx, pwy = (s * pad[0], s * pad[1])
            else:
                pwx, pwy = (s * pad, s * pad)

            if position == "lr":
                p = dict(rect=[pos.x1 - s - pwx, pos.y0 + pwy, s, s], anchor="SE")
            elif position == "ll":
                p = dict(rect=[pos.x0 + pwx, pos.y0 + pwy, s, s], anchor="SW")
            elif position == "ur":
                p = dict(rect=[pos.x1 - s - pwx, pos.y1 - s - pwy, s, s], anchor="NE")
            elif position == "ul":
                p = dict(rect=[pos.x0 + pwx, pos.y1 - s - pwy, s, s], anchor="NW")
            return p

        figax = self.f.add_axes(
            **getpos(self.ax.get_position()), label="logo", zorder=999, animated=True
        )

        figax.set_navigate(False)
        figax.set_axis_off()

        kwargs.setdefault("aspect", "equal")
        kwargs.setdefault("zorder", 999)
        kwargs.setdefault("interpolation_stage", "rgba")

        _ = figax.imshow(im, **kwargs)

        self.l[layer].add_bg_artist(figax)

        if fix_position:
            fixed_pos = (
                figax.get_position()
                .transformed(self.f.transFigure)
                .transformed(self.ax.transAxes.inverted())
            )

            figax.set_axes_locator(
                _TransformedBoundsLocator(fixed_pos.bounds, self.ax.transAxes)
            )

    def add_line(
        self,
        xy,
        xy_crs=4326,
        connect="geod",
        n=None,
        del_s=None,
        mark_points=None,
        layer=None,
        **kwargs,
    ):
        """
        Draw a line by connecting a set of anchor-points.

        The points can be connected with either "geodesic-lines", "straight lines" or
        "projected straight lines with respect to a given crs" (see `connect` kwarg).

        Parameters
        ----------
        xy : list, set or numpy.ndarray
            The coordinates of the anchor-points that define the line.
            Expected shape:  [(x0, y0), (x1, y1), ...]
        xy_crs : any, optional
            The crs of the anchor-point coordinates.
            (can be any crs definition supported by PyProj)
            The default is 4326 (e.g. lon/lat).
        connect : str, optional
            The connection-method used to draw the segments between the anchor-points.

            - "geod": Connect the anchor-points with geodesic lines
            - "straight": Connect the anchor-points with straight lines
            - "straight_crs": Connect the anchor-points with straight lines in the
              `xy_crs` projection and reproject those lines to the plot-crs.

            The default is "geod".
        n : int, list or None optional
            The number of intermediate points to use for each line-segment.

            - If an integer is provided, each segment is equally divided into n parts.
            - If a list is provided, it is used to specify "n" for each line-segment
              individually.

              (NOTE: The number of segments is 1 less than the number of anchor-points!)

            If both n and del_s is None, n=100 is used by default!

            The default is None.
        del_s : int, float or None, optional
            Only relevant if `connect="geod"`!

            The target-distance in meters between the subdivisions of the line-segments.

            - If a number is provided, each segment is equally divided.
            - If a list is provided, it is used to specify "del_s" for each line-segment
              individually.

              (NOTE: The number of segments is 1 less than the number of anchor-points!)

            The default is None.
        mark_points : str, dict or None, optional
            Set the marker-style for the anchor-points.

            - If a string is provided, it is identified as a matplotlib "format-string",
              e.g. "r." for red dots, "gx" for green x markers etc.
            - if a dict is provided, it will be used to set the style of the markers
              e.g.: dict(marker="o", facecolor="orange", edgecolor="g")

            See https://matplotlib.org/stable/gallery/lines_bars_and_markers/marker_reference.html
            for more details

            The default is "o"

        layer : str, int or None
            The name of the layer at which the line should be drawn.
            If None, the layer associated with the used Maps-object (e.g. m.layer)
            is used. Use "all" to add the line to all layers!
            The default is None.
        kwargs :
            additional keyword-arguments passed to plt.plot(), e.g.
            "c" (or "color"), "lw" (or "linewidth"), "ls" (or "linestyle"),
            "markevery", etc.

            See https://matplotlib.org/stable/api/_as_gen/matplotlib.axes.Axes.plot.html
            for more details.

        Returns
        -------
        out_d_int : list
            Only relevant for `connect="geod"`! (An empty list is returned otherwise.)
            A list of the subdivision distances of the line-segments (in meters).
        out_d_tot : list
            Only relevant for `connect="geod"` (An empty list is returned otherwise.)
            A list of total distances of the line-segments (in meters).

        """
        if layer is None:
            layer = self.layer

        # intermediate and total distances
        out_d_int, out_d_tot = [], []

        if len(xy) <= 1:
            _log.error("you must provide at least 2 points")

        if n is not None:
            assert del_s is None, "EOmaps: Provide either `del_s` or `n`, not both!"
            del_s = 0  # pyproj's geod uses 0 as identifier!

            if not isinstance(n, int):
                assert len(n) == len(xy) - 1, (
                    "EOmaps: The number of subdivisions per line segment (n) must be"
                    + " 1 less than the number of points!"
                )

        elif del_s is not None:
            assert n is None, "EOmaps: Provide either `del_s` or `n`, not both!"
            n = 0  # pyproj's geod uses 0 as identifier!

            assert connect in ["geod"], (
                "EOmaps: Setting a fixed subdivision-distance (e.g. `del_s`) is only "
                + "possible for `geod` lines! Use `n` instead!"
            )

            if not isinstance(del_s, (int, float, np.number)):
                assert len(del_s) == len(xy) - 1, (
                    "EOmaps: The number of subdivision-distances per line segment "
                    + "(`del_s`) must be 1 less than the number of points!"
                )
        else:
            # use 100 subdivisions by default
            n = 100
            del_s = 0

        t_xy_plot = self._get_transformer(
            self.get_crs(xy_crs),
            self.crs_plot,
        )
        xplot, yplot = t_xy_plot.transform(*zip(*xy))

        if connect == "geod":
            # connect points via geodesic lines
            if xy_crs != 4326:
                t = self._get_transformer(
                    self.get_crs(xy_crs),
                    self.get_crs(4326),
                )
                x, y = t.transform(*zip(*xy))
            else:
                x, y = zip(*xy)

            geod = self.crs_plot.get_geod()

            if n is None or isinstance(n, int):
                n = repeat(n)

            if del_s is None or isinstance(del_s, (int, float, np.number)):
                del_s = repeat(del_s)

            xs, ys = [], []
            for (x0, x1), (y0, y1), ni, di in zip(pairwise(x), pairwise(y), n, del_s):
                npts, d_int, d_tot, lon, lat, _ = geod.inv_intermediate(
                    lon1=x0,
                    lat1=y0,
                    lon2=x1,
                    lat2=y1,
                    del_s=di,
                    npts=ni,
                    initial_idx=0,
                    terminus_idx=0,
                )

                out_d_int.append(d_int)
                out_d_tot.append(d_tot)

                lon, lat = lon.tolist(), lat.tolist()
                xi, yi = self._transf_lonlat_to_plot.transform(lon, lat)
                xs += xi
                ys += yi
            (art,) = self.ax.plot(xs, ys, **kwargs)

        elif connect == "straight":
            (art,) = self.ax.plot(xplot, yplot, **kwargs)

        elif connect == "straight_crs":
            # draw a straight line that is defined in a given crs

            x, y = zip(*xy)
            if isinstance(n, int):
                # use same number of points for all segments
                xs = np.linspace(x[:-1], x[1:], n).T.ravel()
                ys = np.linspace(y[:-1], y[1:], n).T.ravel()
            else:
                # use different number of points for individual segments

                xs = list(
                    chain(
                        *(np.linspace(a, b, ni) for (a, b), ni in zip(pairwise(x), n))
                    )
                )
                ys = list(
                    chain(
                        *(np.linspace(a, b, ni) for (a, b), ni in zip(pairwise(y), n))
                    )
                )

            x, y = t_xy_plot.transform(xs, ys)

            (art,) = self.ax.plot(x, y, **kwargs)
        else:
            raise TypeError(f"EOmaps: '{connect}' is not a valid connection-method!")

        art.set_label(f"Line ({connect})")
        self.l[layer].add_bg_artist(art)

        if mark_points:
            zorder = kwargs.get("zorder", 10)

            if isinstance(mark_points, dict):
                # only use zorder of the line if no explicit zorder is provided
                mark_points["zorder"] = mark_points.get("zorder", zorder)

                art2 = self.ax.scatter(xplot, yplot, **mark_points)

            elif isinstance(mark_points, str):
                # use matplotlib's single-string style identifiers,
                # (e.g. "r.", "go", "C0x" etc.)
                (art2,) = self.ax.plot(xplot, yplot, mark_points, zorder=zorder, lw=0)

            art2.set_label(f"Line Marker ({connect})")
            self.l[layer].add_bg_artist(art2)

        return out_d_int, out_d_tot

    def add_title(self, title, x=0.5, y=1.01, **kwargs):
        """
        Convenience function to add a title to the map.

        (The title will be visible at the assigned layer.)

        Parameters
        ----------
        title : str
            The title.
        x, y : float, optional
            The position of the text in axis-coordinates (0-1).
            The default is 0.5, 1.01.
        kwargs :
            Additional kwargs are passed to `m.text()`
            The defaults are:

            - `"fontsize": "large"`
            - `horizontalalignment="center"`
            - `verticalalignment="bottom"`

        See Also
        --------

        :py:meth:`Maps.text` : General function to add text to the figure.

        """
        kwargs.setdefault("fontsize", "large")
        kwargs.setdefault("horizontalalignment", "center")
        kwargs.setdefault("verticalalignment", "bottom")
        kwargs.setdefault("transform", self.ax.transAxes)

        self.text(x, y, title, layer=self.layer, **kwargs)

    @wraps(plt.Figure.text)
    def add_text(self, *args, layer=None, **kwargs):
        """Add text to the map."""
        kwargs.setdefault("animated", True)
        kwargs.setdefault("horizontalalignment", "center")
        kwargs.setdefault("verticalalignment", "center")
        kwargs.setdefault("transform", self.ax.transAxes)

        a = self.f.text(*args, **kwargs)

        if layer is None:
            layer = self.layer
        self.l[layer].add_artist(a)
        self.BM.update()

        return a

    def add_extent_indicator(self, x0, y0, x1, y1, crs=4326, npts=100, **kwargs):
        """
        Indicate a rectangular extent in a given crs on the map.

        Parameters
        ----------
        x0, y0, y1, y1 : float
            the boundaries of the shape
        npts : int, optional
            The number of points used to draw the polygon-lines.
            (e.g. to correctly display the distortion of the extent-rectangle when
            it is re-projected to another coordinate-system)
            The default is 100.
        crs : any, optional
            A coordinate-system identifier.
            The default is 4326 (e.g. lon/lat).
        kwargs :
            Additional keyword-arguments are forwarded to the matplotlib-patch.
        """

        verts = _get_rect_poly_verts(x0, y0, x1, y1, npts)

        t = self._get_transformer(self.get_crs(crs), self.crs_plot)
        verts = np.column_stack(t.transform(*verts.T))

        p = Polygon(verts, **kwargs)

        artist = self.ax.add_patch(p)
        self.add_bg_artist(artist)

    def add_marker(
        self,
        ID=None,
        xy=None,
        xy_crs=None,
        radius=None,
        radius_crs=None,
        shape="ellipses",
        buffer=1,
        n=100,
        layer=None,
        update=True,
        **kwargs,
    ):
        """
        Add a marker to the plot.

        Parameters
        ----------
        ID : any
            The index-value of the pixel in m.data.
        xy : tuple
            A tuple of the position of the pixel provided in "xy_crs".
            If "xy_crs" is None, xy must be provided in the plot-crs!
            The default is None
        xy_crs : any
            the identifier of the coordinate-system for the xy-coordinates
        radius : float or "pixel", optional
            - If float: The radius of the marker.
            - If "pixel": It will represent the dimensions of the selected pixel.
              (check the `buffer` kwarg!)

            The default is None in which case "pixel" is used if a dataset is
            present and otherwise a shape with 1/10 of the axis-size is plotted
        radius_crs : str or a crs-specification
            The crs specification in which the radius is provided.
            Either "in", "out", or a crs specification (e.g. an epsg-code,
            a PROJ or wkt string ...)
            The default is "in" (e.g. the crs specified via `m.data_specs.crs`).
            (only relevant if radius is NOT specified as "pixel")
        shape : str, optional
            Indicator which shape to draw. Currently supported shapes are:
            - geod_circles
            - ellipses
            - rectangles

            The default is "circle".
        buffer : float, optional
            A factor to scale the size of the shape. The default is 1.
        n : int
            The number of points to calculate for the shape.
            The default is 100.
        layer : str, int or None
            The name of the layer at which the marker should be drawn.
            If None, the layer associated with the used Maps-object (e.g. m.layer)
            is used. The default is None.
        kwargs :
            kwargs passed to the matplotlib patch.
            (e.g. `zorder`, `facecolor`, `edgecolor`, `linewidth`, `alpha` etc.)
        update : bool, optional
            If True, call m.BM.update() to immediately show dynamic annotations
            If False, dynamic annotations will only be shown at the next update

        Examples
        --------
            >>> m.add_marker(ID=1, buffer=5)
            >>> m.add_marker(ID=1, radius=2, radius_crs=4326, shape="rectangles")
            >>> m.add_marker(xy=(4, 3), xy_crs=4326, radius=20000, shape="geod_circles")
        """
        if ID is not None:
            assert xy is None, "You can only provide 'ID' or 'pos' not both!"
        else:
            if isinstance(radius, str) and radius != "pixel":
                raise TypeError(f"I don't know what to do with radius='{radius}'")

        if xy is not None:
            ID = None
            if xy_crs is not None:
                # get coordinate transformation
                transformer = self._get_transformer(
                    self.get_crs(xy_crs),
                    self.crs_plot,
                )
                # transform coordinates
                xy = transformer.transform(*xy)

        if layer is None:
            layer = self.layer

        # using permanent=None results in permanent makers that  are NOT
        # added to the "m.cb.click.get.permanent_markers" list that is
        # used to manage callback-markers

        permanent = kwargs.pop("permanent", None)

        # call the "mark" callback function to add the marker
        marker = self.cb.click._attach.mark(
            self.cb.click.attach,
            ID=ID,
            pos=xy,
            radius=radius,
            radius_crs=radius_crs,
            ind=None,
            shape=shape,
            buffer=buffer,
            n=n,
            layer=layer,
            permanent=permanent,
            **kwargs,
        )

        if permanent is False and update:
            self.BM.update()

        return marker

    def add_annotation(
        self,
        ID=None,
        xy=None,
        xy_crs=None,
        text=None,
        update=True,
        **kwargs,
    ):
        """
        Add an annotation to the plot.

        Parameters
        ----------
        ID : str, int, float or array-like
            The index-value of the pixel in m.data.
        xy : tuple of float or array-like
            A tuple of the position of the pixel provided in "xy_crs".
            If None, xy must be provided in the coordinate-system of the plot!
            The default is None.
        xy_crs : any
            the identifier of the coordinate-system for the xy-coordinates
        text : callable or str, optional
            if str: the string to print
            if callable: A function that returns the string that should be
            printed in the annotation with the following call-signature:

                >>> def text(m, ID, val, pos, ind):
                >>>     # m   ... the Maps object
                >>>     # ID  ... the ID
                >>>     # pos ... the position
                >>>     # val ... the value
                >>>     # ind ... the index of the clicked pixel
                >>>
                >>>     return "the string to print"

            The default is None.
        update : bool, optional
            If True, call m.BM.update() to immediately show dynamic annotations
            If False, dynamic annotations will only be shown at the next update
        **kwargs
            kwargs passed to m.cb.annotate

        Examples
        --------
        >>> m.add_annotation(ID=1)
        >>> m.add_annotation(xy=(45, 35), xy_crs=4326)

        NOTE: You can provide lists to add multiple annotations in one go!

        >>> m.add_annotation(ID=[1, 5, 10, 20])
        >>> m.add_annotation(xy=([23.5, 45.8, 23.7], [5, 6, 7]), xy_crs=4326)

        The text can be customized by providing either a string

        >>> m.add_annotation(ID=1, text="some text")

        or a callable that returns a string with the following signature:

        >>> def addtxt(m, ID, val, pos, ind):
        >>>     return f"The ID {ID} at position {pos} has a value of {val}"
        >>> m.add_annotation(ID=1, text=addtxt)

        **Customizing the appearance**

        For the full set of possibilities, see:
        https://matplotlib.org/stable/tutorials/text/annotations.html

        >>> m.add_annotation(xy=[7.10, 45.16], xy_crs=4326,
        >>>                  text="blubb", xytext=(30,30),
        >>>                  horizontalalignment="center", verticalalignment="center",
        >>>                  arrowprops=dict(ec="g",
        >>>                                  arrowstyle='-[',
        >>>                                  connectionstyle="angle",
        >>>                                  ),
        >>>                  bbox=dict(boxstyle='circle,pad=0.5',
        >>>                            fc='yellow',
        >>>                            alpha=0.3
        >>>                            )
        >>>                  )

        """
        inp_ID = ID

        if xy is None and ID is None:
            x = self.ax.bbox.x0 + self.ax.bbox.width / 2
            y = self.ax.bbox.y0 + self.ax.bbox.height / 2
            xy = self.ax.transData.inverted().transform((x, y))

        if ID is not None:
            assert xy is None, "You can only provide 'ID' or 'pos' not both!"
            # avoid using np.isin directly since it needs a lot of ram
            # for very large datasets!
            mask, ind = self._find_ID(ID)

            xy = (
                self._data_manager.xorig.ravel()[mask],
                self._data_manager.yorig.ravel()[mask],
            )
            val = self._data_manager.z_data.ravel()[mask]
            ID = np.atleast_1d(ID)
            xy_crs = self.data_specs.crs

            is_ID_annotation = False
        else:
            val = repeat(None)
            ind = repeat(None)
            ID = repeat(None)

            is_ID_annotation = True

        assert (
            xy is not None
        ), "EOmaps: you must provide either ID or xy to position the annotation!"

        xy = (np.atleast_1d(xy[0]), np.atleast_1d(xy[1]))

        if xy_crs is not None:
            # get coordinate transformation
            transformer = self._get_transformer(
                CRS.from_user_input(xy_crs),
                self.crs_plot,
            )
            # transform coordinates
            xy = transformer.transform(*xy)
        else:
            transformer = None

        kwargs.setdefault("permanent", None)

        if isinstance(text, str) or callable(text):
            usetext = repeat(text)
        else:
            try:
                usetext = iter(text)
            except TypeError:
                usetext = repeat(text)

        for x, y, texti, vali, indi, IDi in zip(xy[0], xy[1], usetext, val, ind, ID):
            ann = self.cb.click._attach.annotate(
                self.cb.click.attach,
                ID=IDi,
                pos=(x, y),
                val=vali,
                ind=indi,
                text=texti,
                **kwargs,
            )

            if kwargs.get("permanent", False) is not False:
                self._edit_annotations._add(
                    a=ann,
                    kwargs={
                        "ID": inp_ID,
                        "xy": (x, y),
                        "xy_crs": xy_crs,
                        "text": text,
                        **kwargs,
                    },
                    transf=transformer,
                    drag_coords=is_ID_annotation,
                )

        if update:
            self.BM.update(clear=False)
        return ann

    def add_background_patch(self, color, layer=None, **kwargs):
        """
        Add a background-patch for the map.

        Useful for overlapping axes if you don't want to "see-through"
        the top map.

        Parameters
        ----------
        color : str, rgba tuple
            The color of the patch.
        layer : str, optional
            The layer to use.
            If None, the layer assigned to the Maps-object is used.
            The default is None.
        kwargs :
            All additional kwargs are passed to the created Patch.
            (e.g. alpha, hatch, ...)

        Returns
        -------
        art : TYPE
            DESCRIPTION.

        """
        if layer is None:
            layer = self.layer

        (art,) = self.ax.fill(
            [0, 0, 1, 1],
            [0, 1, 1, 0],
            fc=color,
            ec="none",
            zorder=-9999,
            transform=self.ax.transAxes,
            **kwargs,
        )

        art.set_label("Background patch")

        self.l[layer].add_bg_artist(art)
        return art

    # for backwards compatibility
    # TODO deprecate "text" in favor of "add_text"
    # TODO deprecate "indicate_extent" in favor of "add_extent_indicator"
    text = add_text
    indicate_extent = add_extent_indicator

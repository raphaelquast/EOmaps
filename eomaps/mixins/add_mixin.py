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
from matplotlib.patches import Polygon, PathPatch
from matplotlib.colors import to_rgb
from matplotlib.transforms import TransformedPath, Affine2D
import matplotlib.path as mpath


from ..ne_features import NaturalEarthFeatures
from ..grid import GridFactory
from ..helpers import (
    _TransformedBoundsLocator,
    _get_rect_poly_verts,
    _submit_on_activation,
)
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
            self.add_wms = WebMapContainer(weakref.proxy(self))
            self._wms_legend = dict()

        self.add_feature = NaturalEarthFeatures(weakref.proxy(self))

        if self.parent == self:
            self._grid = GridFactory(self)

        # a set to hold references to the compass objects
        self._compass = set()

        super().__init__(*args, **kwargs)

    @_submit_on_activation(label="Maps.add_gridlines(...)")
    @wraps(GridFactory.add_grid)
    def add_gridlines(self, *args, **kwargs):
        """Add gridlines to the Map."""
        return self.parent._grid.add_grid(m=self, *args, **kwargs)

    @_submit_on_activation(label="Maps.add_compass(...)")
    @wraps(Compass.__call__)
    def add_compass(self, *args, **kwargs):
        """Add a compass (or north-arrow) to the map."""
        c = Compass(weakref.proxy(self))
        c(*args, **kwargs)
        # store a reference to the object (required for callbacks)!
        self._compass.add(c)
        return c

    @_submit_on_activation(label="Maps.add_scalebar(...)")
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
        self._bm.update()
        return s

    @_submit_on_activation(label="Maps.add_logo(...)")
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
            layer = "**SPINES**"

        if filepath is None:
            filepath = Path(__file__).parent.parent / "logo.png"

        im = mpl.image.imread(filepath)

        # replace default rgba colors of transparent regions with the
        # color used by the axes background patch
        try:
            im[..., :3][im[..., 3] == 0] = to_rgb(self.ax.patch.get_facecolor())
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

    @_submit_on_activation(label="Maps.add_line(...)")
    def add_line(
        self,
        xy,
        xy_crs=4326,
        connect="geod",
        n=None,
        del_s=None,
        mark_points=None,
        layer=None,
        dynamic=False,
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
                    return_back_azimuth=True,
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
        if dynamic is True:
            self.l[layer].add_artist(art)
        else:
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

            if dynamic is True:
                self.l[layer].add_artist(art2)
            else:
                self.l[layer].add_bg_artist(art2)

        return out_d_int, out_d_tot

    @_submit_on_activation(label="Maps.add_title(...)")
    def add_title(self, title, **kwargs):
        """
        Convenience function to add a title to the map.

        If used multiple-times, the title will be updated instead of creating
        a new artist that will be added to the map.

        (The title will be visible at the assigned layer.)

        Parameters
        ----------
        title : str
            The title.
        x, y : float, optional
            The position of the text in axis-coordinates (0-1).
            The default is 0.5, 1.01.
        kwargs :
            Additional kwargs are passed to `m.add_text()`
            The defaults are:

            - `"fontsize": "large"`
            - `horizontalalignment="center"`
            - `verticalalignment="bottom"`

        See Also
        --------

        :py:meth:`Maps.text` : General function to add text to the figure.

        """
        if (t := getattr(self, "_title", None)) is not None:
            kwargs["text"] = title
            t.set(**kwargs)
            self._bm.update(layers=(self.layer))
            return t

        kwargs["s"] = title
        kwargs.setdefault("x", 0.5)
        kwargs.setdefault("y", 1.01)
        kwargs.setdefault("fontsize", "large")
        kwargs.setdefault("horizontalalignment", "center")
        kwargs.setdefault("verticalalignment", "bottom")

        self._title = self.add_text(**kwargs)

    @_submit_on_activation(label="Maps.add_text(...)")
    @wraps(plt.Figure.text)
    def add_text(self, *args, layer=None, **kwargs):
        """Add text to the map."""

        kwargs.setdefault("animated", True)
        kwargs.setdefault("verticalalignment", "center")
        kwargs.setdefault("transform", self.ax.transAxes)

        a = self.f.text(*args, **kwargs)

        if layer is None:
            layer = self.layer
        self.l[layer].add_artist(a)
        self._bm.update()

        return a

    @_submit_on_activation(label="Maps.add_extent_indicator(...)")
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

    @_submit_on_activation(label="Maps.add_marker(...)")
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
            The index-value of the pixel in m.data_specs.data.
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
            If True, call m._bm.update() to immediately show dynamic annotations
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
            self._bm.update()

        return marker

    @_submit_on_activation(label="Maps.add_annotation(...)")
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
            If True, call m._bm.update() to immediately show dynamic annotations
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
            self._bm.update(clear=False)
        return ann

    @_submit_on_activation(label="Maps.add_background_patch(...)")
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

    from functools import lru_cache

    @lru_cache
    def _get_clip_path(self, shape, loc, size, n=200):
        from matplotlib.markers import MarkerStyle

        if shape == "s":
            verts = _get_rect_poly_verts(0, 0, 1, 1, n)
            clip_path = mpath.Path(verts)
        elif shape in [".", "o"]:
            ang = np.linspace(0, 2 * np.pi, n)
            verts = 2 * np.column_stack((np.sin(ang), np.cos(ang)))
            clip_path = mpath.Path(verts)
        else:
            clip_path = MarkerStyle(shape).get_path()

        clip_bbox = clip_path.get_extents()

        # make sure shape is positioned according to "loc" assignment
        if loc == "center":
            xshift, yshift = (
                -clip_bbox.width / 2 - clip_bbox.x0,
                -clip_bbox.height / 2 - clip_bbox.y0,
            )
        else:
            if loc.startswith("lower"):
                yshift = -clip_bbox.y0
            elif loc.startswith("upper"):
                yshift = -clip_bbox.y1
            elif loc.startswith("center"):
                yshift = -clip_bbox.height / 2 - clip_bbox.y0

            if loc.endswith("left"):
                xshift = -clip_bbox.x0
            elif loc.endswith("right"):
                xshift = -clip_bbox.x1
            elif loc.endswith("center"):
                xshift = -clip_bbox.width / 2 - clip_bbox.x0

        clip_path = clip_path.transformed(Affine2D().translate(xshift, yshift))

        # scale to desired size (rel. to max. width/height)
        maxs = max(clip_bbox.width, clip_bbox.height)

        if isinstance(size, (int, float, np.number)):
            size = (size, size)

        clip_path = clip_path.transformed(
            Affine2D().scale(size[0] / maxs, size[1] / maxs)
        )
        return clip_path

    def add_peek_layer(
        self,
        layer="base",
        xy=(0.5, 0.5),
        shape="s",
        size=(0.4, 0.4),
        xy_crs="axes",
        shape_crs="axes",
        loc="center",
        boundary=True,
        n_shape_points=100,
        dynamic=False,
        **kwargs,
    ):
        """
        Overlay a part of the map with the content of another layer.


        Parameters
        ----------
        layer : str or list

            - if str: The name of the layer you want to peek at.
            - if list: A list of layer-names of the following form:

                - A layer-name (string)
                - A tuple (< layer-name >, < transparency [0-1] >)

            see `m.show_layer()` for more details on how to provide combined layer-names
        xy: tuple
            The position of the peek-shape (provided in the xy_crs coordinate system).
            (see "loc" argument on the anchor of the position)
            The default is (0.5, 0.5) in "axes" crs.

        shape : str, optional
            The shape of the peek-window.

            - "s": peek a rectangle
            - ".": peek a circle/ellipse
            - "geod_circles": peek an ellipse with "size" defined in meters
            - "left", "right", "top", "bottom":
              Split the map from left (→), right (←), top (↓) or bottom (↑).
              (size and shape_crs kwargs are ignored)
            - "*": peek a star
            - "$x^2$" peek a methematical equation
            - (5, 0, 20) peek a regular 5-sided polygon at 20° angle

            Since the peek-shape generation uses the same methods as matplotlib
            markers under the hood, any method explained here is possible:
            https://matplotlib.org/stable/api/markers_api.html

            The default is "s"

        size: float or (float, float)
            The size of the shape (provided in the "shape_crs" coordinate
            system).

            - If shape_crs="axes":

              - a single number represents a fraction of the shorter size of
                the axes (to get "square" shapes).
              - tuple (xsize, ysize) represents axes fractions of each side.
            - If shape="geod_circles":
              "shape_crs" is ignored and the size is expected to be in meters.
            - If shape=("left", "right", "top" or "bottom"), "size" is ignored.

            The default is (0.5, 0.5) in "axes" crs.
        xy_crs: a CRS specifier
            The coordinate system in which the xy-coordinates are provided.

            - if "axes": relative fraction of axes size
            - if "plot": the crs of the map
            - all other provided values are identified as pyproj-crs identifier

            The default is "axes"
        shape_crs: str or a CRS specifier
            The coordinate system in which the "size" of the shape is defined.

            - if "axes": size in relative fraction of axes width/height
            - if "plot": size in the plot-crs of the map
            - all other provided values are identified as pyproj-crs identifier

            If shape == "geod_circles", "left", "right", "top" or "bottom",
            "shape_crs" is ignored!

            The default is "axes"
        loc : str
            The anchor at which the xy-coordinates are defined.

            - "center": The center of the shape
            - a combination of
              ("upper", "lower", "center") and ("left", "right", "center")
              (e.g. "upper left" or "center right") to use the corresponding
              position of the bounding-box of the shape as xy-anchor.

            If shape == "geod_circles", "left", "right", "top" or "bottom",
            "shape_crs" is ignored!

            The default is "center"
        boundary: bool or dict
            Style settings for the boundary

            - False: don't draw any boundary line
            - True: draw the default boundary line (1px black)
            - dict: use the provided kwargs to style the boundary-line
              (e.g. {"ec":"red", "lw": 4})

            The default is True
        n_shape_points: int
            The number of intermediate points to evaluate for the peek-shape.
            (only relevant for shape=".", "s" or "geod_circles")
            The default is 100
        dynamic : bool
            If True, artists are added as "dynamic" artists, otherwise
            artists are added as "background_artists".

        Additional Parameters
        ---------------------
        alpha : float, optional
            The transparency of the peeked layer. (between 0 and 1)
            If you overlay a (possibly transparent) combination of multiple layers,
            this transparency will be assigned as a global transparency for the
            obtained "combined layer".
            The default is 1.
        **kwargs :
            additional kwargs passed to plt.imshow()
            (e.g. "alpha=0.5" for 50% transparency)


        Examples
        --------
        Overlay a single layer:

        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>> m["ocean"].add_feature.preset.ocean()
        >>> m.cb.click.attach.peek_layer("ocean", size=.3, shape=".")

        Overlay a (transparent) combination of multiple layers:

        >>> m = Maps(Maps.CRS.Stereographic())
        >>> m.all.add_feature.preset.coastline()
        >>> m.add_feature.preset.urban_areas()
        >>> m["ocean"]add_feature.preset.ocean()
        >>> m["land"].add_feature.physical.land(fc="g")
        >>> m.cb.click.attach.peek_layer(
        >>>    ["ocean", ("land", 0.5)], shape=".", shape_crs=4326, size=(15, 15)
        >>> )

        """
        if not isinstance(layer, str):
            layer = self._bm._get_combined_layer_name(*layer)

        if boundary:
            bnd_kwargs = {
                "fc": "none",
                "ec": "k",
                "lw": 1.1,
                "zorder": 100,
                "animated": True,
            }
            if isinstance(boundary, dict):
                bnd_kwargs.update(boundary)
        elif boundary is False:
            pass
        else:
            raise TypeError(
                "EOmaps peek-boundary must be either True/False or a dict of style-kwargs"
            )

        t_ax_data = self.ax.transAxes + self.ax.transData.inverted()

        if shape_crs == "axes":
            if np.size(size) == 1:
                # to allow "square" or "circular" peek-shapes, we have to
                # scale with respect to the axes width/height ratio as well
                asp = self.ax.bbox.width / self.ax.bbox.height
                if asp > 1:
                    tasp = Affine2D().scale(1 / asp, 1)
                else:
                    tasp = Affine2D().scale(1, asp)

                t = tasp + t_ax_data
            else:
                t = t_ax_data

            t_peek_plot = lambda x, y: t.transform(np.column_stack((x, y))).T
            t_plot_peek = lambda x, y: t.inverted().transform(np.column_stack((x, y))).T
            xlim, ylim = (0, 1), (0, 1)
        else:
            if (
                shape_crs == "plot"
                or (shape_ccrs := self._get_cartopy_crs(shape_crs)) == self.crs_plot
            ):
                t_peek_plot = t_plot_peek = lambda x, y: (x, y)
                xlim, ylim = (
                    None,
                    None,
                )  # self.crs_plot.x_limits, self.crs_plot.y_limits
            else:
                # t_peek_plot = self._get_transformer(shape_crs, self.crs_plot).transform
                # t_plot_peek = self._get_transformer(self.crs_plot, shape_crs).transform

                tpepl = (
                    shape_ccrs._as_mpl_transform(self.ax) + self.ax.transData.inverted()
                )
                t_plot_peek = (
                    lambda x, y: tpepl.inverted().transform(np.column_stack((x, y))).T
                )
                t_peek_plot = lambda x, y: tpepl.transform(np.column_stack((x, y))).T

                limcrs = self._get_cartopy_crs(shape_crs)
                xlim, ylim = limcrs.x_limits, limcrs.y_limits

        if xy_crs == "axes":
            t_xy_plot = lambda x, y: t_ax_data.transform(np.column_stack((x, y))).T
        elif xy_crs == "plot":
            t_xy_plot = lambda x, y: (x, y)
        else:
            t_xy_plot = self._get_transformer(xy_crs, self.crs_plot).transform

        # isinstance call is required to support numpy-arrays of vertices for shape
        if isinstance(shape, str) and shape in ("left", "right", "top", "bottom"):
            (x0, x1), (y0, y1) = self.ax.get_xlim(), self.ax.get_ylim()
            x, y = t_xy_plot(*xy)

            # base transformations on transData to ensure correct treatment
            # for shared axes
            if shape == "left":
                x1 = x
            elif shape == "right":
                x0 = x
            elif shape == "top":
                y0 = y
            elif shape == "bottom":
                y1 = y

            clip_path = mpath.Path(
                _get_rect_poly_verts(x0, y0, x1, y1, n_shape_points),
                (
                    mpath.Path.MOVETO,
                    *[mpath.Path.LINETO] * (4 * n_shape_points - 2),
                    mpath.Path.CLOSEPOLY,
                ),
            )
        else:
            if isinstance(shape, str) and shape == "geod_circle":
                assert (
                    np.size(size) == 1
                ), f"Size must be a number for shape={shape}, not {size}"
                lon, lat = self.transform_plot_to_lonlat(*t_xy_plot(*xy))
                shp = self.set_shape._get("geod_circles")

                vx, vy = shp._calc_geod_circle_points(
                    lon=np.atleast_1d(lon),
                    lat=np.atleast_1d(lat),
                    radius=size,
                    n=n_shape_points,
                )

                # antimeridean "wrapping"
                if (abs(np.diff(vx)) > 300).any():
                    vx[vx < 0] = vx[vx < 0] % 360

                verts = np.column_stack(
                    self.transform_lonlat_to_plot(vx.squeeze(), vy.squeeze())
                )[::-1]

            else:
                t_xy_peek = lambda x, y: t_plot_peek(*t_xy_plot(x, y))

                # translate to desired position (in peek-crs)
                clip_path = self._get_clip_path(shape, loc, size, n_shape_points)
                clip_path = clip_path.transformed(Affine2D().translate(*t_xy_peek(*xy)))
                verts = clip_path.vertices.T

                verts = np.column_stack(t_peek_plot(*verts))
                x, y = clip_path.vertices.T

            # TODO find a way to replace infinities with appropriate points
            # on the map boundary
            mask = np.all(np.isfinite(verts), axis=1)
            verts = verts[mask]
            # linear rings require at least 4 coordinates
            if verts.size <= 4:
                return None

            if shape_crs == "axes" and shape != "geod_circle":
                # no need for antimeridean wrapping if "axes" transform is used
                # clip with respect to peek-crs limits
                if xlim is not None:
                    verts[:, 0] = np.clip(verts[:, 0], *xlim)
                if ylim is not None:
                    verts[:, 1] = np.clip(verts[:, 1], *ylim)

                # transform back to plot-crs
                x, y = t_peek_plot(x, y)

                mask = np.logical_and(np.isfinite(x), np.isfinite(y))

                # we need to clip with respect to plot-crs limits to avoid issues
                xlim, ylim = self.crs_plot.x_limits, self.crs_plot.y_limits
                if xlim is not None:
                    x = np.clip(x[mask], *xlim)
                if ylim is not None:
                    y = np.clip(y[mask], *ylim)

                if len(x) <= 4:
                    return

                verts = np.column_stack((x, y))
                # transform to plot crs
                clip_path = mpath.Path(
                    verts, clip_path.codes, clip_path._interpolation_steps
                )
            else:
                clip_path = mpath.Path(
                    verts,
                    (
                        mpath.Path.MOVETO,
                        *[mpath.Path.LINETO] * (len(verts) - 2),
                        mpath.Path.CLOSEPOLY,
                    ),
                )

                if shape == "geod_circle":
                    self._gcp = clip_path
                else:

                    self._cp = clip_path

        argb = self._bm._get_restore_bg_img(layer)

        kwargs.setdefault("interpolation", "nearest")
        kwargs.setdefault("interpolation_stage", "data")
        kwargs.setdefault("animated", True)
        kwargs.setdefault("zorder", 100)
        kwargs.setdefault("resample", False)

        xt = argb.get_extents()
        art = plt.Axes.imshow(
            self.ax,
            argb,
            origin="upper",
            extent=[xt[0], xt[2], xt[1], xt[3]],
            transform=None,
            **kwargs,
        )

        if clip_path is not None:
            if boundary:
                patch = PathPatch(clip_path, **bnd_kwargs)
                marker = self.ax.add_patch(patch)

                if dynamic is True:
                    self.add_artist(marker)
                else:
                    self.add_bg_artist(marker)

            # create a TransformedPath as needed for clipping
            clip_path = TransformedPath(
                clip_path, self.ax.projection._as_mpl_transform(self.ax)
            )

            art.set_clip_path(clip_path)

        # remember buffer object for comparison
        art._peek_bufr = argb

        if dynamic is True:
            self.add_artist(art)
        else:
            self.add_bg_artist(art)

        def update_peek_image(*args, **kwargs):
            argb = self._bm._get_restore_bg_img(layer)
            # only redraw if a new buffer has been obtained
            # (use this to avoid costly equality checks and redraws)
            if art._peek_bufr is argb:
                return

            art._peek_bufr = argb
            art.set_data(argb)

        self._bm.add_hook("after_fetch_bg", update_peek_image)

        def remove_method(*args, **kwargs):
            try:
                art._orig_remove_method(*args, **kwargs)
            except ValueError:
                # ValueError is returned in case the artist has already
                # been removed when this function triggers
                pass
            finally:
                self._bm.remove_hook("after_fetch_bg", update_peek_image)

        art._orig_remove_method = art._remove_method
        art._remove_method = remove_method

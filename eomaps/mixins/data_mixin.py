import logging

_log = logging.getLogger(__name__)

from types import SimpleNamespace
from functools import wraps
import weakref

from pyproj import CRS
import numpy as np

import matplotlib.pyplot as plt
import matplotlib.path as mpath
import matplotlib as mpl

from ..helpers import cmap_alpha, SearchTree, register_modules, _proxy
from ..shapes import Shapes
from ..colorbar import ColorBar
from .._containers import DataSpecs, ClassifySpecs
from ..reader import read_file, from_file, new_layer_from_file
from .._data_manager import DataManager


class DataMixin:
    """Mixin to handle data visualization"""

    from_file = from_file
    new_layer_from_file = new_layer_from_file
    read_file = read_file

    # to make namespace accessible for sphinx
    set_shape = Shapes

    data_specs = DataSpecs

    def __init__(
        self,
        *args,
        **kwargs,
    ):

        super().__init__(*args, **kwargs)

        self._inherit_classification = None

        self._colorbars = []
        self._coll = None  # slot for the collection created by m.plot_map()

        # a list to remember newly registered colormaps
        self._registered_cmaps = []

        # default classify specs
        self._classify_specs = ClassifySpecs(weakref.proxy(self))

        # initialize the data-manager
        self.data_specs = DataSpecs(weakref.proxy(self), x=None, y=None, crs=4326)

        self._data_manager = DataManager(_proxy(self))
        self._data_plotted = False
        self._set_extent_on_plot = True

        self.new_layer_from_file = new_layer_from_file(weakref.proxy(self))

        self.set_shape = self.set_shape(weakref.proxy(self))
        self._shape = None
        # the dpi used for shade shapes
        self._shade_dpi = None

        # the radius is estimated when plot_map is called
        self._estimated_radius = None

        # evaluate and cache crs boundary bounds (for extent clipping)
        self._crs_boundary_bounds = self.crs_plot.boundary.bounds

    @property
    def __lazy_attrs(self):
        # list of attributes that support lazy-evaluation
        exclude = [
            "coll",
            "shape",
            "colorbar",
            "data",
            "data_specs",
            "set_shade_dpi",
        ]
        return [i for i in dir(DataMixin) if not (i.startswith("_") or i in exclude)]

    @property
    def coll(self):
        """The collection representing the dataset plotted by m.plot_map()."""
        return self._coll

    @property
    def shape(self):
        """
        The shape that is used to represent the dataset if `m.plot_map()` is called.

        By default "ellipses" is used for datasets < 500k datapoints and for plots
        where no explicit data is assigned, and otherwise "shade_raster" is used
        for 2D datasets and "shade_points" is used for unstructured datasets.

        """

        if not self._shape_assigned:
            self._set_default_shape()
            self._shape._is_default = True

        return self._shape

    @property
    def colorbar(self):
        """
        Get the **most recently added** colorbar of this Maps-object.

        Returns
        -------
        ColorBar
            EOmaps colorbar object.
        """
        if len(self._colorbars) > 0:
            return self._colorbars[-1]

    @property
    def data(self):
        """The data assigned to this Maps-object."""
        return self.data_specs.data

    @data.setter
    def data(self, val):
        # for downward-compatibility
        self.data_specs.data = val

    def set_data(
        self,
        data=None,
        x=None,
        y=None,
        crs=None,
        encoding=None,
        cpos="c",
        cpos_radius=None,
        parameter=None,
    ):
        """
        Set the properties of the dataset you want to plot.

        Use this function to update multiple data-specs in one go
        Alternatively you can set the data-specifications via

            >>> m.data_specs.< property > = ...`

        Parameters
        ----------
        data : array-like
            The data of the Maps-object.
            Accepted inputs are:

            - a pandas.DataFrame with the coordinates and the data-values
            - a pandas.Series with only the data-values
            - a 1D or 2D numpy-array with the data-values
            - a 1D list of data values

        x, y : array-like or str, optional
            Specify the coordinates associated with the provided data.
            Accepted inputs are:

            - a string (corresponding to the column-names of the `pandas.DataFrame`)

              - ONLY if "data" is provided as a pandas.DataFrame!

            - a pandas.Series
            - a 1D or 2D numpy-array
            - a 1D list

            The default is "lon" and "lat".
        crs : int, dict or str
            The coordinate-system of the provided coordinates.
            Can be one of:

            - PROJ string
            - Dictionary of PROJ parameters
            - PROJ keyword arguments for parameters
            - JSON string with PROJ parameters
            - CRS WKT string
            - An authority string [i.e. 'epsg:4326']
            - An EPSG integer code [i.e. 4326]
            - A tuple of ("auth_name": "auth_code") [i.e ('epsg', '4326')]
            - An object with a `to_wkt` method.
            - A :class:`pyproj.crs.CRS` class

            (see `pyproj.CRS.from_user_input` for more details)

            The default is 4326 (e.g. geographic lon/lat crs)
        parameter : str, optional
            MANDATORY IF a pandas.DataFrame that specifies both the coordinates
            and the data-values is provided as `data`!

            The name of the column that should be used as parameter.

            If None, the first column (despite of the columns assigned as "x" and "y")
            will be used. The default is None.
        encoding : dict or False, optional
            A dict containing the encoding information in case the data is provided as
            encoded values (useful to avoid decoding large integer-encoded datasets).

            If provided, the data will be decoded "on-demand" with respect to the
            provided "scale_factor" and "add_offset" according to the formula:

            >>> actual_value = encoding["add_offset"] + encoding["scale_factor"] * value

            Note: Colorbars and pick-callbakcs will use the encoding-information to
            display the actual data-values!

            If False, no value-transformation is performed.
            The default is False
        cpos : str, optional
            Indicator if the provided x-y coordinates correspond to the center ("c"),
            upper-left corner ("ul"), lower-left corner ("ll") etc.  of the pixel.
            If any value other than "c" is provided, a "cpos_radius" must be set!
            The default is "c".
        cpos_radius : int or tuple, optional
            The pixel-radius (in the input-crs) that will be used to set the
            center-position of the provided data.
            If a number is provided, the pixels are treated as squares.
            If a tuple (rx, ry) is provided, the pixels are treated as rectangles.
            The default is None.

        Examples
        --------
        - using a single `pandas.DataFrame`

          >>> data = pd.DataFrame(dict(lon=[...], lat=[...], a=[...], b=[...]))
          >>> m.set_data(data, x="lon", y="lat", parameter="a", crs=4326)

        - using individual `pandas.Series`

          >>> lon, lat, vals = pd.Series([...]), pd.Series([...]), pd.Series([...])
          >>> m.set_data(vals, x=lon, y=lat, crs=4326)

        - using 1D lists

          >>> lon, lat, vals = [...], [...], [...]
          >>> m.set_data(vals, x=lon, y=lat, crs=4326)

        - using 1D or 2D numpy.arrays

          >>> lon, lat, vals = np.array([[...]]), np.array([[...]]), np.array([[...]])
          >>> m.set_data(vals, x=lon, y=lat, crs=4326)

        - integer-encoded datasets

          >>> lon, lat, vals = [...], [...], [1, 2, 3, ...]
          >>> encoding = dict(scale_factor=0.01, add_offset=1)
          >>> # colorbars and pick-callbacks will now show values as (1 + 0.01 * value)
          >>> # e.g. the "actual" data values are [0.01, 0.02, 0.03, ...]
          >>> m.set_data(vals, x=lon, y=lat, crs=4326, encoding=encoding)

        """
        if data is not None:
            self.data_specs.data = data

        if x is not None:
            self.data_specs.x = x

        if y is not None:
            self.data_specs.y = y

        if crs is not None:
            self.data_specs.crs = crs

        if encoding is not None:
            self.data_specs.encoding = encoding

        if cpos is not None:
            self.data_specs.cpos = cpos

        if cpos_radius is not None:
            self.data_specs.cpos_radius = cpos_radius

        if parameter is not None:
            self.data_specs.parameter = parameter

    @property
    def set_classify(self):
        """
        Interface to the classifiers provided by the 'mapclassify' module.

        To set a classification scheme for a given Maps-object, simply use:

        >>> m.set_classify.< SCHEME >(...)

        Where `< SCHEME >` is the name of the desired classification and additional
        parameters are passed in the call. (check docstrings for more info!)

        A list of available classification-schemes is accessible via
        `mapclassify.CLASSIFIERS`

            - BoxPlot (hinge)
            - EqualInterval (k)
            - FisherJenks (k)
            - FisherJenksSampled (k, pct, truncate)
            - HeadTailBreaks ()
            - JenksCaspall (k)
            - JenksCaspallForced (k)
            - JenksCaspallSampled (k, pct)
            - MaxP (k, initial)
            - MaximumBreaks (k, mindiff)
            - NaturalBreaks (k, initial)
            - Quantiles (k)
            - Percentiles (pct)
            - StdMean (multiples)
            - UserDefined (bins)

        Examples
        --------
        >>> m.set_classify.Quantiles(k=5)

        >>> m.set_classify.EqualInterval(k=5)

        >>> m.set_classify.UserDefined(bins=[5, 10, 25, 50])

        """
        (mapclassify,) = register_modules("mapclassify")

        s = SimpleNamespace(
            **{
                i: self._get_mcl_subclass(getattr(mapclassify, i))
                for i in mapclassify.CLASSIFIERS
            }
        )

        s.__doc__ = DataMixin.set_classify.__doc__

        return s

    def set_classify_specs(self, scheme=None, **kwargs):
        """
        Set classification specifications for the data.

        The classification is ultimately performed by the `mapclassify` module!

        Note
        ----
        The following calls have the same effect:

        >>> m.set_classify.Quantiles(k=5)
        >>> m.set_classify_specs(scheme="Quantiles", k=5)

        Using `m.set_classify()` is the same as using `m.set_classify_specs()`!
        However, `m.set_classify()` will provide autocompletion and proper
        docstrings once the Maps-object is initialized which greatly enhances
        the usability.

        Parameters
        ----------
        scheme : str
            The classification scheme to use.
            (the list is accessible via `mapclassify.CLASSIFIERS`)

            E.g. one of (possible kwargs in brackets):

                - BoxPlot (hinge)
                - EqualInterval (k)
                - FisherJenks (k)
                - FisherJenksSampled (k, pct, truncate)
                - HeadTailBreaks ()
                - JenksCaspall (k)
                - JenksCaspallForced (k)
                - JenksCaspallSampled (k, pct)
                - MaxP (k, initial)
                - MaximumBreaks (k, mindiff)
                - NaturalBreaks (k, initial)
                - Quantiles (k)
                - Percentiles (pct)
                - StdMean (multiples)
                - UserDefined (bins)

        kwargs :
            kwargs passed to the call to the respective mapclassify classifier
            (dependent on the selected scheme... see above)

        """
        register_modules("mapclassify")
        self._classify_specs._set_scheme_and_args(scheme, **kwargs)

    def set_shade_dpi(self, dpi=None):
        """
        Set the dpi used by "shade shapes" to aggregate datasets.

        This only affects the plot-shapes "shade_raster" and "shade_points".

        Note
        ----
        If dpi=None is used (the default), datasets in exported figures will be
        re-rendered with respect to the requested dpi of the exported image!

        Parameters
        ----------
        dpi : int or None, optional
            The dpi to use for data aggregation with shade shapes.
            If None, the figure-dpi is used.

            The default is None.

        """
        self._shade_dpi = dpi
        self._update_shade_axis_size()

    def inherit_data(self, m):
        """
        Use the data of another Maps-object (without copying).

        NOTE
        ----
        If the data is inherited, any change in the data of the parent
        Maps-object will be reflected in this Maps-object as well!

        Parameters
        ----------
        m : eomaps.Maps or None
            The Maps-object that provides the data.
        """
        if m is not None:
            self.data_specs = m.data_specs

            def set_data(*args, **kwargs):
                raise AssertionError(
                    "EOmaps: You cannot set data for a Maps object that "
                    "inherits data!"
                )

            self.set_data = set_data

    def inherit_classification(self, m):
        """
        Use the classification of another Maps-object when plotting the data.

        NOTE
        ----
        If the classification is inherited, the following arguments
        for `m.plot_map()` will have NO effect (they are inherited):

            - "cmap"
            - "vmin"
            - "vmax"

        Parameters
        ----------
        m : eomaps.Maps or None
            The Maps-object that provides the classification specs.
        """
        if m is not None:
            self._inherit_classification = _proxy(m)
        else:
            self._inherit_classification = None

    def plot_map(
        self,
        layer=None,
        dynamic=False,
        set_extent=True,
        assume_sorted=True,
        indicate_masked_points=False,
        **kwargs,
    ):
        """
        Plot the dataset assigned to this Maps-object.

        - To set the data, see `m.set_data()`
        - To change the "shape" that is used to represent the datapoints, see
          `m.set_shape`.
        - To classify the data, see `m.set_classify` or `m.set_classify_specs()`

        NOTE
        ----
        Each call to `plot_map(...)` will override the previously plotted dataset!

        If you want to plot multiple datasets, use a new layer for each dataset!
        (e.g. via `m2 = m.new_layer()`)

        Parameters
        ----------
        layer : str or None
            The layer at which the dataset will be plotted.
            ONLY relevant if `dynamic = False`!

            - If "all": the corresponding feature will be added to ALL layers
            - If None, the layer assigned to the Maps object is used (e.g. `m.layer`)

            The default is None.
        dynamic : bool
            If True, the collection will be dynamically updated.
        set_extent : bool
            Set the plot-extent to the data-extent.

            - if True: The plot-extent will be set to the extent of the data-coordinates
            - if False: The plot-extent is kept as-is

            The default is True
        assume_sorted : bool, optional
            ONLY relevant for the shapes "raster" and "shade_raster"
            (and only if coordinates are provided as 1D arrays and data is a 2D array)

            Sort values with respect to the coordinates prior to plotting
            (required for QuadMesh if unsorted coordinates are provided)

            The default is True.
        indicate_masked_points : bool or dict
            If False, masked points are not indicated.

            If True, any datapoints that could not be properly plotted
            with the currently assigned shape are indicated with a
            circle with a red boundary.

            If a dict is provided, it can be used to update the appearance of the
            masked points (arguments are passed to matplotlibs `plt.scatter()`)
            ('s': markersize, 'marker': the shape of the marker, ...)

            The default is False

        Other Parameters
        ----------------
        vmin, vmax : float, optional
            Min- and max. values assigned to the colorbar. The default is None.
        zorder : float
            The zorder of the artist (e.g. the stacking level of overlapping artists)
            The default is 1
        kwargs
            kwargs passed to the initialization of the matplotlib collection
            (dependent on the plot-shape) [linewidth, edgecolor, facecolor, ...]

            For "shade_points" or "shade_raster" shapes, kwargs are passed to
            `datashader.mpl_ext.dsshow`

        """
        verbose = kwargs.pop("verbose", None)
        if verbose is not None:
            _log.error("EOmaps: The parameter verbose is ignored.")

        # make sure zorder is set to 1 by default
        # (by default shading would use 0 while ordinary collections use 1)
        if self.shape.name != "contour":
            kwargs.setdefault("zorder", 1)
        else:
            # put contour lines by default at level 10
            if self.shape._filled:
                kwargs.setdefault("zorder", 1)
            else:
                kwargs.setdefault("zorder", 10)

        if getattr(self, "coll", None) is not None and len(self.cb.pick.get.cbs) > 0:
            _log.info(
                "EOmaps: Calling `m.plot_map()` or "
                "`m.make_dataset_pickable()` more than once on the "
                "same Maps-object overrides the assigned PICK-dataset!"
            )

        if layer is None:
            layer = self.layer
        else:
            if not isinstance(layer, str):
                _log.info("EOmaps: The layer-name has been converted to a string!")
                layer = str(layer)

        useshape = self.shape  # invoke the setter to set the default shape
        shade_q = useshape.name.startswith("shade_")  # indicator if shading is used

        # make sure the colormap is properly set and transparencies are assigned
        cmap = kwargs.pop("cmap", "viridis")

        if "alpha" in kwargs and kwargs["alpha"] < 1:
            # get a unique name for the colormap
            cmapname = self._get_alpha_cmap_name(kwargs["alpha"])

            cmap = cmap_alpha(
                cmap=cmap,
                alpha=kwargs["alpha"],
                name=cmapname,
            )

            plt.colormaps.register(name=cmapname, cmap=cmap)
            self._emit_signal("cmapsChanged")
            # remember registered colormaps (to de-register on close)
            self._registered_cmaps.append(cmapname)

        # ---------------------- prepare the data

        _log.debug("EOmaps: Preparing dataset")

        # ---------------------- assign the data to the data_manager

        # shade shapes use datashader to update the data of the collections!
        update_coll_on_fetch = False if shade_q else True

        self._data_manager.set_props(
            layer=layer,
            assume_sorted=assume_sorted,
            update_coll_on_fetch=update_coll_on_fetch,
            indicate_masked_points=indicate_masked_points,
            dynamic=dynamic,
        )

        # ---------------------- classify the data
        self._set_vmin_vmax(
            vmin=kwargs.pop("vmin", None), vmax=kwargs.pop("vmax", None)
        )

        if not self._inherit_classification:
            if self._classify_specs.scheme is not None:
                _log.debug("EOmaps: Classifying...")
            elif self.shape.name == "contour" and kwargs.get("levels", None) is None:
                # TODO use custom contour-levels as UserDefined classification?
                self.set_classify.EqualInterval(k=5)

        cbcmap, norm, bins, classified = self._classify_data(
            vmin=self._vmin,
            vmax=self._vmax,
            cmap=cmap,
            classify_specs=self._classify_specs,
        )

        if norm is not None:
            if "norm" in kwargs:
                raise TypeError(
                    "EOmaps: You cannot provide an explicit norm for the dataset if a "
                    "classification scheme is used!"
                )
        else:
            if "norm" in kwargs:
                norm = kwargs.pop("norm")
                if not isinstance(norm, str):  # to allow datashader "eq_hist" norm
                    norm.vmin = self._vmin
                    norm.vmax = self._vmax
            else:
                norm = plt.Normalize(vmin=self._vmin, vmax=self._vmax)

        # todo remove duplicate attributes
        self._classify_specs._cbcmap = cbcmap
        self._classify_specs._norm = norm
        self._classify_specs._bins = bins
        self._classify_specs._classified = classified

        self._cbcmap = cbcmap
        self._norm = norm
        self._bins = bins
        self._classified = classified

        # ---------------------- plot the data

        if shade_q:
            self._shade_map(
                layer=layer,
                dynamic=dynamic,
                set_extent=set_extent,
                assume_sorted=assume_sorted,
                **kwargs,
            )
            self.f.canvas.draw_idle()
        else:
            # dont set extent if "m.set_extent" was called explicitly
            if set_extent and self._set_extent_on_plot:
                # note bg-layers are automatically triggered for re-draw
                # if the extent changes!
                self._data_manager._set_lims()

            self._plot_map(
                layer=layer,
                dynamic=dynamic,
                set_extent=set_extent,
                assume_sorted=assume_sorted,
                **kwargs,
            )

            self.BM._refetch_layer(layer)

        if getattr(self, "_data_mask", None) is not None and not np.all(
            self._data_mask
        ):
            _log.info("EOmaps: Some datapoints could not be drawn!")

        self._data_plotted = True

        self._emit_signal("dataPlotted")

        self.BM.update()

    @wraps(ColorBar._new_colorbar)
    def add_colorbar(self, *args, **kwargs):
        """Add a colorbar to the map."""
        if self.coll is None:
            raise AttributeError(
                "EOmaps: You must plot a dataset before " "adding a colorbar!"
            )
        colorbar = ColorBar._new_colorbar(self, *args, **kwargs)

        self._colorbars.append(colorbar)
        self.BM._refetch_layer(self.layer)
        self.BM._refetch_layer("__SPINES__")

        return colorbar

    def make_dataset_pickable(
        self,
    ):
        """
        Make the associated dataset pickable **without plotting** it first.

        After executing this function, `m.cb.pick` callbacks can be attached to the
        `Maps` object.

        NOTE
        ----
        This function is ONLY necessary if you want to use pick-callbacks **without**
        actually plotting the data**! Otherwise a call to `m.plot_map()` is sufficient!

        - Each `Maps` object can always have only one pickable dataset.
        - The used data is always the dataset that was assigned in the last call to
          `m.plot_map()` or `m.make_dataset_pickable()`.
        - To get multiple pickable datasets, use an individual layer for each of the
          datasets (e.g. first `m2 = m.new_layer()` and then assign the data to `m2`)

        Examples
        --------
        >>> m = Maps()
        >>> m.add_feature.preset.coastline()
        >>> ...
        >>> # a dataset that should be pickable but NOT visible...
        >>> m2 = m.new_layer()
            >>> m2.set_data(*np.linspace([0, -180,-90,], [100, 180, 90], 100).T)
        >>> m2.make_dataset_pickable()
        >>> m2.cb.pick.attach.annotate()  # get an annotation for the invisible dataset
        >>> # ...call m2.plot_map() to make the dataset visible...
        """
        if self.coll is not None:
            _log.error(
                "EOmaps: There is already a dataset plotted on this Maps-object. "
                "You MUST use a new layer (`m2 = m.new_layer()`) to use "
                "`m2.make_dataset_pickable()`!"
            )
            return

        # ---------------------- prepare the data
        self._data_manager = DataManager(_proxy(self))
        self._data_manager.set_props(layer=self.layer, only_pick=True)

        x0, x1 = self._data_manager.x0.min(), self._data_manager.x0.max()
        y0, y1 = self._data_manager.y0.min(), self._data_manager.y0.max()

        # use a transparent rectangle of the data-extent as artist for picking
        (art,) = self.ax.fill([x0, x1, x1, x0], [y0, y0, y1, y1], fc="none", ec="none")

        self._coll = art

        self.tree = SearchTree(m=_proxy(self))
        self.cb.pick._set_artist(art)
        self.cb.pick._init_cbs()
        self.cb._methods.add("pick")

        self._coll_kwargs = dict()
        self._coll_dynamic = True

        # set _data_plotted to True to trigger updates in the data-manager
        self._data_plotted = True

    def _plot_map(
        self,
        layer=None,
        dynamic=False,
        set_extent=True,
        assume_sorted=True,
        **kwargs,
    ):
        _log.info(
            "EOmaps: Plotting "
            f"{self._data_manager.z_data.size} datapoints ({self.shape.name})"
        )

        for key in ("array",):
            assert (
                key not in kwargs
            ), f"The key '{key}' is assigned internally by EOmaps!"

        try:
            self._set_extent = set_extent

            # ------------- plot the data
            self._coll_kwargs = kwargs
            self._coll_dynamic = dynamic

            # NOTE: the actual plot is performed by the data-manager
            # at the next call to m.BM.fetch_bg() for the corresponding layer
            # this is called to make sure m.coll is properly set
            self._data_manager.on_fetch_bg(check_redraw=False)

        except Exception as ex:
            raise ex

    def _shade_map(
        self,
        layer=None,
        dynamic=False,
        set_extent=True,
        assume_sorted=True,
        **kwargs,
    ):
        """
        Plot the dataset using the (very fast) "datashader" library.

        Requires `datashader`... use `conda install -c conda-forge datashader`

        - This method is intended for extremely large datasets
          (up to millions of datapoints)!

        A dynamically updated "shaded" map will be generated.
        Note that the datapoints in this case are NOT represented by the shapes
        defined as `m.set_shape`!

        - By default, the shading is performed using a "mean"-value aggregation hook

        kwargs :
            kwargs passed to `datashader.mpl_ext.dsshow`

        """
        _log.info(
            "EOmaps: Plotting "
            f"{self._data_manager.z_data.size} datapoints ({self.shape.name})"
        )

        ds, mpl_ext, pd, xar = register_modules(
            "datashader", "datashader.mpl_ext", "pandas", "xarray"
        )

        # remove previously fetched backgrounds for the used layer
        if dynamic is False:
            self.BM._refetch_layer(layer)

        # in case the aggregation does not represent data-values
        # (e.g. count, std, var ... ) use an automatic "linear" normalization

        # get the name of the used aggretation reduction
        aggname = self.shape.aggregator.__class__.__name__

        if aggname in ["first", "last", "max", "min", "mean", "mode"]:
            kwargs.setdefault("norm", self._classify_specs._norm)
        else:
            kwargs.setdefault("norm", "linear")

        zdata = self._data_manager.z_data
        if len(zdata) == 0:
            _log.error("EOmaps: there was no data to plot")
            return

        plot_width, plot_height = self._get_shade_axis_size()

        # get rid of unnecessary dimensions in the numpy arrays
        zdata = zdata.squeeze()
        x0 = self._data_manager.x0.squeeze()
        y0 = self._data_manager.y0.squeeze()

        # the shape is always set after _prepare data!
        if self.shape.name == "shade_points" and self._data_manager.x0_1D is None:
            # fill masked-values with None to avoid issues with numba not being
            # able to deal with numpy-arrays
            # TODO report this to datashader to get it fixed properly?
            if isinstance(zdata, np.ma.masked_array):
                zdata = zdata.filled(None)

            df = pd.DataFrame(
                dict(
                    x=x0.ravel(),
                    y=y0.ravel(),
                    val=zdata.ravel(),
                ),
                copy=False,
            )

        else:
            if len(zdata.shape) == 2:
                if (zdata.shape == x0.shape) and (zdata.shape == y0.shape):
                    # 2D coordinates and 2D raster

                    # use a curvilinear QuadMesh
                    if self.shape.name == "shade_raster":
                        self.shape.glyph = ds.glyphs.QuadMeshCurvilinear(
                            "x", "y", "val"
                        )

                    df = xar.Dataset(
                        data_vars=dict(val=(["xx", "yy"], zdata)),
                        # dims=["x", "y"],
                        coords=dict(
                            x=(["xx", "yy"], x0),
                            y=(["xx", "yy"], y0),
                        ),
                    )

                elif (
                    ((zdata.shape[1],) == x0.shape)
                    and ((zdata.shape[0],) == y0.shape)
                    and (x0.shape != y0.shape)
                ):
                    raise AssertionError(
                        "EOmaps: it seems like you need to transpose your data! \n"
                        + f"the dataset has a shape of {zdata.shape}, but the "
                        + f"coordinates suggest ({x0.shape}, {y0.shape})"
                    )
                elif (zdata.T.shape == x0.shape) and (zdata.T.shape == y0.shape):
                    raise AssertionError(
                        "EOmaps: it seems like you need to transpose your data! \n"
                        + f"the dataset has a shape of {zdata.shape}, but the "
                        + f"coordinates suggest {x0.shape}"
                    )

                elif ((zdata.shape[0],) == x0.shape) and (
                    (zdata.shape[1],) == y0.shape
                ):
                    # 1D coordinates and 2D data

                    # use a rectangular QuadMesh
                    if self.shape.name == "shade_raster":
                        self.shape.glyph = ds.glyphs.QuadMeshRectilinear(
                            "x", "y", "val"
                        )

                    df = xar.DataArray(
                        data=zdata,
                        dims=["x", "y"],
                        coords=dict(x=x0, y=y0),
                    )
                    df = xar.Dataset(dict(val=df))
            else:
                try:
                    # try if reprojected coordinates can be used as 2d grid and if yes,
                    # directly use a curvilinear QuadMesh based on the reprojected
                    # coordinates to display the data
                    idx = pd.MultiIndex.from_arrays(
                        [x0.ravel(), y0.ravel()], names=["x", "y"]
                    )

                    df = pd.DataFrame(
                        data=dict(val=zdata.ravel()), index=idx, copy=False
                    )
                    df = df.to_xarray()
                    xg, yg = np.meshgrid(df.x, df.y)
                except Exception:
                    # first convert original coordinates of the 1D inputs to 2D,
                    # then reproject the grid and use a curvilinear QuadMesh to display
                    # the data
                    _log.warning(
                        "EOmaps: 1D data is converted to 2D prior to reprojection... "
                        "Consider using 'shade_points' as plot-shape instead!"
                    )
                    xorig = self._data_manager.xorig.ravel()
                    yorig = self._data_manager.yorig.ravel()

                    idx = pd.MultiIndex.from_arrays([xorig, yorig], names=["x", "y"])

                    df = pd.DataFrame(
                        data=dict(val=zdata.ravel()), index=idx, copy=False
                    )
                    df = df.to_xarray()
                    xg, yg = np.meshgrid(df.x, df.y)

                    # transform the grid from input-coordinates to the plot-coordinates
                    crs1 = CRS.from_user_input(self.data_specs.crs)
                    crs2 = CRS.from_user_input(self._crs_plot)
                    if crs1 != crs2:
                        transformer = self._get_transformer(
                            crs1,
                            crs2,
                        )
                        xg, yg = transformer.transform(xg, yg)

                # use a curvilinear QuadMesh
                if self.shape.name == "shade_raster":
                    self.shape.glyph = ds.glyphs.QuadMeshCurvilinear("x", "y", "val")

                df = xar.Dataset(
                    data_vars=dict(val=(["xx", "yy"], df.val.values.T)),
                    coords=dict(x=(["xx", "yy"], xg), y=(["xx", "yy"], yg)),
                )

            if self.shape.name == "shade_points":
                df = df.to_dataframe().reset_index()

        if set_extent is True and self._set_extent_on_plot is True:
            # convert to a numpy-array to support 2D indexing with boolean arrays
            x, y = np.asarray(df.x), np.asarray(df.y)
            xf, yf = np.isfinite(x), np.isfinite(y)
            x_range = (np.nanmin(x[xf]), np.nanmax(x[xf]))
            y_range = (np.nanmin(y[yf]), np.nanmax(y[yf]))
        else:
            # update here to ensure bounds are set
            self.BM.update()
            x0, x1, y0, y1 = self.get_extent(self.crs_plot)
            x_range = (x0, x1)
            y_range = (y0, y1)

        coll = mpl_ext.dsshow(
            df,
            glyph=self.shape.glyph,
            aggregator=self.shape.aggregator,
            shade_hook=self.shape.shade_hook,
            agg_hook=self.shape.agg_hook,
            # norm="eq_hist",
            # norm=plt.Normalize(vmin, vmax),
            cmap=self._cbcmap,
            ax=self.ax,
            plot_width=plot_width,
            plot_height=plot_height,
            # x_range=(x0, x1),
            # y_range=(y0, y1),
            # x_range=(df.x.min(), df.x.max()),
            # y_range=(df.y.min(), df.y.max()),
            x_range=x_range,
            y_range=y_range,
            vmin=self._vmin,
            vmax=self._vmax,
            **kwargs,
        )

        coll.set_label("Dataset " f"({self.shape.name}  |  {zdata.shape})")

        self._coll = coll

        if dynamic is True:
            self.BM.add_artist(coll, layer=layer)
        else:
            self.BM.add_bg_artist(coll, layer=layer)

        if dynamic is True:
            self.BM.update(clear=False)

    @property
    def _shape_assigned(self):
        """Return True if the shape is explicitly assigned and False otherwise"""
        # the shape is considered assigned if an explicit shape is set
        # or if the data has been plotted with the default shape

        q = self._shape is None or (
            getattr(self._shape, "_is_default", False) and not self._data_plotted
        )

        return not q

    def _classify_data(
        self,
        z_data=None,
        cmap=None,
        vmin=None,
        vmax=None,
        classify_specs=None,
    ):

        if self._inherit_classification is not None:
            try:
                return (
                    self._inherit_classification._cbcmap,
                    self._inherit_classification._norm,
                    self._inherit_classification._bins,
                    self._inherit_classification._classified,
                )
            except AttributeError:
                raise AssertionError(
                    "EOmaps: A Maps object can only inherit the classification "
                    "if the parent Maps object called `m.plot_map()` first!!"
                )

        if z_data is None:
            z_data = self._data_manager.z_data

        if isinstance(cmap, str):
            cmap = plt.get_cmap(cmap).copy()
        else:
            cmap = cmap.copy()

        # evaluate classification
        if classify_specs is not None and classify_specs.scheme is not None:
            (mapclassify,) = register_modules("mapclassify")

            classified = True
            if self._classify_specs.scheme == "UserDefined":
                bins = self._classify_specs.bins
            else:
                # use "np.ma.compressed" to make sure values excluded via
                # masked-arrays are not used to evaluate classification levels
                # (normal arrays are passed through!)
                mapc = getattr(mapclassify, classify_specs.scheme)(
                    np.ma.compressed(z_data[~np.isnan(z_data)]), **classify_specs
                )
                bins = mapc.bins

            bins = np.unique(np.clip(bins, vmin, vmax))

            if vmin < min(bins):
                bins = [vmin, *bins]

            if vmax > max(bins):
                bins = [*bins, vmax]

            # TODO Always use resample once mpl>3.6 is pinned
            if hasattr(cmap, "resampled") and len(bins) > cmap.N:
                # Resample colormap to contain enough color-values
                # as needed by the boundary-norm.
                cbcmap = cmap.resampled(len(bins))
            else:
                cbcmap = cmap

            norm = mpl.colors.BoundaryNorm(bins, cbcmap.N)

            self._emit_signal("cmapsChanged")

            if cmap._rgba_bad:
                cbcmap.set_bad(cmap._rgba_bad)
            if cmap._rgba_over:
                cbcmap.set_over(cmap._rgba_over)
            if cmap._rgba_under:
                cbcmap.set_under(cmap._rgba_under)

        else:
            classified = False
            bins = None
            cbcmap = cmap
            norm = None

        return cbcmap, norm, bins, classified

    def _get_mcl_subclass(self, s):
        # get a subclass that inherits the docstring from the corresponding
        # mapclassify classifier

        class scheme:
            @wraps(s)
            def __init__(_, *args, **kwargs):
                pass

                if "y" in kwargs:
                    _log.error(
                        "EOmaps: The values (e.g. the 'y' parameter) are "
                        + "assigned internally... only provide additional "
                        + "parameters that specify the classification scheme!"
                    )
                    kwargs.pop("y")

                self._classify_specs._set_scheme_and_args(scheme=s.__name__, **kwargs)

        scheme.__doc__ = s.__doc__
        return scheme

    def _set_default_shape(self):
        if self.data is not None:
            # size = np.size(self.data)
            size = np.size(self._data_manager.z_data)
            shape = np.shape(self._data_manager.z_data)

            if len(shape) == 2 and size > 200_000:
                self.set_shape.raster()
            else:
                if size > 500_000:
                    if all(
                        register_modules(
                            "datashader", "datashader.mpl_ext", raise_exception=False
                        )
                    ):
                        # shade_points should work for any dataset
                        self.set_shape.shade_points()
                    else:
                        _log.warning(
                            "EOmaps: Attempting to plot a large dataset "
                            f"({size} datapoints) but the 'datashader' library "
                            "could not be imported! The plot might take long "
                            "to finish! ... defaulting to 'ellipses' "
                            "as plot-shape."
                        )
                        self.set_shape.ellipses()
                else:
                    self.set_shape.ellipses()
        else:
            self.set_shape.ellipses()

    def _find_ID(self, ID):
        # explicitly treat range-like indices (for very large datasets)
        ids = self._data_manager.ids
        if isinstance(ids, range):
            ind, mask = [], []
            for i in np.atleast_1d(ID):
                if i in ids:

                    found = ids.index(i)
                    ind.append(found)
                    mask.append(found)
                else:
                    ind.append(None)

        elif isinstance(ids, (list, np.ndarray)):
            mask = np.isin(ids, ID)
            ind = np.where(mask)[0]

        return mask, ind

    def _get_alpha_cmap_name(self, alpha):
        # get a unique name for the colormap
        try:
            ncmaps = max(
                [
                    int(i.rsplit("_", 1)[1])
                    for i in plt.colormaps()
                    if i.startswith("EOmaps_alpha_")
                ]
            )
        except Exception:
            ncmaps = 0

        return f"EOmaps_alpha_{ncmaps + 1}"

    def _encode_values(self, val):
        """
        Encode values with respect to the provided  "scale_factor" and "add_offset".

        Encoding is performed via the formula:

            `encoded_value = val / scale_factor - add_offset`

        NOTE: the data-type is not altered!!
        (e.g. no integer-conversion is performed, only values are adjusted)

        Parameters
        ----------
        val : array-like
            The data-values to encode

        Returns
        -------
        encoded_values
            The encoded data values
        """
        encoding = self.data_specs.encoding

        if encoding is not None and encoding is not False:
            try:
                scale_factor = encoding.get("scale_factor", None)
                add_offset = encoding.get("add_offset", None)
                fill_value = encoding.get("_FillValue", None)

                if val is None:
                    return fill_value

                if add_offset:
                    val = val - add_offset
                if scale_factor:
                    val = val / scale_factor

                return val
            except Exception:
                _log.exception(f"EOmaps: Error while trying to encode the data: {val}")
                return val
        else:
            return val

    def _decode_values(self, val):
        """
        Decode data-values with respect to the provided "scale_factor" and "add_offset".

        Decoding is performed via the formula:

            `actual_value = add_offset + scale_factor * val`

        The encoding is defined in `m.data_specs.encoding`

        Parameters
        ----------
        val : array-like
            The encoded data-values

        Returns
        -------
        decoded_values
            The decoded data values
        """
        if val is None:
            return None

        encoding = self.data_specs.encoding
        if not any(encoding is i for i in (None, False)):
            try:
                scale_factor = encoding.get("scale_factor", None)
                add_offset = encoding.get("add_offset", None)

                if scale_factor:
                    val = val * scale_factor
                if add_offset:
                    val = val + add_offset

                return val
            except Exception:
                _log.exception(f"EOmaps: Error while trying to decode the data {val}.")
                return val
        else:
            return val

    def _calc_vmin_vmax(self, vmin=None, vmax=None):
        if self.data is None:
            return vmin, vmax

        calc_min, calc_max = vmin is None, vmax is None

        # ignore fill_values when evaluating vmin/vmax on integer-encoded datasets
        if (
            self.data_specs.encoding is not None
            and isinstance(self._data_manager.z_data, np.ndarray)
            and issubclass(self._data_manager.z_data.dtype.type, np.integer)
        ):

            # note the specific way how to check for integer-dtype based on issubclass
            # since isinstance() fails to identify all integer dtypes!!
            #   isinstance(np.dtype("uint8"), np.integer)       (incorrect) False
            #   issubclass(np.dtype("uint8").type, np.integer)  (correct)   True
            # for details, see https://stackoverflow.com/a/934652/9703451

            fill_value = self.data_specs.encoding.get("_FillValue", None)
            if fill_value and any([calc_min, calc_max]):
                # find values that are not fill-values
                use_vals = self._data_manager.z_data[
                    self._data_manager.z_data != fill_value
                ]

                if calc_min:
                    vmin = np.min(use_vals)
                if calc_max:
                    vmax = np.max(use_vals)

                return vmin, vmax

        # use nanmin/nanmax for all other arrays
        if calc_min:
            vmin = np.nanmin(self._data_manager.z_data)
        if calc_max:
            vmax = np.nanmax(self._data_manager.z_data)

        return vmin, vmax

    def _set_vmin_vmax(self, vmin=None, vmax=None):
        # don't encode nan-vailes to avoid setting the fill-value as vmin/vmax
        if vmin is not None:
            vmin = self._encode_values(vmin)
        if vmax is not None:
            vmax = self._encode_values(vmax)

        # handle inherited bounds
        if self._inherit_classification is not None:
            if not (vmin is None and vmax is None):
                raise TypeError(
                    "EOmaps: 'vmin' and 'vmax' cannot be set explicitly "
                    "if the classification is inherited!"
                )

            # in case data is NOT inherited, warn if vmin/vmax is None
            # (different limits might cause a different appearance of the data!)
            if self.data_specs._m == self:
                if self._vmin is None:
                    _log.warning("EOmaps: Inherited value for 'vmin' is None!")
                if self._vmax is None:
                    _log.warning(
                        "EOmaps: Inherited inherited value for 'vmax' is None!"
                    )

            self._vmin = self._inherit_classification._vmin
            self._vmax = self._inherit_classification._vmax
            return

        if not self.shape.name.startswith("shade_"):
            # ignore fill_values when evaluating vmin/vmax on integer-encoded datasets
            self._vmin, self._vmax = self._calc_vmin_vmax(vmin=vmin, vmax=vmax)
        else:
            # get the name of the used aggretation reduction
            aggname = self.shape.aggregator.__class__.__name__
            if aggname in ["first", "last", "max", "min", "mean", "mode"]:
                # set vmin/vmax in case the aggregation still represents data-values
                self._vmin, self._vmax = self._calc_vmin_vmax(vmin=vmin, vmax=vmax)
            else:
                # set vmin/vmax for aggregations that do NOT represent data values
                # allow vmin/vmax = None (e.g. autoscaling)
                self._vmin, self._vmax = vmin, vmax
                if "count" in aggname:
                    # if the reduction represents a count, don't count empty pixels
                    if vmin and vmin <= 0:
                        _log.warning(
                            "EOmaps: setting vmin=1 to avoid counting empty pixels..."
                        )
                        self._vmin = 1

    def _get_shade_axis_size(self, dpi=None, flush=True):
        if flush:
            # flush events before evaluating shade sizes to make sure axes dimensions have
            # been properly updated
            self.f.canvas.flush_events()

        if self._shade_dpi is not None:
            dpi = self._shade_dpi

        fig_dpi = self.f.dpi
        w, h = self.ax.bbox.width, self.ax.bbox.height

        # TODO for now, only handle numeric dpi-values to avoid issues.
        # (savefig also seems to support strings like "figure" etc.)
        if isinstance(dpi, (int, float, np.number)):
            width = int(w / fig_dpi * dpi)
            height = int(h / fig_dpi * dpi)
        else:
            width = int(w)
            height = int(h)

        return width, height

    def _update_shade_axis_size(self, dpi=None, flush=True):
        # method to update all shade-dpis
        # NOTE: provided dpi value is only used if no explicit "_shade_dpi" is set!
        return
        # set the axis-size that is used to determine the number of pixels used
        # when using "shade" shapes for ALL maps objects of a figure
        for m in (self.parent, *self.parent._children):
            if m.coll is not None and m.shape.name.startswith("shade_"):
                w, h = m._get_shade_axis_size(dpi=dpi, flush=flush)
                m.coll.plot_width = w
                m.coll.plot_height = h

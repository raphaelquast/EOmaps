import logging

import numpy as np
from pyproj import CRS, Transformer

_log = logging.getLogger(__name__)


class DataManager:
    def __init__(self, m):
        self.m = m
        self.last_extent = None
        self._all_data = dict()

        self._current_data = dict()

        self._on_next_fetch = []
        self._masked_points_artist = None

        self._radius_margin_factor = 6
        self._radius_margin = None

        self._extent_margin_factor = 0.1

    def set_margin_factors(self, radius_margin_factor, extent_margin_factor):
        """
        Set the margin factors that are applied to the plot extent
        prior to selecting the data.

        Defaults are (6, 0.1)

        Note
        ----
        To make the changes effective this function MUST be called before
        plotting the data (e.g. before calling `m.plot_map()`)!

        Parameters
        ----------
        radius_margin_factor : float
            A multiplication factor for the shape-radius to determine the
            extent-margin for data-selection.

            margin = < shape radius > * radius_margin_factor

        extent_margin_factor : float
            Only used as a fallback if radius could not be determined!

            A multiplication factor for the data extent to determine the
            extent-margin for data-selection.

            margin = < data_extent > * radius_margin_factor
        """
        # multiplication factor for the shape-radius to determine the
        # extent-margin for data-selection
        self._radius_margin_factor = radius_margin_factor
        # multiplication factor for the plot_extent to determine the
        # fallback extent-margin for data-selection
        self._extent_margin_factor = extent_margin_factor

    @property
    def x0(self):
        return self._all_data.get("x0", None)

    @property
    def y0(self):
        return self._all_data.get("y0", None)

    @property
    def xorig(self):
        return self._all_data.get("xorig", None)

    @property
    def yorig(self):
        return self._all_data.get("yorig", None)

    @property
    def z_data(self):
        return self._all_data.get("z_data", None)

    @property
    def ids(self):
        return self._all_data.get("ids", None)

    @property
    def x0_1D(self):
        return getattr(self, "_x0_1D", None)

    @property
    def y0_1D(self):
        return getattr(self, "_y0_1D", None)

    def set_props(
        self,
        layer,
        assume_sorted=True,
        update_coll_on_fetch=True,
        indicate_masked_points=True,
        dynamic=False,
        only_pick=False,
    ):
        # cleanup existing callbacks before attaching new ones
        self.cleanup_callbacks()

        self._only_pick = only_pick

        if self.m._data_plotted:
            self._remove_existing_coll()

        self._all_data = self._prepare_data(assume_sorted=assume_sorted)
        self._indicate_masked_points = indicate_masked_points
        self.layer = layer

        if len(self.x0) == 0:
            _log.info("EOmaps: There is no data to plot")
            return

        if self.x0_1D is not None:
            # if we have 1D coordinates, use them to get the extent
            self._x0min, self._x0max = np.nanmin(self.x0_1D), np.nanmax(self.x0_1D)
            self._y0min, self._y0max = np.nanmin(self.y0_1D), np.nanmax(self.y0_1D)
        else:
            # get the extent from the full coordinate arrays
            self._x0min, self._x0max = np.nanmin(self.x0), np.nanmax(self.x0)
            self._y0min, self._y0max = np.nanmin(self.y0), np.nanmax(self.y0)

        # estimate the radius (used as margin on data selection)
        try:
            self._r = self.m._shapes._estimate_radius(
                self.m, radius_crs="out", method=np.nanmax
            )
            if self._r is not None and all(np.isfinite(i) for i in self._r):
                self._radius_margin = [i * self._radius_margin_factor for i in self._r]
            else:
                self._radius_margin = None
        except Exception:
            self._r = None
            self._radius_margin = None

        if update_coll_on_fetch:
            # attach a hook that updates the collection whenever a new
            # background is fetched
            # ("shade" shapes take care about updating the data themselves!)
            self.attach_callbacks(dynamic=dynamic)

    def attach_callbacks(self, dynamic):
        if dynamic is True:
            if self.on_fetch_bg not in self.m.BM._before_update_actions:
                self.m.BM._before_update_actions.append(self.on_fetch_bg)
        else:
            if self.on_fetch_bg not in self.m.BM._before_fetch_bg_actions:
                self.m.BM._before_fetch_bg_actions.append(self.on_fetch_bg)

    def cleanup_callbacks(self):
        if self.on_fetch_bg in self.m.BM._before_fetch_bg_actions:
            self.m.BM._before_fetch_bg_actions.remove(self.on_fetch_bg)
        if self.on_fetch_bg in self.m.BM._before_update_actions:
            self.m.BM._before_update_actions.remove(self.on_fetch_bg)

    def _prepare_data(self, assume_sorted=True):
        in_crs = self.m.data_specs.crs
        cpos = self.m.data_specs.cpos
        cpos_radius = self.m.data_specs.cpos_radius

        props = dict()
        # get coordinate transformation from in_crs to plot_crs
        # make sure to re-identify the CRS with pyproj to correctly skip re-projection
        # in case we use in_crs == plot_crs
        crs1 = CRS.from_user_input(in_crs)
        crs2 = CRS.from_user_input(self.m._crs_plot)

        # identify the provided data and get it in the internal format
        z_data, xorig, yorig, ids, parameter = self.m._identify_data()

        if cpos is not None and cpos != "c":
            # fix position of pixel-center in the input-crs
            assert (
                cpos_radius is not None
            ), "you must specify a 'cpos_radius if 'cpos' is not 'c'"
            if isinstance(cpos_radius, (list, tuple)):
                rx, ry = cpos_radius
            else:
                rx = ry = cpos_radius

            xorig, yorig = self._set_cpos(xorig, yorig, rx, ry, cpos)

        # invoke the shape-setter to make sure a shape is set
        used_shape = self.m.shape

        # --------- sort by coordinates
        # this is required to avoid glitches in "raster" and "shade_raster"
        # since QuadMesh requires sorted coordinates!
        # (currently only implemented for 1D coordinates and 2D data)
        if assume_sorted is False:
            if used_shape.name in ["raster", "shade_raster"]:
                if (
                    len(xorig.shape) == 1
                    and len(yorig.shape) == 1
                    and len(z_data.shape) == 2
                ):
                    _log.info("EOmaps: Sorting coordinates...")

                    xs, ys = np.argsort(xorig), np.argsort(yorig)
                    np.take(xorig, xs, out=xorig, mode="wrap")
                    np.take(yorig, ys, out=yorig, mode="wrap")
                    np.take(
                        np.take(z_data, xs, 0),
                        indices=ys,
                        axis=1,
                        out=z_data,
                        mode="wrap",
                    )
                else:
                    _log.info(
                        "EOmaps: using 'assume_sorted=False' is only possible"
                        + "if you use 1D coordinates + 2D data!"
                        + "...continuing without sorting."
                    )
            else:
                _log.info(
                    "EOmaps: using 'assume_sorted=False' is only relevant for "
                    + "the shapes ['raster', 'shade_raster']! "
                    + "...continuing without sorting."
                )

        self._z_transposed = False

        if crs1 == crs2:
            if (
                len(xorig.shape) == 1
                and len(yorig.shape) == 1
                and len(z_data.shape) == 2
            ):
                # remember 1 dimensional coordinate vectors for querying
                self._x0_1D = xorig
                self._y0_1D = yorig
                if used_shape.name in ["shade_raster"]:
                    pass
                else:
                    # convert 1D data to 2D (required for all shapes but shade_raster)
                    xorig, yorig = np.meshgrid(xorig, yorig, copy=False)

                    z_data = z_data.T
                    self._z_transposed = True

            x0, y0 = xorig, yorig

        else:
            if z_data.size > 1e7:
                _log.warning(
                    f"EOmaps Warning: Starting to reproject {z_data.size} "
                    "datapoints! This might take a lot of time and consume "
                    "a lot of memory... consider using the data-crs as "
                    "plot-crs to avoid reprojections!"
                )

            _log.info(f"EOmaps: Starting to reproject {z_data.size} datapoints")

            # transform center-points to the plot_crs
            transformer = Transformer.from_crs(
                crs1,
                crs2,
                always_xy=True,
            )
            # convert 1D data to 2D to make sure re-projection is correct
            if (
                len(xorig.shape) == 1
                and len(yorig.shape) == 1
                and len(z_data.shape) == 2
            ):
                xorig, yorig = np.meshgrid(xorig, yorig, copy=False)
                z_data = z_data.T
                self._z_transposed = True

            x0, y0 = transformer.transform(xorig, yorig)
            _log.info("EOmaps: Done reprojecting")

        # use np.asanyarray to ensure that the output is a proper numpy-array
        # (relevant for categorical dtypes in pandas.DataFrames)
        props["xorig"] = np.asanyarray(xorig)
        props["yorig"] = np.asanyarray(yorig)
        props["ids"] = ids
        props["z_data"] = np.asanyarray(z_data)
        props["x0"] = np.asanyarray(x0)
        props["y0"] = np.asanyarray(y0)

        # remember shapes for later use
        # TODO remove this!
        self.m._xshape = props["x0"].shape
        self.m._yshape = props["y0"].shape
        self.m._zshape = props["z_data"].shape

        return props

    def _set_cpos(self, x, y, radiusx, radiusy, cpos):
        # use x = x + ...   instead of x +=  to allow casting from int to float
        if cpos == "c":
            pass
        elif cpos == "ll":
            x = x + radiusx
            y = y + radiusy
        elif cpos == "ul":
            x = x + radiusx
            y = y - radiusy
        elif cpos == "lr":
            x = x - radiusx
            y = y + radiusy
        elif cpos == "ur":
            x = x - radiusx
            y = y - radiusx

        return x, y

    @property
    def current_extent(self):
        return self.m.get_extent(self.m.crs_plot)

    @property
    def extent_changed(self):
        return not self.current_extent == self.last_extent

    def _set_lims(self):
        # set the extent...
        # do this ONLY if this is the first time the collection is plotted!
        # (and BEFORE the collection is added to the axis!)

        # in case a proper radius is defined, add a margin of
        # (1 x radius) to the map
        if self._r is not None and all(np.isfinite(self._r)):
            rx, ry = self._r
        else:
            rx, ry = (0, 0)

        x0min = self._x0min - rx
        y0min = self._y0min - ry
        x0max = self._x0max + rx
        y0max = self._y0max + ry

        ymin, ymax = self.m.ax.projection.y_limits
        xmin, xmax = self.m.ax.projection.x_limits
        # set the axis-extent

        x0, x1, y0, y1 = (
            max(x0min, xmin),
            min(x0max, xmax),
            max(y0min, ymin),
            min(y0max, ymax),
        )

        self.m.ax.set_xlim(x0, x1)
        self.m.ax.set_ylim(y0, y1)

        self.m.f.canvas.draw_idle()
        return (x0, x1, y0, y1)

    def indicate_masked_points(self, **kwargs):
        # remove previous mask artist
        if self._masked_points_artist is not None:
            try:
                self.m.BM.remove_bg_artist(self._masked_points_artist)
                self._masked_points_artist.remove()
                self._masked_points_artist = None
            except Exception:
                _log.exception("EOmaps: Error while indicating masked points.")

        if not hasattr(self.m, "_data_mask") or self.m._data_mask is None:
            return

        mask = self.m._data_mask.ravel()
        npts = np.count_nonzero(mask)
        if npts == 0:
            return

        if npts > 1e5:
            _log.warning(
                "EOmaps: There are more than 100 000 masked points! "
                "... indicating masked points will affect performance!"
            )

        kwargs.setdefault("ec", "r")
        kwargs.setdefault("lw", 0.25)
        kwargs.setdefault("c", self._current_data["z_data"].ravel()[~mask])

        self._masked_points_artist = self.m.ax.scatter(
            self._current_data["x0"].ravel()[~mask],
            self._current_data["y0"].ravel()[~mask],
            cmap=getattr(self.m, "_cbcmap", "Reds"),
            norm=getattr(self.m, "_norm", None),
            **kwargs,
        )

        self.m.BM.add_bg_artist(self._masked_points_artist, layer=self.layer)

    def redraw_required(self, layer):
        """
        Check if a re-draw of the collection is required.

        Parameters
        ----------
        layer : str
            The layer for which the background is fetched.
        """
        if not self.m._data_plotted:
            return

        if self.m.shape.name == "contour":
            return False

        # don't re-draw while the layout-editor is active!
        if self.m.parent._layout_editor.modifier_pressed:
            return False

        # don't re-draw if the layer of the dataset is not requested
        # (note multi-layers trigger re-draws of individual layers as well)
        if layer not in ["all", self.layer]:
            return False

        # don't re-draw if the collection has been hidden in the companion-widget
        if self.m.coll in self.m.BM._hidden_artists:
            return False

        # re-draw if the data has never been plotted
        if self.m.coll is None:
            return True

        # re-draw if the collection has been removed from the axes (but the object
        # still exists... e.g. for temporary artists)
        if self.m.coll.axes is None:
            return True

        # re-draw if the current map-extent has changed
        if self.extent_changed:
            return True

        return False

    def _remove_existing_coll(self):
        if self.m.coll is not None:
            try:
                if self.m._coll_dynamic:
                    self.m.BM.remove_artist(self.m._coll)
                else:
                    self.m.BM.remove_bg_artist(self.m._coll)

                # if the collection is still attached to the axes, remove it
                if self.m.coll.axes is not None:
                    self.m.coll.remove()
                self.m._coll = None
            except Exception:
                _log.exception("EOmaps: Error while trying to remove collection.")

    def _get_current_datasize(self):
        if self._current_data:
            return self._get_datasize(**self._current_data)
        else:
            return 99

    def on_fetch_bg(self, layer=None, bbox=None, check_redraw=True):
        # TODO support providing a bbox as extent?
        if layer is None:
            layer = self.layer
        try:
            if check_redraw and not self.redraw_required(layer):
                return

            # check if the data_manager has no data assigned
            if self.x0 is None and self.m.coll is not None:
                self._remove_existing_coll()
                return False

            props = self.get_props()
            if props is None or props["x0"] is None or props["y0"] is None:
                # fail-fast in case the data is completely outside the extent
                return

            s = self._get_datasize(**props)
            self._print_datasize_warnings(s)

            # stop here in case we are dealing with a pick-only dataset
            if self._only_pick:
                return

            if props["x0"].size < 1 or props["y0"].size < 1:
                # keep original data if too low amount of data is attempted
                # to be plotted
                return

            # remove previous collection from the map
            self._remove_existing_coll()
            # draw the new collection
            coll = self.m._get_coll(props, **self.m._coll_kwargs)
            coll.set_clim(self.m._vmin, self.m._vmax)

            coll.set_label("Dataset " f"({self.m.shape.name}  |  {self.z_data.shape})")

            if self.m.shape.name not in ["scatter_points", "contour"]:
                # avoid use "autolim=True" since it can cause problems in
                # case the data-limits are infinite (e.g. for projected
                # datasets containing points outside the used projection)
                # the extent is set by calling "._set_lims()" in `m.plot_map()`
                self.m.ax.add_collection(coll, autolim=False)

            if self.m._coll_dynamic:
                self.m.BM.add_artist(coll, self.layer)
            else:
                self.m.BM.add_bg_artist(coll, self.layer)

            self.m._coll = coll

            # if required, add masked points indicators
            if self._indicate_masked_points is not False:
                if isinstance(self._indicate_masked_points, dict):
                    self.indicate_masked_points(**self._indicate_masked_points)
                else:
                    self.indicate_masked_points()

            # execute actions that should be performed after the data
            # has been updated.
            # this is used in case pick-callbacks are assigned
            # before a layer has been fetched (e.g. before m.coll is defined)
            # (=lazily initialize the picker when the layer is fetched)
            while len(self._on_next_fetch) > 0:
                self._on_next_fetch.pop(-1)()

            self.m.cb.pick._set_artist(coll)

        except Exception as ex:
            _log.exception(
                f"EOmaps: Unable to plot the data for the layer '{layer}'!",
                exc_info=_log.getEffectiveLevel() <= logging.DEBUG,
            )

    def data_in_extent(self, extent):
        # check if the data extent collides with the map extent
        x0, x1, y0, y1 = extent
        if x0 > self._x0max or self._x0min > x1:
            return False
        if y0 > self._y0max or self._y0min > y1:
            return False
        return True

    def full_data_in_extent(self, extent):
        # check if the map extent fully contains the data extent
        x0, x1, y0, y1 = extent
        if (x0 < self._x0min and x1 > self._x0max) and (
            y0 < self._y0min and y1 > self._y0max
        ):
            return True
        return False

    def _get_q(self, *args, **kwargs):
        # identify the data mask
        x0, x1, y0, y1 = self.current_extent

        if self._radius_margin is not None:
            dx, dy = self._radius_margin
        else:
            # fallback to using a margin of 10% of the data-extent
            dx = (self._x0max - self._x0min) * self._extent_margin_factor
            dy = (self._y0max - self._y0min) * self._extent_margin_factor

        x0 = x0 - dx
        x1 = x1 + dx
        y0 = y0 - dy
        y1 = y1 + dy

        # fail-fast in case the extent is completely outside the region
        if not self.data_in_extent((x0, x1, y0, y1)):
            self.last_extent = (x0, x1, y0, y1)
            self._current_data = None
            return None, None, None

        # in case the extent is larger than the full data,
        # there is no need to query!
        if self.full_data_in_extent((x0, x1, y0, y1)):
            self.last_extent = self.current_extent
            self._current_data = {**self._all_data}
            return True, True, True

        # get mask
        if self.x0_1D is not None:
            # in case 1D coordinates and 2D data is provided, query on 1D vectors!
            q = None
            qx = (self.x0_1D >= x0) & (self.x0_1D <= x1)
            qy = (self.y0_1D >= y0) & (self.y0_1D <= y1)
        else:
            # query extent
            q = ((self.x0 >= x0) & (self.x0 <= x1)) & (
                (self.y0 >= y0) & (self.y0 <= y1)
            )

            if len(q.shape) == 2:
                # in case coordinates are 2D, query the relevant 2D array
                qx = q.any(axis=0)
                qy = q.any(axis=1)
            else:
                qx = None
                qy = None

        return q, qx, qy

    def _estimate_slice_blocksize(self, qx, qy):
        if qx is True and qy is True:
            x0, x1 = 0, len(self.x0)
            y0, y1 = 0, len(self.y0)
        else:
            qx = qx.squeeze()
            qy = qy.squeeze()

            # find the first and last indexes of the x-y-mask to select values
            # (slicing is much faster than boolean indexing for large arrays!)
            x0 = np.argmax(qx)
            x1 = len(qx) - np.argmax(qx[::-1])
            y0 = np.argmax(qy)
            y1 = len(qy) - np.argmax(qy[::-1])

            if x1 == -1:
                x1 = len(qx)
            if y1 == -1:
                y1 = len(qy)

        maxsize = getattr(self.m.shape, "_maxsize", None)
        if maxsize is not None:
            # estimate a suitable blocksize based on the max. data size
            # in x- or y- direction
            d = max((x1 - x0), (y1 - y0))
            bs = int(d / np.sqrt(maxsize))

            if bs > 0:  # to avoid divided by zero errors in %
                x0 = x0 - x0 % bs
                y0 = y0 - y0 % bs
                if x0 < 0:
                    x1 = x1 - x0
                    x0 = 0
                if y0 < 0:
                    y1 = y1 - y0
                    y0 = 0

                x1 = x1 - x1 % bs + bs
                y1 = y1 - y1 % bs + bs
        else:
            bs = None

        return (x0, x1, y0, y1), bs

    def _select_vals(self, val, qs, slices=None):
        # select data based on currently visible region
        q, qx, qy = qs
        if all(i is True for i in (q, qx, qy)):
            ret = val
        elif all(i is None for i in (q, qx, qy)):
            ret = None
        else:
            val = np.asanyarray(val)

            if (
                len(val.shape) == 2
                and qx is not None
                and qy is not None
                and slices is not None
            ):
                (x0, x1, y0, y1) = slices
                ret = val[y0:y1, x0:x1]
            else:
                if q is not None:
                    ret = val.ravel()[q.squeeze()]
                else:
                    ret = val

            if self.m.shape.name not in ["raster", "shade_raster", "contour"]:
                ret = ret.ravel()

        return ret

    # def _select_ids(self, qs):
    #     # identify ids based on currently visible region
    #     q, qx, qy = qs

    #     if all(i is None for i in (q, qx, qy)):
    #         return self.ids

    #     if q is None or len(q.shape) == 2:
    #         # select columns that contain at least one value
    #         wx, wy = np.where(qx)[0], np.where(qy)[0]
    #         ind = np.ravel_multi_index(np.meshgrid(wx, wy), (qx.size, qy.size)).ravel()

    #         if isinstance(self.ids, (list, range)):
    #             idq = [self.ids[i] for i in ind]
    #             if len(idq) == 1:
    #                 idq = idq[0]
    #         elif isinstance(self.ids, np.ndarray):
    #             idq = self.ids.flat[ind]
    #         else:
    #             idq = None
    #     else:
    #         ind = np.where(q)[0]

    #         if isinstance(self.ids, (list, range)):
    #             idq = [self.ids[i] for i in ind]
    #             if len(idq) == 1:
    #                 idq = idq[0]
    #         elif isinstance(self.ids, np.ndarray):
    #             idq = self.ids.flat[ind]
    #         else:
    #             idq = None

    #     return idq

    def _block_view(self, a, blockshape):
        """
        Return a view of an array in the desired block-structure.

        (fast and without creating a copy!)

        If the array-size cannot be broadcasted to the block-shape, boundary-values
        are dropped!

        This function is largely adapted from
        https://github.com/ilastik/ilastik/blob/main/lazyflow/utility/blockwise_view.py

        Parameters
        ----------
        a : numpy.array
            The input array.
        blockshape : tuple
            The desired block shape.
        Returns
        -------
        view : np.array
            A view of the input-array with the desired block-shape.

        """
        blockshape = tuple(blockshape)
        outershape = tuple(np.array(a.shape) // blockshape)
        view_shape = outershape + blockshape

        # make sure the blockshape can always be applied
        # (drop boundary pixels from left and right until blockshape is possible)
        mods = np.mod(a.shape, blockshape)
        starts, stops = mods // 2 + mods % 2, mods // 2

        slices = []
        for i, (sta, sto) in enumerate(zip(starts, stops)):
            if sto > 0:
                s = slice(sta, -sto)
            else:
                s = slice(sta, a.shape[i])

            slices.append(s)

        if len(slices) == 2:
            a = a[slices[0], slices[1]]
        else:
            a = a[slices[0]]

        # a = a[*slices]   # TODO check why pre-commit can't resolve this line!!

        # inner strides: strides within each block (same as original array)
        intra_block_strides = a.strides

        # outer strides: strides from one block to another
        inter_block_strides = tuple(a.strides * np.array(blockshape))

        # This is where the magic happens.
        # Generate a view with our new strides (outer+inner).
        view = np.lib.stride_tricks.as_strided(
            a, shape=view_shape, strides=(inter_block_strides + intra_block_strides)
        )

        if isinstance(a, np.ma.masked_array):
            blockmask = self._block_view(a.mask, blockshape)
            view = np.ma.masked_array(view, blockmask, copy=False)

        return view

    def _zoom(self, blocksize):
        method = getattr(self.m.shape, "_aggregator", "first")
        maxsize = getattr(self.m.shape, "_maxsize", None)
        order = getattr(self.m.shape, "_interp_order", 0)
        valid_fraction = getattr(self.m.shape, "_valid_fraction", 0)

        # only zoom if the shape provides a _maxsize attribute
        if self._current_data["z_data"] is None or maxsize is None:
            return
        elif self._current_data["z_data"].size < maxsize:
            return

        if method == "spline":
            return self._zoom_scipy(maxsize, order)
        else:
            return self._zoom_block(maxsize, method, valid_fraction, blocksize)

    def _fast_block_metric(self, blocks, bs, calc_mean=True):
        """
        Fast way to calculate sum/mean of blocks using numpy's einsum.

        NOTE: this method does NOT check for overflow errors and can cause problems
        if the sum of the values in a block is larger than the max. number possible
        for the dtype of the input-array!
        """
        if isinstance(blocks, np.ma.masked_array):
            valid_fraction = 0.5

            # make sure we don't count masked values
            # (avoid using .filled since it creates a copy!)
            blocks.data[blocks.mask] = 0

            if calc_mean:
                data = np.einsum("ijkl->ij", blocks.data) / np.prod(bs)
            else:
                data = np.einsum("ijkl->ij", blocks.data)

            if valid_fraction == 0:
                mask = np.einsum("ijkl->ij", blocks.mask)
            else:
                # avoid einsum here to avoid casting the boolean array to int
                nmask = np.count_nonzero(blocks.mask, axis=(-1, -2))
                mask = nmask > valid_fraction * np.prod(bs)

            data = np.ma.masked_array(data, mask)
        else:
            if calc_mean:
                data = np.einsum("ijkl->ij", blocks) / np.prod(bs)
            else:
                data = np.einsum("ijkl->ij", blocks)

        return data

    def _zoom_block(self, maxsize, method, valid_fraction, blocksize):
        # zoom data based on a given blocksize
        bs = (blocksize, blocksize)

        zdata = self._current_data["z_data"]
        blocks = self._block_view(zdata, bs)

        if method == "first":
            self._current_data["z_data"] = blocks[:, :, 0, 0]
        elif method == "last":
            self._current_data["z_data"] = blocks[:, :, -1, -1]
        elif method == "min":
            self._current_data["z_data"] = blocks.min(axis=(-1, -2))
        elif method == "max":
            self._current_data["z_data"] = blocks.max(axis=(-1, -2))
        elif method == "mean":
            self._current_data["z_data"] = blocks.mean(axis=(-1, -2))
        elif method == "std":
            self._current_data["z_data"] = blocks.std(axis=(-1, -2))
        elif method == "sum":
            self._current_data["z_data"] = blocks.sum(axis=(-1, -2))
        elif method == "median":
            self._current_data["z_data"] = np.median(blocks, axis=(-1, -2))
        elif method == "mode":
            from scipy.stats import mode

            out, counts = mode(blocks, axis=(-1, -2), nan_policy="propagate")
            self._current_data["z_data"] = out
        elif method == "fast_sum":
            self._current_data["z_data"] = self._fast_block_metric(blocks, bs, False)
        elif method == "fast_mean":
            self._current_data["z_data"] = self._fast_block_metric(blocks, bs, True)
        else:
            raise TypeError(
                f"EOmaps: The method {method} is not a valid aggregation-method!\n"
                "Use one of:\n"
                "['first', 'last', 'min', 'max', 'mean', 'std', 'median', "
                "'fast_mean', 'fast_sum', 'spline']"
            )

        # aggregate coordinates
        for key, val in self._current_data.items():
            if key.startswith("x") or key.startswith("y"):
                self._current_data[key] = np.einsum(
                    "ijkl->ij", self._block_view(val, bs)
                ) / np.prod(bs)

                # self._current_data[key] = self._block_view(val, bs).mean(axis=(-1, -2))

    def _zoom_scipy(self, maxsize, order):
        from scipy.ndimage import zoom

        # estimate scale to approx. 2D data size
        scale = np.sqrt(maxsize / self._current_data["z_data"].size)
        zoomargs = dict(zoom=scale, order=order, mode="reflect", cval=np.nan)

        for key, val in self._current_data.items():
            if key == "ids":
                continue
            if isinstance(val, np.ndarray) and len(val.shape) == 2:
                self._current_data[key] = zoom(val, **zoomargs)
            else:
                self._current_data[key] = zoom(val, **zoomargs)

    def get_props(self, *args, **kwargs):
        # get the masks to select the currently visible data
        # (qs = [<2d mask>, <1d x mask>, <1d y mask>]
        qs = self._get_q()

        # estimate slices (and optional blocksize if requred) for 2D data
        if len(self.z_data.shape) == 2 and all(i is not None for i in qs[1:]):
            slices, blocksize = self._estimate_slice_blocksize(*qs[1:])
        else:
            slices, blocksize = None, None

        # remember last selection and slices (required in case explicit
        # colors are provided since they must be selected accordingly)
        self._last_qs = qs
        self._last_slices = slices

        self._current_data = dict(
            xorig=self._select_vals(self.xorig, qs, slices),
            yorig=self._select_vals(self.yorig, qs, slices),
            x0=self._select_vals(self.x0, qs, slices),
            y0=self._select_vals(self.y0, qs, slices),
            z_data=self._select_vals(self.z_data, qs, slices),
            # ids=self._select_ids(),
        )
        self.last_extent = self.current_extent

        self._zoom(blocksize)
        return self._current_data

    def _get_datasize(self, z_data, x0, y0, **kwargs):
        # if a dataset is provided, use it to identify the data-size
        if z_data is not None:
            return np.size(z_data)

        sx = np.size(x0)

        if len(x0.shape) == 2:
            return sx

        sy = np.size(y0)

        # TODO add better treatment for 1D2D datasets with data=None
        if len(x0.shape) == 1 and len(y0.shape) == 1:
            if sx == sy:
                return sx
            else:
                return sx * sy

        return 99

    def _print_datasize_warnings(self, s):
        if s < 1e5:
            return

        name = self.m.shape.name

        if name in ["raster"]:
            if s < 2e6:
                return
            else:
                txt = f"EOmaps: Plotting {s:.1E} points as {self.m.shape.name}"

            if s < 5e6:
                _log.info(f"{txt}...\n       this might take a few seconds...")
            elif s < 2e7:
                _log.info(f"{txt}...\n       this might take some time...")
            else:
                _log.info(f"{txt}...\n       this might take A VERY LONG TIME❗❗")
        else:
            if name in ["rectangles", "ellipses", "geod_circles"]:
                txt = f"EOmaps: Plotting {s:.1E} {self.m.shape.name}"
            elif name in ["voronoi_diagram", "delaunay_triangulation"]:
                txt = f"EOmaps: Plotting a {self.m.shape.name} of {s:.1E}"
            else:
                return

            if s < 5e5:
                _log.info(f"{txt}...\n       this might take a few seconds...")
            elif s < 1e6:
                _log.info(f"{txt}...\n       this might take some time...")
            else:
                _log.info(f"{txt}...\n       this might take A VERY LONG TIME❗❗")

    def _get_xy_from_index(self, ind, reprojected=False):
        """
        Get x and y coordinates from a list of numerical data indexes

        Parameters
        ----------
        ind : array-like
            a list of indexes
        reprojected : bool, optional
            - if True, the coordinates are returned in the plot-crs.
            - if False, the input coordinates are returned
            The default is False.

        Returns
        -------
        (x, y) : tuple of x- and y- coordinate arrays

        """
        if self.x0_1D is not None:
            # TODO check treatment of transposed data
            # unravel indices since data is 2D
            yind, xind = np.unravel_index(ind, (self.y0_1D.size, self.x0_1D.size))
            # 1D coordinates are only possible if input crs == plot crs!
            return self.x0_1D[xind], self.y0_1D[yind]
        else:
            xind = yind = ind

        if reprojected:
            return (
                self.x0.flat[xind],
                self.y0.flat[yind],
            )
        else:
            return (
                self.xorig.flat[xind],
                self.yorig.flat[yind],
            )

    def _get_val_from_index(self, ind):
        """
        Get x and y coordinates from a list of numerical data indexes

        Parameters
        ----------
        ind : array-like
            a list of indexes

        Returns
        -------
        val : array of the corresponding data values

        """

        # TODO
        # Note datashader transposes the data by itself if 1D coords are provided!
        # (to pick the correct value, we need to pick the transposed one!)

        if self.m.shape.name == "shade_raster" and self.x0_1D is not None:
            val = self.z_data.T.flat[ind]
        else:
            val = self.z_data.flat[ind]

        return val

    def _get_id_from_index(self, ind):
        """
        Identify the ID from a 1D list or range object or a np.ndarray
        (to avoid very large numpy-arrays if no explicit IDs are provided)

        Parameters
        ----------
        ind : int or list of int
            The index of the flattened array.

        Returns
        -------
        val : array of the correspondint IDs

        """
        ids = self.ids
        if isinstance(ids, (list, range)):
            ind = np.atleast_1d(ind).tolist()  # to treat numbers and lists
            ID = np.array([ids[i] for i in ind])
            if len(ID) == 1:
                ID = ID[0]
        elif isinstance(ids, np.ndarray):
            ID = ids.flat[ind]
        else:
            ID = None
        return ID

    def _get_xy_from_ID(self, ID, reprojected=False):
        """
        Get x and y coordinates from a list of data IDs

        Parameters
        ----------
        ID : single ID or list of IDs
            The IDs to search for.

        Returns
        -------
        (x, y) : a tuple of x- and y- coordinate arrays
        """
        ids = self.ids

        # find numerical index from ID
        ID = np.atleast_1d(ID)
        if isinstance(ids, range):
            # if "ids" is range-like, so is "ind", therefore we can simply
            # select the values.
            inds = np.array([ids[i] for i in ID])
        if isinstance(ids, list):
            # for lists, using .index to identify the index
            inds = np.array([ids.index(i) for i in ID])
        elif isinstance(ids, np.ndarray):
            inds = np.flatnonzero(np.isin(ids, ID))
        else:
            inds = None

        return self._get_xy_from_index(inds, reprojected=reprojected)

    def cleanup(self):
        self.cleanup_callbacks()

        self._all_data.clear()
        self._current_data.clear()
        self.last_extent = None

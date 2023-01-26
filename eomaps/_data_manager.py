import numpy as np


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

    def set_props(
        self,
        layer,
        assume_sorted=True,
        update_coll_on_fetch=True,
        indicate_masked_points=True,
    ):
        self._all_data = self.m._prepare_data(assume_sorted=assume_sorted)
        self._indicate_masked_points = indicate_masked_points
        self.layer = layer

        if len(self.x0) == 0:
            print("EOmaps: There is no data to plot")
            return

        self._x0min, self._x0max = np.nanmin(self.x0), np.nanmax(self.x0)
        self._y0min, self._y0max = np.nanmin(self.y0), np.nanmax(self.y0)

        # estimate the radius (used as margin on data selection)
        self._r = self.m._shapes._estimate_radius(self.m, "out")
        if self._r is not None and all(np.isfinite(i) for i in self._r):
            self._radius_margin = [i * self._radius_margin_factor for i in self._r]
        else:
            self._radius_margin = None

        if update_coll_on_fetch:
            # attach a hook that updates the collection whenever a new
            # background is fetched
            # ("shade" shapes take care about updating the data themselves!)
            if self.on_fetch_bg not in self.m.BM._before_fetch_bg_actions:
                self.m.BM._before_fetch_bg_actions.append(self.on_fetch_bg)

    @property
    def current_extent(self):
        return self.m.ax.get_extent(self.m.ax.projection)

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

        return (x0, x1, y0, y1)

    def indicate_masked_points(self, radius=1.0, **kwargs):
        # remove previous mask artist
        if self._masked_points_artist is not None:
            try:
                self.m.BM.remove_bg_artist(self._masked_points_artist)
                self._masked_points_artist.remove()
                self._masked_points_artist = None
            except Exception as ex:
                print(ex)

        if not hasattr(self.m, "_data_mask") or self.m._data_mask is None:
            return

        mask = self.m._data_mask.ravel()
        npts = np.count_nonzero(mask)
        if npts == 0:
            return

        if npts > 1e5:
            print(
                "EOmaps: There are more than 100 000 masked points! "
                "... indicating masked points will affect performance!"
            )

        kwargs.setdefault("ec", "r")
        kwargs.setdefault("lw", 0.25)

        self._masked_points_artist = self.m.ax.scatter(
            self._current_data["x0"].ravel()[~mask],
            self._current_data["y0"].ravel()[~mask],
            cmap=getattr(self.m, "_cbcmap", "Reds"),
            norm=getattr(self.m, "_norm", None),
            c=self._current_data["z_data"].ravel()[~mask],
            **kwargs,
        )

        self.m.BM.add_bg_artist(self._masked_points_artist, layer=self.layer)

    def on_fetch_bg(self, layer, bbox=None):
        try:
            # TODO support providing a bbox as extent

            layer_requested = set(self.layer.split("|")).issubset(set(layer.split("|")))

            if self.layer != "all" and not layer_requested:
                return

            if not hasattr(self, "x0"):
                # self.set_props()
                return

            if self.extent_changed or self.m.coll is None:
                props = self.get_props()
                if props is None:
                    # fail-fast in case the data is completely outside the extent
                    return
                # update the number of immediate points calculated for plot-shapes
                s = self._get_datasize(props)
                self._print_datasize_warnings(s)
                self._set_n(s)

                if props["x0"].size < 1 or props["y0"].size < 1:
                    # keep original data if too low amount of data is attempted
                    # to be plotted

                    # make the collection invisible to avoid plotting it again
                    self.m.coll.set_visible(False)
                    self.m.coll.set_animated(True)
                    return

                coll = self.m._get_coll(props, **self.m._coll_kwargs)
                coll.set_clim(self.m._vmin, self.m._vmax)

                if self.m.shape.name != "scatter_points":
                    # avoid use "autolim=True" since it can cause problems in
                    # case the data-limits are infinite (e.g. for projected
                    # datasets containing points outside the used projection)
                    self.m.ax.add_collection(coll, autolim=False)

                # remove previous collection from the map
                if self.m.coll is not None:
                    try:
                        if self.m._coll_dynamic:
                            self.m.BM.remove_artist(self.m._coll)
                        else:
                            self.m.BM.remove_bg_artist(self.m._coll)

                        self.m._coll.remove()
                    except Exception as ex:
                        print(ex)

                if self.m._coll_dynamic:
                    self.m.BM.add_artist(coll, self.layer)
                else:
                    self.m.BM.add_bg_artist(coll, self.layer)

                self.m._coll = coll

                if self._indicate_masked_points:
                    self.indicate_masked_points()

                # this is used in _cb_container when adding callbacks
                # before a layer has been fetched (e.g. before m.coll is defined)
                # (=lazily initialize the picker when the layer is fetched)
                while len(self._on_next_fetch) > 0:
                    self._on_next_fetch.pop(-1)()

                self.m.cb.pick._set_artist(coll)

        except Exception as ex:
            print(
                f"EOmaps: Unable to plot the data for the layer '{layer}' !"
                f"\n        {ex}"
            )

    def data_in_extent(self, extent):
        x0, x1, y0, y1 = extent
        if x0 > self._x0max or self._x0min > x1:
            return False
        if y0 > self._y0max or self._y0min > y1:
            return False
        return True

    def get_props(self, *args, **kwargs):
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
            print("not in rect")
            self.last_extent = (x0, x1, y0, y1)
            self._current_data = None
            return

        # get mask
        q = ((self.x0 >= x0) & (self.x0 <= x1)) & ((self.y0 >= y0) & (self.y0 <= y1))

        if len(q.shape) == 2:
            # select columns that contain at least one value
            qx = q.any(axis=0)
            qy = q.any(axis=1)
            wx, wy = np.where(qx)[0], np.where(qy)[0]
            ind = np.ravel_multi_index(np.meshgrid(wx, wy), (qx.size, qy.size)).ravel()

            if isinstance(self.ids, (list, range)):
                idq = [self.ids[i] for i in ind]
                if len(idq) == 1:
                    idq = idq[0]
            elif isinstance(self.ids, np.ndarray):
                idq = self.ids.flat[ind]
            else:
                idq = None
        else:
            ind = np.where(q)[0]

            if isinstance(self.ids, (list, range)):
                idq = [self.ids[i] for i in ind]
                if len(idq) == 1:
                    idq = idq[0]
            elif isinstance(self.ids, np.ndarray):
                idq = self.ids.flat[ind]
            else:
                idq = None

        props = dict(
            xorig=self.xorig[qy][:, qx]
            if len(self.xorig.shape) == 2
            else self.xorig[q],
            yorig=self.yorig[qy][:, qx]
            if len(self.yorig.shape) == 2
            else self.yorig[q],
            x0=self.x0[qy][:, qx] if len(self.x0.shape) == 2 else self.x0[q],
            y0=self.y0[qy][:, qx] if len(self.y0.shape) == 2 else self.y0[q],
            z_data=self.z_data[qy][:, qx]
            if len(self.z_data.shape) == 2
            else self.z_data[q],
            ids=idq,
        )
        self.last_extent = self.current_extent
        self._current_data = props

        return props

    def _get_datasize(self, props):
        sx = np.size(props["x0"])
        sy = np.size(props["y0"])

        if self.m._1D2D:
            s = sx * sy
        else:
            s = max(sx, sy)

        return s

    def _set_n(self, s):
        if s < 10:
            n = 100
        elif s < 100:
            n = 75
        elif s < 1000:
            n = 50
        elif s < 10000:
            n = 20
        else:
            n = 12

        self.m.shape.n = n

    def _print_datasize_warnings(self, s):
        if s < 1e5:
            return

        name = self.m.shape.name

        if name in ["raster"]:
            if s < 1e6:
                return
            else:
                txt = f"EOmaps: Plotting {s:.1E} points as {self.m.shape.name}"

            if s < 5e6:
                print(f"{txt}...\n       this might take a few seconds...")
            elif s < 2e7:
                print(f"{txt}...\n       this might take some time...")
            else:
                print(f"{txt}...\n       this might take A VERY LONG TIME❗❗")
        else:
            if name in ["rectangles", "ellipses", "geod_circles"]:
                txt = f"EOmaps: Plotting {s:.1E} {self.m.shape.name}"
            elif name in ["voronoi_diagram", "delaunay_triangulation"]:
                txt = f"EOmaps: Plotting a {self.m.shape.name} of {s:.1E}"
            else:
                return

            if s < 5e5:
                print(f"{txt}...\n       this might take a few seconds...")
            elif s < 1e6:
                print(f"{txt}...\n       this might take some time...")
            else:
                print(f"{txt}...\n       this might take A VERY LONG TIME❗❗")

    def cleanup(self):
        self._all_data.clear()
        self._current_data.clear()
        self.last_extent = None

        if self.on_fetch_bg in self.m.BM._before_fetch_bg_actions:
            self.m.BM._before_fetch_bg_actions.remove(self.on_fetch_bg)

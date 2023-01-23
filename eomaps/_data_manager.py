import numpy as np


class DataManager:
    def __init__(self, m):
        self.m = m
        self.last_extent = None

    def set_props(self):
        assume_sorted = True

        props = self.m._prepare_data(assume_sorted=assume_sorted)
        if len(props["z_data"]) == 0:
            print("EOmaps: there was no data to plot")
            return

        self.x0 = props["x0"]
        self.y0 = props["y0"]
        self.xorig = props["xorig"]
        self.yorig = props["yorig"]
        self.ids = props["ids"]
        self.z_data = props["z_data"]

        # self.last_extent = self.current_extent

        # self._cid_xlim = self.m.ax.callbacks.connect(
        #     "xlim_changed", self.on_extent_changed
        # )

        # self._cid_xlim = self.m.f.canvas.mpl_connect(
        #     "draw_event", self.on_extent_changed
        # )

        # self.m._prepare_data = self.get_props

        self.m.BM._before_fetch_bg_actions = [self.on_extent_changed]

    @property
    def current_extent(self):
        return self.m.ax.get_extent()

    @property
    def extent_changed(self):
        return not self.current_extent == self.last_extent

    def on_extent_changed(self, layer, bbox=None):

        # TODO make sure m.coll is always on m.layer!
        if layer != self.m.layer:
            return

        if (getattr(self.m, "coll", None) is None) or (
            getattr(self.m.coll, "figure", None) is not self.m.f
        ):
            return

        if not hasattr(self, "x0"):
            # self.set_props()
            return

        if self.last_extent is None:
            return

        if self.extent_changed and self.last_extent:
            props = self.get_props()

            if props["x0"].size < 5 and props["y0"].size < 5:
                old_n = getattr(self.m.shape, "n", None)

                if old_n is None or old_n == self.m.shape.n:
                    return
                else:
                    # redraw the shape with the new n
                    props = self.m._props

            coll = self.m._get_coll(props, **self.m._coll_kwargs)
            coll.set_clim(self.m._vmin, self.m._vmax)

            if self.m.shape.name != "scatter_points":
                self.m.ax.add_collection(coll, autolim=self.m._set_extent)

            try:
                if self.m._coll_dynamic:
                    self.m.BM.remove_artist(self.m._coll)
                else:
                    self.m.BM.remove_bg_artist(self.m._coll)

                self.m._coll.remove()
            except Exception as ex:
                print(ex)

            if self.m._coll_dynamic:
                self.m.BM.add_artist(coll, self.m.layer)
            else:
                self.m.BM.add_bg_artist(coll, self.m.layer)

            self.m._coll = coll
            self.m.cb.pick._set_artist(coll)

    def get_props(self, *args, **kwargs):

        if not hasattr(self, "x0"):
            self.set_props()
            # return

        x0, x1, y0, y1 = self.current_extent

        dx = (x1 - x0) / 5
        dy = (y1 - y0) / 5

        x0 = x0 - dx
        x1 = x1 + dx
        y0 = y0 - dy
        y1 = y1 + dy

        # get mask
        q = ((self.x0 >= x0) & (self.x0 <= x1)) & ((self.y0 >= y0) & (self.y0 <= y1))

        # TODO fix IDs
        if len(q.shape) == 2:
            qx = q.any(axis=0)
            qy = q.any(axis=1)

            wx, wy = np.where(qx)[0], np.where(qy)[0]
            ind = np.ravel_multi_index(
                np.meshgrid(wx, wy), (qx.size, qy.size)
            ).T.ravel()

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

        self.m._xshape = props["x0"].shape
        self.m._yshape = props["y0"].shape
        self.m._zshape = props["z_data"].shape
        self._set_n(props)

        self.m._props = props
        return props

    def _get_datasize(self, props):
        sx = np.size(props["x0"])
        sy = np.size(props["y0"])

        if self.m._1D2D:
            s = sx * sy
        else:
            s = max(sx, sy)
        return s

    def _set_n(self, props):
        s = self._get_datasize(props)

        if s < 10:
            n = 500
        elif s < 100:
            n = 100
        elif s < 1000:
            n = 50
        elif s < 10000:
            n = 20
        else:
            n = 12

        self.m.shape.n = n

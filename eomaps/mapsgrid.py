from functools import wraps, lru_cache

import numpy as np
from matplotlib.gridspec import GridSpec
import matplotlib.pyplot as plt

from ._shapes import shapes
from .eomaps import Maps

from .ne_features import NaturalEarth_features

try:
    from ._webmap_containers import wms_container
except ImportError:
    wms_container = None


class MapsGrid:
    """
    Initialize a grid of Maps objects

    Parameters
    ----------
    r : int, optional
        The number of rows. The default is 2.
    c : int, optional
        The number of columns. The default is 2.
    crs : int or a cartopy-projection, optional
        The projection that will be assigned to all Maps objects.
        (you can still change the projection of individual Maps objects later!)
        See the doc of "Maps" for details.
        The default is 4326.
    m_inits : dict, optional
        A dictionary that is used to customize the initialization the Maps-objects.

        The keys of the dictionaries are used as names for the Maps-objects,
        (accessible via `mgrid.m_<name>` or `mgrid[m_<name>]`) and the values are used to
        identify the position of the axes in the grid.

        Possible values are:
        - a tuple of (row, col)
        - an integer representing (row + col)

        Note: If either `m_inits` or `ax_inits` is provided, ONLY objects with the
        specified properties are initialized!

        The default is None in which case a unique Maps-object will be created
        for each grid-cell (accessible via `mgrid.m_<row>_<col>`)
    ax_inits : dict, optional
        Completely similar to `m_inits` but instead of `Maps` objects, ordinary
        matplotlib axes will be initialized. They are accessible via `mg.ax_<name>`.

        Note: If you iterate over the MapsGrid object, ONLY the initialized Maps
        objects will be returned!
    figsize : (float, float)
        The width and height of the figure.
    layer : int or str
        The default layer to assign to all Maps-objects of the grid.
        The default is 0.
    f : matplotlib.Figure or None
        The matplotlib figure to use. If None, a new figure will be created.
        The default is None.
    kwargs
        Additional keyword-arguments passed to the `matplotlib.gridspec.GridSpec()`
        function that is used to initialize the grid.

    Attributes
    ----------
    f : matplotlib.figure
        The matplotlib figure object
    gridspec : matplotlib.GridSpec
        The matplotlib GridSpec instance used to initialize the axes.
    m_<identifier> : eomaps.Maps objects
        The individual Maps-objects can be accessed via `mgrid.m_<identifier>`
        The identifiers are hereby `<row>_<col>` or the keys of the `m_inits`
        dictionary (if provided)
    ax_<identifier> : matplotlib.axes
        The individual (ordinary) matplotlib axes can be accessed via
        `mgrid.ax_<identifier>`. The identifiers are hereby the keys of the
        `ax_inits` dictionary (if provided).
        Note: if `ax_inits` is not specified, NO ordinary axes will be created!


    Methods
    -------
    join_limits :
        join the axis-limits of maps that share the same projection
    share_click_events :
        share click-callback events between the Maps-objects
    share_pick_events :
        share pick-callback events between the Maps-objects
    create_axes :
        create a new (ordinary) matplotlib axes
    add_<...> :
        call the underlying `add_<...>` method on all Maps-objects of the grid
    set_<...> :
        set the corresponding property on all Maps-objects of the grid
    subplots_adjust :
        Dynamically adjust the layout of the subplots, e.g:

        >>> mg.subplots_adjust(left=0.1, right=0.9,
        >>>                    top=0.8, bottom=0.1,
        >>>                    wspace=0.05, hspace=0.25)

    Examples
    --------
    To initialize a 2 by 2 grid with a large map on top, a small map
    on the bottom-left and an ordinary matplotlib plot on the bottom-right, use:

    >>> m_inits = dict(top = (0, slice(0, 2)),
    >>>                bottom_left=(1, 0))
    >>> ax_inits = dict(bottom_right=(1, 1))

    >>> mg = MapsGrid(2, 2, m_inits=m_inits, ax_inits=ax_inits)
    >>> mg.m_top.plot_map()
    >>> mg.m_bottom_left.plot_map()
    >>> mg.ax_bottom_right.plot([1,2,3])

    Returns
    -------
    eomaps.MapsGrid
        Accessor to the Maps objects "m_{row}_{column}".

    Notes
    -----

    - To perform actions on all Maps-objects of the grid, simply iterate over
      the MapsGrid object!
    """

    def __init__(
        self,
        r=2,
        c=2,
        crs=None,
        m_inits=None,
        ax_inits=None,
        figsize=None,
        layer="base",
        f=None,
        **kwargs,
    ):

        self._Maps = []
        self._names = dict()

        if wms_container is not None:
            self._wms_container = wms_container(self)

        gskwargs = dict(bottom=0.01, top=0.99, left=0.01, right=0.99)
        gskwargs.update(kwargs)
        self.gridspec = GridSpec(nrows=r, ncols=c, **gskwargs)

        if m_inits is None and ax_inits is None:
            if isinstance(crs, list):
                crs = np.array(crs).reshape((r, c))
            else:
                crs = np.broadcast_to(crs, (r, c))

            self._custom_init = False
            for i in range(r):
                for j in range(c):
                    crsij = crs[i, j]
                    if isinstance(crsij, np.generic):
                        crsij = crsij.item()

                    if i == 0 and j == 0:
                        # use crs[i, j].item() to convert to native python-types
                        # (instead of numpy-dtypes)  ... check numpy.ndarray.item
                        mij = Maps(
                            crs=crsij,
                            ax=self.gridspec[0, 0],
                            figsize=figsize,
                            layer=layer,
                            f=f,
                        )
                        mij.ax.set_label("mg_map_0_0")
                        self.parent = mij
                    else:
                        mij = Maps(
                            crs=crsij,
                            f=self.parent.f,
                            ax=self.gridspec[i, j],
                            layer=layer,
                        )
                        mij.ax.set_label(f"mg_map_{i}_{j}")
                    self._Maps.append(mij)
                    name = f"{i}_{j}"
                    self._names.setdefault("Maps", []).append(name)
                    setattr(self, "m_" + name, mij)
        else:
            self._custom_init = True
            if m_inits is not None:
                if not isinstance(crs, dict):
                    if isinstance(crs, np.generic):
                        crs = crs.item()

                    crs = {key: crs for key in m_inits}

                assert self._test_unique_str_keys(
                    m_inits
                ), "EOmaps: there are duplicated keys in m_inits!"

                for i, [key, val] in enumerate(m_inits.items()):
                    if ax_inits is not None:
                        q = set(m_inits).intersection(set(ax_inits))
                        assert (
                            len(q) == 0
                        ), f"You cannot provide duplicate keys! Check: {q}"

                    if i == 0:
                        mi = Maps(
                            crs=crs[key],
                            ax=self.gridspec[val],
                            figsize=figsize,
                            layer=layer,
                            f=f,
                        )
                        mi.ax.set_label(f"mg_map_{key}")
                        self.parent = mi
                    else:
                        mi = Maps(
                            crs=crs[key],
                            ax=self.gridspec[val],
                            layer=layer,
                            f=self.parent.f,
                        )
                        mi.ax.set_label(f"mg_map_{key}")

                    name = str(key)
                    self._names.setdefault("Maps", []).append(name)

                    self._Maps.append(mi)
                    setattr(self, f"m_{name}", mi)

            if ax_inits is not None:
                assert self._test_unique_str_keys(
                    ax_inits
                ), "EOmaps: there are duplicated keys in ax_inits!"
                for key, val in ax_inits.items():
                    self.create_axes(val, name=key)

    def new_layer(self, layer=None):
        if layer is None:
            layer = self.parent.layer

        mg = MapsGrid(m_inits=dict())  # initialize an empty MapsGrid
        mg.gridspec = self.gridspec

        for name, m in zip(self._names.get("Maps", []), self._Maps):
            newm = m.new_layer(layer)
            mg._Maps.append(newm)
            mg._names["Maps"].append(name)
            setattr(mg, "m_" + name, newm)

            if m is self.parent:
                mg.parent = newm

        for name in self._names.get("Axes", []):
            ax = getattr(self, f"ax_{name}")
            mg._names["Axes"].append(name)
            setattr(mg, f"ax_{name}", ax)

        return mg

    def cleanup(self):
        for m in self:
            m.cleanup()

    @staticmethod
    def _test_unique_str_keys(x):
        # check if all keys are unique (as strings)
        seen = set()
        return not any(str(i) in seen or seen.add(str(i)) for i in x)

    def __iter__(self):
        return iter(self._Maps)

    def __getitem__(self, key):
        try:
            if self._custom_init is False:
                if isinstance(key, str):
                    r, c = map(int, key.split("_"))
                elif isinstance(key, (list, tuple)):
                    r, c = key
                else:
                    raise IndexError(f"{key} is not a valid indexer for MapsGrid")

                return getattr(self, f"m_{r}_{c}")
            else:
                if str(key) in self._names.get("Maps", []):
                    return getattr(self, "m_" + str(key))
                elif str(key) in self._names.get("Axes", []):
                    return getattr(self, "ax_" + str(key))
                else:
                    raise IndexError(f"{key} is not a valid indexer for MapsGrid")
        except:
            raise IndexError(f"{key} is not a valid indexer for MapsGrid")

    @property
    def _preferred_wms_service(self):
        return self.parent._preferred_wms_service

    def create_axes(self, ax_init, name=None):
        """
        Create (and return) an ordinary matplotlib axes.

        Note: If you intend to use both ordinary axes and Maps-objects, it is
        recommended to use explicit "m_inits" and "ax_inits" dicts in the
        initialization of the MapsGrid to avoid the creation of overlapping axes!

        Parameters
        ----------
        ax_init : set
            The GridSpec speciffications for the axis.
            use `ax_inits = (<row>, <col>)` to get an axis in a given grid-cell
            use `slice(<start>, <stop>)` for `<row>` or `<col>` to get an axis
            that spans over multiple rows/columns.

        Returns
        -------
        ax : matplotlib.axist
            The matplotlib axis instance

        Examples
        --------

        >>> ax_inits = dict(top = (0, slice(0, 2)),
        >>>                 bottom_left=(1, 0))

        >>> mg = MapsGrid(2, 2, ax_inits=ax_inits)
        >>> mg.m_top.plot_map()
        >>> mg.m_bottom_left.plot_map()

        >>> mg.create_axes((1, 1), name="bottom_right")
        >>> mg.ax_bottom_right.plot([1,2,3], [1,2,3])

        """

        if name is None:
            # get all existing axes
            axes = [key for key in self.__dict__ if key.startswith("ax_")]
            name = str(len(axes))
        else:
            assert (
                name.isidentifier()
            ), f"the provided name {name} is not a valid identifier"

        ax = self.f.add_subplot(self.gridspec[ax_init], label=f"mg_ax_{name}")

        self._names.setdefault("Axes", []).append(name)
        setattr(self, f"ax_{name}", ax)
        return ax

    _doc_prefix = (
        "This will execute the corresponding action on ALL Maps "
        + "objects of the MapsGrid!\n"
    )

    @property
    def children(self):
        return [i for i in self if i is not self.parent]

    @property
    def f(self):
        return self.parent.f

    @wraps(Maps.plot_map)
    def plot_map(self, **kwargs):
        for m in self:
            m.plot_map(**kwargs)

    plot_map.__doc__ = _doc_prefix + plot_map.__doc__

    @property
    @lru_cache()
    @wraps(shapes)
    def set_shape(self):
        s = shapes(self)
        s.__doc__ = self._doc_prefix + s.__doc__

        return s

    @wraps(Maps.set_data_specs)
    def set_data_specs(self, *args, **kwargs):
        for m in self:
            m.set_data_specs(*args, **kwargs)

    set_data_specs.__doc__ = _doc_prefix + set_data_specs.__doc__

    set_data = set_data_specs

    @wraps(Maps.set_classify_specs)
    def set_classify_specs(self, scheme=None, **kwargs):
        for m in self:
            m.set_classify_specs(scheme=scheme, **kwargs)

    set_classify_specs.__doc__ = _doc_prefix + set_classify_specs.__doc__

    @wraps(Maps.add_annotation)
    def add_annotation(self, *args, **kwargs):
        for m in self:
            m.add_annotation(*args, **kwargs)

    add_annotation.__doc__ = _doc_prefix + add_annotation.__doc__

    @wraps(Maps.add_marker)
    def add_marker(self, *args, **kwargs):
        for m in self:
            m.add_marker(*args, **kwargs)

    add_marker.__doc__ = _doc_prefix + add_marker.__doc__

    if hasattr(Maps, "add_wms"):

        @property
        @wraps(Maps.add_wms)
        def add_wms(self):
            return self._wms_container

    @property
    @wraps(Maps.add_feature)
    def add_feature(self):
        x = NaturalEarth_features(self)
        return x

    @wraps(Maps.add_gdf)
    def add_gdf(self, *args, **kwargs):
        for m in self:
            m.add_gdf(*args, **kwargs)

    add_gdf.__doc__ = _doc_prefix + add_gdf.__doc__

    @wraps(Maps.add_line)
    def add_line(self, *args, **kwargs):
        for m in self:
            m.add_line(*args, **kwargs)

    add_line.__doc__ = _doc_prefix + add_line.__doc__

    @wraps(Maps.add_scalebar)
    def add_scalebar(self, *args, **kwargs):
        for m in self:
            m.add_scalebar(*args, **kwargs)

    add_scalebar.__doc__ = _doc_prefix + add_scalebar.__doc__

    @wraps(Maps.add_colorbar)
    def add_colorbar(self, *args, **kwargs):
        for m in self:
            m.add_colorbar(*args, **kwargs)

    add_colorbar.__doc__ = _doc_prefix + add_colorbar.__doc__

    @wraps(Maps.add_logo)
    def add_logo(self, *args, **kwargs):
        for m in self:
            m.add_logo(*args, **kwargs)

    add_colorbar.__doc__ = _doc_prefix + add_logo.__doc__

    def share_click_events(self):
        """
        Share click events between all Maps objects of the grid
        """
        self.parent.cb.click.share_events(*self.children)

    def share_move_events(self):
        """
        Share move events between all Maps objects of the grid
        """
        self.parent.cb.move.share_events(*self.children)

    def share_pick_events(self, name="default"):
        """
        Share pick events between all Maps objects of the grid
        """
        if name == "default":
            self.parent.cb.pick.share_events(*self.children)
        else:
            self.parent.cb.pick[name].share_events(*self.children)

    def join_limits(self):
        """
        Join axis limits between all Maps objects of the grid
        (only possible if all maps share the same crs!)
        """
        self.parent.join_limits(*self.children)

    @wraps(Maps.redraw)
    def redraw(self, *args):
        self.parent.redraw(*args)

    @wraps(plt.savefig)
    def savefig(self, *args, **kwargs):

        # clear all cached background layers before saving to make sure they
        # are re-drawn with the correct dpi-settings
        self.parent.BM._refetch_bg = True

        self.parent.savefig(*args, **kwargs)

    @property
    @wraps(Maps.util)
    def util(self):
        return self.parent.util

    @wraps(Maps.subplots_adjust)
    def subplots_adjust(self, **kwargs):
        return self.parent.subplots_adjust(**kwargs)

    @wraps(Maps.get_layout)
    def get_layout(self, *args, **kwargs):
        return self.parent.get_layout(*args, **kwargs)

    @wraps(Maps.apply_layout)
    def apply_layout(self, *args, **kwargs):
        return self.parent.apply_layout(*args, **kwargs)

    @wraps(Maps.edit_layout)
    def edit_layout(self, *args, **kwargs):
        return self.parent.edit_layout(*args, **kwargs)

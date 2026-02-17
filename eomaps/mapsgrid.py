# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""MapsGrid class definition (helper to work with regular grids of maps)."""

from itertools import chain

import numpy as np

from matplotlib.gridspec import GridSpec
import matplotlib.pyplot as plt

from .eomaps import Maps
from ._maps_base import MultiCaller


class MapsGrid(MultiCaller):
    """
    Initialize a grid of Maps objects

    Any action performed on the MapsGrid accessor will be executed on ALL
    Maps of the grid!

    You can access individual Maps-objects via the m_<row>_<col> properties:

    >>> mgrid.m_0_0     # access first map of first row

    or via indexing/slicing:

    >>> mgrid[0,0]      # access first map of first row
    >>> mgrid[0]        # access first map of flattened grid
    >>> mgrid[[0, 1]]   # get accessor to run actions on first and second map
    >>> mgrid[:4]       # get accessor to run actions on first 4 maps

    You can also iterate over the MapsGrid:

    >>> for m in mg:
    >>>     ... # loop over all maps of the grid


    Parameters
    ----------
    nrows : int, optional
        The number of rows. The default is 2.
    ncols : int, optional
        The number of columns. The default is 2.
    crs : int or a cartopy-projection or a list, optional
        The projection that will be assigned to all Maps objects.
        (you can still change the projection of individual Maps objects later!)
        See the doc of "Maps" for details. If a list is provided, it is used
        to assign individual crs to each Maps-object of the grid.
        The default is 4326.
    figsize : (float, float)
        The width and height of the figure.
    layer : int or str
        The default layer to assign to all Maps-objects of the grid.
        The default is "base"
    kwargs
        Additional keyword-arguments passed to the `matplotlib.gridspec.GridSpec()`
        function that is used to initialize the grid.

    Attributes
    ----------
    m_<row>_<col> : eomaps.Maps objects
        The individual Maps-objects can be accessed via
        `mgrid.m_0_0`  -> the first Maps object of the first row


    Examples
    --------
    To initialize a 2 by 2 grid with a large map on top, a small map
    on the bottom-left and an ordinary matplotlib plot on the bottom-right, use:


    >>> mg = MapsGrid(2, 2, crs=4326)
    >>> mg.add_feature.preset.coastline()
    >>> mg.set_data(data=[1,2,3], x=[1,2,3], y=[1,2,3])
    >>> mg.m_top.plot_map()

    Returns
    -------
    eomaps.MapsGrid
        Accessor to the Maps objects "m_{row}_{column}".

    """

    __parent_only_attrs = (
        "f",
        "parent",
        "savefig",
        "redraw",
        "snapshot",
        "show",
        "show_layer",
        "edit_layout",
        "get_layout",
        "apply_layout",
        "subplots_adjust",
        "CRS",
        "fetch_layers",
        "new_inset_map",
        "new_map",
        "new_subplot",
        "util",
    )

    def __init__(self, nrows=2, ncols=2, crs=None, figsize=None, layer=None, **kwargs):
        self.__nrows = nrows
        self.__ncols = ncols

        if crs is None:
            crs = [Maps.CRS.PlateCarree()] * nrows * ncols
        else:
            if isinstance(crs, list):
                crs = [Maps._get_cartopy_crs(i) for i in np.ravel(crs)]
            else:
                crs = [Maps._get_cartopy_crs(crs)] * nrows * ncols

        f = plt.figure(figsize=figsize)
        aspect = f.get_figheight() / f.get_figwidth()

        d = 0.02
        gs = GridSpec(
            nrows,
            ncols,
            bottom=d * aspect,
            top=1 - d * aspect,
            left=d,
            right=1 - d,
            hspace=d * aspect,
            wspace=d,
        )

        m_parent = Maps(f=f, ax=list(gs)[0], crs=crs[0], layer=layer, **kwargs)

        mg = [
            m_parent,
            *(
                Maps(f=f, ax=g, crs=c, layer=layer, parent=m_parent, **kwargs)
                for g, c in zip(list(gs)[1:], crs[1:])
            ),
        ]

        return MultiCaller.__init__(self, elements=mg)

    def __dir__(self):
        return [i for i in dir(Maps) if not i.startswith("_")]

    def __getitem__(self, idx):
        if isinstance(idx, int):
            # implement 1d indexing, e.g. mg[1]
            return self._elements[idx]
        elif isinstance(idx, tuple) and len(idx) == 2:
            # implement 2d indexing, e.g. mg[1,2]
            idx = np.ravel_multi_index(idx, (self.__nrows, self.__ncols)).item()
            return self._elements[idx]
        elif isinstance(idx, slice):
            # implement slicing, e.g.:  mg[1:-2]
            start, stop, step = idx.indices(len(self._elements))
            return sum([self.__getitem__(i) for i in range(start, stop, step)])
        elif isinstance(idx, list):
            # implement multi-seletion, e.g.:  mg[[1,2,5]]
            return sum([self.__getitem__(i) for i in idx])

    def __getattribute__(self, name):
        if name in dir(MapsGrid):
            return object.__getattribute__(self, name)

        if name.startswith("m_"):
            i, *j = map(int, name.removeprefix("m_").split("_"))
            if j:
                idx = (i, j[0])
            else:
                idx = i
            return self.__getitem__(idx)

        if name in object.__getattribute__(self, "_MapsGrid__parent_only_attrs"):
            return object.__getattribute__(self.__getitem__(0), name)
        else:
            return super().__getattribute__(name)

    @property
    def on_all_layers(self):
        """
        Accessor to run actions on **all layers** of **all maps** of the grid.
        """
        return sum(chain(*self.l))

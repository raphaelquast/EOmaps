""" a collection of useful helper-functions """
from itertools import tee

import numpy as np
from matplotlib.colors import LinearSegmentedColormap, ListedColormap


def pairwise(iterable, pairs=2):
    """
    a generator to return n consecutive values from an iterable, e.g.:

        pairs = 2
        s -> (s0,s1), (s1,s2), (s2, s3), ...

        pairs = 3
        s -> (s0, s1, s2), (s1, s2, s3), (s2, s3, s4), ...

    adapted from https://docs.python.org/3.7/library/itertools.html
    """
    x = tee(iterable, pairs)
    for n, n_iter in enumerate(x[1:]):
        [next(n_iter, None) for i in range(n + 1)]
    return zip(*x)


def cmap_alpha(cmap, alpha, interpolate=False):
    """
    add transparency to an existing colormap

    Parameters
    ----------
    cmap : matplotlib.colormap
        the colormap to use
    alpha : float
        the transparency
    interpolate : bool
        indicator if a listed colormap (False) or a interpolated colormap (True)
        should be generated. The default is False

    Returns
    -------
    new_cmap : matplotlib.colormap
        a new colormap with the desired transparency
    """

    new_cmap = cmap(np.arange(cmap.N))
    new_cmap[:, -1] = alpha
    if interpolate:
        new_cmap = LinearSegmentedColormap("new_cmap", new_cmap)
    else:
        new_cmap = ListedColormap(new_cmap)
    return new_cmap

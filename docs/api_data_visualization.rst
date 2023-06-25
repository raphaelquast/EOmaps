
.. _visualize_data:

🔴 Data Visualization
----------------------

.. currentmodule:: eomaps.eomaps


To visualize a dataset, first assign the dataset to the :py:class:`Maps` object,
then select how you want to visualize the data and finally call :py:meth:`Maps.plot_map`.

1. **Assign the data** to a :py:class:`Maps` object via :py:meth:`Maps.set_data`
2. (optional) **set the shape** used to represent the data via  :py:class:`Maps.set_shape`
3. (optional) **assign a classification scheme** for the data via  :py:class:`Maps.set_classify`
4. **Plot the data** by calling :py:meth:`Maps.plot_map`

🗃 Assign the data
~~~~~~~~~~~~~~~~~~

To assign a dataset to a :py:class:`Maps` object, use :py:meth:`Maps.set_data`.


.. autosummary::
    :nosignatures:

    Maps.set_data


A dataset is fully specified by setting the following properties:

- ``data`` : The data-values
- ``x``, ``y``: The coordinates of the provided data
- ``crs``: The coordinate-reference-system of the provided coordinates
- ``parameter`` (optional): The parameter name
- ``encoding`` (optional): The encoding of the data
- ``cpos``, ``cpos_radius`` (optional): the pixel offset


.. note::

    Make sure to use a individual :py:class:`Maps` object (e.g. with ``m2 = m.new_layer()`` for each dataset!
    Calling :py:meth:`Maps.plot_map` multiple times on the same :py:class:`Maps` object will remove
    and override the previously plotted dataset!


.. admonition:: A note on data-reprojection...

    EOmaps handles the reprojection of the data from the input-crs to the plot-crs.

    - Plotting data in its native crs will omit the reprojection step and is therefore a lot faster!
    - If your dataset is 2D (e.g. a raster), it is best (for speed and memory) to provide the coordinates as 1D vectors!

       - Note that reprojecting 1D coordinate vectors to a different crs will result in (possibly very large) 2D coordinate arrays!


The following data-types are accepted as input:

+---------------------------------------------------------------------+------------------------------------------------------------------------------------+
| **pandas DataFrames**                                               | .. code-block:: python                                                             |
|                                                                     |     :name: test_pandas_data_01                                                     |
|                                                                     |                                                                                    |
| - ``data``: ``pandas.DataFrame``                                    |     from eomaps import Maps                                                        |
| - ``x``, ``y``: The column-names to use as coordinates (``string``) |     import pandas as pd                                                            |
| - ``parameter``: The column-name to use as data-values (``string``) |                                                                                    |
|                                                                     |     df = pd.DataFrame(dict(lon=[1,2,3], lat=[2,5,4], data=[12, 43, 2]))            |
|                                                                     |     m = Maps()                                                                     |
|                                                                     |     m.set_data(df, x="lon", y="lat", crs=4326, parameter="data")                   |
|                                                                     |     m.plot_map()                                                                   |
+---------------------------------------------------------------------+------------------------------------------------------------------------------------+
| **pandas Series**                                                   | .. code-block:: python                                                             |
|                                                                     |     :name: test_pandas_data_02                                                     |
|                                                                     |                                                                                    |
| - ``data``, ``x``, ``y``: ``pandas.Series``                         |     from eomaps import Maps                                                        |
| - ``parameter``: (optional) parameter name (``string``)             |     import pandas as pd                                                            |
|                                                                     |                                                                                    |
|                                                                     |     x, y, data = pd.Series([1,2,3]), pd.Series([2, 5, 4]), pd.Series([12, 43, 2])  |
|                                                                     |     m = Maps()                                                                     |
|                                                                     |     m.set_data(data, x=x, y=y, crs=4326, parameter="param_name")                   |
|                                                                     |     m.plot_map()                                                                   |
+---------------------------------------------------------------------+------------------------------------------------------------------------------------+
| **1D** or **2D** data **and** coordinates                           | .. code-block:: python                                                             |
|                                                                     |     :name: test_numpy_data_01                                                      |
|                                                                     |                                                                                    |
| - ``data``, ``x``, ``y``: equal-size ``numpy.array`` (or ``list``)  |     from eomaps import Maps                                                        |
| - ``parameter``: (optional) parameter name (``string``)             |     import numpy as np                                                             |
|                                                                     |                                                                                    |
|                                                                     |     x, y = np.mgrid[-20:20, -40:40]                                                |
|                                                                     |     data = x + y                                                                   |
|                                                                     |     m = Maps()                                                                     |
|                                                                     |     m.set_data(data=data, x=x, y=y, crs=4326, parameter="param_name")              |
|                                                                     |     m.plot_map()                                                                   |
+---------------------------------------------------------------------+------------------------------------------------------------------------------------+
| **1D** coordinates and **2D** data                                  | .. code-block:: python                                                             |
|                                                                     |     :name: test_numpy_data_02                                                      |
|                                                                     |                                                                                    |
| - ``data``: ``numpy.array`` (or ``list``) with shape ``(n, m)``     |     from eomaps import Maps                                                        |
| - ``x``: ``numpy.array`` (or ``list``) with shape ``(n,)``          |     import numpy as np                                                             |
| - ``y``: ``numpy.array`` (or ``list``) with shape ``(m,)``          |                                                                                    |
| - ``parameter``: (optional) parameter name (``string``)             |     x = np.linspace(10, 50, 100)                                                   |
|                                                                     |     y = np.linspace(10, 50, 50)                                                    |
|                                                                     |     data = np.random.normal(size=(100, 50))                                        |
|                                                                     |                                                                                    |
|                                                                     |     m = Maps()                                                                     |
|                                                                     |     m.set_data(data=data, x=x, y=y, crs=4326, parameter="param_name")              |
|                                                                     |     m.plot_map()                                                                   |
+---------------------------------------------------------------------+------------------------------------------------------------------------------------+


💠 Specify how to visualize the data
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To specify how a dataset is visualized on the map, you have to set the *"plot-shape"* via :py:meth:`Maps.set_shape`.

.. currentmodule:: eomaps.eomaps

.. autosummary::
    :nosignatures:

    Maps.set_shape

.. admonition:: A note on speed and performance

    Some ways to visualize the data require more computational effort than others!
    Make sure to select an appropriate shape based on the size of the dataset you want to plot!

    EOmaps dynamically pre-selects the data with respect to the current plot-extent before the actual plot is created!
    If you do not need to see the whole extent of the data, make sure to **set the desired plot-extent**
    via :py:meth:`Maps.set_extent` or :py:meth:`Maps.set_shape_to_extent` **BEFORE** calling :py:meth:`Maps.plot_map` to get a (possibly huge) speedup!

    The number of datapoints mentioned in the following always refer to the number of datapoints that are
    visible in the desired plot-extent.


Possible shapes that work nicely for datasets with up to ~500 000 data-points:

.. currentmodule:: eomaps.shapes.Shapes

.. autosummary::
    :nosignatures:

    geod_circles
    ellipses
    rectangles
    voronoi_diagram
    delaunay_triangulation



Possible shapes that work nicely for up to a few million data-points:

.. autosummary::
    :nosignatures:

    raster


While :py:class:`raster` can still be used for datasets with a few million datapoints, for extremely large datasets
(> 10 million datapoints) it is recommended to use "shading" to **greatly speed-up plotting**.
If shading is used, a dynamic averaging of the data based on the screen-resolution and the
currently visible plot-extent is performed (resampling based on the mean-value is used by default).

Possible shapes that can be used to quickly generate a plot for extremely large datasets are:

.. autosummary::
    :nosignatures:

    shade_points
    shade_raster


.. code-block:: python
    :name: test_set_shape

    from eomaps import Maps
    data, x, y = [.3,.64,.2,.5,1], [1,2,3,4,5], [2,5,3,7,5]

    m = Maps()                                # create a Maps-object
    m.set_data(data, x, y)                    # assign some data to the Maps-object
    m.set_shape.rectangles(radius=1,          # represent the datapoints as 1x1 degree rectangles
                            radius_crs=4326)  # (in epsg=4326 projection)
    m.plot_map(cmap="viridis", zorder=1)      # plot the data

    m2 = m.new_layer()                        # create a new Maps-object on the same layer
    m2.set_data(data, x, y)                   # assign another dataset to the new Maps object
    m2.set_shape.geod_circles(radius=50000,   # draw geodetic circles with 50km radius
                            n=100)          # use 100 intermediate points to represent the shape
    m2.plot_map(ec="k", cmap="Reds",          # plot the data
                zorder=2, set_extent=False)   # (and avoid resetting the plot-extent)

.. note::

    The "shade"-shapes require the additional `datashader <https://datashader.org/>`_ dependency!
    You can install it via:

    .. code-block:: python

       mamba install -c conda-forge datashader

.. admonition:: What's used by default?

    By default, the plot-shape is assigned based on the associated dataset.

    - For datasets with less than 500 000 pixels, ``m.set_shape.ellipses()`` is used.
    - | For larger 2D datasets ``m.set_shape.shade_raster()`` is used
      | ... and ``m.set_shape.shade_points()`` is used for the rest.

To get an overview of the existing shapes and their main use-cases, here's a simple decision-tree:
(... and don't forget to set the plot-extent if you only want to see a subset of the data!)

.. image:: _static/shapes_decision_tree.png

.. image:: _static/minigifs/plot_shapes.gif

📊 Classify the data
~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps

EOmaps provides an interface for `mapclassify <https://github.com/pysal/mapclassify>`_ to classify datasets prior to plotting.

To assign a classification scheme to a :py:class:`Maps` object, use ``m.set_classify.< SCHEME >(...)``.

- Available classifier names are accessible via ``Maps.CLASSIFIERS``.

.. autosummary::
    :nosignatures:

    Maps.set_classify


.. table::
    :widths: 70 30
    :align: center

    +------------------------------------------------------------------+--------------------------------------------------+
    | .. code-block:: python                                           | .. image:: _static/minigifs/classify_data_01.png |
    |     :name: test_classify_data                                    |     :align: center                               |
    |                                                                  |                                                  |
    |     from eomaps import Maps                                      |                                                  |
    |     import numpy as np                                           |                                                  |
    |                                                                  |                                                  |
    |     data = np.random.normal(0, 1, (50, 50))                      |                                                  |
    |     x = np.linspace(-45, 45, 50)                                 |                                                  |
    |     y = np.linspace(-45, 45, 50)                                 |                                                  |
    |                                                                  |                                                  |
    |     m = Maps(figsize=(4, 5))                                     |                                                  |
    |     m.add_feature.preset.coastline(lw=2)                         |                                                  |
    |     m.add_feature.preset.ocean(zorder=99, alpha=0.5)             |                                                  |
    |     m.set_data(data, x, y)                                       |                                                  |
    |     m.set_shape.ellipses()                                       |                                                  |
    |     m.set_classify.StdMean(multiples=[-1.5, -.5, .5, 1.5])       |                                                  |
    |     m.plot_map(vmin=-3, vmax=3)                                  |                                                  |
    |                                                                  |                                                  |
    |     cb = m.add_colorbar(pos=0.2, label="StdMean classification") |                                                  |
    |     cb.tick_params(labelsize=7)                                  |                                                  |
    +------------------------------------------------------------------+--------------------------------------------------+



Currently available classification-schemes are (see `mapclassify <https://github.com/pysal/mapclassify>`_ for details):

- `BoxPlot(hinge) <https://pysal.org/mapclassify/generated/mapclassify.BoxPlot.html>`_
- `EqualInterval(k) <https://pysal.org/mapclassify/generated/mapclassify.EqualInterval.html>`_
- `FisherJenks(k) <https://pysal.org/mapclassify/generated/mapclassify.FisherJenks.html>`_
- `FisherJenksSampled(k, pct, truncate) <https://pysal.org/mapclassify/generated/mapclassify.FisherJenksSampled.html>`_
- `HeadTailBreaks() <https://pysal.org/mapclassify/generated/mapclassify.HeadTailBreaks.html>`_
- `JenksCaspall(k) <https://pysal.org/mapclassify/generated/mapclassify.JenksCaspall.html>`_
- `JenksCaspallForced(k) <https://pysal.org/mapclassify/generated/mapclassify.JenksCaspallForced.html>`_
- `JenksCaspallSampled(k, pct) <https://pysal.org/mapclassify/generated/mapclassify.JenksCaspallSampled.html>`_
- `MaxP(k, initial) <https://pysal.org/mapclassify/generated/mapclassify.MaxP.html>`_
- `MaximumBreaks(k, mindiff) <https://pysal.org/mapclassify/generated/mapclassify.MaximumBreaks.html>`_
- `NaturalBreaks(k, initial) <https://pysal.org/mapclassify/generated/mapclassify.NaturalBreaks.html>`_
- `Quantiles(k) <https://pysal.org/mapclassify/generated/mapclassify.Quantiles.html>`_
- `Percentiles(pct) <https://pysal.org/mapclassify/generated/mapclassify.Percentiles.html>`_
- `StdMean(multiples) <https://pysal.org/mapclassify/generated/mapclassify.StdMean.html>`_
- `UserDefined(bins) <https://pysal.org/mapclassify/generated/mapclassify.UserDefined.html>`_

🖨 Plot the data
~~~~~~~~~~~~~~~~

If you want to plot a map based on a dataset, first set the data and then
call :py:meth:`Maps.plot_map`.

Any additional keyword-arguments passed to :py:meth:`Maps.plot_map` are forwarded to the actual
plot-command for the selected shape.

Useful arguments that are supported by all shapes are:

    - "cmap" : the colormap to use
    - "vmin", "vmax" : the range of values used when assigning the colors
    - "alpha" : the color transparency
    - "zorder" : the "stacking-order" of the feature

Arguments that are supported by all shapes except ``shade`` shapes are:
    - "fc" or "facecolor" : set the face color for the whole dataset
    - "ec" or "edgecolor" : set the edge color for the whole dataset
    - "lw" or "linewidth" : the line width of the shapes


By default, the plot-extent of the axis is adjusted to the extent of the data **if the extent has not been set explicitly before**.
To always keep the extent as-is, use ``m.plot_map(set_extent=False)``.

.. code-block:: python
    :name: test_plot_data

    from eomaps import Maps
    m = Maps()
    m.add_feature.preset.coastline(lw=0.5)

    m.set_data([1,2,3,4,5], [10,20,40,60,70], [10,20,50,70,30], crs=4326)
    m.set_shape.geod_circles(radius=7e5)
    m.plot_map(cmap="viridis", ec="b", lw=1.5, alpha=0.85, set_extent=False)


You can then continue to add a :ref:`colorbar` or create :ref:`zoomed_in_views_on_datasets`.

.. currentmodule:: eomaps.eomaps

.. autosummary::
    :nosignatures:

    Maps.plot_map
    Maps.savefig


🎨 Customize the plot
~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps

All arguments to customize the appearance of a dataset are passed to :py:meth:`Maps.plot_map`.

In general, the colors assigned to the shapes are specified by

- selecting a colormap (``cmap``)

  - either a name of a pre-defined ``matplotlib`` colormap (e.g. ``"viridis"``, ``"RdYlBu"`` etc.)
  - or a general ``matplotlib`` colormap object (see `matplotlib-docs <https://matplotlib.org/stable/tutorials/colors/colormaps.html>`_ for more details)

- (optionally) setting appropriate data-limits via ``vmin`` and ``vmax``.

  - ``vmin`` and ``vmax`` set the range of data-values that are mapped to the colorbar-colors
  - Any values outside this range will get the colormaps ``over`` and ``under`` colors assigned.

.. code-block:: python
    :name: test_customize_the_plot

    from eomaps import Maps
    m = Maps()
    m.set_data([1,2,3,4,5], [10,20,40,60,70], [10,20,50,70,30])
    m.set_shape.ellipses(radius=5)
    m.plot_map(cmap="viridis", vmin=2, vmax=4, ec="b", lw=0.5)


------

Colors can also be set **manually** by providing one of the following arguments to :py:meth:`Maps.plot_map`:

- to set both **facecolor** AND **edgecolor** use ``color=...``
- to set the **facecolor** use ``fc=...`` or ``facecolor=...``
- to set the **edgecolor** use ``ec=...`` or ``edgecolor=...``

.. note::

    - Manual color specifications do **not** work with the ``shade_raster`` and ``shade_points`` shapes!
    - Providing manual colors will **override** the colors assigned by the ``cmap``!
    - The ``colorbar`` does **not** represent manually defined colors!


Uniform colors
**************

To apply a uniform color to all datapoints, you can use `matpltolib's named colors <https://matplotlib.org/stable/gallery/color/named_colors.html>`_ or pass an RGB or RGBA tuple.

- ``m.plot_map(fc="orange")``
- ``m.plot_map(fc=(0.4, 0.3, 0.2))``
- ``m.plot_map(fc=(1, 0, 0.2, 0.5))``

.. code-block:: python
    :name: test_uniform_colors

    from eomaps import Maps

    m = Maps()
    m.set_data(data=None, x=[10,20,30], y=[10,20,30])

    # Use any of matplotlibs "named colors"
    m1 = m.new_layer(copy_data_specs=True)
    m1.set_shape.ellipses(radius=10)
    m1.plot_map(fc="r", zorder=0)

    m2 = m.new_layer(copy_data_specs=True)
    m2.set_shape.ellipses(radius=8)
    m2.plot_map(fc="orange", zorder=1)

    # Use RGB or RGBA tuples
    m3 = m.new_layer(copy_data_specs=True)
    m3.set_shape.ellipses(radius=6)
    m3.plot_map(fc=(1, 0, 0.5), zorder=2)

    m4 = m.new_layer(copy_data_specs=True)
    m4.set_shape.ellipses(radius=4)
    m4.plot_map(fc=(1, 1, 1, .75), zorder=3)

    # For grayscale use a string of a number between 0 and 1
    m5 = m.new_layer(copy_data_specs=True)
    m5.set_shape.ellipses(radius=2)
    m5.plot_map(fc="0.3", zorder=4)


Explicit colors
***************

To explicitly color each datapoint with a pre-defined color, simply provide a list or array of the aforementioned types.

.. code-block:: python
    :name: test_explicit_colors

    from eomaps import Maps

    m = Maps()
    m.set_data(data=None, x=[10, 20, 30], y=[10, 20, 30])

    # Use any of matplotlibs "named colors"
    # (https://matplotlib.org/stable/gallery/color/named_colors.html)
    m1 = m.new_layer(copy_data_specs=True)
    m1.set_shape.ellipses(radius=10)
    m1.plot_map(fc=["indigo", "g", "orange"], zorder=1)

    # Use RGB tuples
    m2 = m.new_layer(copy_data_specs=True)
    m2.set_shape.ellipses(radius=6)
    m2.plot_map(fc=[(1, 0, 0.5),
                    (0.3, 0.4, 0.5),
                    (1, 1, 0)], zorder=2)

    # Use RGBA tuples
    m3 = m.new_layer(copy_data_specs=True)
    m3.set_shape.ellipses(radius=8)
    m3.plot_map(fc=[(1, 0, 0.5, 0.25),
                    (1, 0, 0.5, 0.75),
                    (0.1, 0.2, 0.5, 0.5)], zorder=3)

    # For grayscale use a string of a number between 0 and 1
    m4 = m.new_layer(copy_data_specs=True)
    m4.set_shape.ellipses(radius=4)
    m4.plot_map(fc=[".1", ".2", "0.3"], zorder=4)

RGB/RGBA composites
*******************

To create an RGB or RGBA composite from 3 (or 4) datasets, pass the datasets as tuple:

- the datasets must have the same size as the coordinate arrays!
- the datasets must be scaled between 0 and 1

If you pass a tuple of 3 or 4 arrays, they will be used to set the
RGB (or RGBA) colors of the shapes, e.g.:

- ``m.plot_map(fc=(<R-array>, <G-array>, <B-array>))``
- ``m.plot_map(fc=(<R-array>, <G-array>, <B-array>, <A-array>))``

You can fix individual color channels by passing a list with 1 element, e.g.:

- ``m.plot_map(fc=(<R-array>, [0.12345], <B-array>, <A-array>))``

.. code-block:: python
    :name: test_rgba_composites

    from eomaps import Maps
    import numpy as np

    x, y = np.meshgrid(np.linspace(-20, 40, 100),
                    np.linspace(50, 70, 50))

    # values must be between 0 and 1
    r = np.random.randint(0, 100, x.shape) / 100
    g = np.random.randint(0, 100, x.shape) / 100
    b = [0.4]
    a = np.random.randint(0, 100, x.shape) / 100

    m = Maps()
    m.add_feature.preset.ocean()
    m.set_data(data=None, x=x, y=y)
    m.plot_map(fc=(r, g, b, a))



.. _colorbar:

🌈 Colorbars (with a histogram)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps

Before adding a colorbar, you must plot the data using ``m.plot_map(vmin=..., vmax=...)``.

- ``vmin`` and ``vmax`` hereby specify the value-range used for assigning colors (e.g. the limits of the colorbar).
- If no explicit limits are provided, the min/max values of the data are used.
- For more details, see :ref:`visualize_data`.

Once a dataset has been plotted, a colorbar with a colored histogram on top can be added to the map by calling :py:meth:`Maps.add_colorbar`.

.. note::
    | The colorbar always represents the dataset that was used in the last call to :py:meth:`Maps.plot_map`.
    | If you need multiple colorbars, use an individual :py:class:`Maps` object for each dataset! (e.g. via ``m2  = m.new_layer()``)


.. note::
    Colorbars are only visible if the layer at which the data was plotted is visible!


.. table::
    :widths: 60 40
    :align: center

    +-----------------------------------------------------------------+------------------------------------------+
    | .. code-block:: python                                          | .. image:: _static/minigifs/colorbar.gif |
    |     :name: test_colorbars                                       |     :align: center                       |
    |                                                                 |                                          |
    |     from eomaps import Maps                                     |                                          |
    |     import numpy as np                                          |                                          |
    |                                                                 |                                          |
    |     data = np.random.normal(0, 1, (50, 50))                     |                                          |
    |     x = np.linspace(-45, 45, 50)                                |                                          |
    |     y = np.linspace(-45, 45, 50)                                |                                          |
    |                                                                 |                                          |
    |     m = Maps(layer="all")                                       |                                          |
    |     m.add_feature.preset.coastline()                            |                                          |
    |     m.add_feature.preset.ocean(zorder=99, alpha=0.5)            |                                          |
    |     m.util.layer_selector(loc="upper left")                     |                                          |
    |                                                                 |                                          |
    |     mA = m.new_layer("A")                                       |                                          |
    |     mA.set_data(data, x, y)                                     |                                          |
    |     mA.set_classify.Quantiles(k=5)                              |                                          |
    |     mA.plot_map(vmin=-3, vmax=3)                                |                                          |
    |     cbA = mA.add_colorbar(label="Quantile classification")      |                                          |
    |     cbA.tick_params(rotation=45)                                |                                          |
    |                                                                 |                                          |
    |     mB = m.new_layer("B")                                       |                                          |
    |     mB.set_data(data, x, y)                                     |                                          |
    |     mB.set_classify.EqualInterval(k=5)                          |                                          |
    |     mB.plot_map(vmin=-3, vmax=3)                                |                                          |
    |     cbB = mB.add_colorbar(label="EqualInterval classification") |                                          |
    |     cbB.tick_params(labelcolor="darkblue", labelsize=9)         |                                          |
    |                                                                 |                                          |
    |     m.subplots_adjust(bottom=0.1)                               |                                          |
    |     mA.show()                                                   |                                          |
    +-----------------------------------------------------------------+------------------------------------------+

.. autosummary::
    :nosignatures:

    Maps.add_colorbar


The returned ``ColorBar``-object has the following useful methods defined:

.. currentmodule:: eomaps.colorbar

.. autosummary::
    :nosignatures:

    ColorBar.set_position
    ColorBar.set_labels
    ColorBar.set_hist_size
    ColorBar.tick_params
    ColorBar.set_visible
    ColorBar.remove

📎 Set colorbar tick labels based on bins
*****************************************

.. currentmodule:: eomaps.colorbar

To label the colorbar with custom names for a given set of bins, use :py:meth:`ColorBar.set_bin_labels`:

+-------------------------------------------------------------------------------+------------------------------------------------+
| .. code-block:: python                                                        | .. image:: _static/minigifs/colorbar_ticks.png |
|     :name: test_colorbar_bin_labels                                           |   :align: center                               |
|                                                                               |                                                |
|     import numpy as np                                                        |                                                |
|     from eomaps import Maps                                                   |                                                |
|     # specify some random data                                                |                                                |
|     lon, lat = np.mgrid[-45:45, -45:45]                                       |                                                |
|     data = np.random.normal(0, 50, lon.shape)                                 |                                                |
|                                                                               |                                                |
|     # use a custom set of bins to classify the data                           |                                                |
|     bins = np.array([-50, -30, -20, 20, 30, 40, 50])                          |                                                |
|     names = np.array(["below -50", "A", "B", "C", "D", "E", "F", "above 50"]) |                                                |
|                                                                               |                                                |
|     m = Maps()                                                                |                                                |
|     m.add_feature.preset.coastline()                                          |                                                |
|     m.set_data(data, lon, lat)                                                |                                                |
|     m.set_classify.UserDefined(bins=bins)                                     |                                                |
|     m.plot_map(cmap="tab10")                                                  |                                                |
|     m.add_colorbar()                                                          |                                                |
|                                                                               |                                                |
|     # set custom colorbar-ticks based on the bins                             |                                                |
|     m.colorbar.set_bin_labels(bins, names)                                    |                                                |
+-------------------------------------------------------------------------------+------------------------------------------------+


.. autosummary::
    :nosignatures:

    ColorBar.set_bin_labels


🌠 Using the colorbar as a "dynamic shade indicator"
*****************************************************


.. note::

    This will only work if you use ``m.set_shape.shade_raster()`` or ``m.set_shape.shade_points()`` as plot-shape!


For shade shapes, the colorbar can be used to indicate the distribution of the shaded
pixels within the current field of view by setting ``dynamic_shade_indicator=True``.

    +--------------------------------------------------------------------+--------------------------------------------------+
    | .. code-block:: python                                             | .. image:: _static/minigifs/dynamic_colorbar.gif |
    |   :name: test_colorbar_dynamic_shade_indicator                     |   :align: center                                 |
    |                                                                    |                                                  |
    |   from eomaps import Maps                                          |                                                  |
    |   import numpy as np                                               |                                                  |
    |   x, y = np.mgrid[-45:45, 20:60]                                   |                                                  |
    |                                                                    |                                                  |
    |   m = Maps()                                                       |                                                  |
    |   m.add_feature.preset.coastline()                                 |                                                  |
    |   m.set_data(data=x+y, x=x, y=y, crs=4326)                         |                                                  |
    |   m.set_shape.shade_raster()                                       |                                                  |
    |   m.plot_map()                                                     |                                                  |
    |   m.add_colorbar(dynamic_shade_indicator=True, hist_bins=20)       |                                                  |
    |                                                                    |                                                  |
    +--------------------------------------------------------------------+--------------------------------------------------+
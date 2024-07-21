
📦 Reading data
----------------

.. currentmodule:: eomaps.eomaps

EOmaps provides some basic capabilities to read and plot directly from commonly used file-types.

.. contents:: Contents:
    :local:
    :depth: 1

.. note::

    At the moment, the readers are intended as a "shortcut" to read well-structured datasets!
    If they fail, read the data manually and then set the data as usual via :py:meth:`Maps.set_data`.

    Under the hood, EOmaps uses the following libraries to read data:

    - GeoTIFF (``rioxarray`` + ``xarray.open_dataset()``)
    - NetCDF (``xarray.open_dataset()``)
    - CSV (``pandas.read_csv()``)



Read data from a file
~~~~~~~~~~~~~~~~~~~~~

``m.read_file.<filetype>(...)`` can be used to read all relevant data (e.g. values, coordinates & crs) from a file.

.. code-block:: python

    m = Maps()
    data = Maps.read_file.NetCDF(
        "the filepath",
        parameter="adsf",
        coords=("longitude", "latitude"),
        data_crs=4326,
        isel=dict(time=123)
        )
    m.set_data(**data)
    ...
    m.plot_map()

.. currentmodule:: eomaps.reader

.. autosummary::
    :nosignatures:

    read_file.GeoTIFF
    read_file.NetCDF
    read_file.CSV

Initialize a Maps-object from a file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

``Maps.from_file.<filetype>(...)`` can be used to directly initialize a :py:class:`Maps` object from a file.
(This is particularly useful if you have a well-defined file-structure that you need to access regularly)

.. code-block:: python

    m = Maps.from_file.GeoTIFF(
        "the filepath",
        classify_specs=dict(Maps.CLASSFIERS.Quantiles, k=10),
        cmap="RdBu"
        )
    m.add_colorbar()
    m.cb.pick.attach.annotate()

.. currentmodule:: eomaps.reader

.. autosummary::
    :nosignatures:

    from_file.GeoTIFF
    from_file.NetCDF
    from_file.CSV


Create a new layer from a file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Similar to :py:class:`Maps.from_file` , a new layer based on a file can be added to an existing :py:class:`Maps` object via ``Maps.new_layer_from_file.<filetype>(...)``.

.. code-block:: python

    m = Maps()
    m.add_feature.preset.coastline()

    m2 = m.new_layer_from_file(
        "the filepath",
        parameter="adsf",
        coords=("longitude", "latitude"),
        data_crs=4326,
        isel=dict(time=123),
        classify_specs=dict(Maps.CLASSFIERS.Quantiles, k=10),
        cmap="RdBu"
        )

.. currentmodule:: eomaps.reader

.. autosummary::
    :nosignatures:


    new_layer_from_file.GeoTIFF
    new_layer_from_file.NetCDF
    new_layer_from_file.CSV

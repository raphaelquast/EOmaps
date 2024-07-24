
.. _webmap_layers:

🛰 WebMap layers
----------------

.. contents:: Contents:
    :local:
    :depth: 1

How to add WebMap services to a map
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps

WebMap services (TS/WMS/WMTS) can be attached to the map via :py:meth:`Maps.add_wms`

.. code-block:: python

    m.add_wms.attach.< SERVICE > ... .add_layer.< LAYER >(...)


``< SERVICE >`` hereby specifies the pre-defined WebMap service you want to add,
and ``< LAYER >`` indicates the actual layer-name.

.. code-block:: python

    m = Maps(Maps.CRS.GOOGLE_MERCATOR) # (the native crs of the service)
    m.add_wms.OpenStreetMap.add_layer.default()

.. autosummary::
    :nosignatures:

    Maps.add_wms


.. note::

    It is highly recommended (and sometimes even required) to use the native crs
    of the WebMap service in order to avoid re-projecting the images
    (which degrades image quality and sometimes takes quite a lot of time to finish...)

    - most services come either in ``epsg=4326`` or in ``Maps.CRS.GOOGLE_MERCATOR`` projection


.. grid:: 1 1 1 2

    .. grid-item::

         .. code-block:: python

            from eomaps import MapsGrid
            mg = MapsGrid(crs=Maps.CRS.GOOGLE_MERCATOR)
            mg.join_limits()

            mg.m_0_0.add_wms.OpenStreetMap.add_layer.default()
            mg.m_0_1.add_wms.OpenStreetMap.add_layer.stamen_toner()

            mg.m_1_1.add_wms.S1GBM.add_layer.vv()

            # ... for more advanced
            layer = mg.m_1_0.add_wms.ISRIC_SoilGrids.nitrogen.add_layer.nitrogen_0_5cm_mean
            layer.set_extent_to_bbox() # set the extent according to the boundingBox
            layer.info                 # the "info" property provides useful information on the layer
            layer()                    # call the layer to add it to the map
            layer.add_legend()         # if a legend is provided, you can add it to the map!

    .. grid-item::

        .. image:: ../../_static/minigifs/add_wms.png


Pre-defined WebMap services
~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Global:**

.. currentmodule:: eomaps.eomaps.Maps.add_wms

.. autosummary::
    :nosignatures:

    OpenStreetMap
    ESA_WorldCover
    NASA_GIBS
    ISRIC_SoilGrids
    EEA_DiscoMap
    ESRI_ArcGIS
    S1GBM
    S2_cloudless
    GEBCO
    GMRT
    GLAD
    CAMS
    DLR
    OpenPlanetary



**Services specific for Austria (Europe)**

.. currentmodule:: eomaps.webmap_containers.WebMapContainer

.. autosummary::
    :nosignatures:

    _Austria.AT_basemap
    _Austria.Wien_basemap



.. note::
    Services might be nested directory structures!
    The actual layer is always added via the ``add_layer`` directive.

        :code:`m.add_wms.<...>. ... .<...>.add_layer.<LAYER NAME>()`

    Some of the services dynamically fetch the structure via HTML-requests.
    Therefore it can take a short moment before autocompletion is capable of
    showing you the available options!
    A list of available layers from a sub-folder can be fetched via:

        :code:`m.add_wms.<...>. ... .<LAYER NAME>.layers`

Using custom WebMap services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. currentmodule:: eomaps.eomaps.Maps.add_wms

It is also possible to use custom WMS/WMTS/XYZ services.
(see docstring of :py:meth:`get_service` for more details and examples)

.. autosummary::
    :nosignatures:

    get_service


.. code-block:: python

    m = Maps()
    # define the service
    service = m.add_wms.get_service(<... link to GetCapabilities.xml ...>,
                                    service_type="wms",
                                    res_API=False,
                                    maxzoom=19)
    # once the service is defined, you can use it just like the pre-defined ones
    service.layers   # >> get a list of all layers provided by the service

    # select one of the layers
    layer = service.add_layer. ... .< LAYER >
    layer.info                  # >> get some additional infos for the selected layer
    layer.set_extent_to_bbox()  # >> set the map-extent to the bbox of the layer

    # call the layer to add it to the map
    # (optionally providing additional kwargs for fetching map-tiles)
    layer(...)


Setting date, style and other WebMap properties
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some WebMap services allow passing additional arguments to set properties such as the **date** or the **style** of the map.
To pass additional arguments to a WebMap service, simply provide them when when calling the layer, e.g.:

.. code-block:: python

    m = Maps()
    m.add_wms.< SERVICE >. ... .add_layer.< LAYER >(time=..., styles=[...], ...)

To show an example, here's how to fetch multiple timestamps for the UV-index of the Copernicus Airquality service.
(provided by https://atmosphere.copernicus.eu/)


.. grid:: 1 1 1 2

    .. grid-item::

         .. code-block:: python

            from eomaps import Maps
            import pandas as pd

            m = Maps(layer="all", figsize=(8, 4))
            m.subplots_adjust(left=0.05, right=0.95)
            m.all.add_feature.preset.coastline()
            m.add_logo()

            layer = m.add_wms.CAMS.add_layer.composition_uvindex_clearsky
            timepos = layer.wms_layer.timepositions   # available time-positions
            all_styles = list(layer.wms_layer.styles) # available styles

            # create a list of timestamps to fetch
            start, stop, freq = timepos[1].split(r"/")
            times = pd.date_range(start, stop, freq=freq.replace("PT", ""))
            times = times.strftime("%Y-%m-%dT%H:%M:%SZ")

            style = all_styles[0]     # use the first available style
            for time in times[:6]:
                # call the layer to add it to the map
                layer(time=time,
                      styles=[style],   # provide a list with 1 entry here
                      layer=time        # put each WebMap on an individual layer
                      )

            layer.add_legend()  # add a legend for the WebMap service

            # add a "slider" and a "selector" widget
            m.util.layer_selector(ncol=3, loc="upper center", fontsize=6, labelspacing=1.3)
            m.util.layer_slider()

            # attach a callback to fetch all layers if you press l on the keyboard
            cid = m.all.cb.keypress.attach.fetch_layers(key="l")
            # fetch all layers so that they are cached and switching layers is fast
            m.fetch_layers()
            m.show_layer(times[0])      # make the first timestamp visible

    .. grid-item::

        .. image:: ../../_static/minigifs/advanced_wms.gif

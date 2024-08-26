=============
API Reference
=============

.. currentmodule:: eomaps.eomaps

The Maps object
===============

.. card::
    :link: ../generated/eomaps.eomaps.Maps
    :link-type: doc

    :py:class:`Maps` objects are used as the primary access point to create, edit and interact with maps.

    .. autosummary::
        :toctree: ../generated
        :template: custom-class-template.rst
        :nosignatures:

        Maps


Feature objects
===============


InsetMaps
---------

.. card::
    :shadow: none

    .. card::
        :link: ../generated/eomaps.inset_maps.InsetMaps
        :link-type: doc
        :margin: 0

        :py:class:`InsetMaps` objects highlight specific areas on a map.


        .. currentmodule:: eomaps.inset_maps

        .. autosummary::
            :toctree: ../generated
            :template: custom-class-template.rst
            :nosignatures:

            InsetMaps

    +++

    .. currentmodule:: eomaps.eomaps

    See :py:meth:`Maps.new_inset_map` on how to create a new InsetMap!


ColorBar
--------

.. card::
    :shadow: none

    .. card::
        :link: ../generated/eomaps.colorbar.ColorBar
        :link-type: doc
        :margin: 0

        :py:class:`ColorBar` objects visualize the color- and value-distribution of plotted datasets.

        .. currentmodule:: eomaps.colorbar

        .. autosummary::
            :toctree: ../generated
            :template: custom-class-template.rst
            :nosignatures:

            ColorBar

    +++

    .. currentmodule:: eomaps.eomaps

    See :py:meth:`Maps.add_colorbar` on how to add a colorbar to a map!


GridLines
---------

.. card::
    :shadow: none

    .. card::
        :link: ../generated/eomaps.grid.GridLines
        :link-type: doc
        :margin: 0

        .. currentmodule:: eomaps.grid

        :py:class:`GridLines` objects add lon/lat grids to a map.


        .. autosummary::
            :toctree: ../generated
            :template: custom-class-template.rst
            :nosignatures:

            GridLines

    +++

    .. currentmodule:: eomaps.eomaps

    See :py:meth:`Maps.add_gridlines` on how to add grid-lines to a map!


Compass
-------

.. card::
    :shadow: none

    .. card::
        :link: ../generated/eomaps.compass.Compass
        :link-type: doc
        :margin: 0

        .. currentmodule:: eomaps.compass

        :py:class:`Compass` objects indicate the cardinal directions for a point on a map.


        .. autosummary::
            :toctree: ../generated
            :template: custom-class-template.rst
            :nosignatures:

            Compass

    +++

    .. currentmodule:: eomaps.eomaps

    See :py:meth:`Maps.add_compass` on how to add a compass (or North-arrow) to a map!

Scalebar
--------

.. card::
    :shadow: none

    .. card::
        :link: ../generated/eomaps.scalebar.ScaleBar
        :link-type: doc
        :margin: 0

        .. currentmodule:: eomaps.scalebar

        :py:class:`ScaleBar` objects measure distances on a map.


        .. autosummary::
            :toctree: ../generated
            :template: custom-class-template.rst
            :nosignatures:

            ScaleBar

    +++

    .. currentmodule:: eomaps.eomaps

    See :py:meth:`Maps.add_scalebar` on how to add a scalebar to a map!

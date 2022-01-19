EOmaps
===================================

Welcome to the documentation for **EOmaps**!

In short, EOmaps serves as a layer on top of matplotlib and cartopy to tackle the following points:

🔴 **Speed-up and simplify the creation of maps**
  * directly plot from unstructured 1D datasets (e.g. lists of coordinates and values)
  * reduce overhead to speed-up plotting of large datasets (>1M datapoints)

🔵 Allow a meaningful representation of datapoints as **shapes with geographical dimensions**
  * geodesic circles, ellipses, rectangles etc.
  * Voroni-diagrams, Delaunay triangulations

🟠 Offer a versatile set of tools to **customize the appearance of the maps**
  * add **WebMap layers**, **overlays**, **markers**, **annotations** etc. with only 1 line of code
  * **classify the data** and visualize the data-distribution with a **colored histogram**
  * plot multiple maps in one figure

🟡 Directly use the created maps as **interactive data-analysis widgets**
  * compare/overlay multiple data layers, WebMaps etc. in a single plot
  * add markers and annotations etc. by clicking on the map
  * use the mouse or keyboard to **trigger custom functions on selected datapoints**


*(EOmaps hereby retains access to all functionalities of matplotlib and cartopy.)*

| A detailed overview on how to use EOmaps is given in the :doc:`api` section.
| Make sure to checkout the :doc:`EOmaps_examples` for an overview of the capabilities (incl. source code)!

----------


Contents
--------

.. toctree::
   :maxdepth: 2

   general
   api
   EOmaps_examples

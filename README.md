
<p align="center">
    <a href=https://github.com/raphaelquast/EOmaps>
    <img src="eomaps/logo.png" width="55%" />
    </a>
</p>

[![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml)
[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/EOmaps)
&nbsp; &nbsp; &nbsp;
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/eomaps.svg)](https://anaconda.org/conda-forge/eomaps)
&nbsp; &nbsp; &nbsp;
[![Documentation Status](https://readthedocs.org/projects/eomaps/badge/?version=latest)](https://eomaps.readthedocs.io/en/latest/?badge=latest)
<a href="https://www.buymeacoffee.com/raphaelquast" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png" alt="Buy Me A Coffee" align="right" style="height: 25px !important;" ></a>

----

### A library to create interactive maps of geographical datasets.

<ul type="none">
  <li>🌍 EOmaps provides a simple and intuitive interface to visualize and interact with geographical datasets</li>
  <ul type="none">
    <li>⬥ Data can be provided as 1D or 2D <code>lists</code>, <code>numpy-arrays</code> or <code>pandas.DataFrames</code></li>
    <li>  &nbsp; &nbsp; &nbsp; ... usable also for large datasets with > 1M datapoints!</li>
    <li>⬥ WebMap layers, annotations, markers can be added with a single line of code</li>
    <li>⬥ EOmaps is built on top of <code>matplotlib</code> and <code>cartopy</code> and integrates well <code>pandas</code> and <code>geopandas</code></li>
  </ul>
  <li>🌎 Quickly turn your maps into powerful interactive data-analysis widgets</li>
  <ul type="none">
    <li>⬥ use callback functions to interact with the data (or an underlying database) </li>
    <li>⬥ compare multiple data-layers, WebMaps etc.</li>
  </ul>
</ul>
<br/>
<p align="center">
  🌲🌳 Checkout the <a href=https://eomaps.readthedocs.io/en/latest><b>documentation</b></a> for more details and <a href=https://eomaps.readthedocs.io/en/latest/EOmaps_examples.html><b>examples</b></a> 🌳🌲
</p>

## 🔨 Installation

To install EOmaps (and all its dependencies) via the `conda` package-manager, simply use:

```python
conda install -c conda-forge eomaps
```
For more information, have a look at the [installation instructions](https://eomaps.readthedocs.io/en/latest/general.html#installation) in the documentation!
<br/>


## 🚀 Contribute

Found a bug or got an idea for an interesting feature? Open an [issue](https://github.com/raphaelquast/EOmaps/issues) or start a [discussion](https://github.com/raphaelquast/EOmaps/discussions) and I'll see what I can do!  
(I'm of course also happy about actual pull requests on features and bug-fixes!)

---------------

<p align="center">
<img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig6.gif?raw=true" alt="EOmaps example image 2" width="46%">
<img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig2.gif?raw=true" alt="EOmaps example image 1" width="50%">
<img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig7.gif?raw=true" alt="EOmaps example image 3" width="48%">
<img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig8.gif?raw=true" alt="EOmaps example image 1" width="48%">
<img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig9.gif?raw=true" alt="EOmaps example image 1" width="48%">
<img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig4.gif?raw=true" alt="EOmaps example image 1" width="48%">
</p>


## 🌳 Basic usage

🛸 **Checkout the [documentation](https://eomaps.readthedocs.io/en/latest/api.html)!** 🛸

- A list of coordinates and values is all you need as input!
  - plots of large (>1M datapoints) irregularly sampled datasets are generated in a few seconds!
- Represent your data
  - as shapes with actual geographic dimensions (ellipses, rectangles, geodetic circles)
  - via Voroni diagrams and Delaunay triangulations to get interpolated contour-plots
  - via dynamic data-shading to speed up plots with extremely large datasets
- Re-project the data to any crs supported by <a href=https://scitools.org.uk/cartopy/docs/latest/reference/crs.html#coordinate-reference-systems-crs>cartopy</a>
- Quickly add features and additional layers to the plot
  - Markers, Annotations, WebMap Layers, NaturalEarth features, Scalebars, Compasses (or North-arrows) etc.
- Interact with the data via callback-functions.

```python
import pandas as pd
from eomaps import Maps

# the data you want to plot
lon, lat, data = [1,2,3,4,5], [1,2,3,4,5], [1,2,3,4,5]

# initialize Maps object
m = Maps(crs=Maps.CRS.Orthographic())

# set the data
m.set_data(data=data, xcoord=lon, ycoord=lat, crs=4326)
# set the shape you want to use to represent the data-points
m.set_shape.geod_circles(radius=10000) # (e.g. geodetic circles with 10km radius)

# (optionally) set the appearance of the plot
m.set_plot_specs(cmap="viridis", label="a nice label")
# (optionally) classify the data
m.set_classify_specs(scheme=Maps.CLASSIFIERS.Quantiles, k=5)

# plot the map
m.plot_map()

# add a colorbar with a histogram on top
m.add_colorbar()

# add a scalebar
m.add_scalebar()

# add a compass
m.add_compass()

# add some basic features from NaturalEarth
m.add_feature.preset.coastline()

# use callback functions make the plot interactive!
m.cb.pick.attach.annotate()

# ---- add another plot-layer on a different level (1) to the map
#      (by default only layer 0 is shown!)
m3 = m.new_layer(layer=1)
...
# peek on layer 1 if you click on the map
m.cb.click.attach.peek_layer(layer=1, how=0.4)
# switch between the layers if you press "0" or "1" on the keyboard
m.cb.keypress.attach.switch_layer(layer=0, key="0")
m.cb.keypress.attach.switch_layer(layer=1, key="1")

# ---- add new layers directly from a GeoTIFF / NetCDF or CSV files
m4 = m.new_layer_from_file.GeoTIFF(...)
m4 = m.new_layer_from_file.NetCDF(...)
m4 = m.new_layer_from_file.CSV(...)
```

----

## 🌼 Thanks to

- [Jakob Quast](https://quastquest.jimdofree.com/) for designing the nice logo!

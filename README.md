
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
  🌲🌳 Checkout the <a href=https://eomaps.readthedocs.io/en/latest>documentation</a> for more details and <a href=https://eomaps.readthedocs.io/en/latest/EOmaps_examples.html>examples</a> 🌳🌲
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
- A list of coordinates and values is all you need as input!
  - plots of large (>1M datapoints) irregularly sampled datasets are generated in a few seconds!
  - Represent your data as shapes with actual geographic dimensions (ellipses, rectangles, geodetic circles)
    - or use Voroni diagrams and Delaunay triangulations to get interpolated contour-plots
  - Re-project the data to any crs supported by <a href=https://scitools.org.uk/cartopy/docs/latest/reference/crs.html#coordinate-reference-systems-crs>cartopy</a>
  - ... and get a nice colorbar with a colored histogram on top!

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
# (optionally) add a colorbar
m.add_colorbar()

# ---- add another plot-layer to the map
m2 = m.new_layer()
...
...
```
## 🌌 advanced usage
[click to show] &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; &nbsp; 🛸 Checkout the [docs](https://eomaps.readthedocs.io/en/latest/api.html)! 🛸

<details>

  <summary>🌍 Attach callback functions to interact with the plot</summary>

- Many pre-defined functions for common tasks are available!
  - display coordinates and values, add markers, compare data-layers etc.
  - ... or define your own function and attach it to the plot!
- Maps objects can be interactively connected to analyze relations between datasets!

```python
# get a nice annotation if you click on a datapoint
m.cb.pick.attach.annotate()
# draw a marker if you click on a datapoint
m.cb.pick.attach.mark(facecolor="r", edgecolor="g", shape="rectangles", radius=1, radius_crs=4326)

# show the data-layer `1` in a inset-rectangle (size=20% width of the axes) if you click on the map
m.cb.click.attach.peek_layer(how=0.2, layer=1)
#attach some custom function to interact with the map
m.cb.click.attach(<... a custom function ...>)

# show the data-layer `1` if you press "a" on the keyboard and the layer `0` if you press "q"
m.cb.keypress.attach.switch_layer(layer=0, key="q")
m.cb.keypress.attach.switch_layer(layer=1, key="a")
```

</details>

<details>

  <summary>🌕 Add additional layers and overlays</summary>

- many pre-defined interfaces for WebMap servers exist
  - OpenStreetMap
  - ESA WorldCover
  - Nasa GIBS
  - S1GBM
  - ... and more!

```python
m.add_wms(...)                      # add WebMapService layers
m.add_gdf(...)                      # add geopandas.GeoDataFrames
m.add_feature.<group>.<feature>()   # add feature-layers from NaturalEarth
m.add_colorbar(...)                 # add a colorbar to the map

m.add_annotation(...)               # add static annotations
m.add_marker(...)                   # add static markers
```
  </details>

<details>

  <summary>🪐 Save the figure</summary>

```python
m.savefig("oooh_what_a_nice_figure.png", dpi=300)
```
</details>

<details>

  <summary>🌗 Connect Maps-objects to get multiple interactive layers of data</summary>

```python
m = Maps()
...
m.plot_map()

m2 = m.new_layer(layer=2)
m2.set_data(...)
m2.set_shape(...)
...
m2.plot_map()         # plot another layer of data
m2.cb.attach.peek_layer(layer=2, how=0.25)
```
</details>

<details>

  <summary>🌏 Plot grids of maps</summary>

```python
from eomaps import MapsGrid
mgrid = MapsGrid(2, 2, crs=3857)

for m in mgrid:
   m.plot_specs.label = "asdf"

mgrid.ax_0_0.add_feature.preset.ocean()
mgrid.ax_0_1.add_feature.preset.land()
mgrid.ax_1_0.add_feature.preset.coastline()
mgrid.ax_1_1.add_feature.preset.countries()

mgrid.plot_map()      # call m.plot_map() on all Maps-objects of the grid
mgrid.join_limits()   # join limits
```
</details>

----

## 🌼 Thanks to

- [Jakob Quast](https://quastquest.jimdofree.com/) for designing the nice logo!

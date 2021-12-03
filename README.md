[![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml)
[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/EOmaps)
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
[![Documentation Status](https://readthedocs.org/projects/eomaps/badge/?version=latest)](https://eomaps.readthedocs.io/en/latest/?badge=latest)
<a href="https://www.buymeacoffee.com/raphaelquast" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png" alt="Buy Me A Coffee" align="right" style="height: 33px !important;width: 139px !important;" ></a>


# EOmaps

### ... a library to create interactive maps of geographical datasets

<ol type="none">
  <li>🌍 A simple interface to visualize geographical datasets ... a pandas DataFrame is all you need!</li>
  <ul type="none">
    <li>⬥ applicable also for large datasets with ~ 1M datapoints!  </li>
  </ul>
  <li>🌎 Quickly turn your maps into powerful interactive data-analysis widgets!</li>
  <ul type="none">
    <li>⬥ compare multiple data-layers, WebMaps etc. with only a few lines of code! </li>
    <li>⬥ use callback functions to interact with the data (or an underlying database) </li>
  </ul>
</ol>


#### 🛸 checkout the [documentation](https://eomaps.readthedocs.io/en/latest) for more details and [examples](https://eomaps.readthedocs.io/en/latest/EOmaps_examples.html) 🛸

## 🔨 installation

Installing EOmaps can be done via `pip`.  
However, to make sure all dependencies are correctly installed, make sure to have a look at the [installation instructions](https://eomaps.readthedocs.io/en/latest/general.html#installation) in the documentation!

<br/>

<p align="center">
<img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig2.gif?raw=true" alt="EOmaps example image 1">
<img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig6.gif?raw=true" alt="EOmaps example image 2">
</p>


## 🌳 basic usage
- A pandas DataFrame is all you need as input!
  - plots of large (>1M datapoints) irregularly sampled datasets are generated in a few seconds!
  - Represent your data as shapes with actual geographic dimensions
  - Re-project the data to any crs supported by `cartopy`
- Add annotations, overlays, WebMap-layers etc. to the maps
- ... and get a nice colorbar with a colored histogram on top!

```python
import pandas as pd
from eomaps import Maps

# the data you want to plot
data = pd.DataFrame(dict(lat=[...], lon=[...], value=[...]))

# initialize Maps object
m = Maps()
# set the data
m.set_data(data=data, xcoord="lon", ycoord="lat", parameter="value", crs=4326)
# set the shapes that you want to use to represent the data-points
m.set_shape.geod_circles(radius=10000) # (e.g. geodetic circles with 10km radius)
# set the appearance of the plot
m.set_plot_specs(crs=Maps.CRS.Orthographic(), cmap="viridis")
# (optionally) classify the data
m.set_classify_specs(scheme=Maps.CLASSIFIERS.Quantiles, k=5)
# plot the map
m.plot_map()
```
#### attach callback functions to interact with the plot

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
#### add additional layers and overlays
```python
m.add_wms(...)             # add WebMapService layers
m.add_wms(...)             # add WebMapTileService layers
m.add_gdf(...)             # add geo-dataframes
m.add_overlay(...)         # add overlay-layers from NaturalEarth

m.add_annotation(...)      # add static annotations
m.add_marker(...)          # add static markers
```
#### save the figure
```python
m.savefig("oooh_what_a_nice_figure.png", dpi=300)  
```
## advanced usage
#### connect Maps-objects to get multiple interactive layers of data!
```python
m = Maps()
...
m.plot_map()

m2 = Maps(parent=m) # connect Maps to get multiple interactive data-layers
m2.set_data(...)
m2.set_shape(...)
...
m2.plot_map(layer=2)         # plot another layer of data
m2.cb.attach.peek_layer(layer=2, how=0.25)
```
#### plot grids of maps
```python
from eomaps import MapsGrid
mgrid = MapsGrid(2, 2, connect=True)

for m in mgrid:
   m.plot_specs.plot_crs = 3857

mgrid.ax_0_0.plot_map()
mgrid.ax_0_1.plot_map()
mgrid.ax_1_0.plot_map()
mgrid.ax_1_1.plot_map()

mgrid.parent.join_limits(*mgrid.children)   # join limits
```

[![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml)
[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/EOmaps)
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
[![Documentation Status](https://readthedocs.org/projects/eomaps/badge/?version=latest)](https://eomaps.readthedocs.io/en/latest/?badge=latest)
# EOmaps

### A library to create interactive maps of geographical datasets.

#### 🌍 Simple interface to visualize geographical datasets  
- A `pandas.DataFrame` is all you need as input!
  - plots of large (>1M datapoints) irregularly sampled datasets are generated in a few seconds!
- Represent your data as shapes with actual geographic dimensions and re-project it to any crs supported by `cartopy`
- Add annotations, overlays, WebMap-layers etc. to the maps and get a nice colorbar with a colored histogram on top  

#### 🌎 Turn your maps into powerful interactive data-analysis widgets
- Add "callbacks" to interact with your data
   - Many pre-defined functions for common tasks are available!
      - display coordinates, values or IDs of clicked pixels, add markers, compare data-layers etc.
      - ... or define your own function and attach it to the plot!
- Connect multiple interactive maps to analyze relations between datasets

#### 🛸 check out the [documentation](https://eomaps.readthedocs.io) for more details and [examples](https://eomaps.readthedocs.io/en/latest/EOmaps_examples.html)! 🛸


## install

Installing EOmaps can be done via `pip`. To make sure all dependencies are correctly installed, please have a look at the [🛸 installation instructions 🛸](https://eomaps.readthedocs.io/en/latest/usage.html#installation) in the documentation.


## basic usage
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
m.set_plot_specs(crs=Maps.CRS, cmap="viridis")
# (optionally) classify the data
m.set_classify_specs(scheme=Maps.CLASSIFIERS.Quantiles, k=5)

# plot the map
m.plot_map()
```
#### attach callback functions to interact with the plot
```python
m.cb.pick.attach.annotate()
m.cb.pick.attach.mark(facecolor="r", edgecolor="g", shape="rectangles", radius=1, radius_crs=4326)

m.cb.click.attach.peek_layer(how="top", layer=1)
m.cb.click.attach(<... a custom function ...>)

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

m2 = Maps(gs_ax=m.figure.ax) # use the same axes
m2.connect(m)                # connect the maps-objects for shared interactivity
m2.set_data(...)
m2.set_shape(...)
...
m2.plot_map(layer=2)         # plot another layer of data
m2.cb.attach.peek_layer(layer=2, how=0.25)
```
#### plot map-grids
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

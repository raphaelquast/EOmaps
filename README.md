[![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml)
[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/EOmaps)
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
# EOmaps

A general-purpose library to plot interactive maps of geographical datasets.

#### 🌍 A simple interface to plot geographical datasets  
- An ordinary `pandas.DataFrame` is all you need as input!
  - plots of large (>1M datapoints) irregularly sampled datasets are generated in a few seconds!
- Represent your data as shapes with actual geographic dimensions 
- Reproject the map to any cartopy-projection
- Add annotations, overlays, WebMap-layers etc. to the maps 
- Get a nice colorbar with a colored histogram on top  

#### 🌎 Easily turn the plot into a clickable data-analysis widget  
- Add functions that are executed if you
  - `m.cb.click`: click anywhere on the map
  - `m.cb.pick`: "pick" a pixel of a previously plotted dataset
  - `m.cb.keypress`: press a key on the keyboard
- Many pre-defined functions for common tasks are available!
  - `annotate`: add an annotation to indicate the location and value of the clicked pixel
  - `mark`: add a markers (ellipses, rectangles, geodetic_circles etc.) at the location of the clicked pixel
  - `peek-layer`: click on the map to show another layer of data  
    (either gradually from the edges or as a rectangle around the clicked pixel)
  - ... or define your own function and attach it to the plot!

#### 🛸 check out the example-notebook:  [EOmaps_examples](https://github.com/raphaelquast/maps/blob/dev/examples/EOmaps_examples.ipynb) 🛸

![EOmaps example image](https://github.com/raphaelquast/EOmaps/blob/dev/examples/example_image.png?raw=true)

## install
The recommended way to install EOmaps with conda + pip:

1. (only if you're on WINDOWS)  
   due to an issue with libspatialindex.dll for the conda-forge build of rtree, install rtree from default channel  
   [(corresponding issue on rtree-feedstock)](https://github.com/conda-forge/rtree-feedstock/issues/31)
   ```
   conda install "rtree>=0.9.7"
   ```
2. install remaining dependencies from `conda-forge` channel
   ```
   conda install -c conda-forge numpy pandas geopandas "matplotlib>=3.0" "cartopy>=0.20.0" descartes mapclassify pyproj pyepsg
   ```
3. install EOmaps from pip
   ```
   pip install eomaps
   ```

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

# set the appearance of the plot
m.set_plot_specs(crs=4326, cmap="viridis")
# set the shapes that you want to use to represent the data-points
m.set_shape.geod_circles(radius=10000) # (e.g. geodetic circles with 10km radius)

# (optionally) classify the data
m.set_classify_specs(scheme=m.classify_specs.SCHEMES.Quantiles, k=5)

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

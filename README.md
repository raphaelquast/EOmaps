[![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml)
[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/EOmaps)
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
# EOmaps

A general-purpose library to plot interactive maps of geographical datasets.

The primary purpose is 2-fold:
1. ease the pain of creating plots of irregularly sampled geographical datasets
   - provided as 1D DataFrames and usable with large amounts of data (>1M datapoints)
   - specify pixel-dimensions in actual geographical units  
2. provide an easy-to-use way to turn the plot into a clickable data-analysis widget
   - pick datapoints, add markers/annotations, create plots, execute custom functions etc.

... additional features:  
🌍 plot the data in almost any crs you like  
🌏 add overlays to the plots (NaturalEarth features, geo-dataframes, etc.)  
🌎 get a nice colorbar with a colored histogram on top  

- check out the example-notebook: 🛸 [EOmaps_examples.ipynb](https://github.com/raphaelquast/maps/blob/dev/examples/EOmaps_examples.ipynb) 🛸

## choose how to represent your data
![alt text](https://github.com/raphaelquast/EOmaps/blob/dev/examples/plotshapes.png?raw=true)
## use the full power of cartopy to display your data
![alt text](https://github.com/raphaelquast/EOmaps/blob/dev/examples/projections.png?raw=true)

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
m.set_plot_specs(plot_epsg=4326, cmap="viridis")
# set the shapes that you want to assign to the data-points
m.set_shape.geod_circles(radius=10000)

# (optionally) classify the data
m.set_classify_specs(scheme=m.classify_specs.SCHEMES.Quantiles, k=5)

# plot the map
m.plot_map()
```
#### attach callback functions to interact with the plot
```python
m.cb.attach.annotate()
m.cb.attach.mark(facecolor="r", edgecolor="g", shape="rectangles", radius=1, radius_crs=4326)
m.cb.attach(<... a custom function ...>)
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
# save the figure
m.savefig("oooh_what_a_nice_figure.png", dpi=300)  
```
## advanced usage
#### connect Maps-objects to get multiple interactive layers of data!
```python
m2 = Maps()
m2.connect(m)       # connect the maps-objects
m2.set_data(...)
m2.set_shape(...)
...
m2.plot_map()       # plot another layer of data
m2.cb.attach.annotate()
```

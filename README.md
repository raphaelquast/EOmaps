[![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml)
[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/EOmaps)
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
# EOmaps

A general-purpose library to plot interactive maps of geographical datasets.

### basic features:
🌍 reproject & plot irregular datasets as ellipses or rectangles with actual geographical dimensions  
🌎 interact with the plot via "callback-functions"  
🌏 add overlays to the plots (NaturalEarth features, geo-dataframes, etc.)  
🌍 get a nice colorbar with a colored histogram on top  

- check out the example-notebook: 🛸 [EOmaps_examples.ipynb](https://github.com/raphaelquast/maps/blob/dev/examples/EOmaps_examples.ipynb) 🛸


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

# initialize Maps object
m = Maps()

# set the data
m.data = pd.DataFrame(dict(lat=[...], lon=[...], value=[...]))
m.set_data_specs(xcoord="lon", ycoord="lat", parameter="value", in_crs=4326)

# set the appearance of the plot
m.set_plot_specs(plot_epsg=4326, shape="rectangles")
m.set_classify_specs(scheme="Quantiles", k=5)

# plot the map
m.plot_map()

m.add_callback(...)        # attach a callback-function
m.add_discrete_layer(...)  # plot additional data-layers
m.add_gdf(...)             # plot geo-dataframes

m.add_overlay(...)         # add overlay-layers

m.add_annotation(...)      # add static annotations
m.add_marker(...)          # add static markers

# access individual objects of the generated figure
m.figure.<...>

# save the figure
m.savefig("oooh_what_a_nice_figure.png", dpi=300)  
```


### callbacks
(e.g. execute functions when clicking on the map)
- `"annotate"`: add annotations to the map
- `"mark"`: add markers to the map
- `"plot"`: generate a plot of the picked values
- `"print_to_console"`: print pixel-info to the console
- `"get_values"`: save the picked values to a dict
- `"load"`: load objects from a collection
- ... or use a custom function

    ```python
    def some_callback(self, **kwargs):
        print("hello world")
        print("the position of the clicked pixel", kwargs["pos"])
        print("the data-index of the clicked pixel", kwargs["ID"])
        print("data-value of the clicked pixel", kwargs["val"])
        self.m  # access to the Maps object
    m.add_callback(some_callback)
    ```

[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/MapIt)
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
# EOmaps

A general-purpose library to plot interactive maps of geographical datasets.

🚀  feel free to contribute!

### features
- reproject & plot datasets as ellipses or rectangles with actual geographical dimensions
- interact with the database underlying the plot via "callback-functions"
- add overlays to the plots (NaturalEarth features, geo-dataframes, etc.)
- get a nice colorbar with a colored histogram on top

## install

a simple `pip install eomaps` should do the trick

## basic usage

- check out the example-notebook: 🛸 [A_basic_map.ipynb](https://github.com/raphaelquast/maps/blob/dev/examples/A_basic_map.ipynb) 🛸

```python
import pandas as pd
from eomaps import Maps

# initialize Maps object
m = Maps()

# set the data
m.data = pd.DataFrame(dict(lat=[...], lon=[...], value=[...]))
m.set_data_specs(xcoord="lat", ycoord="lon", parameter="value", in_crs=4326)

# set the appearance of the plot
m.set_plot_specs(plot_epsg=4326, shape="rectangles")
m.set_classify_specs(scheme="Quantiles", k=5)

# plot the map
m.plot_map()

m.add_callback(...)        # attach a callback-function
m.add_discrete_layer(...)  # plot additional data-layers
m.add_gdf(...)             # plot geo-dataframes

m.add_overlay(...)         # add overlay-layers

m.add_annotation(...)      # add annotations
m.add_marker(...)          # add markers

# access individual objects of the generated figure
# (f, ax, cb, gridspec etc.)
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

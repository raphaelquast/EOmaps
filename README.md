[![codecov](https://codecov.io/gh/raphaelquast/MapIt/branch/dev/graph/badge.svg?token=25M85P7MJG)](https://codecov.io/gh/raphaelquast/MapIt)
# MapIt

a general-purpose library to plot maps of large non-rectangular datasets.

❗❗❗ this library is a **work-in-progress** and subject to structural changes ❗❗❗  
🚀  feel free to contribute!

### features
- plot data-points as ellipses or rectangles with actual geographical dimensions
- reproject data
- interact with the dataset via "callback-functions"
- add overlays to the plots (NaturalEarth features, geo-dataframes, etc.)
- get a nice colorbar with a colored histogram on top


# basic usage

- check out the example-notebook: 🛸 [A_basic_map.ipynb](https://github.com/raphaelquast/maps/blob/dev/examples/A_basic_map.ipynb) 🛸

```python
from mapit import MapIt

m = MapIt()

m.data = "... a pandas-dataframe with coordinates and data-values ..."

m.set_data_specs("... data specifications ...")
m.set_plot_specs("... variables that control the appearance of the plot ...")
m.set_classify_specs("... automatic classification of the data va mapclassify ...")

# plot the map
m.plot_map()

m.add_callback(...)
m.add_discrete_layer(...)
m.add_overlay(...)

m.figure.   # access to individual objects of the generated figure (f, ax, cb, gridspec etc.)

```

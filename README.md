# maps

a general-purpose library to plot maps of large non-rectangular datasets.

❗❗❗ this is a **work-in-progress** library that is subject to structural changes ❗❗❗  
🚀  feel free to contribute!

### features
- plot data-points as ellipses or rectangles with actual geographical dimensions
- reproject data
- interact with the dataset via "callback-functions"
- add overlays to the plots (NaturalEarth features, geo-dataframes, etc.)
- get a nice colorbar with a colored histogram on top

### ⚙ dependencies
**TODO** put this in a proper `setup.py`

```
numpy, pandas, geopandas, matplotlib, cartopy >= 0.20.0, descartes, mapclassify, pyproj
```

# basic usage

- check out the jupyter notebook: 🛸 [A_basic_map.ipynb](https://github.com/raphaelquast/maps/blob/dev/examples/A_basic_map.ipynb) 🛸

```python
from maps import Maps

m = Maps()

m.data = ... a pandas-dataframe with coordinates and data-values ...

m.set_data_specs( ... data specifications ...)
m.set_plot_specs( ... variables that control the appearance of the plot ...)
m.set_classify_specs( ... automatic classification of the data va mapclassify ...)

# plot the map
m.plot_map()

m.figure.(...)  # access to individual objects of the generated figure

```


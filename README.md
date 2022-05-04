
<p align="center">
    <a href=https://github.com/raphaelquast/EOmaps>
    <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/logo.png?raw=true" alt="EOmaps logo" width="55%">
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

<a href="https://zenodo.org/badge/latestdoi/410829039" target="_blank"><img src="https://zenodo.org/badge/410829039.svg" alt="DOI: 10.5281/zenodo.6459598" align="right" style="height: 20px !important;" ></a>

----

### A library to create interactive maps of geographical datasets.

<ul type="none">
  <li>🌍 EOmaps provides a simple and intuitive interface to visualize and interact with geographical datasets</li>
  <ul type="none">
    <li>⬥ Data can be provided as 1D or 2D <code>lists</code>, <code>numpy-arrays</code>, <code>pandas.DataFrames</code></li>
    <li>  &nbsp; &nbsp; &nbsp; or directly from GeoTIFFs,  NetCDFs and csv-files.</li>
    <li>  &nbsp; &nbsp; &nbsp; ... usable also for large datasets with millions of datapoints!</li>
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

---

### ❗ update notice ❗
> There are breaking API changes between `EOmaps v3.x` and `EOmaps v4.0`  
> To quickly update existing scripts, see: [⚙ Port script from EOmaps v3.x to v4.x](https://eomaps.readthedocs.io/en/latest/FAQ.html#port-script-from-eomaps-v3-x-to-v4-x)

<details>
<summary>[click to show] a quick summary of the API changes</summary>

- the following properties and functions have been removed:
  - ❌ `m.plot_specs.`
  - ❌ `m.set_plot_specs()`
  - Arguments are now directly passed to relevant functions:  

    ```python
    m = Maps
    # m.set_plot_specs(cmap=..., vmin=..., vmax=..., cpos=..., cpos_radius=..., histbins=...)
    # m.plot_specs.<  > = ...
    m.set_data(..., cpos=..., cpos_radius=...)
    m.plot_map(cmap=..., vmin=..., vmax=...)
    m.add_colorbar(histbins=...)
    ```


- 🔶 `m.set_shape.voroni_diagram` is renamed to `m.set_shape.voronoi_diagram`
- 🔷 custom callbacks are no longer bound to the Maps-object  
  -  the call-signature of custom callbacks has changed to:  
     `def cb(self, *args, **kwargs)  >>  def cb(*args, **kwargs)`





</details>

---


## 🔨 Installation

To install EOmaps (and all its dependencies) via the `conda` package-manager, simply use:

```python
conda install -c conda-forge eomaps
```
For more information, have a look at the [installation instructions](https://eomaps.readthedocs.io/en/latest/general.html#installation) in the documentation!
<br/>


## ✔️ Citation
Did EOmaps help in your research?  
Consider supporting the development and add a citation to your publication!

[![https://doi.org/10.5281/zenodo.6459598](https://zenodo.org/badge/410829039.svg)](https://zenodo.org/badge/latestdoi/410829039)


## 🚀 Contribute

Found a bug or got an idea for an interesting feature?  
Open an [issue](https://github.com/raphaelquast/EOmaps/issues) or start a [discussion](https://github.com/raphaelquast/EOmaps/discussions) and I'll see what I can do!  
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
  - via dynamic data-shading to speed up plots of extremely large datasets
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
m.set_data(data=data, x=lon, y=lat, crs=4326)
# set the shape you want to use to represent the data-points
m.set_shape.geod_circles(radius=10000) # (e.g. geodetic circles with 10km radius)

# (optionally) classify the data
m.set_classify_specs(scheme=Maps.CLASSIFIERS.Quantiles, k=5)

# plot the map using matplotlibs "viridis" colormap
m.plot_map(cmap="viridis", vmin=2, vmax=4)

# add a colorbar with a histogram on top
m.add_colorbar(histbins=200)

# add a scalebar
m.add_scalebar()

# add a compass (or north-arrow)
m.add_compass()

# add some basic features from NaturalEarth
m.add_feature.preset.coastline()

# add WebMap services
m.add_wms.OpenStreetMap.add_layer.default()

# use callback functions make the plot interactive!
m.cb.pick.attach.annotate()

# ----- use multiple layers to compare and analyze different datasets!
# ---- add another plot-layer to the map
m3 = m.new_layer(layer="layer 2")
m3.add_feature.preset.ocean()

# peek on layer 1 if you click on the map
m.cb.click.attach.peek_layer(layer="layer 2", how=0.4)
# switch between the layers if you press "0" or "1" on the keyboard
m.cb.keypress.attach.switch_layer(layer=0, key="0")
m.cb.keypress.attach.switch_layer(layer="layer 2", key="1")

# get a clickable widget to switch between the available plot-layers
m.util.layer_selector()

# ---- add new layers directly from GeoTIFF / NetCDF or CSV files
m4 = m.new_layer_from_file.GeoTIFF(...)
m4 = m.new_layer_from_file.NetCDF(...)
m4 = m.new_layer_from_file.CSV(...)
```

----

## 🌼 Thanks to

- [Jakob Quast](https://quastquest.jimdofree.com/) for designing the nice logo!

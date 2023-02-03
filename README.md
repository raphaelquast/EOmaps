
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

# EOmaps - Interactive maps in python!

EOmaps is a <tt>python</tt> package to visualize and analyze geographical datasets.

It is built on top of [matplotlib](matplotlib.org/) and [cartopy](https://scitools.org.uk/cartopy/docs/latest/) and aims to provide an
intuitive and easy-to-use interface to handle the following tasks:

- Speed up and simplify the creation and comparison of maps
- Visualize small datasets as well as millions of datapoints
- Handle 1D and 2D datasets and create plots from NetCDF, GeoTIFF or CSV files
- Take care of re-projecting the data
- Compare, combine and overlay multiple plot-layers and WebMap services
- Use the maps as interactive data-analysis widgets  
  (e.g. execute functions if you click on the map)
- Provide a versatile set of tools to customize the maps  
  (incl. scalebars, north-arrows and a nice colorbar with a histogram on top)
- Help arranging multiple maps (and other plots/images) in one figure
- Export high resolution images (png, jpeg etc.)

## 🔨 Installation

To install EOmaps (and all its dependencies) via the [conda](https://docs.conda.io/projects/conda/en/stable/) package-manager, simply use:
```python
conda install -c conda-forge eomaps
```
... to get a <u>**huge speedup**</u>, use [mamba](https://mamba.readthedocs.io/en/latest/) to solve the dependencies!
```python
conda install -c conda-forge mamba
mamba install -c conda-forge eomaps
```
Need more information?
- Have a look at the [🐛Installation](https://eomaps.readthedocs.io/en/latest/general.html#installation) instructions in the docs.
- Checkout the quickstart guide [🚀 From 0 to EOmaps](https://eomaps.readthedocs.io/en/latest/FAQ.html#from-0-to-eomaps-a-quickstart-guide).
<br/>

## 📖 Documentation

Make sure to have a look at the <a href=https://eomaps.readthedocs.io/en/latest><b>🌳 Documentation 🌳</b></a> which provides a lot of <a href=https://eomaps.readthedocs.io/en/latest/EOmaps_examples.html><b>🌐Examples</b></a> on how to create awesome interactive maps (incl. 🐍 source code)!

## ✔️ Citation
Did EOmaps help in your research?  
Consider supporting the development and add a citation to your publication!

[![https://doi.org/10.5281/zenodo.6459598](https://zenodo.org/badge/410829039.svg)](https://zenodo.org/badge/latestdoi/410829039)


## 🚀 Contribute

Found a bug or got an idea for an interesting feature?  
Open an [issue](https://github.com/raphaelquast/EOmaps/issues) or start a [discussion](https://github.com/raphaelquast/EOmaps/discussions), and I'll see what I can do!  

Interested in actively contributing to the library?
- Any contributions are welcome! (new features, enhancements, fixes, documentation updates, outreach etc.)
- Have a look at this [🌟 overview project](https://github.com/users/raphaelquast/projects/5/views/8) to get an overview of existing ideas that could use some help.
- Get in touch by opening a discussion in the [🐜 Contribution](https://github.com/raphaelquast/EOmaps/discussions/categories/contribution) section!


---------------
<table>
  <tr>
    <td valign="center" style="width:50%">
        <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig6.gif?raw=true" alt="EOmaps example 6">
      </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/minigifs/advanced_wms.gif?raw=true" alt="EOmaps example 2">
      </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig9.gif?raw=true" alt="EOmaps example 9">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig4.gif?raw=true" alt="EOmaps example 4">
    </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig7.gif?raw=true" alt="EOmaps example 7">
      </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig2.gif?raw=true" alt="EOmaps example 8">
      </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/minigifs/layout_editor.gif?raw=true" alt="EOmaps inset-maps">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/fig8.gif?raw=true" alt="EOmaps example 3">
    </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/example_lines.png?raw=true" alt="EOmaps example 9">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/inset_maps.png?raw=true" alt="EOmaps example 4">
    </td>
  </tr>
</table>





## 🌳 Basic usage

**Checkout the  [🚀 Basics](https://eomaps.readthedocs.io/en/latest/api.html)**  in the documentation!

```python
from eomaps import Maps
import numpy as np
### Initialize Maps object
m = Maps(crs=Maps.CRS.Orthographic(), figsize=(12, 8))

### Add map-features from NaturalEarth
m.add_feature.preset.coastline()
m.add_feature.cultural.admin_0_countries(scale=50, fc="none", ec="g", lw=0.3)

### Add imagery from open-access WebMap services
m.add_wms.OpenStreetMap.add_layer.default()

### Plot datasets
# --- Create some random data
x, y = np.mgrid[-50:40:5, -20:50:3]
data = x + y
# ---
m.set_data(data=data, x=x, y=y, crs=4326) # assign a dataset
m.set_shape.ellipses() # set how you want to represent the data-points on the map
m.set_classify_specs(scheme=Maps.CLASSIFIERS.FisherJenks, k=6) # classify the data
m.plot_map(cmap="viridis", vmin=-100, vmax=100, set_extent=False) # plot the data
m.add_colorbar(hist_bins="bins", label="What a nice colorbar") # add a colorbar

### Use callback functions to interact with the map
#   (NOTE: you can also define custom callbacks!)
# - Click callbacks are executed if you click anywhere on the map
#   (Use keypress-modifiers to trigger only if a button is pressed)
m.cb.click.attach.mark(shape="geod_circles", radius=1e5, button=3)
m.cb.click.attach.peek_layer(layer="layer 2", how=0.4)
m.cb.click.attach.annotate(modifier="a")
# - Pick callbacks identify the closest datapoint
m.cb.pick.attach.annotate()
# - Keypress callbacks are executed if you press a key on the keyboard
#   (using "m.all" ensures that the cb triggers irrespective of the visible layer)
m.all.cb.keypress.attach.switch_layer(layer="base", key="0")
m.all.cb.keypress.attach.switch_layer(layer="layer 2", key="1")

### Use multiple layers to compare and analyze different datasets
m2 = m.new_layer(layer="layer 2") # create a new plot-layer
m2.add_feature.preset.ocean() # populate the layer
# Get a clickable widget to switch between the available plot-layers
m.util.layer_selector(loc="upper center")

### Add zoomed-in "inset-maps" to highlight areas on th map
m_inset = m.new_inset_map((10, 45), radius=10, layer="base")
m_inset.add_feature.preset.coastline()
m_inset.add_feature.preset.ocean()

### Reposition axes based on a given layout (check m.get_layout())
m.apply_layout(
    {'0_map': [0.44306, 0.25, 0.48889, 0.73333],
     '1_cb': [0.0125, 0.0, 0.98, 0.23377],
     '1_cb_histogram_size': 0.8,
     '2_map': [0.03333, 0.46667, 0.33329, 0.5]}
    )

### Add a scalebar
s = m_inset.add_scalebar(lon=15.15, lat=44.45,
                         autoscale_fraction=.4,
                         scale_props=dict(n=6),
                         label_props=dict(scale=3, every=2),
                         patch_props=dict(lw=0.5)
                         )

### Add a compass (or north-arrow)
c = m_inset.add_compass(pos=(.825,.88), layer="base")

### Plot data directly from GeoTIFF / NetCDF or CSV files
#m4 = m.new_layer_from_file.GeoTIFF(...)
#m4 = m.new_layer_from_file.NetCDF(...)
#m4 = m.new_layer_from_file.CSV(...)
```

----

## 🌼 Thanks to

- [Jakob Quast](https://quastquest.jimdofree.com/) for designing the nice logo!

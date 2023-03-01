
<p align="center">
    <a href=https://github.com/raphaelquast/EOmaps>
    <img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/_static/logo.png?raw=true" alt="EOmaps logo" width="55%">
    </a>
</p>

[![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml)
[![codecov](https://codecov.io/gh/raphaelquast/EOmaps/graph/badge.svg)](https://codecov.io/gh/raphaelquast/EOmaps)
&nbsp; &nbsp; &nbsp;
[![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)
[![Conda Version](https://img.shields.io/conda/vn/conda-forge/eomaps.svg)](https://anaconda.org/conda-forge/eomaps)
&nbsp; &nbsp; &nbsp;
[![Documentation Status](https://readthedocs.org/projects/eomaps/badge/?version=latest)](https://eomaps.readthedocs.io/en/latest/?badge=latest)
&nbsp; &nbsp; &nbsp;
<a href="https://www.buymeacoffee.com/raphaelquast" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png" alt="Buy Me A Coffee" align="right" style="height: 25px !important;" ></a>

<a href="https://app.gitter.im/#/room/#EOmaps:gitter.im" target="_blank"><img src="https://img.shields.io/gitter/room/raphaelquast/EOmaps?style=social" alt="chat on gitter" align="left" style="height: 20px !important;" ></a>

<a href="https://zenodo.org/badge/latestdoi/410829039" target="_blank"><img src="https://zenodo.org/badge/410829039.svg" alt="DOI: 10.5281/zenodo.6459598" align="right" style="height: 20px !important;" ></a>

----

# EOmaps - Interactive maps in python!

EOmaps is a <tt>python</tt> package to visualize and analyze geographical datasets.

It is built on top of [matplotlib](matplotlib.org/) and [cartopy](https://scitools.org.uk/cartopy/docs/latest/) and aims to provide an
intuitive and easy-to-use interface to speed up and simplify the creation and comparison of maps.

- Visualize small datasets as well as millions of datapoints
- Handle 1D and 2D datasets with the same interface and create plots from NetCDF, GeoTIFF or CSV files
- Take care of re-projecting the data
- Compare, combine or (transparently) overlay multiple plot-layers
- Turn the maps into interactive data-analysis widgets with a few lines of code
- Provide a versatile set of tools to customize the maps (Features, WebMaps, Markers, Annotations etc.)
- Simplify the process of composing multiple maps (and other plots/images) in a single figure
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

## 📖 Documentation

Make sure to have a look at the <a href=https://eomaps.readthedocs.io/en/latest><b>🌳 Documentation 🌳</b></a> which provides a lot of <a href=https://eomaps.readthedocs.io/en/latest/EOmaps_examples.html><b>🌐Examples</b></a> on how to create awesome interactive maps (incl. 🐍 source code)!

## ✔️ Citation
Did EOmaps help in your research?  
Support the development and add a citation to your publication!

[![https://doi.org/10.5281/zenodo.6459598](https://zenodo.org/badge/410829039.svg)](https://zenodo.org/badge/latestdoi/410829039)


## 🌟 Contribute

Found a bug or got an idea for an interesting feature?  
Open an [issue](https://github.com/raphaelquast/EOmaps/issues) or start a [discussion](https://github.com/raphaelquast/EOmaps/discussions), and I'll see what I can do!  

Interested in actively contributing to the library? Awesome!
- Any contributions are welcome!
  - New features (or ideas for new features)
  - Enhancements for existing features
  - Bug-fixes, code-style improvements, unittests etc.
  - Documentation updates
  - Outreach (e.g. blog-posts, tutorials, talks ... )
- Have a look at existing [Issues](https://github.com/raphaelquast/EOmaps/contribute) or this [🌟 overview project](https://github.com/users/raphaelquast/projects/5/views/8) to see where EOmaps could use your help.
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
# --- Create some random data
x, y = np.meshgrid(range(-50, 40, 5), range(-20, 50, 3))
data = np.random.randint(-100, 100, x.shape)


### Initialize Maps object
m = Maps(layer="all", crs=Maps.CRS.Orthographic(), figsize=(12, 8))
m.add_feature.preset.coastline() # Add a map-feature from NaturalEarth

### Plot a dataset
m_data = m.new_layer("data")                   # create a new layer
m_data.set_data(data=data, x=x, y=y, crs=4326) # assign a dataset
m_data.set_shape.ellipses()                    # set how to represent the data-points
m_data.set_classify.FisherJenks(k=6)           # classify the data
m_data.plot_map(cmap="viridis", vmin=-100, vmax=100, set_extent=False) # plot the data
m_data.add_colorbar(hist_bins="bins", label="What a nice colorbar")    # add a colorbar

### Add zoomed-in "inset-maps" to highlight a specific area on th map
m_inset = m.new_inset_map((10, 45), radius=10, layer="data", plot_position=(.2, .6))
m_inset.inherit_data(m_data)               # inherit the data
m_inset.inherit_classification(m_data)     # inherit the classification
m_inset.plot_map(zorder=1)                 # plot the data on the inset-map as well
m_inset.add_feature.preset.ocean(zorder=2) # overlay some features from NaturalEarth
m_inset.add_feature.preset.coastline(zorder=3)

### Add imagery from open-access WebMap services
m_inset.add_wms.OpenStreetMap.add_layer.stamen_watercolor()

### Add a scalebar
s = m_inset.add_scalebar(lon=15.15, lat=44.45,
                         autoscale_fraction=.4,
                         scale_props=dict(n=6),
                         label_props=dict(scale=3, every=2),
                         patch_props=dict(lw=0.5, fc="w"))

### Add a compass (or north-arrow)
c = m_inset.add_compass(pos=(12.2, 51.6), pos_transform="lonlat")

### Compare and analyze multiple plot-layers
m2 = m.new_layer(layer="ocean") # create another layer
m2.add_feature.preset.ocean()   # populate the layer

# ... or use the (layer argument to directly put a feature on a specific layer)
m.add_feature.cultural.admin_0_countries(
    layer="overlay", scale=50, fc="none", ec="g", lw=0.3)

# Get a clickable widget to switch between the available plot-layers
m.util.layer_selector(loc="upper center")
# Transparently overlay the "ocean" layer on top of the "data" layer
m.show_layer("data", ("ocean", 0.8))

# ---- Attach callback functions to interact with the map
#      (Note: you can also define custom callbacks!)
### CLICK callbacks are executed if you click anywhere on the map
m.cb.click.attach.peek_layer(layer="overlay", how=0.4)
m.cb.click.attach.mark(shape="geod_circles", radius=5e5, button=3, fc="r")
# Use keypress-modifiers to trigger callbacks only if a button is pressed
m.cb.click.attach.annotate(modifier="a")

### PICK callbacks identify the closest datapoint of a dataset
m_data.cb.pick.attach.annotate(text=lambda val, **kwargs: f"value = {val:.2f}")
m_inset.cb.pick.attach.annotate()

### KEYPRESS callbacks are executed if you press a key on the keyboard
#  (using "m.all" ensures that the cb triggers irrespective of the visible layer)
m.all.cb.keypress.attach.switch_layer(layer="data", key="1")
m.all.cb.keypress.attach.switch_layer(layer="data|ocean", key="2")

### Reposition axes based on a pre-defined layout (check m.get_layout())
m.apply_layout(
    {'figsize': [12.0, 8.0],
     '0_map': [0.44306, 0.25, 0.48889, 0.73333],
     '1_cb': [0.115, 0.0, 0.775, 0.23377],
     '1_cb_histogram_size': 0.8,
     '2_inset_map': [0.03335, 0.35, 0.33329, 0.5]}
    )

### Plot data directly from GeoTIFF / NetCDF or CSV files
#m4 = m.new_layer_from_file.GeoTIFF(...)
#m4 = m.new_layer_from_file.NetCDF(...)
#m4 = m.new_layer_from_file.CSV(...)
```

----

## 🌼 Thanks to

- [Jakob Quast](https://quastquest.jimdofree.com/) for designing the nice logo!

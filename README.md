
<p align="center">
    <a href=https://github.com/raphaelquast/EOmaps>
    <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/logo.png?raw=true" alt="EOmaps logo" width="50%">
    </a>
</p>

| Tests | Package | Documentation | License | Citation |
|:-:|:-:|:-:|:-:|:-:|
| [![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml)  [![codecov](https://codecov.io/gh/raphaelquast/EOmaps/graph/badge.svg)](https://codecov.io/gh/raphaelquast/EOmaps) | [![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)  [![Conda Version](https://img.shields.io/conda/vn/conda-forge/eomaps.svg)](https://anaconda.org/conda-forge/eomaps) | [![Documentation Status](https://readthedocs.org/projects/eomaps/badge/?version=latest)](https://eomaps.readthedocs.io/en/latest/?badge=latest) |  [![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://github.com/raphaelquast/EOmaps/blob/master/LICENSE) | [![10.5281/zenodo.6459598](https://zenodo.org/badge/410829039.svg)](https://zenodo.org/badge/latestdoi/410829039) |

<a href="https://www.buymeacoffee.com/raphaelquast" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png" alt="Buy Me A Coffee" align="right" style="height: 25px !important;" ></a>
<a href="https://app.gitter.im/#/room/#EOmaps:gitter.im" target="_blank"><img src="https://img.shields.io/gitter/room/raphaelquast/EOmaps?style=social" alt="chat on gitter" align="left" style="height: 20px !important;" ></a>

----
  

<h3 align="center">A python package to visualize and analyze geographical datasets.</h3>

> **EOmaps** aims to provide a comprehensive, flexible, well-documented and easy-to-use API to create publication-ready maps that can directly be used for interactive data analysis.

## How does it work?

**EOmaps** is built on top of [matplotlib](https://matplotlib.org/) and [cartopy](https://scitools.org.uk/cartopy/docs/latest/) and integrates well with the scientific python infrastructure (e.g., `numpy`, `pandas`, `geopandas`, `xarray` etc.), allowing you to visualize point-, raster- or vector-datasets provided in almost any format you can imagine, no matter if you're dealing with just a few unsorted datapoints or multi-dimensional stacks of global high-resolution datasets.  

Figures created with EOmaps are multi-layered, so you can (transparently) overlay and interactively compare your datasets with ease. With the accompanying GUI widget, you can quickly switch layers, change the layout, examine the large collection of features and web-map services, and explore the capabilities of EOmaps. 
Once you're map is ready, you can export it as high-resolution image or vector-graphic for further editing.
Leveraging the powers of matplotlib, you can also embed interactive maps in Jupyter Notebooks, GUI frameworks like `Qt`, `tkinter`, `wx` or on a webpage (html).


> [!TIP]
> For a quick hands-on introduction, checkout this article on dev.to:  
> [Geographic data visualization and analysis with EOmaps: Interactive maps in python!](https://dev.to/raphaelquast/geographic-data-visualization-and-analysis-with-eomaps-interactive-maps-in-python-48e1)

---

### What can EOmaps do for you?

<!-- 
<img src=https://eomaps.readthedocs.io/en/latest/_images/intro.png width=40%>
<img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/minigifs/companion_widget.gif?raw=true" alt="EOmaps GUI" width=40%>
-->

Checkout the [🌱 Basics](https://eomaps.readthedocs.io/en/latest/api_basics.html) in the documentation to get started!

<table><tr><td valign="top">

- Create [▤ multi-layered maps](https://eomaps.readthedocs.io/en/latest/api_basics.html#layer-management)  
  (and interactively compare layers with each other)
- [🔴 Visualize datasets](https://eomaps.readthedocs.io/en/latest/api_data_visualization.html) with millions of datapoints  
  (and handle reprojections)
- Get a useful [🧰 CompanionWidget GUI](https://eomaps.readthedocs.io/en/latest/api_companion_widget.html)
- Use [🛸 Callbacks](https://eomaps.readthedocs.io/en/latest/api_callbacks.html) to make your figure interactive
- Adjust the layout with the [🏗️ LayoutEditor](https://eomaps.readthedocs.io/en/latest/api_layout_editor.html)
- [🗺 Export](https://eomaps.readthedocs.io/en/latest/api_basics.html#image-export-jpeg-png-svg-etc) high resolution images (png, jpeg, tiff, ...)  
  or vektor graphics (svg, eps, pdf ...)
    
</td><td valign="top">

- Provide a comprehensive set of tools to customize the map
  - [🌵NaturalEarth features](https://eomaps.readthedocs.io/en/latest/api_naturalearth_features.html)
  - [📏Scalebars](https://eomaps.readthedocs.io/en/latest/api_scalebar.html)
  - [▦ Gridlines](https://eomaps.readthedocs.io/en/latest/api_gridlines.html)
  - [🛰 WebMap layers](https://eomaps.readthedocs.io/en/latest/api_webmaps.html)
  - [🏕 Annotations, Markers, Lines, Logos...](https://eomaps.readthedocs.io/en/latest/api_annotations_markers_etc.html)
- . . . and much more!  
    
</td></tr></table>


## 🔨 Installation

To install **EOmaps** (and all its dependencies) with the [conda](https://docs.conda.io/projects/conda/en/stable/) package-manager, simply use:
```python
conda install -c conda-forge eomaps
```

> [!TIP]
> To get a <u>**huge speedup**</u>, use [mamba](https://mamba.readthedocs.io/en/latest/) to solve the dependencies!
> ```python
> mamba install -c conda-forge eomaps
> ```
 

> Advanced users can also use `pip` to install **EOmaps** (and selectively install optional dependency groups)
> ```pyhton
> pip install eomaps       # install only minimal required dependencies
> pip install eomaps[all]  # install all optional dependencies
> ...
> ```

Need more information?
- Have a look at the [🐛Installation](https://eomaps.readthedocs.io/en/latest/installation.html) instructions in the docs.
- Checkout the quickstart guide [🚀 From 0 to EOmaps](https://eomaps.readthedocs.io/en/latest/FAQ.html#from-0-to-eomaps-a-quickstart-guide).

## 📖 Documentation

Make sure to have a look at the <a href=https://eomaps.readthedocs.io/en/latest><b>📖 Documentation </b></a>!  
It provides a lot of <a href=https://eomaps.readthedocs.io/en/latest/EOmaps_examples.html><b>🌐Examples</b></a> on how to create awesome interactive maps (incl. 🐍 source code)!

## ✔️ Citation
Did EOmaps help in your research?  
Support the development and add a citation to your publication!

<a href="https://doi.org/10.5281/zenodo.6459598"><img src="https://zenodo.org/badge/410829039.svg" alt="https://zenodo.org/badge/latestdoi/410829039" align="left"></a>

<details>
<summary>BibTeX</summary>
<br>
The following BibTeX entry uses the DOI that always points to the latest release of EOmaps!<br>
(You can get the DOI for a specific version form the <a href="https://doi.org/10.5281/zenodo.6459598">zenodo-page</a>)

```bibtex
@software{eomaps,
  author       = {Raphael Quast},
  title        = {EOmaps: A python package to visualize and analyze geographical datasets.},
  doi          = {10.5281/zenodo.6459598},
  url          = {https://doi.org/10.5281/zenodo.6459598}
}
```
    
</details>


## 🌟 Contribute

Interested in contributing to EOmaps? Awesome!

- Checkout the [🚀 Contribution Guide](https://eomaps.readthedocs.io/en/latest/contribute.html) on how to get started!

> Found a bug or got an idea for an interesting feature?  
> Open an [issue](https://github.com/raphaelquast/EOmaps/issues) or start a [discussion](https://github.com/raphaelquast/EOmaps/discussions), and I'll see what I can do!  


---------------

<table>
  <tr>
    <td colspan=2 valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/assets/22773387/fe27e290-019e-4179-929d-d33bc590758e" alt="EOmaps GUI">
    </td>
      <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig9.gif?raw=true" alt="EOmaps example 9">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig4.gif?raw=true" alt="EOmaps example 4">
    </td>
  </tr>
  <tr>
    <td valign="center" style="width:50%">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig6.gif?raw=true" alt="EOmaps example 6">
      </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/minigifs/advanced_wms.gif?raw=true" alt="EOmaps example 2">
      </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig7.gif?raw=true" alt="EOmaps example 7">
      </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig3.gif?raw=true" alt="EOmaps example 8">
      </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/minigifs/layout_editor.gif?raw=true" alt="EOmaps inset-maps">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig8.gif?raw=true" alt="EOmaps example 3">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/example_lines.png?raw=true" alt="EOmaps example 9">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/inset_maps.png?raw=true" alt="EOmaps example 4">
    </td>

  </tr>
</table>

----

## ☕ Support

The development of EOmaps is supported by:

<a href="https://www.tuwien.at/en/mg/geo/rs"><img height=30 align=left src="https://github.com/raphaelquast/EOmaps/assets/22773387/1ad88e68-eb16-4549-8159-8b4a6db8ab28"> TU Wien Department of Geodesy and Geoinformation - Research Area Remote Sensing</a>

<br/>

## 🌼 Thanks to

- [Jakob Quast](https://quastquest.jimdofree.com/) for designing the nice logo!

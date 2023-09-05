
<p align="center">
    <a href=https://github.com/raphaelquast/EOmaps>
    <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/logo.png?raw=true" alt="EOmaps logo" width="55%">
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

**EOmaps** is a <tt>python</tt> package to visualize and analyze geographical datasets.

It is built on top of [matplotlib](matplotlib.org/) and [cartopy](https://scitools.org.uk/cartopy/docs/latest/) and provides an intuitive and easy-to-use interface to speed up and simplify the creation and comparison of maps.

> For a quick hands-on introduction, checkout this article on dev.to:  
> [Geographic data visualization and analysis with EOmaps: Interactive maps in python!](https://dev.to/raphaelquast/geographic-data-visualization-and-analysis-with-eomaps-interactive-maps-in-python-48e1)
>
> ---

### What can EOmaps do for you?

- Create [▤ multi-layered maps](https://eomaps.readthedocs.io/en/latest/api.html#basics) and interactively compare different layers with each other
- [🔴 Visualize datasets](https://eomaps.readthedocs.io/en/latest/api.html#data-visualization) with  millions of datapoints and handle reprojections
- Provide a comprehensive set of tools to customize the map
  - [🌵NaturalEarth features](https://eomaps.readthedocs.io/en/latest/api.html#naturalearth-features)
  - [📏Scalebars](https://eomaps.readthedocs.io/en/latest/api.html#scalebars)
  - [▦ Gridlines](https://eomaps.readthedocs.io/en/latest/api.html#gridlines)
  - [🛰 WebMap layers](https://eomaps.readthedocs.io/en/latest/api.html#webmap-layers)
  - [🏕 Annotations, Markers, Lines, Logos...](https://eomaps.readthedocs.io/en/latest/api.html#annotations-markers-lines-logos-etc)
  - . . .
- Get a useful [🧰 CompanionWidget](https://eomaps.readthedocs.io/en/latest/api.html#companion-widget) GUI
- Use [🛸 Callbacks](https://eomaps.readthedocs.io/en/latest/api.html#callbacks-make-the-map-interactive) to interact with the figure
- Interactively re-arrange multiple maps in a figure with the [🏗️ LayoutEditor](https://eomaps.readthedocs.io/en/latest/api.html#layout-editor)
- [🗺 Export](https://eomaps.readthedocs.io/en/latest/api.html#export-the-map-as-jpeg-png-etc) publication ready high resolution images (png, jpeg, tiff, ...)  
or export figures as vektor graphics (svg, eps, pdf ...)
- . . . and much more!  

Checkout the [🌱 Basics](https://eomaps.readthedocs.io/en/latest/api.html#basics) in the documentation to get started!

<img src=https://eomaps.readthedocs.io/en/latest/_images/intro.png width=50%>

## 🔨 Installation

To install EOmaps (and all its dependencies) via the [conda](https://docs.conda.io/projects/conda/en/stable/) package-manager, simply use:
```python
conda install -c conda-forge eomaps
```
> ... to get a <u>**huge speedup**</u>, use [mamba](https://mamba.readthedocs.io/en/latest/) to solve the dependencies!
> ```python
> conda install -c conda-forge mamba
> mamba install -c conda-forge eomaps
> ```
Need more information?
- Have a look at the [🐛Installation](https://eomaps.readthedocs.io/en/latest/general.html#installation) instructions in the docs.
- Checkout the quickstart guide [🚀 From 0 to EOmaps](https://eomaps.readthedocs.io/en/latest/FAQ.html#from-0-to-eomaps-a-quickstart-guide).

## 📖 Documentation

Make sure to have a look at the <a href=https://eomaps.readthedocs.io/en/latest><b>📖 Documentation </b></a> which provides a lot of <a href=https://eomaps.readthedocs.io/en/latest/EOmaps_examples.html><b>🌐Examples</b></a> on how to create awesome interactive maps (incl. 🐍 source code)!

## ✔️ Citation
Did EOmaps help in your research?  
Support the development and add a citation to your publication!

[![https://doi.org/10.5281/zenodo.6459598](https://zenodo.org/badge/410829039.svg)](https://zenodo.org/badge/latestdoi/410829039)


## 🌟 Contribute

Interested in contributing to EOmaps? Awesome!

- Checkout the [🚀 Contribution Guide](https://eomaps.readthedocs.io/en/latest/contribute.html) on how to get started!

> Found a bug or got an idea for an interesting feature?  
> Open an [issue](https://github.com/raphaelquast/EOmaps/issues) or start a [discussion](https://github.com/raphaelquast/EOmaps/discussions), and I'll see what I can do!  


---------------


<center><img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/minigifs/companion_widget.gif?raw=true" alt="EOmaps example 6" width=50%></center>


<table>
  <tr>
    <td valign="center" style="width:50%">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig6.gif?raw=true" alt="EOmaps example 6">
      </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/minigifs/advanced_wms.gif?raw=true" alt="EOmaps example 2">
      </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig9.gif?raw=true" alt="EOmaps example 9">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig4.gif?raw=true" alt="EOmaps example 4">
    </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig7.gif?raw=true" alt="EOmaps example 7">
      </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig2.gif?raw=true" alt="EOmaps example 8">
      </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/minigifs/layout_editor.gif?raw=true" alt="EOmaps inset-maps">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/fig8.gif?raw=true" alt="EOmaps example 3">
    </td>
  </tr>
  <tr>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/example_lines.png?raw=true" alt="EOmaps example 9">
    </td>
    <td valign="center">
        <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/_static/inset_maps.png?raw=true" alt="EOmaps example 4">
    </td>
  </tr>
</table>

----

## 🌼 Thanks to

- [Jakob Quast](https://quastquest.jimdofree.com/) for designing the nice logo!

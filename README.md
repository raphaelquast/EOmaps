
<p align="center">
    <a href=https://github.com/raphaelquast/EOmaps>
    <img src="https://github.com/raphaelquast/EOmaps/blob/master/docs/source/_static/logo.png?raw=true" alt="EOmaps logo" width="55%">
    </a>
</p>

<div align="center">


|     Tests & Review      | [![tests](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml/badge.svg?branch=master)](https://github.com/raphaelquast/EOmaps/actions/workflows/testMaps.yml) | [![codecov](https://codecov.io/gh/raphaelquast/EOmaps/graph/badge.svg)](https://codecov.io/gh/raphaelquast/EOmaps)  |                    [![pyOpenSci](https://tinyurl.com/y22nb8up)](https://github.com/pyOpenSci/software-submission/issues/138)                    |
| :---------------------: | :------------------------------------------------------------------------------------------------------------------------------------------------------------------------------: | :-----------------------------------------------------------------------------------------------------------------: | :---------------------------------------------------------------------------------------------------------------------------------------------: |
| Package & Documentation |                                                [![pypi](https://img.shields.io/pypi/v/eomaps)](https://pypi.org/project/eomaps/)                                                 | [![Conda Version](https://img.shields.io/conda/vn/conda-forge/eomaps.svg)](https://anaconda.org/conda-forge/eomaps) | [![Documentation Status](https://readthedocs.org/projects/eomaps/badge/?version=latest)](https://eomaps.readthedocs.io/en/latest/?badge=latest) |
|   License & Citation    |                [![License: BSD 3 clause](https://img.shields.io/badge/License-BSD_3_clause-blue.svg)](https://github.com/raphaelquast/EOmaps/blob/master/LICENSE)                |  [![10.5281/zenodo.6459598](https://zenodo.org/badge/410829039.svg)](https://zenodo.org/badge/latestdoi/410829039)  |                                                                                                                                                 |


</div>

<a href="https://www.buymeacoffee.com/raphaelquast" target="_blank"><img src="https://www.buymeacoffee.com/assets/img/custom_images/yellow_img.png" alt="Buy Me A Coffee" align="right" style="height: 25px !important;" ></a>
<a href="https://app.gitter.im/#/room/#EOmaps:gitter.im" target="_blank"><img src="https://img.shields.io/gitter/room/raphaelquast/EOmaps?style=social" alt="chat on gitter" align="left" style="height: 20px !important;" ></a>

----

<h3 align="center">A python package to visualize and analyze geographical datasets.</h3>

<table>
<tr><td>  
<i><b>EOmaps</b> aims to provide a comprehensive, flexible, well-documented and easy-to-use API to create publication-ready maps that can directly be used for interactive data analysis.</i>
</td></tr>
</table>

## What can I do with EOmaps?

**EOmaps** is built on top of [matplotlib](https://matplotlib.org/) and [cartopy](https://scitools.org.uk/cartopy/docs/latest/) and integrates well with the scientific python infrastructure (e.g., [numpy](https://numpy.org/), [pandas](https://pandas.pydata.org/), [geopandas](https://geopandas.org/), [xarray](https://xarray.dev/) etc.), allowing you to visualize point-, raster- or vector-datasets provided in almost any format you can imagine, no matter if you're dealing with just a few unsorted datapoints or multi-dimensional stacks of global high-resolution datasets.  

Figures created with EOmaps are multi-layered, so you can (transparently) overlay and interactively compare your datasets with ease. With the accompanying GUI widget, you can quickly switch layers, change the layout, examine the large collection of features and web-map services, and explore the capabilities of EOmaps.
Once you're map is ready, you can export it as high-resolution image or vector-graphic for further editing.
Leveraging the powers of matplotlib, you can also embed interactive maps in Jupyter Notebooks, on a webpage or in GUI frameworks like Qt, tkinter etc..

> [!IMPORTANT]
>
> EOmaps is 100% free and open-source.  
> As such, acknowledgement is extremely important to allow continued support and development of the package.
>  
> Did EOmaps help in your research? $\Rightarrow$ **Add a ✔️ Citation to your publication!**
>
> <a href="https://doi.org/10.5281/zenodo.6459598"><img src="https://zenodo.org/badge/410829039.svg" alt="https://zenodo.org/badge/latestdoi/410829039" align="left"></a>
>
> <details>
> <summary>BibTeX</summary>
> <br>
> The following BibTeX entry uses a DOI that always points to the latest release of EOmaps!<br>
> (You can get the DOI for a specific version form the <a href="https://doi.org/10.5281/zenodo.6459598">zenodo-page</a>)
>
> ```bibtex
> @software{eomaps,
>   author       = {Raphael Quast},
>   title        = {EOmaps: A python package to visualize and analyze geographical datasets.},
>   doi          = {10.5281/zenodo.6459598},
>   url          = {https://doi.org/10.5281/zenodo.6459598}
> }
> ```
>  
> </details>
>

## 🚀 Getting started

Head over to the start-page of the <a href=https://eomaps.readthedocs.io/><b>📖 Documentation </b></a> to get an overview of all available features and functionalities!

> [!TIP]
> For a quick hands-on introduction, checkout this article on dev.to:  
> [Geographic data visualization and analysis with EOmaps: Interactive maps in python!](https://dev.to/raphaelquast/geographic-data-visualization-and-analysis-with-eomaps-interactive-maps-in-python-48e1)


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
> ```python
> pip install eomaps       # install only minimal required dependencies
> pip install eomaps[all]  # install all optional dependencies
> ...
> ```

For more detailes, have a look at the [Installation Instructions](https://eomaps.readthedocs.io/en/dev/installation.html) or the quickstart guide ["From 0 to EOmaps"](https://eomaps.readthedocs.io/en/dev/quickstart_quide.html#quickstart-guide)!


## 🌟 Contribute

Interested in contributing to EOmaps? **Awesome!**  
You can find detailed instructions on how to setup EOmaps for development in the [Contribution Guide](https://eomaps.readthedocs.io/en/dev/contribute/contribute.html)!

> Found a bug or got an idea for an interesting feature?  
> Open an [issue](https://github.com/raphaelquast/EOmaps/issues) or start a [discussion](https://github.com/raphaelquast/EOmaps/discussions), and I'll see what I can do!  


---------------

<table>
  <tr>
    <td colspan=2 valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/user_guide/interactivity/api_companion_widget.html"><img src="https://github.com/raphaelquast/EOmaps/assets/22773387/fe27e290-019e-4179-929d-d33bc590758e" alt="EOmaps GUI Example"></a>
    </td>
      <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/auto_examples/widgets/timeseries.html#example-timeseries"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/example_images/example_timeseries.gif?raw=true" alt="EOmaps Timeseries Example"></a>
    </td>
    <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/auto_examples/callbacks/callbacks.html#example-callbacks"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/example_images/example_callbacks.gif?raw=true" alt="EOmaps Callbacks Example"></a>
    </td>
  </tr>
  <tr>
    <td valign="center" style="width:50%">
        <a href="https://eomaps.readthedocs.io/en/dev/auto_examples/images/webmaps.html#example-webmaps"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/example_images/example_webmaps.gif?raw=true" alt="EOmaps Webmaps Example"></a>
      </td>
    <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/user_guide/map_features/api_webmaps.html#setting-webmap-properties"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/minigifs/advanced_wms.gif?raw=true" alt="EOmaps Webmaps Example 2"></a>
      </td>
    <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/auto_examples/geomap_components/scalebars.html#example-scalebars"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/example_images/example_scalebars.gif?raw=true" alt="EOmaps Scalebars Example"></a>
      </td>
    <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/auto_examples/Maps/multiple_maps.html#example-multiple-maps"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/example_images/example_multiple_maps.gif?raw=true" alt="EOmaps Multiple Maps Example"></a>
      </td>
  </tr>
  <tr>
    <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/user_guide/interactivity/api_layout_editor.html"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/minigifs/layout_editor.gif?raw=true" alt="EOmaps LayoutEditor Example"></a>
    </td>
    <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/auto_examples/geometry/vector_data.html#example-vector-data"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/example_images/example_vector_data.gif?raw=true" alt="EOmaps Vector Data Example"></a>
    </td>
    <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/auto_examples/geometry/lines.html#example-lines"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/example_images/example_lines.png?raw=true" alt="EOmaps Lines Example"></a>
    </td>
    <td valign="center">
        <a href="https://eomaps.readthedocs.io/en/dev/auto_examples/Maps/inset_maps.html#example-inset-maps"><img src="https://github.com/raphaelquast/EOmaps/blob/dev/docs/source/_static/example_images/example_inset_maps.png?raw=true" alt="EOmaps InsetMaps Example"></a>
    </td>

  </tr>
</table>

----

## ☕ Support

The development of EOmaps has been supported by:

<a href="https://www.tuwien.at/en/mg/geo/rs"><img height=30 align=left src="https://github.com/raphaelquast/EOmaps/assets/22773387/1ad88e68-eb16-4549-8159-8b4a6db8ab28"> TU Wien Department of Geodesy and Geoinformation - Research Area Remote Sensing</a>

<br/>

## 🌼 Thanks to

- [Jakob Quast](https://quastquest.jimdofree.com/) for designing the nice logo!

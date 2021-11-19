🌐 EOmaps examples
==================

... a collection of examples that show how to create beautiful interactive maps.

🐣 Quickly visualize your data
------------------------------

Here are the 3 basic steps to visualize your data:

    1. Initialize a Maps-object with ``m = Maps()``

    2. set the data and its specifications via

      .. code-block:: python

        m.set_data_specs(
            m.data = "a pandas-DataFrame holding the data & coordinates"
            parameter = "the DataFrame-column you want to plot",
            xcord = "the name of the DataFrame-column representing the x-coordinates"
            ycord = "the name of the DataFrame-column representing the y-coordinates"
            crs = "the coordinate-system of the x- and y- coordinates"
        )

    3. call ``m.plot_map()`` to generate the map!

.. code-block:: python

    from eomaps import Maps
    import pandas as pd
    import numpy as np

    # create some data
    lon, lat = np.meshgrid(np.arange(-20, 40, .25), np.arange(30, 60, .25))
    data = pd.DataFrame(dict(lon=lon.flat,
                             lat=lat.flat,
                             data_variable=np.sqrt(lon**2 + lat**2).flat
                             )
                        ).sample(15000)

    m = Maps()
    m.set_data(data = data,
               parameter="data_variable",
               xcoord="lon",
               ycoord="lat",
               in_crs=4326)

    m.plot_map()
    m.cb.pick.attach.annotate()  # add a basic annotation (on left-click)

.. image:: _static/fig1.gif

.. raw:: html

   <hr>


🌍 Data-classification and multiple Maps in one figure
------------------------------------------------------

-  create grids of maps via ``MapsGrid`` specification to
-  classify your data via classifiers provided by the ``mapclassify`` module
-  add individual callback functions to each subplot and connect events

.. code-block:: python

    from eomaps import MapsGrid, Maps
    import pandas as pd
    import numpy as np

    # create some data
    lon, lat = np.meshgrid(np.arange(-20, 40, .5), np.arange(30, 60, .5))
    data = pd.DataFrame(dict(lon=lon.flat,
                             lat=lat.flat,
                             data_variable=np.sqrt(lon**2 + lat**2).flat
                             )
                        ).sample(4000)

    # --------- initialize a grid of Maps objects
    mg = MapsGrid(1, 3)

    # --------- set specs for the first axes
    mg.m_0_0.set_data_specs(data=data, xcoord="lon", ycoord="lat", in_crs=4326)
    mg.m_0_0.set_plot_specs(crs=4326, title="epsg=4326")
    mg.m_0_0.set_classify_specs(scheme="EqualInterval", k=10)

    # --------- set specs for the second axes
    mg.m_0_1.copy_from(mg.m_0_0, copy_data="share")
    mg.m_0_1.set_plot_specs(crs=Maps.crs_list.Stereographic(), title="Stereographic")
    mg.m_0_1.set_shape.rectangles()
    mg.m_0_1.set_classify_specs(scheme="Quantiles", k=4)

    # --------- set specs for the third axes
    mg.m_0_2.copy_from(mg.m_0_0, copy_data="share")
    mg.m_0_2.set_plot_specs(crs=3035, title="epsg=3035")
    mg.m_0_2.set_classify_specs(scheme="StdMean", multiples=[-1, -.75, -.5, -.25, .25, .5, .75, 1])

    for m in mg:
        m.plot_map()
        m.figure.ax_cb.tick_params(rotation=90, labelsize=8)

    # --------- set figsize and use a "tight_layout"
    mg.f.set_figheight(5)
    mg.f.tight_layout()

    # add some callbacks to indicate the clicked data-point
    for m in mg:
        m.cb.pick.attach.mark(fc="r", ec="none", buffer=1, permanent=True, shape=m.shape.name)
        m.cb.pick.attach.mark(fc="none", ec="r", lw=1, buffer=5, permanent=True, shape=m.shape.name)

        m.cb.click.attach.mark(fc="none", ec="k", lw=2, buffer=10, permanent=False, shape=m.shape.name)

    mg.m_0_1.cb.pick.attach.annotate(layer=11, text="the closest point is here!")
    # put it on a layer > 10 (the default for markers) so that it appears above the markers

    # share click & pick-events between the maps
    mg.share_click_events()
    mg.share_pick_events()


.. image:: _static/fig2.gif



🗺 Customize the appearance of the plot
---------------------------------------

-  use ``m.set_plot_specs()`` to set the general appearance of the plot
-  after creating the plot, you can access individual objects via ``m.figure.<...>`` … most importantly:

   -  ``coll`` : the collection representing the data on the map
   -  ``f`` : the matplotlib figure
   -  ``ax``, ``ax_cb``, ``ax_cb_plot`` : the axes used for plotting the map, colorbar and histogram
   -  ``gridspec``, ``cb_gridspec`` : the matplotlib GridSpec instances for the plot and the colorbar

.. code-block:: python

    from eomaps import Maps
    import pandas as pd
    import numpy as np

    # create some data
    lon, lat = np.meshgrid(np.arange(-30, 60, .25), np.arange(30, 60, .3))
    data = pd.DataFrame(dict(lon=lon.flat,
                             lat=lat.flat,
                             data_variable=np.sqrt(lon**2 + lat**2).flat
                             )
                        ).sample(3000)

    # ---------initialize a Maps object and set the data
    m = Maps()
    m.set_data(data=data, xcoord="lon", ycoord="lat", in_crs=4326)

    # --------- set the appearance of the plot
    m.set_plot_specs(
        label="some parameter",      # set the label of the colorbar
        title="What a nice figure",  # set the title of the figure
        cmap="RdYlBu",               # set the colormap
        crs=3857,                    # plot the map in a pseudo-mercator projection
        histbins="bins",             # use the histogram-bins as set by the classification scheme
        vmin=35,                     # set all values below vmin to vmin
        vmax=60,                     # set all values above vmax to vmax
        cpos="c",                    # the pixel-coordinates represent the "center-position"
        alpha=.75,                   # add some transparency
        add_colorbar=True,           # print the colorbar + histogram
        coastlines=True,             # add coastlines provided by NaturalEarth
        density=True,                # make the histogram values represent the "probability-density"
    )

    m.set_shape.geod_circles(radius=30000)

    # --------- set the classification scheme that should be applied to the data
    m.set_classify_specs(scheme="UserDefined", bins=[35, 36, 37, 38,
                                                     45, 46, 47, 48,
                                                     55, 56, 57, 58])

    # plot the map with some additional arguments passed to the polygons
    m.plot_map(edgecolor="k", linewidth=0.5)

    # ------------------ set the size and position of the figure and its axes
    # change width & height
    m.figure.f.set_figwidth(9)
    m.figure.f.set_figheight(5)

    # adjust the padding
    m.figure.gridspec.update(bottom=0.1, top=.95, left=0.075, right=.95, hspace=0.2)
    # add a y-label to the histogram
    _ = m.figure.ax_cb_plot.set_ylabel("The Y label")

    # --------- customize the appearance of the colorbar
    # change the height-ratio between the colorbar and the histogram
    m.figure.cb_gridspec.set_height_ratios([1, .0001])
    # manually position the colorbar anywhere on the figure
    m.figure.set_colorbar_position(pos=[0.125, 0.1 , .83, .15], ratio=999)


.. image:: _static/fig3.png



🛸 Turn your plot into a powerful data-analysis tool
----------------------------------------------------

-  **callback functions** can easily be attached to the plot to turn it
   into an interactive plot-widget!

   -  there’s a nice list of (customizeable) pre-defined callbacks:

      -  ``annotate`` (and ``clear_annotations``)
      -  ``mark`` (and ``clear_markers``)
      -  ``peek_layer`` (and ``switch_layer``)
      -  ``plot``, ``print_to_console``, ``get_values``, ``load``...

   -  … but you can also define a custom one!

.. code-block:: python

    from eomaps import Maps
    import pandas as pd
    import numpy as np

    # create some data
    #lon, lat = np.mgrid[-20:40, 30:60]
    lon, lat = np.meshgrid(np.linspace(-20,40, 50),
                           np.linspace(30,60, 50))

    data = pd.DataFrame(dict(lon=lon.flat, lat=lat.flat, data=np.sqrt(lon**2 + lat**2).flat))

    # --------- initialize a Maps object and plot a basic map
    m1 = Maps()
    m1.set_data(data = data, xcoord="lon", ycoord="lat", in_crs=4326)
    m1.set_plot_specs(plot_crs=3035,
                      title="A clickable widget!",
                      histbins="bins")
    m1.set_shape.rectangles()
    m1.set_classify_specs(scheme="EqualInterval", k=5)
    m1.plot_map()
    m1.figure.f.set_figheight(8)

    # --------- attach pre-defined CALLBACK funcitons ---------

    ### add a temporary annotation and a marker if you left-click on a pixel
    m1.cb.pick.attach.mark(button=1, permanent=False, fc=[0,0,0,.5], ec="w", ls="--", buffer=2.5, shape="ellipses", layer=1)
    m1.cb.pick.attach.annotate(button=1, permanent=False, bbox=dict(boxstyle="round", fc="w", alpha=0.75), layer=10)
    ### save all picked values to a dict accessible via m1.cb.get.picked_vals
    cid = m1.cb.pick.attach.get_values(button=1)

    ### add a permanent marker if you right-click on a pixel
    m1.cb.pick.attach.mark(button=3, permanent=True, facecolor=[1, 0,0,.5], edgecolor="k", buffer=1, shape="rectangles", layer=1)

    ### add a customized permanent annotation if you right-click on a pixel
    def text(m, ID, val, pos, ind):
        return f"ID={ID}"
    cid = m1.cb.pick.attach.annotate(button=3, permanent=True, bbox=dict(boxstyle="round", fc="r"), text=text, xytext=(10, 10),
                                layer=9, # put the permanent annotations on a layer below the temporary annotations
                                )

    ### remove all permanent markers and annotations if you middle-click anywhere on the map
    cid = m1.cb.pick.attach.clear_annotations(button=2)
    cid = m1.cb.pick.attach.clear_markers(button=2)

    # --------- define a custom callback to update some text to the map
    txt = m1.figure.f.text(.5, .35, "You clicked on 0 pixels so far",
                          fontsize=15, horizontalalignment="center",
                          verticalalignment="top",
                          color="w", fontweight="bold", animated=True)
    txt2 = m1.figure.f.text(.18, .9, "   lon    /    lat " + "\n",
                          fontsize=12, horizontalalignment="right",
                          verticalalignment="top",
                          fontweight="bold", animated=True)

    # add the custom text objects to the blit-manager (m.BM) to avoid re-drawing the whole
    # image if the text changes. (use a high layer number to draw the texts above all other things)
    m1.BM.add_artist(txt, layer=20)
    m1.BM.add_artist(txt2, layer=20)

    def cb1(self, pos, ID, val, **kwargs):
        # update the text that indicates how many pixels we've clicked
        nvals = len(self.cb.pick.get.picked_vals['ID'])
        txt.set_text(f"You clicked on {nvals} pixel" +
                      ("s" if nvals > 1 else "") +
                      "!\n... and the " +
                      ("average" if nvals > 1 else "") +
                      f"value is {np.mean(self.cb.pick.get.picked_vals['val']):.3f}")

        # update the list of lon/lat coordinates on the top left of the figure
        d = self.data.loc[ID]
        lonlat_list = txt2.get_text().splitlines()
        if len(lonlat_list) > 10:
            lonlat_txt = lonlat_list[0] + "\n" + "\n".join(lonlat_list[-10:]) + "\n"
        else:
            lonlat_txt = txt2.get_text()
        txt2.set_text(lonlat_txt + f"{d['lon']:.2f}  /  {d['lat']:.2f}" + "\n")

    cid = m1.cb.pick.attach(cb1, button=1)

    def cb2(self, pos, ID, val, **kwargs):
        # plot a marker at the pixel-position
        l, = self.figure.ax.plot(*pos, marker="*", animated=True)
        # print the value at the pixel-position
        t = self.figure.ax.text(pos[0], pos[1]-150000, f"{val:.2f}", horizontalalignment="center", verticalalignment="bottom", color=l.get_color(), animated=True)
        # add the artists to the Blit-Manager (m1.BM) to avoid triggering a re-draw of the whole figure each time the callback triggers

        # use layer=11 to make sure the marker is drawn ABOVE the temporary annotations (by default drawn on layer 10)
        self.BM.add_artist(l, layer=11)
        # use layer=1 to draw the text BELOW the annotations
        self.BM.add_artist(t, layer=1)
    cid = m1.cb.pick.attach(cb2, button=3)

    # add some static text
    _ = m1.figure.f.text(.7, .85, "Left-click: temporary annotations\nRight-click: permanent annotations\nMiddle-click: clear permanent annotations",
                         fontsize=10, horizontalalignment="left",
                         verticalalignment="top",
                         color="k", fontweight="bold")

    m1.cb.click.attach.mark(fc="r", ec="none", radius=10000, shape="geod_circles", permanent=False)
    m1.cb.click.attach.mark(fc="none", ec="r", radius=50000, shape="geod_circles", permanent=False)



.. image:: _static/fig4.gif



🌲 🏡🌳 Add overlays and indicators
-----------------------------------

… an a bit more advanced example - use “connected” Maps-objects to get
multiple interactive data-layers - add fancy static annotations and
markers

… generation of the plot might take a bit longer since overlays might
need to be downloaded first!

.. code-block:: python

    from eomaps import Maps
    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt

    # create some data
    lon, lat = np.meshgrid(np.linspace(-20,40, 100),
                           np.linspace(30,60, 100))
    data = pd.DataFrame(dict(lon=lon.flat, lat=lat.flat, param=(((lon - lon.mean())**2 - (lat - lat.mean())**2)).flat))
    data_OK = data[data.param >= 0]
    data_OK.var = np.sqrt(data_OK.param)
    data_mask = data[data.param < 0]

    # --------- initialize a Maps object and plot a basic map
    m = Maps()
    m.set_data(data = data_OK, xcoord="lon", ycoord="lat", in_crs=4326)
    m.set_plot_specs(crs=m.crs_list.Orthographic(),
                     title="Wooohoo, a flashy map-widget with static indicators!",
                     histbins=200,
                     cmap="Spectral_r")
    m.set_shape.rectangles(mesh=True)
    m.set_classify_specs(scheme="Quantiles", k=10)

    m.plot_map()
    m.figure.f.set_figheight(7)

    # ... add a basic "annotate" callback
    cid = m.cb.click.attach.annotate(bbox=dict(alpha=0.75), color="w")

    # --------- add another layer of data to indicate the values in the masked area
    #           (copy all defined specs but the classification)
    m2 = m.copy(connect=True, copy_classify_specs=False, gs_ax=m.figure.ax)
    m2.data_specs.data = data_mask
    m2.set_shape.rectangles(mesh=False)
    m2.plot_specs.cmap="magma"
    m2.plot_map()

    # --------- add another layer with data that is dynamically updated if we click on the masked area
    m3 = m.copy(connect=True, copy_classify_specs=False, gs_ax=m.figure.ax)
    m3.data_specs.data = data_OK.sample(1000)
    m3.set_shape.ellipses(radius=25000, radius_crs=3857)
    m3.set_plot_specs(cmap="gist_ncar")
    # plot the map and assign a "dynamic_layer_idx" to allow dynamic updates of the collection
    m3.plot_map(edgecolor="w", linewidth=0.25, layer=10, dynamic=True)

    # --------- define a callback that will change the position and data-values of the additional layer
    def callback(self, **kwargs):
        selection = np.random.randint(0, len(m3.data), 1000)
        m3.figure.coll.set_array(data_OK.param.iloc[selection])

    # attach the callback to the second Maps object such that it triggers when we click on the masked-area
    m2.cb.click.attach(callback)

    # --------- add some basic overlays from NaturalEarth
    m.add_overlay(dataspec=dict(resolution='10m',
                                category='physical',
                                name='lakes'),
                  styledict=dict(ec="none", fc="b"))
    m.add_overlay(dataspec=dict(resolution='10m',
                                category='cultural',
                                name='admin_0_countries'),
                  styledict=dict(ec=".75", fc="none", lw=0.5))
    m.add_overlay(dataspec=dict(resolution='10m',
                                category='cultural',
                                name='urban_areas'),
                  styledict=dict(ec="none", fc="r"))
    m.add_overlay(dataspec=dict(resolution='10m',
                                category='physical',
                                name='rivers_lake_centerlines'),
                  styledict=dict(ec="b", fc="none", lw=0.25))

    # --------- add a customized legend for the overlays
    m.add_overlay_legend(ncol=2, loc="lower center", facecolor="w", framealpha=1,
                         update_hl={"admin_0_countries":       [plt.Line2D([], [], c=".75"), "Country boarders"],
                                    "rivers_lake_centerlines": [plt.Line2D([], [], c="b", alpha=0.5), "Rivers"],
                                    "lakes":                   [None, "Lakes"],
                                    "urban_areas":             [None, "Urban Areas"]},
                         sort_order=["lakes", "rivers_lake_centerlines", "urban_areas", "admin_0_countries"])

    # --------- add some fancy (static) indicators for selected pixels
    mark_id = 6060
    for buffer in np.linspace(1, 5, 10):
        m.add_marker(ID=mark_id, shape="ellipses", radius="pixel", fc=[1,0,0,.1], ec="r", buffer=buffer*5)
    m.add_marker(ID=mark_id, shape="rectangles", radius="pixel", fc="g", ec="y", buffer=3, alpha=0.5)
    m.add_marker(ID=mark_id, shape="ellipses", radius="pixel", fc="k", ec="none", buffer=.2)
    m.add_annotation(ID=mark_id, text=f"Here's Vienna!\n... the data-value is={m.data.param.loc[mark_id]:.2f}",
                     xytext=(80, 85), textcoords="offset points", bbox=dict(boxstyle="round", fc="w", ec="r"), horizontalalignment="center",
                     arrowprops=dict(arrowstyle="fancy", facecolor="r", connectionstyle="arc3,rad=0.35"))

    mark_id = 3324
    m.add_marker(ID=mark_id, shape="ellipses", radius=3 ,fc="none", ec="g", ls="--", lw=2)
    m.add_annotation(ID=mark_id, text="", xytext=(0, 98), textcoords="offset points",
                     arrowprops=dict(arrowstyle="fancy", facecolor="g", connectionstyle="arc3,rad=-0.25"))

    m.add_marker(ID=mark_id, shape="geod_circles", radius=500000, radius_crs=3857, fc="none", ec="b", ls="--", lw=2)
    m.add_annotation(ID=mark_id, text="Here's the center of:\n    $\\bullet$ a blue 'circle' with 50km radius\n    $\\bullet$ a green 'circle' with 3deg radius",
                     xytext=(-80, 100), textcoords="offset points", bbox=dict(boxstyle="round", fc="w", ec="k"), horizontalalignment="left",
                     arrowprops=dict(arrowstyle="fancy", facecolor="w", connectionstyle="arc3,rad=0.35"))


.. image:: _static/fig5.gif

👀 FAQ
=======

🕷 Using EOmaps with the Spyder IDE
-----------------------------------

To use the whole potential of EOmaps with the awesome `Spyder IDE <https://www.spyder-ide.org>`_  ,
the plot-settings must be adjusted to ensure that ``matplotlib`` plots remain interactive.

- By default, plots are rendered as static images into the "plots-pane"... to avoid this and create
  interactive ``matplotlib`` widgets instead, go to the preferences and set the "Graphics backend" to "Automatic" :

.. image:: _static/spyder_preferences.png


🕷 Using EOmaps with the PyCharm IDE
------------------------------------

The `PyCharm IDE <https://www.jetbrains.com/pycharm/>`_  automatically registers its own matplotlib backend
which (for some unknown reason) freezes on interactive plots.

To my knowledge there are 2 possibilities to force ``pycharm`` to use the original ``matplotlib`` backends:

- | 🚲 The "manual" way:
  | Add the following lines to the start of each script:
  | (for more info and alternative backends see `matpltolib docs <https://matplotlib.org/stable/users/explain/backends.html>`_)

  .. code-block:: python

    import matpltolib
    matplotlib.use("Qt5Agg")

- | 🚗 The "automatic" way:
  | Go to the preferences and add the aforementioned lines to the *"Starting script"*
  | (to ensure that the ``matplotlib`` backend is always set prior to running a script)

  .. image:: _static/pycharm_preferences.png


In addition, if you use a **commercial version** of PyCharm, make sure to **disable** *"Show plots in tool window"*
in the **Python Scientific** preferences since it forces plots to be rendered as static images.

.. image:: _static/pycharm_preferences_2.png




📓 Using EOmaps with Jupyter Notebooks
--------------------------------------

While EOmaps works best with matplotlib's ``Qt5Agg`` backend, most of the functionalities work
reasonably well if you want the figures embedded in a Jupyter Notebook.


🔸 For jupyter-lab (and classic notebooks) you can use the ``ipympl`` backend

- To install, simply use ``conda install -c conda-forge ipympl``
- Once it's installed, (and before you start plotting) use the magic ``%matplotlib widget`` to activate the backend.
- See here for more details: https://github.com/matplotlib/ipympl

🔸 For classical notebooks, there's also the ``nbagg`` backend provided by matplotlib

- To use it, simply execute the magic ``%matplotlib notebook`` before starting to plot.

🔸 Finally, you can also use the magic ``%matplotlib qt`` and use the ``qt5agg`` backend within Jupyter Notebooks!

- This way the plots will NOT be embedded in the notebook but they are created as separate widgets.


Checkout the `matplotlib doc <https://matplotlib.org/stable/users/explain/interactive.html#jupyter-notebooks-jupyterlab>`_
for more info!

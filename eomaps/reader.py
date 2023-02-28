from functools import wraps
import numpy as np
from pyproj import CRS
from pathlib import Path

pd = None


def _register_pandas():
    global pd
    try:
        import pandas as pd
    except ImportError:
        return False

    return True


xar = None


def _register_xarray():
    global xar
    try:
        import xarray as xar
    except ImportError:
        return False
    return True


rioxarray = None


def _register_rioxarray():
    global rioxarray
    try:
        import rioxarray
    except ImportError:
        return False
    return True


def identify_geotiff_cmap(path, band=1):
    """
    Identify GeoTIFF colormap.

    Check if a GeoTiff file contains a color specification and return appropriate
    colormap and classify-specs to plot the data

    Parameters
    ----------
    path : str
        The path to the GeoTIFF file.
    band : int
        The band to use for identifying the colormap.

    Returns
    -------
    cmap : matplotlib colormap
        The identified colormap
    classify_specs : dict
        A dict that can be used as classify-specs.

    """
    try:
        try:
            import rasterio
            from matplotlib.colors import ListedColormap

            with rasterio.open(path) as tifffile:
                c = tifffile.colormap(band)

            colors = np.array(list(c.values())) / 255
            bins = list(c)

            cmap = ListedColormap(colors)

            classify_specs = dict(scheme="UserDefined", bins=bins)
        except ValueError:
            print(
                f"EOmaps: No cmap found for GeoTIFF band {band}, defaulting to 'viridis'"
            )
            classify_specs = None
            cmap = "viridis"
        except IndexError:
            print(
                f"EOmaps: No cmap found for GeoTIFF band {band}, defaulting to 'viridis'"
            )
            classify_specs = None
            cmap = "viridis"

        return cmap, classify_specs

    except ImportError as ex:
        print("EOmaps: Unable to identify cmap for GeoTIFF:", ex)
        return "viridis", None


class read_file:
    """
    A collection of methods to read data from a file.

    More details in the individual reader-functions!

    Currently supported filetypes are:

    - NetCDF (requires `xarray`)
    - GeoTIFF (requires `rioxarray` + `xarray`)
    - CSV (requires `pandas`)

    """

    @staticmethod
    def GeoTIFF(
        path_or_dataset,
        crs_key=None,
        data_crs=None,
        sel=None,
        isel=None,
        set_data=None,
        mask_and_scale=False,
    ):
        """
        Read all relevant information necessary to add a GeoTIFF to the map.

        Parameters
        ----------
        path_or_dataset : str, pathlib.Path or xar.Dataset
            - If str or pathlib.Path: The path to the file.
            - If xar.Dataset: The xarray.Dataset instance to use
        crs_key : str, optional
            The variable-name that holds the crs-information.

            By default the following options are tried:
            - <crs_key> = "spatial_ref", "crs"

              - crs = file.<crs_key>.attrs["crs_wkt"]
              - crs = file.<crs_key>.attrs["wkt"]
        data_crs : None, optional
            Optional way to specify the crs of the data explicitly.
            ("crs_key" will be ignored if "crs" is provided!)
        sel : dict, optional
            A dictionary of keyword-arguments passed to `xarray.Dataset.sel()`
            (see https://xarray.pydata.org/en/stable/generated/xarray.Dataset.sel.html)
            The default is None.
        isel : dict, optional
            A dictionary of keyword-arguments passed to `xarray.Dataset.isel()`.
            (see https://xarray.pydata.org/en/stable/generated/xarray.Dataset.isel.html)
            The default is {"band" : 0}  (if sel is None).
        set_data : None or eomaps.Maps
            Indicator if the dataset should be returned None or assigned to the
            provided Maps-object  (e.g. by using m.set_data(...)).
            The default is None.
        mask_and_scale : bool
            Indicator if the data should be masked and scaled with respect to the
            file-attributes *_FillValue*, *scale_factor* and *add_offset*.

            - If False: the data will only be scaled "on demand", avoiding costly
              initialization of very large float-arrays. Masking will still be applied
              in case a *_FillValue* attribute has been found.
              (a masked-array is returned to avoid dtype conversions)
              The encoding is accessible via `m.data_specs.encoding`
            - If True: all data will be masked and scaled after reading.
              For more details see `xarray.open_dataset`.

            NOTE: using `mask_and_scale=True` results in a conversion of the data-values
            to floats!! For very large datasets this can cause a huge increase in
            memory-usage! EOmaps handles the scaling internally to show correct
            values for callbacks and colorbars, even if `mask_and_scale=False`!

            The default is False.

        Returns
        -------
        dict (if set_data is False) or None (if set_data is True)
            A dict that contains the data required for plotting.

        Examples
        --------

        # to just read the data use one of the following:

        >>> path = r"C:/folder/file.tiff"
        >>> data = m.read_file.GeoTIFF(path)

        >>> file = xar.open_dataset(path)
        >>> data = m.read_file.GeoTIFF(file)

        >>> with xar.open_dataset(path) as file:
        >>>     data = m.read_file.GeoTIFF(file)

        # to assign the data directly to the Maps-object, use `set_data=<Maps object>`:

        >>> m.read_file.GeoTIFF(path, set_data=m)

        """

        assert _register_xarray() and _register_rioxarray(), (
            "EOmaps: missing dependency for read_GeoTIFF: 'xarray' 'rioxarray'\n"
            + "To install, use 'conda install -c conda-forge xarray'"
            + "To install, use 'conda install -c conda-forge rioxarray'"
        )

        if isel is None and sel is None:
            isel = {"band": 0}

        opened = False  # just an indicator if we have to close the file in the end
        try:
            if isinstance(path_or_dataset, (str, Path)):
                # if a path is provided, open the file (and close it in the end)
                ncfile = xar.open_dataset(
                    path_or_dataset, mask_and_scale=mask_and_scale
                )
                opened = True

            elif isinstance(path_or_dataset, xar.Dataset):
                # if an xar.Dataset is provided, use it
                ncfile = path_or_dataset
            else:
                raise ValueError(
                    "EOmaps: `m.read_file.GeoTIFF` accepts only a path "
                    + "to a GeoTIFF file or an `xarray.Dataset` object!"
                )

            if sel is not None:
                usencfile = ncfile.sel(**sel)
            elif isel is not None:
                usencfile = ncfile.isel(**isel)
            else:
                usencfile = ncfile

            ncdims = list(usencfile.dims)  # dimension order as stored in the file
            varnames = list(usencfile)
            if len(varnames) > 1:
                raise AssertionError(
                    "EOmaps: there is more than 1 variable name available! "
                    + "please select a specific dataset via the 'sel'- "
                    + f"or 'isel' kwargs. Available variable names: {varnames}"
                )
            else:
                usencfile = usencfile[varnames[0]]

            dims = list(usencfile.dims)
            if len(dims) > 2:
                raise AssertionError(
                    "EOmaps: there are more than 2 dimensions! "
                    + "please select a specific dataset via the 'sel'- "
                    + f"or 'isel' kwargs. Available dimensionss: {dims}"
                )

            if data_crs is None:
                for crskey in ["spatial_ref", "crs"]:
                    if crskey in ncfile:
                        crsattr = ncfile[crskey].attrs
                        for wktkey in ["crs_wkt", "wkt"]:
                            if wktkey in crsattr:
                                data_crs = crsattr[wktkey]

            assert data_crs is not None, (
                "EOmaps: No crs information found... please specify the crs "
                + "via the 'data_crs' argument explicitly!"
            )
            # check if we need to transpose the data
            # (e.g. if data is provided with [y, x] dimensions instead of [x, y])
            data = np.moveaxis(usencfile.values, *[dims.index(i) for i in ncdims])

            x, y = (
                getattr(usencfile, ncdims[0]).values,
                getattr(usencfile, ncdims[1]).values,
            )

            # only use masked arrays if mask_and_scale is False!
            # (otherwise the mask is already applied as NaN's in the float-array)
            # Using masked-arrays ensures that we can deal with integers as well!
            if mask_and_scale is False:
                encoding = usencfile.attrs
                fill_value = encoding.get("_FillValue", None)
                if fill_value:
                    data = np.ma.masked_where(data == fill_value, data, copy=False)
            else:
                encoding = None

            if set_data is not None:
                set_data.set_data(
                    data=data,
                    x=x,
                    y=y,
                    crs=data_crs,
                    encoding=encoding,
                )
            else:
                return dict(
                    data=data,
                    x=x,
                    y=y,
                    crs=data_crs,
                    encoding=encoding,
                )
        finally:
            if opened:
                ncfile.close()

    @staticmethod
    def NetCDF(
        path_or_dataset,
        parameter=None,
        coords=None,
        crs_key=None,
        data_crs=None,
        sel=None,
        isel=None,
        set_data=None,
        mask_and_scale=False,
    ):
        """
        Read all relevant information necessary to add a NetCDF to the map.

        Parameters
        ----------
        path_or_dataset : str, pathlib.Path or xar.Dataset
            - If str or pathlib.Path: The path to the file.
            - If xar.Dataset: The xarray.Dataset instance to use

        parameter : str
            The name of the variable to use as parameter.
            If None, the first variable of the NetCDF file will be used.
            The default is None.
        coords : tuple of str
            The names of the variables to use as x- and y- coordinates.
            (e.g. ('lat', 'lon'))
            The default is None in which case the coordinate-dimensions defined in the
            NetCDF will be used.
        crs_key : str, optional
            The attribute-name that holds the crs-information.

            By default the following options are tried:
            - <crs_key> = "spatial_ref", "crs", "crs_wkt"

              - crs = file.attrs.<crs_key>
        data_crs : None, optional
            Optional way to specify the crs of the data explicitly.
            ("crs_key" will be ignored if "data_crs" is provided!)
        sel : dict, optional
            A dictionary of keyword-arguments passed to `xarray.Dataset.sel()`
            (see https://xarray.pydata.org/en/stable/generated/xarray.Dataset.sel.html)
            The default is None.
        isel : dict, optional
            A dictionary of keyword-arguments passed to `xarray.Dataset.isel()`.
            (see https://xarray.pydata.org/en/stable/generated/xarray.Dataset.isel.html)
            The default is {"band" : 0}  (if sel is None).
        set_data : None or eomaps.Maps
            Indicator if the dataset should be returned None or assigned to the
            provided Maps-object  (e.g. by using m.set_data(...)).
            The default is None.
        mask_and_scale : bool
            Indicator if the data should be masked and scaled with respect to the
            file-attributes *_FillValue*, *scale_factor* and *add_offset*.

            - If False: the data will only be scaled "on demand", avoiding costly
              initialization of very large float-arrays. Masking will still be applied
              in case a *_FillValue* attribute has been found.
              (a masked-array is returned to avoid dtype conversions)
              The encoding is accessible via `m.data_specs.encoding`
            - If True: all data will be masked and scaled after reading.
              For more details see `xarray.open_dataset`.

            NOTE: using `mask_and_scale=True` results in a conversion of the data-values
            to floats!! For very large datasets this can cause a huge increase in
            memory-usage! EOmaps handles the scaling internally to show correct
            values for callbacks and colorbars, even if `mask_and_scale=False`!

            The default is False.

        Returns
        -------
        dict (if set_data is False) or None (if set_data is True)
            A dict that contains the data required for plotting.

        Examples
        --------

        # to just read the data use one of the following:

        >>> path = r"C:/folder/file.tiff"
        >>> data = m.read_file.NetCDF(path)

        >>> file = xar.open_dataset(path)
        >>> data = m.read_file.NetCDF(file)

        >>> with xar.open_dataset(path) as file:
        >>>     data = m.read_file.NetCDF(file)

        # to assign the data directly to the Maps-object, use `set_data=<Maps object>`:

        >>> m.read_file.NetCDF(path, set_data=m)


        """

        assert _register_xarray(), (
            "EOmaps: missing dependency for read_GeoTIFF: 'xarray'\n"
            + "To install, use 'conda install -c conda-forge xarray'"
        )

        opened = False  # just an indicator if we have to close the file in the end
        try:
            if isinstance(path_or_dataset, (str, Path)):
                # if a path is provided, open the file (and close it in the end)
                opened = True
                ncfile = xar.open_dataset(
                    path_or_dataset, mask_and_scale=mask_and_scale
                )
            elif isinstance(path_or_dataset, xar.Dataset):
                # if an xar.Dataset is provided, use it
                ncfile = path_or_dataset
            else:
                raise ValueError(
                    "EOmaps: `m.read_file.NetCDF` accepts only a path "
                    + "to a NetCDF file or an `xarray.Dataset` object!"
                )

            if sel is not None:
                usencfile = ncfile.sel(**sel)
            elif isel is not None:
                usencfile = ncfile.isel(**isel)
            else:
                usencfile = ncfile

            if parameter is None:
                parameter = next(iter(ncfile))
                print(f"EOmaps: Using NetCDF variable '{parameter}' as parameter.")
            else:
                assert parameter in ncfile, (
                    f"EOmaps: The provided parameter-name '{parameter}' is not valid."
                    + f"Available parameters are {list(ncfile)}"
                )

            data = usencfile[parameter]
            if coords is None:
                coords = list(data.dims)
                if len(coords) != 2:
                    raise AssertionError(
                        "EOmaps: could not identify the coordinate-dimensions! "
                        + "Please provide coordinate-names explicitly via the "
                        + "'coords' kwarg.\n"
                        + f"Available coordinates: {list(usencfile.coords)}\n"
                        + f"Available variables: {list(ncfile)}"
                    )
                else:
                    print(f"EOmaps: Using NetCDF coordinates: {coords}")

            if data_crs is None:
                for crskey in ["spatial_ref", "crs", "crs_wkt"]:
                    if crskey in usencfile.attrs:
                        data_crs = usencfile.attrs[crskey]

            assert data_crs is not None, (
                "EOmaps: No crs information found... please specify the crs "
                + "via the 'data_crs' or 'crs_key' argument explicitly!"
                + f"Available parameters are {list(ncfile)}, {list(ncfile.attrs)}"
            )

            if coords[0] in usencfile.coords:
                x = usencfile.coords[coords[0]]
            elif coords[0] in usencfile:
                x = usencfile[coords[0]]
            else:
                raise AssertionError(
                    f"EOmaps: Coordinate '{coords[0]}' is not present in the NetCDF.\n"
                    + f"Available coordinates: {list(usencfile.coords)}\n"
                    + f"Available variables: {list(ncfile)}"
                )

            if coords[1] in usencfile.coords:
                y = usencfile.coords[coords[1]]
            elif coords[1] in usencfile:
                y = usencfile[coords[1]]
            else:
                raise AssertionError(
                    f"EOmaps: Coordinate '{coords[1]}' is not present in the NetCDF\n"
                    + f"Available coordinates: {list(usencfile.coords)}\n"
                    + f"Available variables: {list(ncfile)}"
                )

            check_shapes = (
                (data.shape == (x.size, y.size))
                or (data.shape == (y.size, x.size))
                or (data.shape == x.shape and data.shape == y.shape)
            )

            if not check_shapes:
                dstr = str([f"{i}: {j}" for i, j in zip(data.dims, data.shape)])
                xstr = str([f"{i}: {j}" for i, j in zip(x.dims, x.shape)])
                ystr = str([f"{i}: {j}" for i, j in zip(y.dims, y.shape)])
                raise AssertionError(
                    "EOmaps: Invalid dimensions of data and coordinates!\n"
                    f"data: {dstr}\n"
                    f"x   : {xstr}\n"
                    f"y   : {ystr}\n"
                )

            if data.shape == (y.size, x.size) and len(x.shape) == 1:
                data = data.values.T
            else:
                data = data.values

            # only use masked arrays if mask_and_scale is False!
            # (otherwise the mask is already applied as NaN's in the float-array)
            # Using masked-arrays ensures that we can deal with integers as well!
            if mask_and_scale is False:
                encoding = dict(
                    scale_factor=getattr(usencfile[parameter], "scale_factor", 1),
                    add_offset=getattr(usencfile[parameter], "add_offset", 0),
                    _FillValue=getattr(usencfile[parameter], "_FillValue", None),
                )
                fill_value = encoding.get("_FillValue", None)
                if fill_value:
                    data = np.ma.masked_where(data == fill_value, data, copy=False)
            else:
                encoding = None

            if set_data is not None:
                set_data.set_data(
                    data=data,
                    x=x.values,
                    y=y.values,
                    crs=data_crs,
                    parameter=parameter,
                    encoding=encoding,
                )
            else:
                return dict(
                    data=data,
                    x=x.values,
                    y=y.values,
                    crs=data_crs,
                    parameter=parameter,
                    encoding=encoding,
                )

        finally:
            if opened:
                ncfile.close()

    @staticmethod
    def CSV(
        path,
        parameter=None,
        x=None,
        y=None,
        crs=None,
        set_data=None,
        **kwargs,
    ):
        """
        Read all relevant information necessary to add a CSV-file to the map.

        Use it as:

        >>> data = m.read_file.CSV(...)

        or

        >>> m.read_file.CSV(set_data=m)

        Parameters
        ----------
        path : str
            The path to the csv-file.
        parameter : str
            The column-name to use as parameter.
        x : str
            The column-name to use as "x" coordinates.
        y : str
            The column-name to use as "y" coordinates.
        crs : crs-identifier
            The crs of the data. (see "Maps.set_data" for details)

        kwargs :
            additional kwargs passed to `pandas.read_csv`.

        Returns
        -------
        dict (if set_data is False) or None (if set_data is True)
            A dict that contains the data required for plotting.

        """
        assert _register_pandas(), (
            "EOmaps: missing dependency for read_csv: 'pandas'\n"
            + "To install, use 'conda install -c conda-forge pandas'"
        )

        data = pd.read_csv(path, **kwargs)

        for key in [parameter, x, y]:
            assert key in data, (
                f"EOmaps: the parameter-name {key} is not a column of the csv-file!\n"
                + f"Available columns are: {list(data)}"
            )

        if set_data is not None:
            set_data.set_data(
                data=data[[parameter, x, y]],
                x=x,
                y=y,
                crs=crs,
                parameter=parameter,
            )
        else:
            return dict(
                data=data[[parameter, x, y]],
                x=x,
                y=y,
                crs=crs,
                parameter=parameter,
            )


def _from_file(
    data,
    crs=None,
    shape=None,
    classify_specs=None,
    val_transform=None,
    coastline=False,
    parent=None,
    figsize=None,
    layer=None,
    extent=None,
    **kwargs,
):
    """
    Convenience function to initialize a new Maps-object from a file.

    EOmaps will try several attempts to plot the data (fastest first).

    - fist, shading as a raster is used: `m.set_shape.shade_raster`
    - if it fails, shading with points is used: `m.set_shape.shade_raster`
    - if it fails, ordinary ellipse-plot is created: `m.set_shape.ellipses`


    This function is (in principal) a shortcut for:

        >>> m = Maps(crs=..., layer=...)
        >>> m.set_data(**m.read_GeoTIFF(...))
        >>> m.set_classify_specs(...)
        >>> m.plot_map(**kwargs)

    Parameters
    ----------
    path : str
        The path to the GeoTIFF file.
    crs : any, optional
        The plot-crs. A crs-identifier usable with cartopy.
        The default is None, in which case the crs of the GeoTIFF is used if
        possible, else epsg=4326.
    sel : dict, optional
        A dict of keyword-arguments passed to `xarray.Dataset.sel()`
        The default is {"band": 0}.
    isel : dict, optional
        A dict of keyword-arguments passed to `xarray.Dataset.isel()`.
        The default is None.
    classify_specs : dict, optional
        A dict of keyword-arguments passed to `m.set_classify_specs()`.
        The default is None.
    val_transform : None or callable
        A function that is used to transform the data-values.
        (e.g. to apply scaling etc.)

        >>> def val_transform(a):
        >>>     return a / 10
    coastline: bool
        Indicator if a coastline should be added or not.
        The default is False
    parent : eomaps.Maps
        The parent Maps object to use (e.g. `parent.new_layer()` will be used
        to create a Maps-object for the dataset)
    figsize : tuple, optional
        The size of the figure. (Only relevant if parent is None!)
    extent : tuple or string

        - If a tuple is provided, it is used to set the plot-extent
          before plotting via `m.set_extent(extent)`

          - (x0, x1, y0, y1) : provide the extent in lat/lon
          - ((x0, x1, y0, y1), crs) : provide the extent in the given crs

        - If a string is provided, it is used to attempt to set the plot-extent
          before plotting via `m.set_extent_to_location(extent)`

        The default is None
    kwargs :
        Keyword-arguments passed to `m.plot_map()`
    Returns
    -------
    m : eomaps.Maps
        The created Maps object.

    """
    from . import Maps  # do this here to avoid circular imports

    if val_transform:
        data["data"] = val_transform(data["data"])

    if parent is not None:
        if layer is None:
            layer = parent.layer

        m = parent.new_layer(
            copy_data_specs=False,
            copy_classify_specs=False,
            copy_shape=False,
            layer=layer,
        )
    else:
        if layer is None:
            layer = "base"
        # get crs from file
        if crs is None:
            crs = data.get("crs", None)
        # try if it's possible to initialize a Maps-object with the file crs
        try:
            crs = Maps._get_cartopy_crs(crs=crs)
        except Exception:
            try:
                crs = Maps._get_cartopy_crs(crs=CRS.from_user_input(crs))

            except Exception:
                crs = 4326
                print(f"EOmaps: could not use native crs... defaulting to epsg={crs}.")

        m = Maps(crs=crs, figsize=figsize, layer=layer)

    if coastline:
        m.add_feature.preset.coastline()

    m.set_data(**data)
    if classify_specs:
        m.set_classify_specs(**classify_specs)

    if shape is not None:
        # use the provided shape
        if isinstance(shape, str):
            getattr(m.set_shape, shape)()
        elif isinstance(shape, dict):
            getattr(m.set_shape, shape["shape"])(
                **{k: v for k, v in shape.items() if k != "shape"}
            )

    if extent is not None:
        if isinstance(extent, tuple):
            if len(extent) == 2 and len(extent[0]) == 4:
                m.set_extent(extent[0], crs=extent[1])
            elif len(extent) == 4:
                m.set_extent(extent)
            else:
                print(
                    "EOmaps: unable to identify the provided extent"
                    f"{extent}... defaulting to global"
                )
        elif isinstance(extent, str):
            m.set_extent_to_location(extent)
        else:
            print(
                "EOmaps: unable to identify the provided extent"
                f"{extent}... defaulting to global"
            )

    m.plot_map(**kwargs)
    return m


class from_file:
    """
    A collection of methods to initialize a new Maps-object from a file.
    (see individual reader-functions for details)

    Currently supported filetypes are:

    - NetCDF (requires `xarray`)
    - GeoTIFF (requires `rioxarray` + `xarray`)
    - CSV (requires `pandas`)
    """

    @staticmethod
    def NetCDF(
        path_or_dataset,
        parameter=None,
        coords=None,
        data_crs_key=None,
        data_crs=None,
        sel=None,
        isel=None,
        plot_crs=None,
        shape=None,
        classify_specs=None,
        val_transform=None,
        coastline=False,
        mask_and_scale=False,
        **kwargs,
    ):
        """
        Convenience function to initialize a new Maps-object from a NetCDF file.

        If no explicit shape is provided, EOmaps will try several attempts to plot
        the data (fastest first).

        - fist, shading as a raster is used: `m.set_shape.shade_raster`
        - if it fails, shading with points is used: `m.set_shape.shade_raster`
        - if it fails, ordinary ellipse-plot is created: `m.set_shape.ellipses`

        This function is (in principal) a shortcut for:

        >>> m = Maps(crs=...)
        >>> m.set_data(**m.read_file.NetCDF(...))
        >>> m.set_classify_specs(...)
        >>> m.plot_map(**kwargs)

        Parameters
        ----------
        path_or_dataset : str, pathlib.Path or xar.Dataset
            - If str or pathlib.Path: The path to the file.
            - If xar.Dataset: The xarray.Dataset instance to use
        parameter : str, optional
            The name of the variable to use as parameter.
            If None, the first variable of the NetCDF file will be used.
            The default is None.
        coords : tuple of str
            The names of the variables to use as x- and y- coordinates.
            (e.g. ('lat', 'lon'))
            The default is None in which case the coordinate-dimensions defined in the
            NetCDF will be used.
        data_crs_key : str, optional
            The attribute-name that holds the crs-information.

            By default the following options are tried:
            - <crs_key> = "spatial_ref", "crs", "crs_wkt"

              - crs = file.attrs.<crs_key>

        data_crs : None, optional
            Optional way to specify the crs of the data explicitly.
            ("data_crs_key" will be ignored if "data_crs" is provided!)
        sel : dict, optional
            A dictionary of keyword-arguments passed to `xarray.Dataset.sel()`
            (see https://xarray.pydata.org/en/stable/generated/xarray.Dataset.sel.html)

            >>> sel = dict(altitude=100, time=pd.Date)

            The default is None.
        isel : dict, optional
            A dictionary of keyword-arguments passed to `xarray.Dataset.isel()`.
            (see https://xarray.pydata.org/en/stable/generated/xarray.Dataset.isel.html)
            The default is {"band" : 0}  (if sel is None).
        plot_crs : any, optional
            The plot-crs. A crs-identifier usable with cartopy.
            The default is None, in which case the crs of the GeoTIFF is used if
            possible, else epsg=4326.
        shape : str, dict or None, optional
            - if str: The name of the shape to use, e.g. one of:
              ['geod_circles', 'ellipses', 'rectangles', 'voronoi_diagram',
              'delaunay_triangulation', 'shade_points', 'shade_raster']
            - if dict: a dictionary with parameters passed to the selected shape.
              The dict MUST contain a key "shape" that holds the name of the shape!

              >>> dict(shape="rectangles", radius=1, radius_crs=.5)

        classify_specs : dict, optional
            A dict of keyword-arguments passed to `m.set_classify_specs()`.
            The default is None.
        val_transform : None or callable
            A function that is used to transform the data-values.
            (e.g. to apply scaling etc.)

            >>> def val_transform(a):
            >>>     return a / 10
        coastline: bool
            Indicator if a coastline should be added or not.
            The default is False
        mask_and_scale : bool
            Indicator if the data should be masked and scaled with respect to the
            file-attributes *_FillValue*, *scale_factor* and *add_offset*.

            - If False: the data will only be scaled "on demand", avoiding costly
              initialization of very large float-arrays. Masking will still be applied
              in case a *_FillValue* attribute has been found.
              (a masked-array is returned to avoid dtype conversions)
              The encoding is accessible via `m.data_specs.encoding`
            - If True: all data will be masked and scaled after reading.
              For more details see `xarray.open_dataset`.

            NOTE: using `mask_and_scale=True` results in a conversion of the data-values
            to floats!! For very large datasets this can cause a huge increase in
            memory-usage! EOmaps handles the scaling internally to show correct
            values for callbacks and colorbars, even if `mask_and_scale=False`!

            The default is False.
        extent : tuple or string
            Set the extent of the map prior to plotting
            (can provide great speedups if only a subset of the dataset is shown!)

            - If a tuple is provided, it is used to set the plot-extent
              before plotting via `m.set_extent(extent)`

              - (x0, x1, y0, y1) : provide the extent in lat/lon
              - ((x0, x1, y0, y1), crs) : provide the extent in the given crs

            - If a string is provided, it is used to attempt to set the plot-extent
              before plotting via `m.set_extent_to_location(extent)`

            The default is None
        kwargs :
            Keyword-arguments passed to `m.plot_map()`

        Returns
        -------
        m : eomaps.Maps
            The created Maps object.

        Examples
        --------
        # to just read the data use one of the following:

        >>> from eomaps import Maps
        >>> path = r"C:/folder/file.nc"
        >>> m = Maps.from_file.NetCDF(path)

        # to select specific datasets from the file, use `sel` or `isel`:

        >>> from datetime import datetime, timedelta
        >>> sel = dict(date=datetime(2021,1,1),
        >>>            tolerance=timedelta(10),
        >>>            method="nearest")
        >>> m = Maps.from_file.NetCDF(path, sel=sel)

        # you can also use already opened filehandles:

        >>> file = xar.open_dataset(path)
        >>> m = Maps.from_file.NetCDF(file)

        >>> with xar.open_dataset(path) as file:
        >>>     m = Maps.from_file.NetCDF(file)

        """

        assert _register_xarray(), (
            "EOmaps: missing dependency for read_NetCDF: 'xarray'\n"
            + "To install, use 'conda install -c conda-forge xarray'"
        )

        # read data
        data = read_file.NetCDF(
            path_or_dataset,
            parameter=parameter,
            coords=coords,
            crs_key=data_crs_key,
            data_crs=data_crs,
            sel=sel,
            isel=isel,
            set_data=None,
            mask_and_scale=mask_and_scale,
        )

        if val_transform:
            data["data"] = val_transform(data["data"])

        return _from_file(
            data,
            crs=plot_crs,
            shape=shape,
            classify_specs=classify_specs,
            val_transform=val_transform,
            coastline=coastline,
            **kwargs,
        )

    @staticmethod
    def GeoTIFF(
        path_or_dataset,
        data_crs_key=None,
        data_crs=None,
        sel=None,
        isel=None,
        plot_crs=None,
        shape=None,
        classify_specs=None,
        val_transform=None,
        coastline=False,
        mask_and_scale=False,
        **kwargs,
    ):
        """
        Convenience function to initialize a new Maps-object from a GeoTIFF file.

        If no explicit shape is provided, EOmaps will try several attempts to plot
        the data (fastest first).

        - fist, shading as a raster is used: `m.set_shape.shade_raster`
        - if it fails, shading with points is used: `m.set_shape.shade_raster`
        - if it fails, ordinary ellipse-plot is created: `m.set_shape.ellipses`

        This function is (in principal) a shortcut for:

        >>> m = Maps(crs=...)
        >>> m.set_data(**m.read_file.GeoTIFF(...))
        >>> m.set_classify_specs(...)
        >>> m.plot_map(**kwargs)

        Parameters
        ----------
        path_or_dataset : str, pathlib.Path or xar.Dataset
            - If str or pathlib.Path: The path to the file.
            - If xar.Dataset: The xarray.Dataset instance to use
        data_crs_key : str, optional
            The variable-name that holds the crs-information.

            By default the following options are tried:
            - <crs_key> = "spatial_ref", "crs"

              - crs = file.<crs_key>.attrs["crs_wkt"]
              - crs = file.<crs_key>.attrs["wkt"]
        data_crs : None, optional
            Optional way to specify the crs of the data explicitly.
            ("data_crs_key" will be ignored if "data_crs" is provided!)
        sel : dict, optional
            A dictionary of keyword-arguments passed to `xarray.Dataset.sel()`
            (see https://xarray.pydata.org/en/stable/generated/xarray.Dataset.sel.html)
            The default is None.
        isel : dict, optional
            A dictionary of keyword-arguments passed to `xarray.Dataset.isel()`.
            (see https://xarray.pydata.org/en/stable/generated/xarray.Dataset.isel.html)
            The default is {"band" : 0}  (if sel is None).
        plot_crs : any, optional
            The plot-crs. A crs-identifier usable with cartopy.
            The default is None, in which case the crs of the GeoTIFF is used if
            possible, else epsg=4326.
        shape : str, dict or None, optional
            - if str: The name of the shape to use, e.g. one of:
              ['geod_circles', 'ellipses', 'rectangles', 'voronoi_diagram',
              'delaunay_triangulation', 'shade_points', 'shade_raster']
            - if dict: a dictionary with parameters passed to the selected shape.
              The dict MUST contain a key "shape" that holds the name of the shape!

              >>> dict(shape="rectangles", radius=1, radius_crs=.5)

        classify_specs : dict, optional
            A dict of keyword-arguments passed to `m.set_classify_specs()`.
            The default is None.
        val_transform : None or callable
            A function that is used to transform the data-values.
            (e.g. to apply scaling etc.)

            >>> def val_transform(a):
            >>>     return a / 10
        coastline: bool
            Indicator if a coastline should be added or not.
            The default is False
        mask_and_scale : bool
            Indicator if the data should be masked and scaled with respect to the
            file-attributes *_FillValue*, *scale_factor* and *add_offset*.

            - If False: the data will only be scaled "on demand", avoiding costly
              initialization of very large float-arrays. Masking will still be applied
              in case a *_FillValue* attribute has been found.
              (a masked-array is returned to avoid dtype conversions)
              The encoding is accessible via `m.data_specs.encoding`
            - If True: all data will be masked and scaled after reading.
              For more details see `xarray.open_dataset`.

            NOTE: using `mask_and_scale=True` results in a conversion of the data-values
            to floats!! For very large datasets this can cause a huge increase in
            memory-usage! EOmaps handles the scaling internally to show correct
            values for callbacks and colorbars, even if `mask_and_scale=False`!

            The default is False.
        extent : tuple or string
            Set the extent of the map prior to plotting
            (can provide great speedups if only a subset of the dataset is shown!)

            - If a tuple is provided, it is used to set the plot-extent
              before plotting via `m.set_extent(extent)`

              - (x0, x1, y0, y1) : provide the extent in lat/lon
              - ((x0, x1, y0, y1), crs) : provide the extent in the given crs

            - If a string is provided, it is used to attempt to set the plot-extent
              before plotting via `m.set_extent_to_location(extent)`

            The default is None
        kwargs :
            Keyword-arguments passed to `m.plot_map()`

        Returns
        -------
        m : eomaps.Maps
            The created Maps object.

        Examples
        --------
        # to just read the data use one of the following:

        >>> from eomaps import Maps
        >>> path = r"C:/folder/file.tiff"
        >>> m = Maps.from_file.GeoTIFF(path)

        # to select specific datasets from the file, use `sel` or `isel`:

        >>> sel = dict(band = 1)
        >>> m = Maps.from_file.GeoTIFF(path, sel=sel)

        # you can also use already opened filehandles:

        >>> file = xar.open_dataset(path)
        >>> m = Maps.from_file.GeoTIFF(file)

        >>> with xar.open_dataset(path) as file:
        >>>     m = Maps.from_file.GeoTIFF(file)

        """

        assert _register_xarray() and _register_rioxarray(), (
            "EOmaps: missing dependency for read_GeoTIFF: 'xarray' 'rioxarray'\n"
            + "To install, use 'conda install -c conda-forge xarray'"
            + "To install, use 'conda install -c conda-forge rioxarray'"
        )

        # read data
        data = read_file.GeoTIFF(
            path_or_dataset,
            sel=sel,
            isel=isel,
            set_data=None,
            data_crs=data_crs,
            crs_key=data_crs_key,
            mask_and_scale=mask_and_scale,
        )

        if val_transform:
            data["data"] = val_transform(data["data"])

        if (
            classify_specs is None
            and kwargs.get("cmap", None) is None
            and isinstance(path_or_dataset, (Path, str))
        ):

            # try to identify used band
            if sel is not None and "band" in sel:
                band = sel.get("band", 1)

            elif isel is not None and "band" in isel:
                with xar.open_dataset(path_or_dataset) as ncfile:
                    band = np.atleast_1d(ncfile.isel(**isel).band.values)[0]
            else:
                band = 1

            cmap, classify_specs = identify_geotiff_cmap(path_or_dataset, band=band)
            kwargs["cmap"] = cmap

        return _from_file(
            data,
            crs=plot_crs,
            shape=shape,
            classify_specs=classify_specs,
            val_transform=val_transform,
            coastline=coastline,
            **kwargs,
        )

    @staticmethod
    def CSV(
        path=None,
        parameter=None,
        x=None,
        y=None,
        data_crs=None,
        plot_crs=None,
        shape=None,
        classify_specs=None,
        val_transform=None,
        coastline=False,
        read_kwargs=None,
        **kwargs,
    ):
        """
        Convenience function to initialize a new Maps-object from a CSV file.

        If no explicit shape is provided, EOmaps will try several attempts to plot
        the data (fastest first).

        - fist, shading as a raster is used: `m.set_shape.shade_raster`
        - if it fails, shading with points is used: `m.set_shape.shade_raster`
        - if it fails, ordinary ellipse-plot is created: `m.set_shape.ellipses`

        This function is (in principal) a shortcut for:

        >>> m = Maps(crs=...)
        >>> m.set_data(**m.read_file.CSV(...))
        >>> m.set_classify_specs(...)
        >>> m.plot_map(**kwargs)


        Parameters
        ----------
        path : str
            The path to the csv-file.
        parameter : str
            The column-name to use as parameter.
        x : str
            The column-name to use as "x" coordinate.
        y : str
            The column-name to use as "y" coordinate.
        data_crs : crs-identifier
            The crs of the data. (see "Maps.set_data" for details)
        plot_crs : any, optional
            The plot-crs. A crs-identifier usable with cartopy.
            The default is None, in which case the crs of the GeoTIFF is used if
            possible, else epsg=4326.
        shape : str, dict or None, optional
            - if str: The name of the shape to use, e.g. one of:
              ['geod_circles', 'ellipses', 'rectangles', 'voronoi_diagram',
              'delaunay_triangulation', 'shade_points', 'shade_raster']
            - if dict: a dictionary with parameters passed to the selected shape.
              The dict MUST contain a key "shape" that holds the name of the shape!

              >>> dict(shape="rectangles", radius=1, radius_crs=.5)

        classify_specs : dict, optional
            A dict of keyword-arguments passed to `m.set_classify_specs()`.
            The default is None.
        val_transform : None or callable
            A function that is used to transform the data-values.
            (e.g. to apply scaling etc.)

            >>> def val_transform(a):
            >>>     return a / 10
        coastline: bool
            Indicator if a coastline should be added or not.
            The default is False
        read_kwargs : dict
            Additional kwargs passed to pandas.read_file()
            (e.g. to set index_col etc.)
            The default is None
        extent : tuple or string
            Set the extent of the map prior to plotting
            (can provide great speedups if only a subset of the dataset is shown!)

            - If a tuple is provided, it is used to set the plot-extent
              before plotting via `m.set_extent(extent)`

              - (x0, x1, y0, y1) : provide the extent in lat/lon
              - ((x0, x1, y0, y1), crs) : provide the extent in the given crs

            - If a string is provided, it is used to attempt to set the plot-extent
              before plotting via `m.set_extent_to_location(extent)`

            The default is None

        kwargs :
            Keyword-arguments passed to `m.plot_map()`

        Returns
        -------
        m : eomaps.Maps
            The created Maps object.

        """
        if read_kwargs is None:
            read_kwargs = dict()

        # read data
        data = read_file.CSV(
            path=path, parameter=parameter, x=x, y=y, crs=data_crs, **read_kwargs
        )

        return _from_file(
            data,
            crs=plot_crs,
            shape=shape,
            classify_specs=classify_specs,
            val_transform=val_transform,
            coastline=coastline,
            **kwargs,
        )


class new_layer_from_file:
    """
    A collection of methods to add a new layer to an existing Maps-object from a file.
    (see individual reader-functions for details)

    Currently supported filetypes are:

    - NetCDF (requires `xarray`)
    - GeoTIFF (requires `rioxarray` + `xarray`)
    - CSV (requires `pandas`)
    """

    # assign a parent maps-object and call m.new_layer instead of creating a new one.
    def __init__(self, m):
        self._m = m

    @wraps(from_file.NetCDF)
    def NetCDF(self, *args, **kwargs):
        return from_file.NetCDF(*args, **kwargs, parent=self._m)

    @wraps(from_file.GeoTIFF)
    def GeoTIFF(self, *args, **kwargs):
        return from_file.GeoTIFF(*args, **kwargs, parent=self._m)

    @wraps(from_file.CSV)
    def CSV(self, *args, **kwargs):
        return from_file.CSV(*args, **kwargs, parent=self._m)

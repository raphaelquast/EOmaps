import sys
import click


def _identify_crs(crs):
    from eomaps import Maps

    if crs == "web":
        crs = "google_mercator"

    # if crs can be idenified as integer, return it
    try:
        return int(crs)
    except ValueError:
        pass

    if crs.startswith("Maps.CRS"):
        x = getattr(Maps.CRS, crs[9:])
        if callable(x):
            return x()
        else:
            return x
    else:
        import inspect

        options = [
            key
            for key, val in Maps.CRS.__dict__.items()
            if (
                not key.startswith("_")
                and (inspect.isclass(val) and (issubclass(val, Maps.CRS.CRS)))
                or (isinstance(val, Maps.CRS.CRS))
            )
        ]
        [
            options.remove(i)
            for i in ("epsg", "CRS", "Geocentric", "Geodetic", "Projection")
            if i in options
        ]
        query = [i.lower() for i in options]

        try:
            idx = query.index(crs.lower())
            x = getattr(Maps.CRS, options[idx])
        except Exception:
            from difflib import get_close_matches

            matches = get_close_matches(crs, query, 3, cutoff=0.3)
            if len(matches) == 1:
                txt = f"did you mean '{options[query.index(matches[0])]}' ?"
            elif len(matches) > 1:
                txt = f"did you mean {[options[query.index(i)] for i in matches]} ?"
            else:
                txt = ""

            click.echo(f"EOmaps: unable to identify the crs: '{crs}'... {txt}")
            return None

        if callable(x):
            return x()
        else:
            return x


@click.command()
@click.option(
    "--crs",
    type=str,
    default=None,
    help=(
        "Set the projection used for plotting the map. "
        "(Integers are identified as epsg-codes, "
        "strings are identified as cartopy-crs names)."
        "The default is 'web' (e.g. Web Mercator Projection)."
        "\n\n\b\n"
        "- web (Web Mercator)\n"
        "- stereographic\n"
        "- 4326\n"
        "- equi7_eu\n"
    ),
)
@click.option(
    "--file",
    type=str,
    default="",
    help=(
        "A path to a file (or a filename in the current working directory) "
        "that should be plotted. "
        "(Supported filetypes: csv, GeoTIFF, NetCDF"
    ),
)
@click.option(
    "--ne",
    type=click.Choice(
        [
            "coastline",
            "ocean",
            "land",
            "countries",
            "urban_areas",
            "lakes",
            "rivers_lake_centerlines",
        ],
        case_sensitive=False,
    ),
    default=[],
    multiple=True,
    help=("Add one (or multiple) NaturalEarth features to the map."),
)
@click.option(
    "--wms",
    type=click.Choice(
        [
            "osm",
            "google_satellite",
            "google_roadmap",
            "s2_cloudless" "landcover",
            "topo",
            "terrain_light",
            "basemap",
            "basemap_light",
            "s1_vv",
        ],
        case_sensitive=False,
    ),
    default=None,
    multiple=False,
    help=("Add one (or multiple) WebMap services to the map."),
)
def cli(crs=None, file=None, ne=None, wms=None):
    """A simple command line interface for EOmaps."""
    try:
        # make sure qt5 is used as backend
        import matplotlib

        matplotlib.use("qt5agg")
    except Exception:
        click.echo("... unable to activate PyQt5 backend... defaulting to tkinter")

    from eomaps import Maps

    # disable interactive mode (e.g. tell show to block)
    import matplotlib.pyplot as plt

    plt.ioff()

    if crs is None and wms is not None:
        crs = "google_mercator"
    elif crs is None:
        crs = "google_mercator"

    usecrs = _identify_crs(crs)

    if usecrs is None:
        return
    m = Maps(crs=usecrs)

    for ne_feature in ne:
        try:
            getattr(m.add_feature.preset, ne_feature.lower())()
        except Exception:
            click.echo(f"EOmaps: Unable to add NaturalEarth feature: {ne_feature}")

    if wms is not None:
        if wms in ["osm"]:
            m.add_wms.OpenStreetMap.add_layer.default()
        elif wms in ["google_roadmap"]:
            m.add_wms.GOOGLE.add_layer.roadmap_standard()
        elif wms in ["google_satellite"]:
            m.add_wms.GOOGLE.add_layer.satellite()
        elif wms in ["s2_cloudless"]:
            m.add_wms.S2_cloudless.add_layer.s2cloudless_3857()
        elif wms in ["landcover"]:
            m.add_wms.ESA_WorldCover.add_layer.WORLDCOVER_2020_MAP()
        elif wms in ["topo"]:
            m.add_wms.GEBCO.add_layer.GEBCO_LATEST()
        elif wms in ["terrain_light"]:
            m.add_wms.S2_cloudless.add_layer.terrain_light_3857()
        elif wms in ["basemap"]:
            m.add_wms.DLR_basemaps.add_layer.basemap()
        elif wms in ["basemap_light"]:
            m.add_wms.DLR_basemaps.add_layer.litemap()
        elif wms in ["s1_vv"]:
            m.add_wms.S1GBM.add_layer.vv()

    if len(file) > 0:
        m._init_companion_widget()
        m._companion_widget.show()
        m._companion_widget.tabs.tab_open.new_file_tab(file)

    def on_close(*args, **kwargs):
        sys.exit()

    m.BM.canvas.mpl_connect("close_event", on_close)

    m.show()
    sys.exit()

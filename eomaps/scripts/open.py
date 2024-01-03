# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

import sys
import os
import click

try:
    # make sure qt5 is used as backend
    import matplotlib

    matplotlib.use("qt5agg")

except Exception:
    click.echo("... unable to activate PyQt5 backend... defaulting to 'tkinter'")


def _identify_crs(crs):
    from eomaps import Maps

    if crs == "web":
        crs = "google_mercator"

    # if crs can be identified as integer, return it
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
        "The projection of the map."
        "\n\n\b\n"
        "- integer (4326,3857 ...epsg code)"
        "\b\n"
        "- string (web, equi7_eu ...Maps.CRS name)"
        "\n\b\n"
        "The default is 'web' (e.g. Web Mercator Projection)."
        "\n\n\b\n"
    ),
)
@click.option(
    "--file",
    type=str,
    default="",
    help=(
        "Path to a file that should be plotted. "
        "\n\n\b\n"
        "Supported filetypes: csv, GeoTIFF, NetCDF, Shapefile, GeoJson, ... "
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
@click.option(
    "--location",
    type=str,
    default=None,
    multiple=False,
    help=("Query OpenStreetMap for a location and set the map extent accordingly."),
)
@click.option(
    "--loglevel",
    type=str,
    default=None,
    multiple=False,
    help=("Set the log level. (info, warning, error, debug"),
)
def cli(crs=None, file=None, ne=None, wms=None, location=None, loglevel=None):
    """
    Command line interface for EOmaps.

    Keyboard-shortcuts for the map:

    \b
    "w" : open the companion widget

    \b
    "ctrl + c" : export to clipboard

    \b
    "f" : fullscreen

    \b
    """
    from eomaps import Maps

    Maps.config(use_interactive_mode=False, log_level=loglevel)

    if crs is None and wms is not None:
        crs = "google_mercator"
    elif crs is None:
        crs = "google_mercator"

    usecrs = _identify_crs(crs)

    if usecrs is None:
        return
    m = Maps(crs=usecrs)

    if location is not None:
        m.set_extent_to_location(location)

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
            m.add_wms.DLR.basemap.add_layer.basemap()
        elif wms in ["basemap_light"]:
            m.add_wms.DLR.basemap.add_layer.litemap()
        elif wms in ["s1_vv"]:
            m.add_wms.S1GBM.add_layer.vv()

    if len(file) > 0:
        m._init_companion_widget()
        m._companion_widget.show()
        m._companion_widget.tabs.tab_open.new_file_tab(file)

    def on_close(*args, **kwargs):
        try:
            # TODO check why ordinary exists cause the following qt errors
            # see https://stackoverflow.com/a/13723190/9703451 for os._exit
            # "QGuiApplication::font(): no QGuiApplication instance
            #  and no application font set."
            sys.exit(0)
        except SystemExit:
            os._exit(0)
        else:
            os._exit(0)

    m.BM.canvas.mpl_connect("close_event", on_close)
    m.show()

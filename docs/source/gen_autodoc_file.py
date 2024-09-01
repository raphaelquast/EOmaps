from pathlib import Path
from operator import attrgetter
from itertools import chain

from eomaps import Maps, widgets

# TODO there must be a better way than this...
# BM needs to be a property otherwise there are problems with jupyter notebooks
# In order to make BM still accessible to sphinx, override it prior to generating
# the autodoc-files
from eomaps._blit_manager import BlitManager

Maps.BM = BlitManager


def get_autosummary(
    currentmodule="eomaps.eomaps",
    members=[],
    template="obj_with_attributes_no_toc",
):
    return (
        f".. currentmodule:: {currentmodule}\n"
        ".. autosummary::\n"
        "    :toctree: ../generated\n"
        "    :nosignatures:\n"
        f"    :template: {template}.rst\n\n"
        + "\n".join(f"    {m}" for m in members)
        + "\n\n"
    )


def get_members(obj, key="", with_sublevel=False, names_only=False, exclude=[]):
    """get a list of attributes of a given object"""
    # use attrgetter to allow also nested attributes (Maps.x.y)
    if len(key) == 0:
        startstr = f"{obj.__name__}"
        members = filter(lambda x: not x.startswith("_") and not x in exclude, dir(obj))
    else:
        startstr = f"{obj.__name__}.{key}"
        members = filter(
            lambda x: not x.startswith("_") and not x in exclude,
            dir(attrgetter(key)(obj)),
        )

    if names_only:
        return members

    if with_sublevel:
        return chain(
            *(
                (
                    f"{startstr}.{m}",
                    *(
                        f"{startstr}.{m}.{f}"
                        for f in get_members(
                            obj, f"{key}.{m}" if key else m, names_only=True
                        )
                    ),
                )
                for m in members
            )
        )
    else:
        return (f"{startstr}.{f}" for f in members)


def make_feature_toctree_file():
    # Fetch all members of the Maps object that should get a auto-generated docs-file
    members = list(get_members(Maps, "", False, exclude=["CRS", "CLASSIFIERS"]))
    for key in (
        "set_shape",
        "draw",
        "from_file",
        "new_layer_from_file",
        "read_file",
        "util",
        "add_wms",
        "BM",
        "data_specs",
        "classify_specs",
    ):
        members.extend(get_members(Maps, key, False))
    for key in ("add_feature", "cb"):
        members.extend(get_members(Maps, key, True))
    for key in (
        "cb.click.attach",
        "cb.pick.attach",
        "cb.move.attach",
        "cb.keypress.attach",
    ):
        members.extend(get_members(Maps, key, True))
    for key in ("cb.click.get", "cb.pick.get", "cb.move.get", "cb.keypress.get"):
        members.extend(get_members(Maps, key, False))

    # create a page that will be used for sphinx-autodoc to create stub-files
    s = ":orphan:\n\n"
    s += get_autosummary(
        "eomaps.eomaps", ["Maps.config", *members], "obj_with_attributes_no_toc"
    )

    s += get_autosummary("eomaps.mapsgrid", ["MapsGrid"], "custom-class-template")
    s += get_autosummary("eomaps.colorbar", ["ColorBar"], "custom-class-template")
    s += get_autosummary("eomaps.compass", ["Compass"], "custom-class-template")
    s += get_autosummary("eomaps.scalebar", ["ScaleBar"], "custom-class-template")
    s += get_autosummary(
        "eomaps.callbacks",
        ["ClickCallbacks", "PickCallbacks", "KeypressCallbacks"],
        "custom-class-template",
    )

    s += get_autosummary(
        "eomaps.grid", ["GridLines", "GridLabels"], "custom-class-template"
    )
    s += get_autosummary(
        "eomaps.inset_maps",
        [
            "InsetMaps.set_inset_position",
            "InsetMaps.add_extent_indicator",
            "InsetMaps.add_indicator_line",
        ],
        "obj_with_attributes_no_toc",
    )

    s += get_autosummary(
        "eomaps.widgets",
        [
            i.rsplit(".", 1)[1]
            for i in get_members(widgets)
            if not i.rsplit(".", 1)[-1][0].islower()
        ],
    )

    basepath = Path(__file__).parent

    with open(basepath / "api" / "autodoc_additional_props.rst", "w") as file:
        file.write(s)

    # Copy the custom api files to the "generated" docs folder so that they serve
    # as the autodoc-files for the associated objects.
    # This is done to redirect links for :py:class:`<object>` to the custom file
    # to get a more customized page for the API docs of the objects.

    src_basepath = basepath / "api"
    dest_basepath = basepath / "generated"

    (basepath / "generated").mkdir(exist_ok=True)
    # copy all files starting with "eomaps." (e.g. "eomaps.eomaps.Maps.rst")
    # Note: original source-files are ignored in conf.py to avoid duplication warnings!
    for file in filter(lambda x: x.stem.startswith("eomaps."), src_basepath.iterdir()):
        (dest_basepath / file.name).write_text(file.read_text())

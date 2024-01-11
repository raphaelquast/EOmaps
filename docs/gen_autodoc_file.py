from pathlib import Path
from operator import attrgetter
from itertools import chain

from eomaps import Maps
from eomaps.colorbar import ColorBar


def get_members(
    obj, key="", with_sublevel=False, prefix="", names_only=False, exclude=[]
):
    """get a list of attributes of a given object"""
    # use attrgetter to allow also nested attributes (Maps.x.y)
    if len(key) == 0:
        startstr = f"{prefix}{obj.__name__}"
        members = filter(lambda x: not x.startswith("_") and not x in exclude, dir(obj))
    else:
        startstr = f"{prefix}{obj.__name__}.{key}"
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
    s = (
        ":orphan:\n"
        ".. currentmodule:: eomaps.eomaps\n\n"
        ".. autosummary::\n"
        "    :toctree: ../generated\n"
        "    :nosignatures:\n"
        "    :template: obj_with_attributes_no_toc.rst\n\n"
        #        "    Maps\n"
        "    ColorBar\n"
        "    Maps.config\n"
    )

    s += (
        "\n".join(get_members(Maps, "", False, "    ", exclude=["CRS", "CLASSIFIERS"]))
        + "\n"
    )

    for key in ("set_shape", "draw", "from_file", "read_file", "util", "add_wms"):
        s += "\n".join(get_members(Maps, key, False, "    ")) + "\n"

    for key in ("add_feature", "cb"):
        s += "\n".join(get_members(Maps, key, True, "    ")) + "\n"

    s += "\n\n"
    s += (
        ".. currentmodule:: eomaps.colorbar\n"
        ".. autosummary::\n"
        "    :toctree: ../generated\n"
        "    :nosignatures:\n"
        "    :template: custom-class-template.rst\n\n"
        "    ColorBar\n"
    )

    s += "\n\n"
    s += (
        ".. currentmodule:: eomaps.grid\n"
        ".. autosummary::\n"
        "    :toctree: ../generated\n"
        "    :nosignatures:\n"
        "    :template: custom-class-template.rst\n\n"
        "    GridLines\n"
        "    GridLabels\n"
    )

    s += "\n\n"
    s += (
        ".. currentmodule:: eomaps.compass\n"
        ".. autosummary::\n"
        "    :toctree: ../generated\n"
        "    :nosignatures:\n"
        "    :template: custom-class-template.rst\n\n"
        "    Compass\n"
    )

    s += "\n\n"
    s += (
        ".. currentmodule:: eomaps.scalebar\n"
        ".. autosummary::\n"
        "    :toctree: ../generated\n"
        "    :nosignatures:\n"
        "    :template: custom-class-template.rst\n\n"
        "    ScaleBar\n"
    )

    with open(
        Path(__file__).parent / "api" / "autodoc_additional_props.rst", "w"
    ) as file:
        file.write(s)

    src = Path(__file__).parent / "api" / "api_Maps.rst"

    (Path(__file__).parent / "generated").mkdir(exist_ok=True)
    dest = Path(__file__).parent / "generated" / "eomaps.eomaps.Maps.rst"

    dest.write_text(src.read_text())  # for text files

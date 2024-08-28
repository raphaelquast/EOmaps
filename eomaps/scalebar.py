# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Interactive scalebar."""

import logging
from collections import OrderedDict
from functools import lru_cache
import importlib.metadata
from packaging import version

import numpy as np

from matplotlib.collections import LineCollection
from matplotlib.textpath import TextPath
from matplotlib.patches import Polygon, PathPatch
from matplotlib.transforms import Affine2D
from matplotlib.font_manager import FontProperties
from matplotlib.colors import to_hex

from .helpers import pairwise

_picked_scalebars = set()

_log = logging.getLogger(__name__)

# TODO remove this once pyproj >3.5 is enforced
pyproj_version = version.parse(importlib.metadata.version("pyproj"))
if pyproj_version >= version.Version("3.5"):
    _pyproj_geod_fix_args = {"return_back_azimuth": True}
else:
    _pyproj_geod_fix_args = {}


class ScaleBar:
    """
    Base class for EOmaps scalebars.

    Note
    ----
    To add a new scalebar to a map, see
    :py:meth:`Maps.add_scalebar <eomaps.eomaps.Maps.add_scalebar>`.

    """

    def __init__(
        self,
        m,
        preset=None,
        scale=None,
        n=10,
        autoscale_fraction=0.1,
        auto_position=(0.75, 0.25),
        size_factor=1,
        scale_props=None,
        patch_props=None,
        label_props=None,
        line_props=None,
        layer=None,
    ):
        """
        Add a scalebar to the map.

        The scalebar represents a ruler in units of meters whose direction
        follows geodesic lines.

        Note
        ----
        You can click on the scalebar to dynamically adjust its position,
        orientation and size!

        Use ` .print_code()` to print the command that will reproduce the current
        appearance of the scalebar to the console.

        - **LEFT-CLICK** on the scalebar to make the scalebar interactive
        - drag the scalebar with the <LEFT MOUSE BUTTON>
        - use the **SCROLL WHEEL** to adjust the (auto-)scale of the scalebar
          (hold < shift > to make bigger steps)
        - use < control > + **SCROLL WHEEL** to adjust the size of the labels

        Keyboard-shortcuts (only active if a scalebar is selected):

        - use < + > and < - > to rotate the scalebar
        - use the < arrow-keys > to increase the frame size
        - use < alt > + < arrow-keys > to decrease the frame size
        - use < control > + < left > and < right > keys to adjust the label-offset
        - use < control > + < up > and < down > keys to rotate the labels

        - use < delete > to remove the scalebar from the plot
        - use the < escape > to exit editing the scalebar

        Parameters
        ----------
        pos : (float, float)
            The longitude and latitude of the starting point for the scalebar
            (If None, the center of the axis is used )
        rotation : float
            The azimuth-direction (in degrees) in which the scalebar points.
            The default is 90.
        preset : str
            The name of the style preset to use.

            - "bw" : a black and white scalebar with no background color
            - "bw_2" : a black and white scalebar with white background
            - "kr" : a black and red scalebar with semi-transparent white background

        scale : float or None, optional
            The distance of the segments of the scalebar.

            - If None: the scale is automatically updated based on the current
              zoom level and the provided "autoscale_fraction".
            - If float: A fixed length of the segments (in meters).
              (e.g. the total length of the scalebar will be `n * scale`

            The default is None.
        n : int, optional
            The number of segments to use.
            The default is 10.
        autoscale_fraction : float, optional
            The (approximate) fraction of the axis width to use as size for the scalebar
            in the autoscale procedure. Note that this is number is not exact since
            (depending on the crs) the final scalebar might be curved.
            The default is 0.25.
        auto_position : tuple or False, optional
            Re-position the scalebar automatically on pan/zoom events.

            - If False: the position of the scalebar remains fixed.
            - If a tuple is provided, it is identified as relative (x, y) position
              on the axes (e.g. (0,0)=lower left, (1,1)=upper right )

            The default is (0.75, 0.25).
        size_factor : float, optional
            A factor that is used to adjust the relative size of the labels.
            The default is 1

        scale_props : dict, optional
            A dictionary that is used to set the properties of the scale.

            - "n": (int) The number of scales (e.g. line-segments) to draw.
            - "width": (float) The width of the scalebar
            - "colors" (tuple): A sequence of colors that will be repeated to
              color the individual line-fragments of the scalebar.
              (you can provide more than 2 colors!)
              The default is ("k", "w").

            The default is:
                >>> dict(n=10, width=5, colors=("k", "w"))
        patch_props : dict, optional
            A dictionary that is used to set the properties of the frame-patch.

            - "offsets": A tuple that is used to adjust the offset of the
              frame-patch. Individual values represent `(top, bottom, left, right)`
              on a horizontally oriented scalebar.
              The default is (1, 1, 1, 1).
            - ... additional kwargs are passed to the PolygonPatch used to draw the
              frame. Possible values are:

             - "facecolor", "edgecolor", "linewidth", "linestyle", "alpha" ...

            The default is:
                >>> dict(fc=".75", ec="k", lw=1)
        label_props : dict, optional
            A dictionary that is used to set the properties of the labels.

            - "scale": A scaling factor for the fontsize
            - "offset" : A scaling factor to adjust the offset of the labels
              relative to the scalebar
            - "rotation" : the rotation angle of the labels (in degrees)
              relative to the curvature of the scalebar
            - "color" : The color of the text
            - "every" : indicator which sections should be labelled
              If an integer is provided, every nth section is labelled,
              If a list or tuple is provided, it is used to label the selected sections.
            - ... additional kwargs are passed to `matplotlib.font_manager.FontProperties`
              to set the used font-properties. Possible values are:

              - "family", "style", "variant", "stretch", and "weight"

              for example: `{family="Helvetica", style="italic"}`

            The default is:
                >>> dict(scale=1, offset=1, rotation=0, every=2)
        line_props : dict, optional
            A dictionary that is used to set the properties of the text-indicator lines.
            (e.g. the lines between the scale and the labels)

            All arguments are passed to the LineCollection used to draw the lines.
            Possible values are:

             - "edgecolor" (or "ec"), "linewidth" (or "lw"), "linestyle" (or "ls") ...

        layer : str, optional
            The layer at which the scalebar should be visible.
            If None, the layer of the Maps-object used to create the scalebar is used.
            The default is None.
        pickable : bool, optional
            If True, the scalebar can be interactively adjusted using the mouse
            and keyboard-shortcuts. If False, the scalebar is non-interactive.
            The default is True
        """
        self._m = m

        if layer is None:
            layer = self._m.layer
        self._layer = layer

        # number of intermediate points for evaluating the curvature
        self._interm_pts = 20
        # size-factor to adjust the size of the labels
        self._size_factor = size_factor

        # ----- Interactivity parameters
        self._pickable = False
        # click offset relative to the start-position of the scale
        self._pick_start_offset = (0.0, 0.0)
        # multiplier for changing the scale of the scalebar
        self._scale_factor_base = 1000
        # multipliers for changing the label size
        self._size_factor_base = 50
        # interval for adjusting the text-offset
        self._cb_offset_interval = 0.05
        # interval for rotating the scalebar
        self._cb_rotate_interval = 1

        self._scale = scale
        self._n = n
        self._estimated_scale = None

        self._artists = OrderedDict(patch=None, scale=None)
        self._texts = dict()
        self._scale_props = dict()
        self._label_props = dict()
        self._line_props = dict()
        self._patch_props = dict()
        self._patch_offsets = (1, 1, 1, 1)

        self._font_kwargs = dict()
        self._fontkeys = ("family", "style", "variant", "stretch", "weight")

        # apply preset styling (so that additional properties are applied on top)
        self._preset = None
        self._apply_preset(preset)

        self._autoscale = autoscale_fraction

        assert (
            isinstance(auto_position, tuple) or auto_position is False
        ), "EOmaps: Scalebar 'auto_position' must be either a tuple (x, y) or False!"

        self._auto_position = auto_position

        self._set_scale_props(**(scale_props if scale_props else {}))
        # set the label properties
        self._set_label_props(**(label_props if label_props else {}))
        # set the patch properties
        self._set_patch_props(**(patch_props if patch_props else {}))
        # set the line properties
        self._set_line_props(**(line_props if line_props else {}))

        # cache geod from plot_crs
        self._geod = self._m.crs_plot.get_geod()
        # cache renderer
        self._renderer = None

    @property
    def _current_scale(self):
        """The currently used scale of the scalebar."""
        if self._scale is None:
            if self._estimated_scale is None:
                self._estimated_scale()
            return self._estimated_scale
        else:
            return self._scale

    def get_scale(self):
        """Get the currently used scale of the scalebar."""
        return self._current_scale

    def print_code(self, fixed=True, return_str=False):
        """
        Print the command that will reproduce the scalebar in its current state.

        Parameters
        ----------
        fixed : bool, optional
            - If True, the returned command will produce a scalebar that is fixed
              with respect to its scale, and position.
            - If False, the command will produce a scalebar that autoscales itself
              with respect to the currently set autoscale parameters.

            The default is True.
        return_str: bool, optional
            If True, the string is returned.
            If False, the string is only printed and None is returned.
            The default is False.

        Returns
        -------
        code : str
            A string of the command that will reproduce the scalebar.

        """
        s = self._get_code(fixed=fixed)
        try:
            import black

            code = black.format_str(s, mode=black.Mode())
            print(code)
            if return_str:
                return s
        except ImportError:
            _log.debug("Error during code formatting", exc_info=True)
            print(s)
            if return_str:
                return s

    def _get_code(self, fixed=True, precision=10):
        """
        Return a string that can be used to reproduce the scalebar in its current state.

        Parameters
        ----------
        fixed : bool, optional
            - If True, the returned command will produce a scalebar that is fixed
              with respect to its scale, position and properties.
            - If False, the command will produce a scalebar that autoscales itself
              with respect to the currently set autoscale parameters.

            The default is True.
        precision : int, optional
            The float precision used for lon/lat/azim values.
            The default is 10.

        Returns
        -------
        s : str
            A command that will add the scalebar to the map when executed.

        """
        patch_offsets = [round(i, 3) for i in self._patch_offsets]
        patchprops = {"offsets": patch_offsets, **self._patch_props}

        labelprops = {**self._label_props, **self._font_kwargs}

        layer = f"'{self._layer}'" if self._layer else "None"

        if fixed:
            s = (
                "m.add_scalebar("
                f"pos=({np.format_float_positional(self._lon, precision)}, "
                f"{np.format_float_positional(self._lat, precision)}), "
                f"rotation={np.format_float_positional(self._azim, precision=10)}, "
                f"scale={self._scale if self._scale else 'None'}, "
                f"n={self._n}, "
                f"preset={self._preset if self._preset else 'None'}, "
                f"scale_props={self._scale_props}, "
                f"patch_props={patchprops}, "
                f"label_props={labelprops}, "
                f"line_props={self._line_props}, "
                f"layer={layer}, "
                f"size_factor={self._size_factor}"
                ")"
            )
        else:
            autopos = [
                np.format_float_positional(i, 3)
                for i in self._get_pos_as_autopos(self._lon, self._lat)
            ]

            s = (
                "m.add_scalebar("
                f"autoscale_fraction={self._autoscale}, "
                f"auto_position=({autopos[0]}, {autopos[1]}), "
                f"n={self._n}, "
                f"preset={self._preset if self._preset else 'None'}, "
                f"scale_props={self._scale_props}, "
                f"patch_props={patchprops}, "
                f"label_props={labelprops}, "
                f"line_props={self._line_props}, "
                f"layer={layer}, "
                f"size_factor={self._size_factor}"
                ")"
            )

        return s

    def _get_preset_props(self, preset):
        scale_props = dict(width=5, colors=("k", "w"))
        patch_props = dict(fc=".75", ec="k", lw=1, ls="-")
        label_props = dict(scale=2, offset=1, every=2, rotation=0, color="k")
        line_props = dict(ec="k", lw=0.5, linestyle=(0, (5, 5)))

        if preset is None:
            pass
        elif preset == "bw":
            scale_props.update(dict(width=4, colors=("k", "w")))
            patch_props.update(dict(fc="none", ec="none"))
            label_props.update(
                dict(
                    scale=1.5,
                    offset=0.5,
                    every=2,
                    weight="bold",
                    family="Courier New",
                )
            )
        elif preset == "bw_2":
            scale_props.update(dict(width=3, colors=("k", ".25", ".5", ".75", ".95")))
            patch_props.update(dict(fc="w"))
            label_props.update(dict(every=5, weight="bold", family="Calibri"))
        elif preset == "kr":
            scale_props.update(dict(width=3, colors=("k", "r")))
            patch_props.update(dict(fc=(1, 1, 1, 0.25), ec="r", lw=0.25))
            label_props.update(dict(weight="bold", family="Impact"))
        else:
            raise TypeError(f"EOmaps: The scalebar preset '{preset}' is not available.")

        return scale_props, patch_props, label_props, line_props

    def _apply_preset(self, preset):
        self._preset = preset

        scale_props, patch_props, label_props, line_props = self._get_preset_props(
            preset
        )
        self._set_scale_props(**scale_props)
        self._set_patch_props(**patch_props)
        self._set_label_props(**label_props)
        self._set_line_props(**line_props)

    def apply_preset(self, preset):
        """
        Apply a style-preset to the Scalebar.

        Currently available presets are:

            - "bw" : a black and white scalebar with no background color
            - "bw_2" : a black and white scalebar with white background
            - "kr" : a black and red scalebar with semi-transparent white background


        Parameters
        ----------
        preset : str
            The name of the preset.

        """
        self._apply_preset(preset)
        self._estimate_scale()
        self._update(BM_update=True)

    @staticmethod
    def _round_to_n(x, n=0):
        # round to n significant digits
        # 1234 -> 1000
        # 0.01234 -> 0.1
        res = round(x, n - int(np.floor(np.log10(abs(x)))))
        if res.is_integer():
            return int(res)
        else:
            return res

    def _extent_changed(self):
        extent = self._m.get_extent(self._m.crs_plot)

        if not hasattr(self, "_prev_extent"):
            self._prev_extent = extent
            return True
        else:
            changed = not np.allclose(extent, self._prev_extent)
            self._prev_extent = extent
            return changed

    def _estimate_scale(self):
        try:
            x0, x1, y0, y1 = self._m.get_extent(4326)

            x0, x1 = np.clip((x0, x1), -180, 180)
            y0, y1 = np.clip((y0, y1), -90, 90)

            n = 100

            lons, lats = np.meshgrid(np.linspace(x0, x1, n), np.linspace(y0, y1, n))

            geod = self._geod
            ls = geod.line_lengths(lons, lats)
            scale = np.nanmedian(ls) * self._autoscale * 100

            # estimate the scale so that the actually drawn labels are properly rounded
            if isinstance(self._label_props["every"], int):
                scale = (
                    self._round_to_n(scale / self._n * self._label_props["every"], 1)
                    / self._label_props["every"]
                )
            else:
                scale = self._round_to_n(scale, 1) / self._n

            self._estimated_scale = scale
        except Exception:
            raise AssertionError(
                "EOmaps: Unable to automatically determine an "
                "appropriate scale for the scalebar... is the "
                "currently visible map extent heavily distorted?"
            )

    def _get_autopos(self, pos):
        # try to position the colorbar at the lower right corner of the axis
        x0, y0 = (self._m.ax.transAxes + self._m.ax.transData.inverted()).transform(pos)
        lon, lat = self._m._transf_plot_to_lonlat.transform(x0, y0)

        if not all(np.isfinite([x0, y0])):
            # if it fails, try to position it at the center of the extent
            extent = self._m.get_extent()
            lon, lat = self._m._transf_plot_to_lonlat.transform(
                np.mean(extent[:2]),
                np.mean(extent[2:]),
            )
        return lon, lat

    def _get_pos_as_autopos(self, lon, lat):
        pos = self._m._transf_lonlat_to_plot.transform(lon, lat)
        pos = (self._m.ax.transData + self._m.ax.transAxes.inverted()).transform(pos)
        return pos

    def _set_auto_position(self, pos):
        """Move the scalebar to the desired position and apply auto-scaling."""
        lon, lat = self._get_autopos(pos)
        self._set_position(lon, lat, self._azim)

    def set_scale(self, scale=None):
        """
        Set the length of a segment of the scalebar in meters.

        Parameters
        ----------
        scale  : float, optional
            The length (in meters) of the individual line-segments.
            If None, the scale will be determined automatically based on the currently
            visible plot-extent. The default is None.

        See Also
        --------
        ScaleBar.set_n : Set the number of segments to use.

        """
        self._scale = scale
        self._update(BM_update=True)

    def set_n(self, n=None):
        """
        Set number of segments to use for the scalebar.

        Parameters
        ----------
        n  : int, optional
            The number of segments. The default is None.

        See Also
        --------
        ScaleBar.set_scale : Set the length of the scalebar segments.

        """
        self._n = n

        # if the number of segments changed, re-draw labels completely!
        self._redraw_minitxt()
        self._update(BM_update=True)

    def set_scale_props(self, width=None, colors=None, **kwargs):
        """
        Set the style properties of the scale.

        Parameters
        ----------
        width : float, optional
            The width of the scalebar (in ordinary matplotlib linewidth units).
            The default is 5.
        colors : tuple, optional
            A sequence of colors that will be repeated to color the individual
            line-fragments of the scalebar. (you can provide more than 2 colors!)
            The default is ("k", "w").

        See Also
        --------
        ScaleBar.set_scale : Set a fixed length of the scalebar segments.
        ScaleBar.set_n : Set the number of segments to use.
        ScaleBar.set_patch_props : Set style properties of the scalebar frame.
        ScaleBar.set_label_props : Set style properties of the labels.
        ScaleBar.set_line_props : Set style of the lines between scalebar and labels.

        """
        self._set_scale_props(width=width, colors=colors, **kwargs)

        self._update(BM_update=True)

    def _set_scale_props(self, width=None, colors=None, **kwargs):
        if len(kwargs) > 0:
            raise TypeError(f"{list(kwargs)} are not allowed as 'scale_props' kwargs.")

        if width is not None:
            self._scale_props["width"] = width
        if colors is not None:
            self._scale_props["colors"] = colors

    def set_patch_props(self, offsets=None, **kwargs):
        """
        Set the style properties of the background patch.

        Parameters
        ----------
        offsets : tuple, optional
            A tuple that is used to adjust the offset of the frame-patch.
            Individual values represent `(top, bottom, left, right)` on a
            horizontally oriented scalebar. The default is (1, 1, 1, 1).
        kwargs :
            Additional kwargs are passed to the `matpltlotlib.Patches.PolygonPatch`
            that is used to draw the frame.
            The default is `{"fc": ".75", "ec": "k", "lw": 1, "ls": "-"}`

            Possible values are:

            - "facecolor", "edgecolor", "linewidth", "linestyle", "alpha" ...

        See Also
        --------
        ScaleBar.set_scale_props : Set style of the scale.
        ScaleBar.set_label_props : Set style of the labels.
        ScaleBar.set_line_props : Set style of the lines between scalebar and labels.

        """
        for key in kwargs:
            if not hasattr(self._artists["patch"], f"set_{key}"):
                raise AttributeError(f"EOmaps: '{key}' is not a valid patch property!")

        self._set_patch_props(offsets=offsets, **kwargs)
        self._update(BM_update=True)

    def _set_patch_props(self, offsets=None, **kwargs):
        for key, synonym in [
            ["fc", "facecolor"],
            ["ec", "edgecolor"],
            ["lw", "linewidth"],
            ["ls", "linestyle"],
        ]:
            if key in self._patch_props:
                self._patch_props[key] = kwargs.pop(
                    key, kwargs.pop(synonym, self._patch_props[key])
                )

        if offsets is not None:
            self._patch_offsets = offsets

        self._patch_props.update(kwargs)

    def set_line_props(self, update=True, **kwargs):
        """
        Set the style properties of the lines connecting the scale and the labels.

        Parameters
        ----------
        kwargs :
            All kwargs are passed to the `matpltlotlib.Collections.LineCollection`
            that is used to draw the frame.
            The default is `{"ec": "k", "lw": 1, "ls": "--"}`

            Possible values are:

            - "edgecolor" (or "ec"), "linewidth" (or "lw"), "linestyle" (or "ls") ...

        See Also
        --------
        ScaleBar.set_scale_props : Set style of the scale.
        ScaleBar.set_patch_props : Set style of the scalebar frame.
        ScaleBar.set_label_props : Set style of the labels.

        """
        for key in kwargs:
            if not hasattr(self._artists["patch_lines"], f"set_{key}"):
                raise AttributeError(f"EOmaps: '{key}' is not a valid line property!")

        self._set_line_props(**kwargs)
        self._update(BM_update=True)

    def _set_line_props(self, **kwargs):

        for key, synonym in [
            ["fc", "facecolor"],
            ["ec", "edgecolor"],
            ["lw", "linewidth"],
            ["ls", "linestyle"],
        ]:
            if key in self._line_props:
                self._line_props[key] = kwargs.pop(
                    key, kwargs.pop(synonym, self._line_props[key])
                )

        self._line_props.update(kwargs)

    def set_label_props(
        self,
        scale=None,
        rotation=None,
        every=None,
        offset=None,
        color=None,
        update=True,
        **kwargs,
    ):
        """
        Set the style properties of the labels.

        Parameters
        ----------
        scale : int, optional
            A scaling factor for the fontsize of the labels. The default is 1.
        rotation : float, optional
            The rotation angle of the labels (in degrees) relative to the
            curvature of the scalebar. The default is 0.
        every : int, list or tuple of ints, optional
            Indicator which sections of the scalebar should be labelled.

            - if int: every nth section is labelled
            - if a list/tuple is provided, only the selected sections are labelled.

            The default is 2.
        offset : float, optional
            A scaling factor to adjust the offset of the labels relative to the
            scalebar. The default is 1.
        color : str or tuple
            The color of the text.
            The default is "k" (e.g. black)
        kwargs :
            Additional kwargs are passed to `matplotlib.font_manager.FontProperties`
            to set the font specifications of the labels. Possible values are:

              - "family", "style", "variant", "stretch", and "weight"

            For example:
                >>> dict(family="Helvetica", style="italic").

        See Also
        --------
        ScaleBar.set_scale_props : Set style of the scale.
        ScaleBar.set_patch_props : Set style of the scalebar frame.
        ScaleBar.set_line_props : Set style of the lines between scalebar and labels.

        """
        for key in kwargs:
            if not hasattr(FontProperties, f"set_{key}"):
                raise AttributeError(f"EOmaps: '{key}' is not a valid font property!")

        self._set_label_props(
            scale=scale,
            rotation=rotation,
            every=every,
            offset=offset,
            color=color,
            **kwargs,
        )

        # in case the number of labels changed, re-draw labels completely
        if every is not None:
            self._redraw_minitxt()

        self._update(BM_update=True)

    def _set_label_props(
        self,
        scale=None,
        rotation=None,
        every=None,
        offset=None,
        color=None,
        **kwargs,
    ):

        if scale is not None:
            self._label_props["scale"] = scale
        if rotation is not None:
            self._label_props["rotation"] = rotation
        if every is not None:
            self._label_props["every"] = every
        if offset is not None:
            self._label_props["offset"] = offset
        if color is not None:
            self._label_props["color"] = color

        self._font_kwargs.update(
            **{key: kwargs.pop(key) for key in self._fontkeys if key in kwargs}
        )
        self._font_props = FontProperties(**self._font_kwargs)

        self._label_props.update(kwargs)

    def set_position(self, pos=None, auto_pos=None, azim=None):
        """
        Set the position of the colorbar.

        The position hereby represents the starting-point of the scalebar!

        Note
        ----
        If you set the position explicitly via the "pos" kwarg, the scalebar will no
        longer automatically update its position on pan/zoom events.
        (it can still be dragged to another position)

        Parameters
        ----------
        pos : (float, float) or None, optional
            (longitude, latitude) of the starting-point of the scalebar.

            The default is None.
        auto_pos : (float, float) or None, optional
            (x, y) of the starting-point of the scalebar in relative axis-coordinates.
            (e.g. (0, 0) = lower left corner and (1, 1) = upper right corner).

            Note: If you specify a point outside the map the scalebar will not be
            visible!

            The default is None.
        azim : float, optional
            The azimuth-direction in which to calculate the intermediate
            points for the scalebar. The default is None.

        """
        if pos is not None and auto_pos is not None:
            raise TypeError(
                "EOmaps: You can only provide either pos or auto_pos, "
                "to set the position of the scalebar, not both!"
            )

        if pos is not None:
            self._auto_position = False
            self._set_position(*pos, azim=azim)

        if auto_pos is not None:
            self._auto_position = auto_pos

        self._update(BM_update=True)

    def set_rotation(self, ang=0):
        """
        Set the absolute rotation angle of the first segment of the scalebar.

        Note
        ----
        This method sets the "absolute rotation angle" in display units,
        not the "azimuth angle" which can be set with :py:meth:`ScaleBar.set_position`.

        Parameters
        ----------
        ang : float
            The rotation angle.

        """
        lon, lat, _ = self.get_position()
        x0, y0 = self._m._transf_lonlat_to_plot.transform(lon, lat)
        x1, y1 = self._m._transf_lonlat_to_plot.transform(
            *self._geod.fwd(lon, lat, -ang, self.get_scale())[:2]
        )
        azim = np.rad2deg(-np.arctan2(x1 - x0, y1 - y0))
        self.set_position((lon, lat), azim=azim)

    def _set_position(self, lon=None, lat=None, azim=None, update=False):
        if lon is None:
            lon = self._lon
        if lat is None:
            lat = self._lat
        if azim is None:
            azim = self._azim

        self._lon = lon
        self._lat = lat
        self._azim = azim
        pts = self._get_pts(lon, lat, azim)
        d = self._get_d()
        ang = self._get_ang(pts[0][0], pts[0][1])

        # do this after setting _lon, _lat and _azim !
        # and BEFORE all other changes since we need the size of the text-patches!
        self._update_minitxt(d, pts)

        # update scale properties
        self._artists["scale"].set_verts(pts)
        # don't use first and last scale (they are just used as placeholders)
        color_names = self._get_scale_color_names()
        colors = np.tile(
            color_names,
            int(np.ceil(len(pts) / len(color_names))),
        )[: len(pts)]
        self._artists["scale"].set_colors(colors)
        self._artists["scale"].set_linewidth(self._scale_props["width"])

        verts = self._get_patch_verts(pts, lon, lat, ang, d)
        # TODO check how to deal with invalid vertices!!
        # print(np.all(np.isfinite(self._m._transf_plot_to_lonlat.transform(*verts.T))))
        # verts = np.ma.masked_invalid(verts)

        self._artists["patch"].set_xy(verts)
        self._artists["patch"].update(self._patch_props)

        # update indicator lines
        line_verts = self._get_line_verts(pts, lon, lat, self._azim, d)
        self._artists["patch_lines"].set_segments(line_verts)
        self._artists["patch_lines"].update(self._line_props)

        if getattr(self, "_picked", False):
            self._artists["patch"].set_edgecolor("r")
            self._artists["patch"].set_linewidth(2)
            self._artists["patch"].set_linestyle("-")

    def set_size_factor(self, s):
        """
        Set the size_factor that is used to adjust the size of the labels.

        Parameters
        ----------
        s : float
            The size factor. The default is 1.
        """
        self._size_factor = s
        self._update(BM_update=True)

    def get_size_factor(self):
        """
        Get the current size-factor of the scalebar.

        Returns
        -------
        size_factor
            The size factor.

        """
        return self._size_factor

    def get_position(self):
        """
        Return the current position (and orientation) of the scalebar.

        Returns
        -------
        list
            a list corresponding to [longitude, latitude, azimuth].
        """
        return [self._lon, self._lat, self._azim]

    def set_auto_scale(self, autoscale_fraction=0.25):
        """
        Automatically evaluate an appropriate scale for the scalebar.

        (and dynamically update the scale on pan/zoom events.)


        Parameters
        ----------
        autoscale_fraction : float, or None, optional
            The (approximate) fraction of the axis width to use as size for the scalebar
            in the autoscale procedure. Note that this is number is not exact since
            (depending on the crs) the final scalebar might be curved.

            If None, the current scale is maintained.
            The default is 0.25.
        """
        self._autoscale = autoscale_fraction
        self._update(BM_update=True)

    def set_pickable(self, q):
        """
        Set if the scalebar is interactive (True) or not (False).

        If True, the following interactions can be performed:

        - **LEFT-CLICK** on the scalebar to make the scalebar interactive
        - drag the scalebar with the <LEFT MOUSE BUTTON>
        - use the **SCROLL WHEEL** to adjust the (auto-)scale of the scalebar
        - use < control > + **SCROLL WHEEL** to adjust the size of the labels

        Keyboard-shortcuts (only active if a scalebar is selected):

        - use < + > and < - > to rotate the scalebar
        - use the < arrow-keys > to increase the frame size
        - use < alt > + < arrow-keys > to decrease the frame size
        - use < control > + < left > and < right > keys to adjust the label-offset
        - use < control > + < up > and < down > keys to rotate the labels

        - use < delete > to remove the scalebar from the plot
        - use the < escape > to exit editing the scalebar

        Parameters
        ----------
        q : bool
            Indicator if the scalebar is interactive (True) or not (False).

        """
        if q is True:
            self._make_pickable()
        else:
            self._undo_pickable()

    def _get_base_pts(self, lon, lat, azim, npts=None):
        if npts is None:
            npts = self._n + 1

        pts = self._geod.fwd_intermediate(
            lon1=lon,
            lat1=lat,
            azi1=azim,
            npts=npts,
            del_s=self._current_scale,
            initial_idx=0,
            terminus_idx=0,
            **_pyproj_geod_fix_args,
        )

        if isinstance(self._label_props["every"], int):
            self._every = [
                i for i in range(pts.npts) if i % self._label_props["every"] == 0
            ]
        else:
            self._every = [i for i in self._label_props["every"] if i <= pts.npts]
        return pts

    def _get_pts(self, lon, lat, azim):
        pts = self._get_base_pts(lon, lat, azim)

        lons, lats = [], []
        for [lon1, lon2], [lat1, lat2] in zip(pairwise(pts.lons), pairwise(pts.lats)):
            # get intermediate points
            p = self._geod.inv_intermediate(
                lon1=lon1,
                lat1=lat1,
                lon2=lon2,
                lat2=lat2,
                npts=self._interm_pts,
                initial_idx=0,
                terminus_idx=0,
                **_pyproj_geod_fix_args,
            )
            lons.append(p.lons)
            lats.append(p.lats)

        # transform points to plot-crs
        pts_t = self._m._transf_lonlat_to_plot.transform(np.array(lons), np.array(lats))
        pts_t = np.stack(pts_t, axis=2)

        return pts_t

    def _get_txt(self, n):
        scale = self._current_scale
        # the text displayed above the scalebar
        units = {" mm": 0.001, " m": 1, " km": 1000, "k km": 1000000}
        for key, val in units.items():
            x = scale * n / val
            if scale * n / val < 1000:
                return np.format_float_positional(x, trim="-", precision=3) + key

        return f"{scale} m"

    def _txt(self):
        return self._get_txt(self._n)

    def _get_d(self):
        # the base length used to define the size of the scalebar
        x0, x1, y0, y1 = self._m.get_extent(self._m.crs_plot)

        return (
            np.max(np.abs([x0 - x1, y0 - y1]))
            / self._size_factor_base
            * self._size_factor
        )

    def _get_patch_verts(self, pts, lon, lat, ang, d):
        offsets = self._patch_offsets

        # top bottom left right refers to a horizontally oriented colorbar!
        ot = d * offsets[0]
        ob = self._maxw + d * (self._label_props["offset"] + offsets[1])
        o_l = d * offsets[2]
        o_r = d * offsets[3]

        dxy = np.gradient(pts.reshape((-1, 2)), axis=0)
        alpha = np.arctan2(dxy[:, 1], -dxy[:, 0])
        t = np.column_stack([np.sin(alpha), np.cos(alpha)])

        # in case the top scale has a label, add a margin to encompass the text!
        if len(pts) in self._every:
            o_r += self._top_h / 2

        ptop = pts.reshape((-1, 2)) - ot * t
        pbottom = pts.reshape((-1, 2)) + ob * t

        ptop[0] += (o_l * np.cos(alpha[0]), -o_l * np.sin(alpha[0]))
        pbottom[0] += (o_l * np.cos(alpha[0]), -o_l * np.sin(alpha[0]))

        ptop[-1] -= (o_r * np.cos(alpha[-1]), -o_r * np.sin(alpha[-1]))
        pbottom[-1] -= (o_r * np.cos(alpha[-1]), -o_r * np.sin(alpha[-1]))

        # TODO check how to deal with invalid vertices (e.g. self-intersections)

        return np.vstack([ptop, pbottom[::-1]])

    def _get_ang(self, p0, p1):
        # estimate the rotation-angle for the text
        try:
            dx0, dy0 = p1 - p0
            ang = np.arctan2(dy0, dx0)
            if not np.isfinite(ang):
                ang = 0
        except:
            ang = 0
        return ang

    def _get_txt_coords(self, lon, lat, d, ang):
        # get the base point for the text
        xt, yt = self._m._transf_lonlat_to_plot.transform(lon, lat)
        xt = xt - d * self._label_props["offset"] * np.sin(ang)
        yt = yt + d * self._label_props["offset"] * np.cos(ang)
        return xt, yt

    def _get_line_pts(self, lon, lat, d, ang):
        # get the base point for the text
        x0, y0 = self._m._transf_lonlat_to_plot.transform(lon, lat)

        offset = d / 3

        ox = offset * self._label_props["offset"] * np.sin(ang)
        oy = offset * self._label_props["offset"] * np.cos(ang)

        x0 -= ox
        y0 += oy

        x1 = x0 - d * self._label_props["offset"] * np.sin(ang) + ox * 1.2
        y1 = y0 + d * self._label_props["offset"] * np.cos(ang) - oy * 1.2
        return (x0, y0), (x1, y1)

    def _get_line_verts(self, pts, lon, lat, ang, d):
        line_pts = self._get_base_pts(lon, lat, ang)
        line_lons, line_lats = line_pts.lons, line_pts.lats

        angs = np.arctan2(*np.array([p[0] - p[-1] for p in pts]).T[::-1])
        angs = [*angs, angs[-1]]

        lines = []
        for i, (lon, lat, ang) in enumerate(zip(line_lons, line_lats, angs)):
            if i not in self._every:
                continue

            lines.append(self._get_line_pts(lon, lat, d, ang))

        return lines

    # cache this to avoid re-evaluating the text-size when dragging the scalebar
    @lru_cache(1)
    def _get_maxw(self, sscale, sn, lscale, lrotation, levery):
        # arguments are only used for caching!

        # the max. width of the texts
        _maxw = 0
        _top_h = 0

        _transf_data_inverted = self._m.ax.transData.inverted()

        # make sure to cache the renderer instance to avoid performance issues!
        if self._renderer is None:
            self._renderer = self._m.f.canvas.get_renderer()

        # use the longest label to evaluate the max. width of the texts
        try:
            txtartist = self._artists[
                max(self._texts, key=lambda x: len(self._texts[x]))
            ]
            bbox = txtartist.get_window_extent(self._renderer).transformed(
                _transf_data_inverted
            )
            _maxw = max(bbox.width, bbox.height)
        except Exception:
            pass

        # evaluate the size of the "top" label
        try:
            _top_label = next(i for i in sorted(self._texts))
            val = self._artists[_top_label]
            bbox = val.get_window_extent(self._renderer).transformed(
                _transf_data_inverted
            )
            _top_h = np.sqrt(bbox.width**2 + bbox.height**2)
        except Exception:
            pass

        self._maxw = _maxw
        self._top_h = _top_h

    def _set_minitxt(self, d, pts):
        angs = np.arctan2(*np.array([p[0] - p[-1] for p in pts]).T[::-1])
        angs = [*angs, angs[-1]]
        pts = self._get_base_pts(self._lon, self._lat, self._azim, npts=self._n + 2)

        self._texts.clear()
        for i, (lon, lat, ang) in enumerate(zip(pts.lons, pts.lats, angs)):
            if i not in self._every:
                continue

            if i == 0:
                txt = "0"
            else:
                txt = self._get_txt(i)

            xy = self._get_txt_coords(lon, lat, d, ang)
            tp = TextPath(
                xy, txt, size=self._label_props["scale"] * d / 2, prop=self._font_props
            )

            patch = PathPatch(tp, color=self._label_props["color"], lw=0, zorder=1)
            patch.set_transform(
                Affine2D().rotate_around(
                    *xy, ang + np.pi / 2 + np.deg2rad(self._label_props["rotation"])
                )
                + self._m.ax.transData
            )
            patch.set_clip_on(False)
            self._artists[f"text_{i}"] = self._m.ax.add_artist(patch)
            self._texts[f"text_{i}"] = txt
            self._m.BM.add_artist(self._artists[f"text_{i}"], layer=self._layer)

    def _redraw_minitxt(self):
        # re-draw the text patches in case the number of texts changed

        # don't redraw if we haven't drawn anything yet
        if not hasattr(self, "_artists"):
            return

        for key in list(self._artists):
            if key.startswith("text_"):
                self._artists[key].remove()
                self._m.BM.remove_artist(self._artists[key])
                del self._artists[key]

        pts = self._get_pts(self._lon, self._lat, self._azim)
        d = self._get_d()
        self._set_minitxt(d, pts)

    def _update_minitxt(self, d, pts):
        angs = np.arctan2(*np.array([p[0] - p[-1] for p in pts]).T[::-1])
        angs = [*angs, angs[-1]]
        pts = self._get_base_pts(self._lon, self._lat, self._azim, npts=self._n + 2)

        for i, (lon, lat, ang) in enumerate(zip(pts.lons, pts.lats, angs)):
            if i not in self._every:
                continue

            if i == 0:
                txt = "0"
            else:
                txt = self._get_txt(i)

            xy = self._get_txt_coords(lon, lat, d, ang)

            tp = PathPatch(
                TextPath(
                    xy,
                    txt,
                    size=self._label_props["scale"] * d / 2,
                    prop=self._font_props,
                ),
                lw=0,
            )

            self._texts[f"text_{i}"] = txt
            self._artists[f"text_{i}"].set_path(tp.get_path())
            self._artists[f"text_{i}"].set_transform(
                Affine2D().rotate_around(
                    *xy, ang + np.pi / 2 + np.deg2rad(self._label_props["rotation"])
                )
                + self._m.ax.transData
            )

        # do this to allow using every as key for the lru_cache
        if isinstance(self._label_props["every"], int):
            hashable_every = self._label_props["every"]
        else:
            hashable_every = frozenset(self._label_props["every"])

        self._get_maxw(
            self._current_scale,
            self._n,
            self._label_props["scale"],
            self._label_props["rotation"],
            hashable_every,
        )

    def _add_scalebar(self, pos, azim, pickable=True):

        assert (
            self._artists["scale"] is None
        ), "EOmaps: there is already a scalebar present!"

        # we need to make sure that the figure has been drawn to ensure that the
        # ax-transformations work as expected
        # TODO is there a way to omit this?
        self._m.f.canvas.draw()

        if pos is None:
            lon, lat = self._get_autopos(self._auto_position)
        else:
            # don't auto-reposition if lon/lat has been provided
            lon, lat = pos
            self._auto_position = False

        self._lon = lon
        self._lat = lat
        self._azim = azim

        if self._scale is None:
            self._estimate_scale()

        pts = self._get_pts(lon, lat, azim)
        d = self._get_d()
        ang = self._get_ang(pts[0][0], pts[0][1])

        # -------------- add the labels
        self._set_minitxt(d, pts)

        # -------------- add the patch
        self._get_maxw(
            self._current_scale,
            self._n,
            self._label_props["scale"],
            self._label_props["rotation"],
            self._label_props["every"],
        )

        verts = self._get_patch_verts(pts, lon, lat, ang, d)
        p = Polygon(verts, **self._patch_props)
        self._artists["patch"] = self._m.ax.add_artist(p)

        # -------------- add lines between text and scale
        line_verts = self._get_line_verts(pts, lon, lat, self._azim, d)
        lc = LineCollection(line_verts, **self._line_props)
        self._artists["patch_lines"] = self._m.ax.add_artist(lc)
        self._m.BM.add_artist(self._artists["patch_lines"], layer=self._layer)

        # -------------- add the scalebar
        coll = LineCollection(pts)

        color_names = self._get_scale_color_names()
        colors = np.tile(
            color_names,
            int(np.ceil(len(pts) / len(color_names))),
        )[: len(pts)]
        coll.set_colors(colors)
        coll.set_linewidth(self._scale_props["width"])
        self._artists["scale"] = self._m.ax.add_collection(coll, autolim=False)

        # -------------- make all artists animated
        self._artists["scale"].set_zorder(1)
        self._artists["patch"].set_zorder(0)

        self._m.BM.add_artist(self._artists["scale"], layer=self._layer)
        self._m.BM.add_artist(self._artists["patch"], layer=self._layer)

        # update scalebar props whenever new backgrounds are fetched
        # (e.g. to take care of updates on pan/zoom/resize)
        self._m.BM._before_fetch_bg_actions.append(self._update)

        if pickable is True:
            self._make_pickable()

        # make sure scalebar-artists are not clipped with respect
        # to the spine of the axes
        for _, a in self._artists.items():
            if a is not None:
                a.set_clip_on(False)

    def _get_scale_color_names(self):
        colors = []
        for i in self._scale_props["colors"]:
            if isinstance(i, tuple):
                colors.append(to_hex(i, keep_alpha=True))
            else:
                colors.append(i)
        return colors

    def _make_pickable(self):
        if self._pickable is True:
            return

        self._picked = False
        self._pick_drag = False

        self._artists["patch"].set_picker(True)

        # if not hasattr(self, "_cid_PICK"):
        if getattr(self, "_cid_PICK", None) is None:
            self._cid_PICK = self._m.f.canvas.mpl_connect("pick_event", self._cb_pick)

        self._pickable = True

    def _undo_pickable(self):
        if not self._pickable:
            return

        self._unpick()
        self._artists["patch"].set_picker(None)

        if getattr(self, "_cid_PICK", None) is not None:
            self._m.f.canvas.mpl_disconnect(self._cb_pick)
            self._cid_PICK = None

        self._pickable = False

    def _unpick(self):
        global _picked_scalebars

        if self._picked:
            self._picked = False
            self._pick_drag = False
            self._remove_cbs()
            if self in _picked_scalebars:
                _picked_scalebars.remove(self)

    def _cb_pick(self, event):
        global _picked_scalebars

        if event.mouseevent.button == 1:
            if event.artist is self._artists["patch"]:
                # unpick all other scalebars to make sure overlapping scalebars
                # are not picked together
                while len(_picked_scalebars) > 0:
                    s = _picked_scalebars.pop()
                    s._unpick()
                    s._update()

                self._picked = True
                self._add_cbs()
                # forward mouseevent to start dragging if button remains pressed
                self._cb_click(event.mouseevent)
                _picked_scalebars.add(self)
                self._update(BM_update=True)

    def _cb_click(self, event):
        if (
            self._picked
            and event.button == 1
            and self._artists["patch"].contains(event)[0]
        ):
            # TODO
            # if self._auto_position is False:
            #     print("The position of this scalebar is fixed!")
            #     return

            self._pick_drag = True
            # get the offset_position of the click with respect to the
            # reference point of the scalebar
            xdata, ydata = event.xdata, event.ydata
            if xdata is not None and ydata is not None:
                lon0, lat0 = self._m._transf_plot_to_lonlat.transform(
                    event.xdata, event.ydata
                )
                self._pick_start_offset = self._lon - lon0, self._lat - lat0
            else:
                # None event coordinates happen if you click outside
                # the axes-spine
                self._pick_start_offset = 0, 0

        elif event.button in ["up", "down"]:
            # pass scroll events that happen on top of the scalebar
            # (they are handled explicitly in "cb_scroll" )
            pass
        elif self._picked:
            self._unpick()
            self._update(BM_update=True)

    def _cb_move(self, event):
        if not self._picked or not self._pick_drag:
            return

        if event.button != 1:
            return

        ox, oy = self._pick_start_offset
        try:
            lon, lat = self._m._transf_plot_to_lonlat.transform(
                event.xdata, event.ydata
            )
        except Exception:
            _log.info("EOmaps: Unable to position scalebar.")
            return

        self._update(lon=lon + ox, lat=lat + oy, BM_update=True)

    def _cb_scroll(self, event):
        if not self._picked:
            return

        if event.key == "control":
            self._size_factor = max(
                0.01, self._size_factor + event.step / self._size_factor_base
            )
        elif event.key == "r":
            self._azim += event.step * self._cb_rotate_interval
        else:

            if event.key == "shift":
                multip = 5
            else:
                multip = 1

            if self._scale is None:
                self._autoscale = np.clip(
                    self._autoscale + multip * event.step / self._scale_factor_base,
                    0.01,
                    0.99,
                )
                prev_scale = self._scale
                try:
                    self._estimate_scale()
                except Exception:
                    self._scale = prev_scale
            else:
                _log.warning(
                    "EOmaps: The scale of the scalebar is fixed! "
                    "Use s.set_scale(None) to use autoscaling!"
                )

        self._update(BM_update=True)

    def _cb_keypress(self, event):
        if not self._picked:
            return

        key = event.key
        udlr = ["left", "right", "down", "up"]

        if event.key == "delete":
            self.remove()
            return

        # rotate
        if key == "+":
            self._azim += self._cb_rotate_interval
        elif key == "-":
            self._azim -= self._cb_rotate_interval
        # set text offset
        elif key == "ctrl+right":
            o = self._label_props["offset"]
            o += self._cb_offset_interval
            self._set_label_props(offset=o)
        elif key == "ctrl+left":
            o = self._label_props["offset"]
            o -= self._cb_offset_interval
            self._set_label_props(offset=o)
        # set text rotation
        elif key == "ctrl+up":
            o = self._label_props["rotation"]
            o += self._cb_rotate_interval
            self._set_label_props(rotation=o)
        elif key == "ctrl+down":
            o = self._label_props["rotation"]
            o -= self._cb_rotate_interval
            self._set_label_props(rotation=o)
        # set patch offsets
        elif key in udlr:
            patch_offsets = [*self._patch_offsets]
            patch_offsets[udlr.index(key)] += 0.1
            self._set_patch_props(offsets=patch_offsets)
        elif key in ("alt+" + i for i in udlr):
            patch_offsets = [*self._patch_offsets]
            patch_offsets[udlr.index(key[4:])] -= 0.1
            self._set_patch_props(offsets=patch_offsets)
        # unpick scalebar
        elif event.key == "escape":
            self._unpick()

        self._update(BM_update=True)

    def _add_cbs(self):
        self._remove_cbs()

        self._cid_MOVE = self._m.f.canvas.mpl_connect(
            "motion_notify_event", self._cb_move
        )
        self._cid_SCROLL = self._m.f.canvas.mpl_connect("scroll_event", self._cb_scroll)
        self._cid_CLICK = self._m.f.canvas.mpl_connect(
            "button_press_event", self._cb_click
        )
        self._cid_KEYPRESS = self._m.f.canvas.mpl_connect(
            "key_press_event", self._cb_keypress
        )

    def _remove_cbs(self):
        for cidname in (
            "_cid_MOVE",
            "_cid_SCROLL",
            "_cid_CLICK",
            "_cid_KEYPRESS",
        ):
            cid = getattr(self, cidname, None)
            if cid is not None:
                self._m.f.canvas.mpl_disconnect(cid)
                setattr(self, cidname, None)

    def _update(self, lon=None, lat=None, azim=None, BM_update=False, **kwargs):
        # only do this if the extent changed (to avoid performance issues)
        if self._extent_changed():
            # check if the scalebar is in the current field-of-view
            # if not, avoid updating it and make it invisible
            if self._auto_position is False:
                bbox = self._artists["patch"].get_extents()
                if not self._m.ax.bbox.overlaps(bbox):
                    for a in self._artists.values():
                        a.set_visible(False)
                    return
                else:
                    for a in self._artists.values():
                        a.set_visible(True)

            # clear the cache to re-evaluate the text-width if label
            # props have changed
            self.__class__._get_maxw.cache_clear()

            # estimate a new scale if the scale is not fixed explicitly
            if self._scale is None:
                prev_scale = self._scale
                try:
                    self._estimate_scale()
                except Exception:
                    self._scale = prev_scale

        # make sure scalebars are not positioned out of bounds
        if lon is not None and lat is not None:
            lon = np.clip(lon, -179, 179)
            lat = np.clip(lat, -89, 89)

        if self._auto_position is not False:
            if lon is not None and lat is not None:
                self._auto_position = self._get_pos_as_autopos(lon, lat)
            self._set_auto_position(self._auto_position)
        else:
            self._set_position(lon=lon, lat=lat, azim=azim)

        if BM_update:
            # note: when using this function as before_fetch_bg action, updates
            # would cause a recursion!
            self._m.BM.update()

    def remove(self):
        """Remove the scalebar from the map."""
        self._unpick()
        for a in self._artists.values():
            self._m.BM.remove_artist(a)
            a.remove()

        # remove trigger to update scalebar properties on fetch_bg
        if self._update in self._m.BM._before_fetch_bg_actions:
            self._m.BM._before_fetch_bg_actions.remove(self._update)

        self._renderer = None

        self._m.BM.update()

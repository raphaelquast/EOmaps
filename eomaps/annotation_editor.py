# Copyright EOmaps Contributors
#
# This file is part of EOmaps and is released under the BSD 3-clause license.
# See LICENSE in the root of the repository for full licensing details.

"""Functionalities for editable annotations."""
import logging
from types import SimpleNamespace
import numpy as np

_log = logging.getLogger(__name__)

_eomaps_picked_ann = None


class DraggableBase:
    """
    Helper base class for a draggable artist (legend, offsetbox).

    This class is a copy of the DraggableBase class of matplotlib
    to handle the drawing of artists with EOmaps.

    >>> from matplotlib.offsetbox import DraggableBase

    """

    def __init__(self, ref_artist, use_blit=False):
        self.ref_artist = ref_artist
        if not ref_artist.pickable():
            ref_artist.set_picker(True)
        self.got_artist = False
        self._use_blit = use_blit and self.canvas.supports_blit
        self.cids = [
            self.canvas.callbacks._connect_picklable("pick_event", self.on_pick),
            self.canvas.callbacks._connect_picklable(
                "button_release_event", self.on_release
            ),
        ]

    # A property, not an attribute, to maintain picklability.
    canvas = property(lambda self: self.ref_artist.figure.canvas)

    def on_motion(self, evt):
        if self._check_still_parented() and self.got_artist:
            dx = evt.x - self.mouse_x
            dy = evt.y - self.mouse_y
            self.update_offset(dx, dy)

    def on_pick(self, evt):
        if self._check_still_parented() and evt.artist == self.ref_artist:
            self.mouse_x = evt.mouseevent.x
            self.mouse_y = evt.mouseevent.y
            self.got_artist = True
            self._c1 = self.canvas.callbacks._connect_picklable(
                "motion_notify_event", self.on_motion
            )
            self.save_offset()

    def on_release(self, event):
        if self._check_still_parented() and self.got_artist:
            self.finalize_offset()
            self.got_artist = False
            self.canvas.mpl_disconnect(self._c1)

    def _check_still_parented(self):
        if self.ref_artist.figure is None:
            self.disconnect()
            return False
        else:
            return True

    def disconnect(self):
        """Disconnect the callbacks."""
        for cid in self.cids:
            self.canvas.mpl_disconnect(cid)
        try:
            c1 = self._c1
        except AttributeError:
            pass
        else:
            self.canvas.mpl_disconnect(c1)

    def save_offset(self):
        pass

    def update_offset(self, dx, dy):
        pass

    def finalize_offset(self):
        pass


class DraggableAnnotation(DraggableBase):
    """Base class for draggable annotations."""

    def __init__(
        self,
        annotation,
        use_blit=True,
        drag_coords=True,
        select_signal=None,
        edit_signal=None,
    ):
        super().__init__(annotation, use_blit=use_blit)

        self.annotation = annotation
        self._drag_coords = drag_coords

        self._what = "xyann"
        self._init_ec = self.annotation.get_bbox_patch().get_edgecolor()
        self._ax_bbox = self.annotation.axes.bbox

        self._select_signal = select_signal
        self._edit_signal = edit_signal

    @property
    def _text_func(self):
        t = self.annotation._EOmaps_text
        if callable(t):
            return t
        else:
            return None

    def _get_what(self, key):
        if key == "control":
            what = "xy"
        elif key == "r":
            what = "rotate"
        elif key == "shift":
            what = "size"
        else:
            what = "xyann"

        return what

    def on_pick(self, evt):
        # global variable to store the currently picked annotation
        # (to avoid picking multiple annotations at once)
        global _eomaps_picked_ann

        if _eomaps_picked_ann is not None and evt.artist is not _eomaps_picked_ann:
            _eomaps_picked_ann._draggable.on_release(None)
            _eomaps_picked_ann = None

        if evt.artist is not self.annotation:
            return

        self._what = self._get_what(evt.mouseevent.key)

        # don't do anything if the picked annotation is already active
        if evt.artist is not _eomaps_picked_ann:
            self._init_ec = self.annotation.get_bbox_patch().get_edgecolor()

        super().on_pick(evt)

        self.annotation.get_bbox_patch().set_edgecolor("r")

        _eomaps_picked_ann = self.annotation

        # emit signal if provided
        if self._select_signal is not None:
            self._select_signal()

    def save_offset(self):
        ann = self.annotation

        if self._what == "xyann":
            self.ox, self.oy = ann.get_transform().transform(ann.xyann)
        elif self._what == "xy":
            self._ax_bbox = ann.axes.bbox
            self.x, self.y = ann.axes.transData.transform(ann.xy)
        elif self._what == "rotate":
            self.rot = ann.get_rotation()
        elif self._what == "size":
            self.size = ann.get_size()

    def update_offset(self, dx, dy):
        ann = self.annotation

        if self._what == "xyann":
            ann.xyann = (
                ann.get_transform().inverted().transform((self.ox + dx, self.oy + dy))
            )
        elif self._what == "xy":
            if not self._drag_coords and self.annotation.figure is not None:
                self.annotation.figure._EOmaps_parent._log_on_event(
                    "warning",
                    "EOmaps: The position of annotations based on IDs "
                    "cannot be dynamically updated!",
                    "button_release_event",
                )
                return

            # don't allow moving the annotation anchor outside the axis bounds
            # (otherwise it would disappear if "annotation_clip=True")
            ann.xy = ann.axes.transData.inverted().transform(
                (
                    np.clip(self.x + dx, self._ax_bbox.x0 + 1, self._ax_bbox.x1 - 1),
                    np.clip(self.y + dy, self._ax_bbox.y0 + 1, self._ax_bbox.y1 - 1),
                )
            )

            # dynamically update the text if a function is used to set the text
            if self._text_func:
                # TODO allow additional args (ID, val, ind) used in pick-annotations?
                # (currently only click-annotations can be dragged so this should
                # not be an issue..)
                txt = self._text_func(pos=ann.xy)
                ann.set_text(txt)

        elif self._what == "rotate":
            d = dx / ann.figure.bbox.width - dy / ann.figure.bbox.height
            ann.set_rotation(self.rot - d * 360)
        elif self._what == "size":
            d = 1 + (dx / ann.figure.bbox.width + dy / ann.figure.bbox.height)
            ann.set_size(self.size * d)

    def on_release(self, event):
        # in case release was outside of text, "unpick" the annotation
        # (e.g. to avoid keeping the picked annotation until the editor is exited)
        global _eomaps_picked_ann

        super().on_release(event)

        if _eomaps_picked_ann is not None:
            if event is None or not _eomaps_picked_ann.contains(event)[0]:

                _eomaps_picked_ann.get_bbox_patch().set_edgecolor(
                    _eomaps_picked_ann._draggable._init_ec
                )

                if _eomaps_picked_ann.figure:
                    # only attempt to draw if the figure still exists
                    # (e.g. to avoid issues with multiple simultaneous figures)
                    _eomaps_picked_ann.axes.draw_artist(_eomaps_picked_ann)
                    _eomaps_picked_ann.figure.canvas.blit()

                _eomaps_picked_ann = None
                # emit signal if provided
                if self._select_signal is not None:
                    self._select_signal()

        if self.annotation.figure is not None:
            self.annotation.figure._EOmaps_parent.BM.update()

    def on_motion(self, evt):
        # check if a keypress event triggered a change of the interaction
        # (e.g. move/rotate etc.)
        if self._check_still_parented() and self.got_artist:
            what = self._get_what(evt.key)
            if what != self._what:
                self._what = what
                self.save_offset()
                # if interaction changed, we need to re-set the start positions!
                self.mouse_x = evt.x
                self.mouse_y = evt.y

        super().on_motion(evt)
        if self.annotation.figure is not None:
            self.annotation.figure._EOmaps_parent.BM.update(artists=[self.annotation])
        # emit signal if provided
        if self._edit_signal is not None:
            self._edit_signal()

    def disconnect(self):
        try:
            # reset edgecolor
            self.annotation.get_bbox_patch().set_edgecolor(self._init_ec)
            self.annotation.axes.draw_artist(self.annotation)

            super().disconnect()
        except Exception:
            # disconnection can fail in case the figure has already been closed
            pass


class _EditorBase:
    """
    A base class for "Editor" classes that should display an info textbox.

    - left click: toggle help-text visibility

    """

    def __init__(self, *args, m=None, **kwargs):
        self.m = m
        self._info_cids = set()

    def set_info(self, x, y, text):
        self._info_x = x
        self._info_y = y
        self._info_text = text

    def _on_press(self, event):
        if event.button == 3:
            self.toggle_info_text()

    def show_info_text(self):
        # only re-draw if info-text is None
        if getattr(self, "_info_artist", None) is not None:
            return

        self._info_artist = self.m.f.text(
            self._info_x,
            self._info_y,
            self._info_text,
            transform=self.m.f.transFigure,
            ha="left",
            va="top",
            fontsize=min(self.m.f.bbox.width * 72 / self.m.f.dpi / 60, 12),
            bbox=dict(
                boxstyle="round", facecolor=".8", edgecolor="k", lw=0.5, alpha=0.9
            ),
            zorder=1e6,
            fontfamily="monospace",
        )

        self.m.BM.add_artist(self._info_artist, "all")

        self._info_cids.add(
            self.m.f.canvas.mpl_connect("button_press_event", self._on_press)
        )
        self.m.BM._before_fetch_bg_actions.append(self._update_info_fontsize)
        self.m.BM.update()

    def toggle_info_text(self):
        if getattr(self, "_info_artist", None) is not None:
            self._info_artist.set_visible(not self._info_artist.get_visible())
        self.m.BM.update()

    def remove_info_text(self):
        while len(self._info_cids) > 0:
            self.m.f.canvas.mpl_disconnect(self._info_cids.pop())

        try:
            self.m.BM._before_fetch_bg_actions.remove(self._update_info_fontsize)
        except ValueError:
            pass

        if getattr(self, "_info_artist", None) is not None:
            self.m.BM.remove_artist(self._info_artist, "all")
            try:
                self._info_artist.remove()
            except Exception:
                _log.error(
                    "There was a problem while trying to remove the "
                    "Editor info text artist."
                )

            self._info_artist = None
            self.m.BM.update()

    def _update_info_fontsize(self, *args, **kwargs):
        if getattr(self, "_info_artist", None) is not None:
            fontsize = min(self.m.f.bbox.width * 72 / self.m.f.dpi / 60, 15)
            self._info_artist.set_fontsize(fontsize)


class AnnotationEditor(_EditorBase):
    """Class to handle interactive annotation edits."""

    def __init__(self, m):
        super().__init__(m=m)
        self.set_info(
            0.72,
            0.98,
            (
                "AnnotationEditor Controls:\n\n"
                "CLICK:   Select annotation\n"
                "  -      Move text-box\n"
                "\n"
                "CONTROL: Move anchor\n"
                "SHIFT:   Resize\n"
                "R:       Rotate\n"
                "DELETE:  Delete\n\n"
                "Note: Use the widget to set\n"
                "      text, style etc. of\n"
                "      selected annotations"
                "\n\n(right-click to hide info)"
            ),
        )

        self._annotations = list()
        self._drag_active = False
        self._remove_cid = None

    @property
    def _last_selected_annotation(self):
        global _eomaps_picked_ann
        return _eomaps_picked_ann

    def _set_last_selected_annotation(self, ann):
        global _eomaps_picked_ann
        _eomaps_picked_ann = ann

    def emit_selected_signal(self, *args, **kwargs):
        self.m._emit_signal("annotationSelected")

    def emit_edit_signal(self, *args, **kwargs):
        self.m._emit_signal("annotationEdited")

    def _add(self, a, kwargs, transf=None, drag_coords=True):
        if a not in self._annotations:
            self._annotations.append(
                SimpleNamespace(
                    a=a, kwargs=kwargs, transf=transf, drag_coords=drag_coords
                )
            )
            if self._drag_active:
                a._draggable = DraggableAnnotation(
                    a,
                    drag_coords=drag_coords,
                    select_signal=self.emit_selected_signal,
                    edit_signal=self.emit_edit_signal,
                )

    def __call__(self, q=True):
        """
        Toggle if annotations are editable or not.

        If annotations are editable, they can be "picked" with the right mouse button
        and the following interactions can be performed:

        NOTE: keys must be pressed before picking the annotation!

        - drag an annotation with the mouse to change the text-position
        - hold down "control" while dragging to change the annotation-coordinates
        - hold down "shift" while dragging to change the fontsize
        - hold down "r" while dragging to rotate the text

        Parameters
        ----------
        q : bool, optional
            If True, annotations of this Maps-object will be editable.
            If False, annotations will be set to "fixed".
            The default is True.

        See Also
        --------
        print_code(): Print the code to reproduce the annotations to the console.

        """
        if q:
            for ann in self._annotations:
                self._make_ann_editable(ann.a, ann.drag_coords)

            self._drag_active = True

            self._remove_cid = self.m.f.canvas.mpl_connect(
                "key_press_event", self.remove_selected_annotation
            )

            self.m._emit_signal("annotationEditorActivated")
            self.m.BM._clear_all_temp_artists()

            self.show_info_text()
            self.m.cb.execute_callbacks(False)
            _log.info("EOmaps: Annotations editable!")
        else:
            for ann in self._annotations:
                self._undo_ann_editable(ann.a)

            self._drag_active = False

            # reset last picked annotation on exit
            global _eomaps_picked_ann
            _eomaps_picked_ann = None

            if self._remove_cid:
                self.m.f.canvas.mpl_disconnect(self._remove_cid)

            self.remove_info_text()

            self.m._emit_signal("annotationEditorDeactivated")
            self.m.BM.update()
            self.m.cb.execute_callbacks(True)

    def _make_ann_editable(self, ann, drag_coords=True):
        # avoid issues with annotations that are removed during interactive editing
        if ann.figure is not self.m.f:
            return

        drag = getattr(ann, "_draggable", None)
        if drag:
            drag.disconnect()

        ann._draggable = DraggableAnnotation(
            ann,
            drag_coords=drag_coords,
            select_signal=self.emit_selected_signal,
            edit_signal=self.emit_edit_signal,
        )

    def _undo_ann_editable(self, ann):
        # avoid issues with annotations that are removed during interactive editing
        if ann.figure is not self.m.f:
            return

        drag = getattr(ann, "_draggable", None)
        if drag:
            drag.disconnect()

    @property
    def annotations(self):
        d = [ann.a for ann in self._annotations]

        return d

    def _get_what(self, what):
        if what == "all":
            use_anns = self._annotations
        elif isinstance(what, int):
            use_anns = [self._annotations[what]]
        elif isinstance(what, (list, tuple)):
            use_anns = [self._annotations[i] for i in what]

        return use_anns

    def update_text(self, text, what="all"):
        """
        Update the text of one (or more) annotations.

        You can either provide a static string, or a function that is used to
        dynamically update the annotation-text


        Parameters
        ----------
        text : str or callable
            if str: the string to print
            if callable: A function that returns the string that should be
            printed in the annotation with the following call-signature:

            >>> def text(m, ID, val, pos, ind):
            >>>     # m   ... the Maps object
            >>>     # ID  ... the ID
            >>>     # pos ... the position
            >>>     # val ... the value
            >>>     # ind ... the index of the clicked pixel
            >>>
            >>>     return "the string to print"

        what : TYPE, optional
            DESCRIPTION. The default is "all".

        """
        use_anns = self._get_what(what)

        for ann in use_anns:
            ann.kwargs["text"] = text
            ann.a._EOmaps_text = text

            if callable(text):
                txt = text(
                    pos=ann.a.xy,
                    ID=ann.kwargs.get("ID", None),
                    val=ann.kwargs.get("val", None),
                    ind=ann.kwargs.get("ind", None),
                )
                ann.a.set_text(txt)
            else:
                ann.a.set_text(str(text))

        self.m.BM.update()

    def print_code(
        self,
        m_name="m",
        what="all",
        sanitize_coordinates=True,
        replace=None,
        use_ids=False,
    ):
        """
        Print the code to reproduce the annotations to the console.


        Note
        ----
        While this works nicely in most standard cases, it can not be guaranteed
        that extensively customized annotations are properly translated to code!

        Text-functions that are used to dynamically update the annotation-text will
        be replaced by the currently visible text! To maintain interactivity, you can
        replace individual arguments via the `replace` dict.

        If coordinates are provided in a custom crs, they will be reprojected to
        epsg=4326 to avoid issues with incorrect string-representations of the crs and
        to make the annotation independent of the current map-crs (in case xy_crs=None).

        Parameters
        ----------
        m_name : str, optional
            The variable-name of the Maps-object used in the code.
            (code will be generated as `< m_name >.add_annotation(...)`)
            The default is "m".
        what : str, int or list of int, optional
            Indicator which annotation codes should be printed.

            - if "all": the code for all annotations is printed
            - if int: only the code for the nth annotation is printed
            - if list of int: the code for the annotations [0,.., i, .., n] is printed

            The default is "all".
        sanitize_coordinates : bool, optional
            If Tue, annotation coordinates where the crs has not been specified
            explicitly are reprojected to epsg=4326 to avoid ambiguities (e.g. if the
            plot-crs changes etc.)

            If False, coordinates will be returned as-is (which might lead to incorrect
            results in some cases). The default is True
        replace : dict or None, optional
            A dictionary of values used to replace the arguments of the annotation-call.
            This is particularly useful if you want to keep annotations interactive,
            for example if you use a function to set the text, you can use the following
            to maintain the function in the printed text:

            >>> my_textfunc = lambda ID, **kwargs: str(ID)
            >>> m._edit_annotations.print_code(replace={"text": my_textfunc})
        use_ids : bool, optional
            If True, ID values are used to identify the annotation-positions.
            (NOTE: this can cause problems because the Maps-object must have
            the correct data assigned to identify the annotation!)
            If False, always use the current position of the annotation
            as input-argument for the returned code.

        """

        if replace is None:
            replace = dict()

        prefix = "\n"

        use_anns = self._get_what(what)

        anns = []
        for i, ann in enumerate(use_anns):
            a = ann.a
            kwargs = {**ann.kwargs}

            s = f"{m_name}.add_annotation("

            txt = kwargs["text"]
            if txt is not None and callable(a._EOmaps_text) and "text" not in replace:
                # if a function was provided as txt
                s = "# NOTE: Text function has been replaced by output!\n" + s

            # in case coordinates have been provided in a custom crs, reproject
            # it to lat/lon
            if sanitize_coordinates and not isinstance(
                kwargs.get("xy_crs", None), (int, str)
            ):
                # if xy_crs was provided other than str or int, reproject to lat/lon
                # to make sure the code still works if the map-crs changes

                xy_crs = 4326
                if ann.transf is not None:
                    xy = self.m._transf_plot_to_lonlat.transform(
                        *ann.transf.transform(*a.xy)
                    )
                else:
                    xy = self.m._transf_plot_to_lonlat.transform(*a.xy)

                if not all(i in replace for i in ("xy", "xy_crs")):
                    s = "# NOTE: Anchor coordinates reprojected to epsg=4326!\n" + s
            else:
                xy_crs = kwargs["xy_crs"]
                if xy_crs is not None and not isinstance(xy_crs, (int)):
                    xy_crs = str(xy_crs)
                xy = a.xy

            kwargs.update(
                dict(
                    xy=tuple(xy),
                    xy_crs=xy_crs,
                    xytext=tuple(a.xyann),
                    rotation=a.get_rotation(),
                    fontsize=a.get_size(),
                    text=a.get_text() if txt is not None else None,
                ),
            )

            # remove arguments that should not be printed
            kwargs.pop("permanent", None)
            if "ID" in kwargs:
                if kwargs["ID"] is None or use_ids is False:
                    kwargs.pop("ID")
                else:
                    kwargs.pop("xy")
                    kwargs.pop("xy_crs")

            for key, val in kwargs.items():
                if key in replace:
                    s += f"{key}={replace[key]}, "
                    continue

                if isinstance(val, str):
                    val = val.encode("unicode-escape").decode()
                    s += rf"{key}='{val}', "
                else:
                    s += f"{key}={val}, "

            s += ")"

            anns.append(s)

        prefix += "\n"

        try:
            import black

            for i in range(len(anns)):
                try:
                    anns[i] = black.format_str(anns[i], mode=black.Mode())
                except Exception as ex:
                    anns[i] = f"\n##### error: {ex}\n#####\n"
                    pass
        except:
            pass
        print(prefix + "\n\n".join(anns))

    def update_selected_text(self, text=None):
        if text is not None:
            _eomaps_picked_ann.set_text(text)

        self.m.BM.update()

    def remove_selected_annotation(self, event):
        if event is None or event.key == "delete":
            global _eomaps_picked_ann
            if _eomaps_picked_ann:
                self.m.BM.remove_artist(_eomaps_picked_ann)
                _eomaps_picked_ann.remove()
                _eomaps_picked_ann = None
                self.m.BM.update()

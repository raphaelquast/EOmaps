from matplotlib.offsetbox import DraggableBase
from types import SimpleNamespace
import numpy as np

picked_ann = None


class DraggableAnnotationNew(DraggableBase):
    def __init__(self, annotation, use_blit=False, drag_coords=True):
        super().__init__(annotation, use_blit=use_blit)

        self.annotation = annotation
        self._drag_coords = drag_coords

        self._what = "xyann"
        self._init_ec = self.annotation.get_bbox_patch().get_edgecolor()
        self._ax_bbox = self.annotation.axes.bbox

        t = self.annotation._EOmaps_text
        if callable(t):
            self._text_func = t
        else:
            self._text_func = None

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
        print(evt.artist)
        # global variable to store the currently picked annotation
        # (to avoid picking multiple annotations at once)
        global picked_ann

        if picked_ann is not None and evt.artist is not picked_ann:
            picked_ann._draggable.on_release(None)
            picked_ann = None

        if evt.artist is not self.annotation:
            return

        self._what = self._get_what(evt.mouseevent.key)

        self._init_ec = self.annotation.get_bbox_patch().get_edgecolor()
        super().on_pick(evt)

        self.annotation.get_bbox_patch().set_edgecolor("r")

        picked_ann = self.annotation

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
            if not self._drag_coords:
                print(
                    "EOmaps: The annotation-coordinates of annotations based on IDs "
                    "cannot be dynamically updated!"
                )
                return

            # don't allow moving the annotation anchor outside the axis bounds
            # (otherwhise it would disappear if "annotation_clip=True")
            ann.xy = ann.axes.transData.inverted().transform(
                (
                    np.clip(self.x + dx, self._ax_bbox.x0 + 1, self._ax_bbox.x1 - 1),
                    np.clip(self.y + dy, self._ax_bbox.y0 + 1, self._ax_bbox.y1 - 1),
                )
            )

            # dynamically update the text if a function is used to set the text
            if self._text_func:
                txt = self._text_func(pos=ann.xy)
                ann.set_text(txt)

        elif self._what == "rotate":
            ann.set_rotation(self.rot - dx / ann.figure.bbox.width * 180)
        elif self._what == "size":
            d = 1 + (dx / ann.figure.bbox.width + dy / ann.figure.bbox.height)
            ann.set_size(self.size * d)

    def on_release(self, event):
        ann = self.annotation
        ann.get_bbox_patch().set_edgecolor(self._init_ec)
        super().on_release(event)
        if ann.figure:
            # only attempt to draw if the figure still exists
            # (e.g. to avoid issues with multiple simultaneous figures)
            ann.figure.canvas.draw_idle()

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

    def disconnect(self):
        try:
            super().disconnect()
        except Exception:
            # disconnection can fail in case the figure has already been closed
            pass


class AnnotationEditor:
    def __init__(self, m):
        self.m = m
        self._annotations = list()

        self._drag_active = False

    def _add(self, a, kwargs, transf=None, drag_coords=True):
        if a not in self._annotations:
            self._annotations.append(
                SimpleNamespace(
                    a=a, kwargs=kwargs, transf=transf, drag_coords=drag_coords
                )
            )
            if self._drag_active:
                a._draggable = DraggableAnnotationNew(a, drag_coords=drag_coords)

    def __call__(self, q=True, print_msg=True):
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
        print_msg: bool, optional
            Indicator if info-message should be printed or not.
            The default is True.

        See Also
        --------
        print_code(): Print the code to reproduce the annotations to the console.

        """
        if q:
            for ann in self._annotations:
                self._make_ann_editable(ann.a, ann.drag_coords)
                self._drag_active = True
            if print_msg:
                print(
                    f"EOmaps: Annotations editable! Shortcuts:\n"
                    " -  default : move annotation\n"
                    " - 'control': move anchor\n"
                    " - 'shift':   resize\n"
                    " - 'r':       rotate\n"
                )
        else:
            for ann in self._annotations:
                self._undo_ann_editable(ann.a)
                self._drag_active = False

    def _make_ann_editable(self, ann, drag_coords=True):
        drag = getattr(ann, "_draggable", None)
        if drag:
            drag.disconnect()

        ann._draggable = DraggableAnnotationNew(ann, drag_coords=drag_coords)

    def _undo_ann_editable(self, ann):
        drag = getattr(ann, "_draggable", None)
        if drag:
            drag.disconnect()

    def print_code(self, m="m", what="all", sanitize_coordinates=True):
        """
        Print the code to reproduce the annotations to the console.

        NOTE: While this works nicely in most standard cases, it can not be guaranteed
        that extensively customized annotations are properly translated to code!

        Parameters
        ----------
        m : str, optional
            The variable-name of the Maps-object used in the code.
            (code will be generated as `< object name >.add_annotation(...)`)
            The default is "m".
        what : str, int or list of int, optional
            Indicator which annotation codes should be printed.

            - if "all": the code for all annotations is printed
            - if int: only the code for the nth annotation is printed
            - if list of int: the code for the annotations [0,.., i, .., n] is printed

            The default is "all".
        sanitize_coordinates : bool, optional
            If Tue, annotation coordinates where the crs has not been specified
            explicitly are reprojected to epsg=4326 to avoid amiguities (e.g. if the
            plot-crs changes etc.)

            If False, coordinates will be returned as-is (which might lead to incorrect
            results in some cases). The default is True

        """
        prefix = "\n"

        if what == "all":
            use_anns = self._annotations
        elif isinstance(what, int):
            use_anns = (self._annotations[what],)
        elif isinstance(what, (list, tuple)):
            use_anns = (self._annotations[i] for i in what)

        anns = []
        for i, ann in enumerate(use_anns):
            a = ann.a
            kwargs = {**ann.kwargs}

            s = f"{m}.add_annotation("

            txt = kwargs["text"]
            if txt is not None and callable(a._EOmaps_text):
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
                if kwargs["ID"] is None:
                    kwargs.pop("ID")
                else:
                    kwargs.pop("xy")
                    kwargs.pop("xy_crs")

            for key, val in kwargs.items():
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

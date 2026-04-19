import weakref
from functools import wraps

from ..utilities import Utilities
from ..drawer import ShapeDrawer
from ..annotation_editor import AnnotationEditor


class ToolsMixin:
    draw = ShapeDrawer
    util = Utilities

    def __init__(self, *args, **kwargs):
        if self.parent == self:
            self.__util = Utilities(self)
            self.__edit_annotations = AnnotationEditor(self)

        self.util = self.parent._ToolsMixin__util

        # do this on init to avoid confusing sphinx
        self.draw = self._draw

        super().__init__(*args, **kwargs)

    @property
    def _draw(self):
        # avoid initializing draw on init of Maps object
        # to reduce init-time
        if not hasattr(self, "_draw"):
            self._draw = ShapeDrawer(weakref.proxy(self))
        return self._draw

    @property
    def _edit_annotations(self):
        return self.parent._ToolsMixin__edit_annotations

    @wraps(AnnotationEditor.__call__)
    def edit_annotations(self, b=True, **kwargs):
        # self.parent._edit_annotations(b, **kwargs)
        return self._edit_annotations(b, **kwargs)

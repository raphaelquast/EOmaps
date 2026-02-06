import weakref
from functools import wraps

from ..utilities import Utilities
from ..draw import ShapeDrawer
from ..annotation_editor import AnnotationEditor


class ToolsMixin:
    draw = ShapeDrawer
    util = Utilities

    def __init__(self, *args, **kwargs):
        if self.parent == self:
            self.util = Utilities(self)
            self.__edit_annotations = AnnotationEditor(self)
        else:
            self.util = self.parent.util

        super().__init__(*args, **kwargs)

        self.draw = ShapeDrawer(weakref.proxy(self))

    @property
    def _edit_annotations(self):
        return self.parent._ToolsMixin__edit_annotations

    @wraps(AnnotationEditor.__call__)
    def edit_annotations(self, b=True, **kwargs):
        self._edit_annotations(b, **kwargs)

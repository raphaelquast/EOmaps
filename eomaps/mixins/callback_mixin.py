from ..callback_container import CallbackContainer
from ..helpers import _from_parent


class CallbackMixin:
    cb = CallbackContainer

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # initialize accessor for callbacks
        self.cb = CallbackContainer(self)
        self.cb._init_cbs()

    @property
    @_from_parent
    def execute_callbacks(self):
        """
        Indicator if callbacks are executed or not.

        If set to False, no callback functions are triggered!
        (The set value is shared across all Maps-objects of a figure)

        """
        try:
            return self.__execute_callbacks
        except AttributeError:
            self.__execute_callbacks = True
            return self.__execute_callbacks

    @execute_callbacks.setter
    @_from_parent
    def execute_callbacks(self, value):
        self.__execute_callbacks = value

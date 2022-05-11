from abc import ABC, abstractmethod
from autoinject import injector


class ContextInformant(ABC):

    context_manager: "autoinject.class_registry.ContextManager" = None

    @injector.construct
    def __init__(self, name:str = None):
        if name is None:
            name = str(self.__class__)
        self.name = name

    @abstractmethod
    def get_context_id(self):
        pass

    def clear_context(self, context_name):
        self.context_manager.clear_context(self.name, context_name)


class NamedContextInformant(ContextInformant):

    def __init__(self):
        super().__init__('named_context')
        self.current_context = "_default"

    def switch_context(self, context_name):
        self.current_context = context_name

    def get_context_id(self):
        return self.current_context



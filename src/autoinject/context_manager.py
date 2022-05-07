from abc import ABC, abstractmethod
from .class_registry import ClassRegistry


class ContextManager(ABC):

    def __init__(self, cls_registry):
        super().__init__()
        self._registry = cls_registry

    @abstractmethod
    def _get_cached_object(self, cls_name):
        pass

    @abstractmethod
    def _save_object_to_cache(self, cls_name, obj):
        pass

    def get_object(self, cls):
        cls_as_str = str(cls)
        cache_check_obj = self._get_cached_object(cls_as_str)
        if not cache_check_obj:
            new_obj = self._registry.get_instance(cls_as_str)
            self._save_object_to_cache(cls_as_str, new_obj)
            return new_obj
        else:
            return cache_check_obj


class GlobalContextManager(ContextManager):

    def __init__(self, cls_registry: ClassRegistry):
        super().__init__(cls_registry)
        self.object_cache = {}

    def _get_cached_object(self, cls_name):
        return self.object_cache[cls_name] if cls_name in self.object_cache else None

    def _save_object_to_cache(self, cls_name, obj):
        self.object_cache[cls_name] = obj


class NamedContextManager(ContextManager):

    def __init__(self, cls_registry: ClassRegistry):
        super().__init__(cls_registry)
        self.contexts = {
            "_default": []
        }
        self.current_context = "_default"

    def create_context(self, context_name):
        self.contexts[context_name] = {}

    def remove_context(self, context_name):
        if context_name in self.contexts and not context_name == '_default':
            del self.contexts[context_name]
            if self.current_context == context_name:
                self.current_context = '_default'

    def set_context(self, context_name):
        if context_name not in self.contexts:
            self.create_context(context_name)
        self.current_context = context_name

    def _get_cached_object(self, cls_name):
        return self.contexts[self.current_context][cls_name] if cls_name in self.contexts[self.current_context] else None

    def _save_object_to_cache(self, cls_name, obj):
        self.contexts[self.current_context][cls_name] = obj

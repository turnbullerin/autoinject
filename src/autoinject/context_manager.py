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

    @abstractmethod
    def _get_cached_object(self, cls_name):
        return self.object_cache[cls_name] if cls_name in self.object_cache else None

    @abstractmethod
    def _save_object_to_cache(self, cls_name, obj):
        self.object_cache[cls_name] = obj

from abc import ABC, abstractmethod
from .class_registry import ClassRegistry, CacheStrategy


class CacheStrategyNotSupportedError(ValueError):
    pass


class ContextManager(ABC):

    def __init__(self, cls_registry):
        super().__init__()
        self._registry = cls_registry

    @abstractmethod
    def _get_cached_object(self, cls_name, strategy):
        pass

    @abstractmethod
    def _save_object_to_cache(self, cls_name, obj, strategy):
        pass

    @abstractmethod
    def _supports_caching_strategy(self, strategy):
        pass

    def get_object(self, cls):
        cls_as_str = str(cls)
        strategy = self._registry.get_cache_strategy(cls)
        if strategy == CacheStrategy.NO_CACHE:
            return self._registry.get_instance(cls_as_str)
        if not self._supports_caching_strategy(strategy):
            raise CacheStrategyNotSupportedError("Strategy {} is not supported".format(strategy))
        cache_check_obj = self._get_cached_object(cls_as_str, strategy)
        if not cache_check_obj:
            new_obj = self._registry.get_instance(cls_as_str)
            self._save_object_to_cache(cls_as_str, new_obj, strategy)
            return new_obj
        else:
            return cache_check_obj


class NamedContextManager(ContextManager):

    def __init__(self, cls_registry: ClassRegistry):
        super().__init__(cls_registry)
        self.contexts = {
            "_default": {},
            "_global": {},
        }
        self.current_context = "_default"

    def create_context(self, context_name):
        self.contexts[context_name] = {}

    def remove_context(self, context_name):
        if context_name in self.contexts and context_name not in ('_default', "_global"):
            del self.contexts[context_name]
            if self.current_context == context_name:
                self.current_context = '_default'

    def set_context(self, context_name):
        if context_name == "_global":
            raise ValueError("Cannot set context to _global, reserved space")
        if context_name not in self.contexts:
            self.create_context(context_name)
        self.current_context = context_name

    def _get_cached_object(self, cls_name, strategy):
        if strategy == CacheStrategy.CONTEXT_CACHE:
            return self.contexts[self.current_context][cls_name] if cls_name in self.contexts[self.current_context] else None
        else:
            return self.contexts["_global"][cls_name] if cls_name in self.contexts["_global"] else None

    def _save_object_to_cache(self, cls_name, obj, strategy):
        if strategy == CacheStrategy.CONTEXT_CACHE:
            self.contexts[self.current_context][cls_name] = obj
        else:
            self.contexts["_global"][cls_name] = obj

    def _supports_caching_strategy(self, strategy):
        return strategy in (CacheStrategy.NO_CACHE, CacheStrategy.GLOBAL_CACHE, CacheStrategy.CONTEXT_CACHE)

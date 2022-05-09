from .class_registry import ClassRegistry, CacheStrategy


class CacheStrategyNotSupportedError(ValueError):
    pass


class ContextManager:

    def __init__(self, cls_registry):
        super().__init__()
        self._registry = cls_registry
        self._context_cache = {}
        self._global_cache = {}
        self._informants = []

    def clear_context(self, informant, context_name):
        remove_key = "::{}:{}::".format(informant.name, context_name)
        remove_keys = [key for key in self._context_cache if remove_key in key]
        for key in remove_keys:
            del self._context_cache[key]

    def register_informant(self, informant):
        self._informants.append(informant)

    def _get_context_hash(self):
        h = "base::"
        for informant in self._informants:
            h += "{}:{}::".format(informant.name, informant.get_context_id())
        return h

    def get_object(self, cls):
        cls_as_str = self._registry.cls_to_str(cls)
        strategy = self._registry.get_cache_strategy(cls)
        if strategy == CacheStrategy.NO_CACHE:
            return self._registry.get_instance(cls_as_str)
        elif strategy == CacheStrategy.GLOBAL_CACHE:
            if cls_as_str not in self._global_cache:
                self._global_cache[cls_as_str] = self._registry.get_instance(cls_as_str)
            return self._global_cache[cls_as_str]
        else:
            context_hash = self._get_context_hash()
            if context_hash not in self._context_cache:
                self._context_cache[context_hash] = {}
            if cls_as_str not in self._context_cache[context_hash]:
                self._context_cache[context_hash][cls_as_str] = self._registry.get_instance(cls_as_str)
            return self._context_cache[context_hash][cls_as_str]

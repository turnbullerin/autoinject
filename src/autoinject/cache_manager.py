""" The context manager manages object caches based on contexts.

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import gc
import weakref

from .debug import debug
from .class_registry import ClassRegistry, CacheStrategy, ClassInfo, InjectableInfo
from .informants import SituationInformant, ThreadedContextInformant, ContextVarInformant
import time
import atexit
import autoinject.types as ait
import typing as t




class _SubCacheManager:
    """Manage a sub-context which will have a different GLOBAL state as well (used for test cases)."""

    def __init__(self, context_manager: "CacheManager"):
        self.context_manager: "CacheManager" = context_manager
        self._global_cache: t.Optional[t.Dict[str, t.Any]] = None
        self._context_cache: t.Optional[t.Dict[str, t.Dict[str, t.Any]]] = None
        self._constructors: t.Optional[t.Dict[str, InjectableInfo]] = None

    def __enter__(self) -> "CacheManager":
        debug("Entering subcache", debug_type="subcache")
        self._global_cache = self.context_manager.global_cache
        self._context_cache = self.context_manager.context_cache
        self._constructors = {
            x: self.context_manager.cls_registry.object_constructors[x].copy()
            for x in self.context_manager.cls_registry.object_constructors
        }
        self.context_manager.global_cache = {}
        self.context_manager.context_cache = {}

        return self.context_manager

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.context_manager.teardown()
        self.context_manager.global_cache = self._global_cache or {}
        self.context_manager.context_cache = self._context_cache or {}
        self.context_manager.cls_registry.object_constructors = self._constructors or {}
        self._global_cache = None
        self._context_cache = None
        self._constructors = None
        debug("Exiting subcache", debug_type="subcache")

class CacheManager:
    """  Responsible for managing the object caches based on the context.

        A context can be anything that other packages would like to define; it is defined by an implementation of
        :class:`autoinject.informants.ContextInformant` which provides the context manager with a unique value for
        each context. If multiple informants are registered, they are aggregated together; if any informant reports
        a different context ID, then it is a different context.

        When retrieving an object, they are lazily instantiated from the ``ClassRegistry`` as needed, then cached based
        on the :class:`autoinject.class_registry.CacheStrategy` defined for them.

        :param cls_registry: An instance of the class registry to use
        :type cls_registry: autoinject.informants.ClassRegistry
    """

    garbage_collection_frequency = 0

    def __init__(self, cls_registry: ClassRegistry):
        """ Constructor"""
        super().__init__()
        self.cls_registry = cls_registry
        self.context_cache: t.Dict[str, t.Dict[str, t.Any]] = {}
        self.global_cache: t.Dict[str, t.Any] = {}
        self._informants: t.List[SituationInformant] = []
        self.contextvar_info = ContextVarInformant()
        self.thread_info = ThreadedContextInformant()
        self.register_informant(self.thread_info)
        self.register_informant(self.contextvar_info)
        self._last_gc: t.Optional[float] = None
        atexit.register(self.teardown)
        gc.callbacks.append(self._gc_callback)

    def _gc_callback(self, phase, info):
        if phase == 'start':
            self.cleanup()

    def teardown(self):
        """Remove all object references to ensure they get garbage collected."""
        # Global cache clean-up
        self._cleanup_cache_dict(self.global_cache)
        self.global_cache = {}
        # Context-based cache clean-up
        for cache_key in list(self.context_cache.keys()):
            self._cleanup_cache_dict(self.context_cache[cache_key])
            del self.context_cache[cache_key]
        self.context_cache = {}

    def destroy_cache_id(self, informant: SituationInformant, context_name: str):
        """ Removes the context and all objects from the context cache.

        ``context_name`` should be a value that would have been sent by ``get_context_id()``

        :param informant: The context informant to remove the context for
        :type informant: autoinject.informants.SituationInformant
        :param context_name: The name of the context to destroy
        :type context_name: str
        """
        remove_key = "::{}:{}::".format(informant.name.replace(":", "_"), context_name.replace(":", "_"))
        remove_keys = [key for key in self.context_cache.keys() if remove_key in key]
        for key in remove_keys:
            debug("Destroying cache [%s]", key, debug_type="cleanup")
            self._cleanup_cache_dict(self.context_cache[key])
            del self.context_cache[key]

    def _cleanup_cache_dict(self, obj_dict: t.Dict[str, object]):
        """Cleanup all objects in a list of objects."""
        for obj in obj_dict.values():
            self._cleanup_object(obj)

    def _cleanup_object(self, obj: object):
        """Cleanup an object on leaving scope."""
        if hasattr(obj, "__cleanup__"):
            debug("Cleaning up object [%s]", obj, debug_type="cleanup")
            obj.__cleanup__()

    def register_informant(self, informant: SituationInformant):
        """ Registers a context informant

        :param informant: The informant to register
        :type informant: SituationInformant
        """
        informant.set_cache_manager(self)
        self._informants.append(informant)
        debug("Registered informant [%s]", informant, debug_type="informant_management")

    def _get_context_hash(self, ignore_informants: t.Optional[t.List[str]] = None) -> str:
        """ Gets a unique string based on all context informants registered

        :returns: A unique string based on the informants
        :rtype: str
        """
        return "::" +  "::".join(
            "{}:{}".format(informant.name.replace(":", "_"), informant.get_cache_id().replace(":", "_"))
            for informant in self._informants if ignore_informants is None or informant.name not in ignore_informants
        ) + "::"

    def cleanup(self):
        """ Asks each informant to check for expired contexts """
        debug("Cleanup called", debug_type="cleanup")
        for informant in self._informants:
            informant.check_expired_caches()
        self._prune_weakrefs()
        self._last_gc = time.monotonic()

    def _prune_weakrefs(self):
        for x in list(self.global_cache.keys()):
            if isinstance(self.global_cache[x], weakref.ReferenceType) and self.global_cache[x]() is None:
                del self.global_cache[x]
                debug("Removedinvalid weakref from global cache [%s]", x)
        for y in self.context_cache:
            for x in list(self.context_cache[y].keys()):
                if isinstance(self.context_cache[y][x], weakref.ReferenceType) and self.context_cache[y][x]() is None:
                    del self.context_cache[y][x]
                    debug("Removing invalid weakref from context cache [%s] [%s]", y, x, debug_type="cleanup")

    def subcontext(self):
        return _SubCacheManager(self)

    def clear_cache(self, cls: ait.InjectableType):
        """Remove the class from all caches."""
        cls_as_str = self.cls_registry.get_cache_key(cls)
        if cls_as_str in self.global_cache:
            del self.global_cache[cls_as_str]
            debug("Removed %s from global cache", cls_as_str, debug_type="cleanup")
        for ctx in self.context_cache:
            if cls_as_str in self.context_cache[ctx]:
                del self.context_cache[ctx][cls_as_str]
                debug("Removed %s from context cache %s", cls_as_str, ctx, debug_type="cleanup")

    def get_object(self, cls: ait.InjectableType) -> t.Any:
        """ Retrieves an object of type cls from the cache or class registry.

        The caching strategy is respected by this method.

        :param cls: The type to retrieve
        :type cls: type OR str
        :returns: An object of type cls
        :rtype: object
        """
        if self.garbage_collection_frequency > 0:
            if self._last_gc is None or (time.monotonic() - self._last_gc) > self.garbage_collection_frequency:
                self.cleanup()
        obj_info = self.cls_registry.get_class_info(cls)
        if obj_info.strategy == CacheStrategy.NO_CACHE:
            debug("Uncached object built for [%s]", obj_info.cache_key, debug_type="fetch")
            return obj_info.constructor()
        elif obj_info.strategy == CacheStrategy.GLOBAL_CACHE:
            debug("Checking global cache for [%s]", obj_info.cache_key, debug_type="fetch")
            return self._get_object(self.global_cache, obj_info)
        else:
            context_hash = self._get_context_hash(obj_info.ignore_informants)
            if context_hash not in self.context_cache:
                debug("Adding new context cache for [%s]", context_hash, debug_type="fetch")
                self.context_cache[context_hash] = {}
            debug("Checking context cache [%s] for [%s]", context_hash, obj_info.cache_key, debug_type="fetch")
            return self._get_object(self.context_cache[context_hash], obj_info)

    @staticmethod
    def _get_object(cache_dict: t.Dict[str, t.Any], obj_info: ClassInfo):
        if obj_info.cache_key in cache_dict:
            if isinstance(cache_dict[obj_info.cache_key], weakref.ReferenceType):
                obj = cache_dict[obj_info.cache_key]()
                if obj is not None:
                    debug("Using weakref cached object for [%s]: [%s]", obj_info.cache_key, obj, debug_type="fetch")
                    return obj
            else:
                cached = cache_dict[obj_info.cache_key]
                debug("Using cached object for [%s]: [%s]", obj_info.cache_key, cached, debug_type="fetch")
                return cached
        if obj_info.constructor.as_weakref:
            x = obj_info.constructor()
            debug("Built weakref object for [%s]: [%s]", obj_info.cache_key, x, debug_type="fetch")
            cache_dict[obj_info.cache_key] = weakref.ref(x)
            return x
        new_obj = obj_info.constructor()
        cache_dict[obj_info.cache_key] = new_obj
        debug("Built new object for [%s]: [%s]", obj_info.cache_key, new_obj, debug_type="fetch")
        return cache_dict[obj_info.cache_key]


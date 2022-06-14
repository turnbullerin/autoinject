""" The context manager manages object caches based on contexts.

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
from .class_registry import ClassRegistry, CacheStrategy
from .informants import ContextInformant, ThreadedContextInformant
import time


# Time that must elapse since last call to cleanup() before get_object() will automatically
# trigger the call.
GARBAGE_COLLECTION_FREQUENCY = 5


class ContextManager:
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

    def __init__(self, cls_registry: ClassRegistry):
        """ Constructor"""
        super().__init__()
        self._registry = cls_registry
        self._context_cache = {}
        self._global_cache = {}
        self._informants = []
        self.register_informant(ThreadedContextInformant())
        self._last_gc = None

    def destroy_context(self, informant: ContextInformant, context_name: str):
        """ Removes the context and all objects from the context cache.

        ``context_name`` should be a value that would have been sent by ``get_context_id()``

        :param informant: The context informant to remove the context for
        :type informant: autoinject.informants.ContextInformant
        :param context_name: The name of the context to destroy
        :type context_name: str
        """
        remove_key = "::{}:{}::".format(informant.name, context_name)
        remove_keys = [key for key in self._context_cache if remove_key in key]
        for key in remove_keys:
            del self._context_cache[key]

    def register_informant(self, informant: ContextInformant):
        """ Registers a context informant

        :param informant: The informant to register
        :type informant: ContextInformant
        """
        informant.set_context_manager(self)
        self._informants.append(informant)

    def _get_context_hash(self) -> str:
        """ Gets a unique string based on all of the context informants registered

        :returns: A unique string based on the informants
        :rtype: str
        """
        h = "base::"
        for informant in self._informants:
            h += "{}:{}::".format(informant.name, informant.get_context_id())
        return h

    def cleanup(self):
        """ Asks each informant to check for expired contexts """
        for informant in self._informants:
            informant.check_expired_contexts()
        self._last_gc = time.monotonic()

    def get_object(self, cls):
        """ Retrieves an object of type cls from the cache or class registry.

        The caching strategy is respected by this method.

        :param cls: The type to retrieve
        :type cls: type OR str
        :returns: An object of type cls
        :rtype: object
        """
        if self._last_gc is None or (time.monotonic() - self._last_gc) > GARBAGE_COLLECTION_FREQUENCY:
            self.cleanup()
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

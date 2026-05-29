import contextvars
import unittest

from autoinject import NamedSituationInformant, CacheManager, ClassRegistry, CacheStrategy, ContextVarInformant
from autoinject.informants import ContextVarManager
from autoinject.reflect import fqn


class Service:
    ...


class TestInformants(unittest.TestCase):

    def test_no_cache_manager_raises(self):
        x = NamedSituationInformant()
        with self.assertRaises(Exception):
            _ = x.cache_manager

    def test_destroy_self(self):
        x = NamedSituationInformant()
        class_registry = ClassRegistry()
        cache_manager = CacheManager(class_registry)
        cache_manager.register_informant(x)
        x.set_cache_manager(cache_manager)
        class_registry.register(Service, caching_strategy=CacheStrategy.CONTEXT_CACHE)
        y = cache_manager.get_object(Service)
        chash = cache_manager._get_context_hash()
        self.assertIn(chash, cache_manager.context_cache)
        self.assertIn(fqn(Service), cache_manager.context_cache[chash])
        x.destroy_self()
        self.assertNotIn(chash, cache_manager.context_cache)

class TestContextManager(unittest.TestCase):

    def test_bad_str(self):
        x = ContextVarInformant()
        with self.assertRaises(ValueError):
            _ = ContextVarManager(x, context="foobar")  # type: ignore # intended failure

    def test_bad_type(self):
        x = ContextVarInformant()
        with self.assertRaises(TypeError):
            _ = ContextVarManager(x, context=self)  # type: ignore # intended failure

    def test_good_context(self):
        x = ContextVarInformant()
        c = contextvars.Context()
        y = ContextVarManager(x, context=c)
        self.assertIs(y._context, c)

    def test_enter_error(self):
        cache_manager = CacheManager(ClassRegistry())
        x = ContextVarInformant()
        x.set_cache_manager(cache_manager)
        c = contextvars.Context()
        y = ContextVarManager(x, context=c)
        with y as z:
            with self.assertRaises(ValueError):
                with z as q:
                    ...



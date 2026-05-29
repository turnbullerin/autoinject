import gc
import unittest
import weakref

from autoinject import InjectionManager, CacheStrategy

injector = InjectionManager()

@injector.register(as_weakref=True, caching_strategy=CacheStrategy.GLOBAL_CACHE)
class Service: ...

@injector.register(as_weakref=True, caching_strategy=CacheStrategy.CONTEXT_CACHE)
class NonSafeService: ...

@injector.register(as_weakref=True, caching_strategy=CacheStrategy.GLOBAL_CACHE)
class OtherService: ...

@injector.register(as_weakref=True, caching_strategy=CacheStrategy.CONTEXT_CACHE)
class NonSafeOtherService: ...

@injector.construct
class Client:
    service: Service
    nonsafe_service: NonSafeService

@injector.construct
class OtherClient:
    service: OtherService
    nonsafe_service: NonSafeOtherService

client = Client()
client2 = Client()

class TestAsWeakRef(unittest.TestCase):

    def test_is_weak_ref(self):
        self.assertTrue(injector.cls_registry.object_constructors["tests.test_weakref.Service"].constructors[0].as_weakref)

    def test_cache_as_weakref(self):
        self.assertIsInstance(injector.cache_manager.global_cache["tests.test_weakref.Service"], weakref.ReferenceType)

    def test_use_as_service(self):
        self.assertIsInstance(client.service, Service)

    def test_use_as_nonsafeservice(self):
        self.assertIsInstance(client.nonsafe_service, NonSafeService)

    def test_global_same(self):
        self.assertIs(client.service, client2.service)

    def test_local_same(self):
        self.assertIs(client.nonsafe_service, client.nonsafe_service)

    def test_clean_weakrefs(self):
        self.assertNotIn('tests.test_weakref.OtherService', injector.cache_manager.global_cache)
        cli = OtherClient()
        self.assertIsInstance(cli.service, OtherService)
        self.assertIsInstance(cli.nonsafe_service, NonSafeOtherService)
        self.assertIsInstance(injector.cache_manager.global_cache["tests.test_weakref.OtherService"], weakref.ReferenceType)
        cc = injector.cache_manager.context_cache
        self.assertIsInstance(cc[list(cc.keys())[0]]["tests.test_weakref.NonSafeOtherService"], weakref.ReferenceType)
        del cli
        self.assertIsNone(injector.cache_manager.global_cache['tests.test_weakref.OtherService']())
        gc.collect(2)
        self.assertNotIn("tests.test_weakref.OtherService", injector.cache_manager.global_cache)


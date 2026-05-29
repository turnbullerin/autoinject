from unittest import TestCase

from autoinject import CacheStrategy, InjectionManager
from autoinject.reflect import fqn

injector = InjectionManager()

@injector.injectable
@injector.with_weight(20)
@injector.with_cache_strategy(CacheStrategy.GLOBAL_CACHE)
@injector.as_weakref
@injector.with_ignore_informants(['five'])
class Service:
    ...



@injector.construct
class Client:
    service: Service


class TestClassVariables(TestCase):

    def test_injection_properties(self):
        client = Client()
        self.assertIsInstance(client.service, Service)
        entry = injector.cls_registry.object_constructors[fqn(Service)]
        self.assertEqual(20, entry.constructors[0].weight)
        self.assertTrue(entry.constructors[0].as_weakref)
        self.assertIs(entry.constructors[0].strategy, CacheStrategy.GLOBAL_CACHE)
        self.assertEqual(entry.constructors[0].ignore_informants, ['five'])
from unittest import TestCase

from autoinject import CacheStrategy, InjectionManager
from autoinject.reflect import fqn

injector = InjectionManager()

@injector.injectable
class Service:
    AUTOINJECT_WEIGHT = 20
    AUTOINJECT_CACHE_STRATEGY = CacheStrategy.GLOBAL_CACHE
    AUTOINJECT_AS_WEAKREF = True
    AUTOINJECT_IGNORE_INFORMANTS = ['five']


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
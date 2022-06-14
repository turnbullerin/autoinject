import unittest
import autoinject


class ForTestByName:
    pass


class TestRegistry(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.registry = autoinject.ClassRegistry()

        class TestClass:

            def __init__(self, def_arg='one', def_arg2='none'):
                self.def_arg = def_arg
                self.def_arg2 = def_arg2

        self.test_class = TestClass

    def test_register_base_class(self):
        self.assertFalse(self.registry.is_injectable(self.test_class))
        self.assertRaises(autoinject.ClassNotFoundException, self.registry.get_instance, self.test_class)
        self.registry.register(self.test_class)
        self.assertTrue(self.registry.is_injectable(self.test_class))
        self.assertIsInstance(self.registry.get_instance(self.test_class), self.test_class)

    def test_register_class_by_name(self):
        self.assertFalse(self.registry.is_injectable("tests.test_registry.ForTestByName"))
        self.assertRaises(autoinject.ClassNotFoundException, self.registry.get_instance, "tests.test_registry.ForTestByName")
        self.registry.register(ForTestByName)
        self.assertTrue(self.registry.is_injectable("tests.test_registry.ForTestByName"))
        self.assertIsInstance(self.registry.get_instance("tests.test_registry.ForTestByName"), ForTestByName)

    def test_register_class_constructor_args(self):
        self.registry.register(self.test_class, 'two', def_arg2='alpha')
        obj = self.registry.get_instance(self.test_class)
        self.assertEqual(obj.def_arg, 'two')
        self.assertEqual(obj.def_arg2, 'alpha')

    def test_register_class_custom_constructor(self):
        def build_test():
            return self.test_class('three')
        self.registry.register(self.test_class, constructor=build_test)
        obj = self.registry.get_instance(self.test_class)
        self.assertEqual(obj.def_arg, 'three')

    def test_register_class_custom_constructor_args(self):
        def build_test(a, b, *other, z=''):
            return self.test_class("{} {}".format(a, b), z)
        self.registry.register(self.test_class, "four", "five", constructor=build_test, z='beta')
        obj = self.registry.get_instance(self.test_class)
        self.assertEqual(obj.def_arg, 'four five')
        self.assertEqual(obj.def_arg2, 'beta')

    def test_cache_strategy_none(self):
        self.registry.register(self.test_class, caching_strategy=autoinject.CacheStrategy.NO_CACHE)
        self.assertEqual(self.registry.get_cache_strategy(self.test_class), autoinject.CacheStrategy.NO_CACHE)

    def test_cache_strategy_global(self):
        self.registry.register(self.test_class, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        self.assertEqual(self.registry.get_cache_strategy(self.test_class), autoinject.CacheStrategy.GLOBAL_CACHE)

    def test_cache_strategy_context(self):
        self.registry.register(self.test_class, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
        self.assertEqual(self.registry.get_cache_strategy(self.test_class), autoinject.CacheStrategy.CONTEXT_CACHE)

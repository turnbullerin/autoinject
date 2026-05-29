import unittest
import typing as t
import autoinject
import autoinject.reflect as reflect


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
        self.assertRaises(autoinject.ClassNotFoundException, self.registry.get_class_info, self.test_class)
        self.registry.register(self.test_class)
        self.assertTrue(self.registry.is_injectable(self.test_class))
        self.assertIsInstance(self.registry.get_class_info(self.test_class).constructor(), self.test_class)

    def test_bad_fetch(self):
        with self.assertRaises(autoinject.ClassNotFoundException):
            x = self.registry.get_class_info(self.test_class).strategy

    def test_register_class_by_name(self: t.Self):
        fqn: str = reflect.fqn(ForTestByName)
        self.assertFalse(self.registry.is_injectable(fqn))
        self.assertRaises(autoinject.ClassNotFoundException, self.registry.get_class_info, fqn)
        self.registry.register(ForTestByName)
        self.assertTrue(self.registry.is_injectable(fqn))
        self.assertIsInstance(self.registry.get_class_info(fqn).constructor(), ForTestByName)

    def test_register_class_constructor_args(self):
        self.registry.register(self.test_class, 'two', def_arg2='alpha')
        obj = self.registry.get_class_info(self.test_class).constructor()
        self.assertEqual(obj.def_arg, 'two')
        self.assertEqual(obj.def_arg2, 'alpha')

    def test_register_class_custom_constructor(self):
        def build_test():
            return self.test_class('three')
        self.registry.register(self.test_class, constructor=build_test)
        obj = self.registry.get_class_info(self.test_class).constructor()
        self.assertEqual(obj.def_arg, 'three')

    def test_register_class_custom_constructor_args(self):
        def build_test(a, b, *other, z=''):
            return self.test_class("{} {}".format(a, b), z)
        self.registry.register(self.test_class, "four", "five", constructor=build_test, z='beta')
        obj = self.registry.get_class_info(self.test_class).constructor()
        self.assertEqual(obj.def_arg, 'four five')
        self.assertEqual(obj.def_arg2, 'beta')

    def test_cache_strategy_none(self):
        self.registry.register(self.test_class, caching_strategy=autoinject.CacheStrategy.NO_CACHE)
        self.assertEqual(self.registry.get_class_info(self.test_class).strategy, autoinject.CacheStrategy.NO_CACHE)

    def test_cache_strategy_global(self):
        self.registry.register(self.test_class, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        self.assertEqual(self.registry.get_class_info(self.test_class).strategy, autoinject.CacheStrategy.GLOBAL_CACHE)

    def test_cache_strategy_context(self):
        self.registry.register(self.test_class, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
        self.assertEqual(self.registry.get_class_info(self.test_class).strategy, autoinject.CacheStrategy.CONTEXT_CACHE)

    def test_str_is_not_context(self):
        self.assertFalse(self.registry.is_context('foobar'))

    def test_no_constructor(self):
        class ProtocolClass(t.Protocol): ...
        self.registry.register(ProtocolClass)
        with self.assertRaises(TypeError):
            self.registry.get_class_info(ProtocolClass)
        class RealClass: ...
        self.registry.register(ProtocolClass, constructor=RealClass)
        x = self.registry.get_class_info(ProtocolClass)
        self.assertIs(x.constructor.constructor, RealClass)

    def test_cls_to_type(self):
        x = self.registry.cls_to_type(autoinject.reflect.fqn(ForTestByName))
        self.assertIs(x, ForTestByName)

    def test_bad_arg_to_is_injectable(self):
        self.assertFalse(self.registry.is_injectable(self)) # type: ignore # intended failure

    def test_register_constructor_as_str(self):
        fqn = autoinject.reflect.fqn(ForTestByName)
        self.registry.register(fqn)
        self.assertIs(self.registry.object_constructors[fqn].constructors[0].constructor, ForTestByName)

    def test_unregister_by_str(self):
        fqn = autoinject.reflect.fqn(ForTestByName)
        self.registry.register(ForTestByName)
        self.assertIn(fqn, self.registry.object_constructors)
        self.registry.unregister(fqn, fqn)
        self.assertNotIn(fqn, self.registry.object_constructors)

    def test_unregister_bad_str(self):
        fqn = autoinject.reflect.fqn(ForTestByName)
        self.registry.register(ForTestByName)
        self.assertIn(fqn, self.registry.object_constructors)
        self.registry.unregister(fqn, "what")
        self.assertIn(fqn, self.registry.object_constructors)

    def test_unregister_bad_constructor(self):
        fqn = autoinject.reflect.fqn(ForTestByName)
        self.registry.register(ForTestByName)
        self.assertIn(fqn, self.registry.object_constructors)
        self.registry.unregister(fqn, self.__class__)
        self.assertIn(fqn, self.registry.object_constructors)

    def test_unregister_bad_type(self):
        fqn = autoinject.reflect.fqn(ForTestByName)
        self.registry.register(ForTestByName)
        self.assertIn(fqn, self.registry.object_constructors)
        self.registry.unregister("What?", ForTestByName)
        self.assertIn(fqn, self.registry.object_constructors)



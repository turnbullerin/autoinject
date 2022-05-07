import unittest

import autoinject


class TestContextManager(unittest.TestCase):

    def setUp(self):
        self.registry = autoinject.ClassRegistry()
        self.ctx = autoinject.NamedContextManager(self.registry)

    def test_context_switch(self):
        self.assertEqual(self.ctx.current_context, '_default')
        self.ctx.create_context('test_context')
        self.assertEqual(self.ctx.current_context, '_default')
        self.assertIn('test_context', self.ctx.contexts)
        self.ctx.set_context('test_context')
        self.assertEqual(self.ctx.current_context, 'test_context')
        self.ctx.remove_context('test_context')
        self.assertEqual(self.ctx.current_context, '_default')
        self.assertNotIn('test_context', self.ctx.contexts)

    def test_strategy_support(self):
        self.assertTrue(self.ctx._supports_caching_strategy(autoinject.CacheStrategy.NO_CACHE))
        self.assertTrue(self.ctx._supports_caching_strategy(autoinject.CacheStrategy.CONTEXT_CACHE))
        self.assertTrue(self.ctx._supports_caching_strategy(autoinject.CacheStrategy.GLOBAL_CACHE))

    def test_cannot_remove_default(self):
        self.ctx.remove_context('_default')
        self.assertIn('_default', self.ctx.contexts)

    def test_cannot_remove_global(self):
        self.ctx.remove_context('_global')
        self.assertIn('_global', self.ctx.contexts)

    def test_no_context_obj(self):
        class TestClass:
            pass
        self.registry.register_class(TestClass, caching_strategy=autoinject.CacheStrategy.NO_CACHE)
        obj1 = self.ctx.get_object(TestClass)
        obj2 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(obj1) == hash(obj2))

    def test_global_obj(self):
        class TestClass:
            pass
        self.registry.register_class(TestClass, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        obj1 = self.ctx.get_object(TestClass)
        obj2 = self.ctx.get_object(TestClass)
        self.assertTrue(hash(obj1) == hash(obj2))

    def test_context_obj(self):
        class TestClass:
            pass
        self.registry.register_class(TestClass, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
        def_obj1 = self.ctx.get_object(TestClass)
        def_obj2 = self.ctx.get_object(TestClass)
        self.assertTrue(hash(def_obj1) == hash(def_obj2))
        self.ctx.set_context('new_context')
        def_obj3 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(def_obj1) == hash(def_obj3))
        self.ctx.set_context("_default")
        def_obj4 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(def_obj4) == hash(def_obj3))
        self.assertTrue(hash(def_obj4) == hash(def_obj1))
        self.ctx.set_context('new_context2')
        def_obj5 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(def_obj5) == hash(def_obj4))
        self.assertFalse(hash(def_obj5) == hash(def_obj3))
        self.assertFalse(hash(def_obj5) == hash(def_obj2))
        self.ctx.set_context('new_context')
        def_obj6 = self.ctx.get_object(TestClass)
        self.assertTrue(hash(def_obj6) == hash(def_obj3))





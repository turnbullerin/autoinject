import unittest
import autoinject


class ForNameTest:
    pass


class TestContextManager(unittest.TestCase):

    def setUp(self):
        self.registry = autoinject.ClassRegistry()
        self.ctx = autoinject.ContextManager(self.registry)

    def test_context_switch(self):
        pass

    def test_no_context_obj(self):
        class TestClass:
            pass
        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.NO_CACHE)
        obj1 = self.ctx.get_object(TestClass)
        obj2 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(obj1) == hash(obj2))

    def test_teardown_call(self):
        class TestClass:

            def __init__(self):
                self.closed = False

            def __cleanup__(self):
                self.closed = True
        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        # Ensure we can still get an object
        obj1 = self.ctx.get_object(TestClass)
        self.assertFalse(obj1.closed)
        # Trigger teardown and ensure our __cleanup__ handler got called.
        self.ctx.teardown()
        self.assertTrue(obj1.closed)
        # New objects should be different
        obj2 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(obj1) == hash(obj2))

    def test_teardown_context(self):
        class TestClass:

            def __init__(self):
                self.closed = False

            def __cleanup__(self):
                self.closed = True
        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
        nci = autoinject.NamedContextInformant()
        self.ctx.register_informant(nci)
        nci.switch_context("alpha")
        alpha_obj = self.ctx.get_object(TestClass)
        self.assertFalse(alpha_obj.closed)
        nci.switch_context("beta")
        beta_obj = self.ctx.get_object(TestClass)
        self.assertFalse(beta_obj.closed)
        nci.destroy("alpha")
        self.assertTrue(alpha_obj.closed)
        self.assertFalse(beta_obj.closed)
        beta_obj2 = self.ctx.get_object(TestClass)
        self.assertTrue(hash(beta_obj) == hash(beta_obj2))
        nci.switch_context("alpha")
        alpha_obj2 = self.ctx.get_object(TestClass)
        alpha_obj3 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(alpha_obj2) == hash(alpha_obj))
        self.assertFalse(hash(alpha_obj2) == hash(beta_obj))
        self.assertTrue(hash(alpha_obj2) == hash(alpha_obj3))

    def test_global_obj(self):
        class TestClass:
            pass
        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        obj1 = self.ctx.get_object(TestClass)
        obj2 = self.ctx.get_object(TestClass)
        self.assertTrue(hash(obj1) == hash(obj2))

    def test_context_obj(self):
        class TestClass:
            pass
        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
        nci = autoinject.NamedContextInformant()
        self.ctx.register_informant(nci)
        nci.switch_context("alpha")
        def_obj1 = self.ctx.get_object(TestClass)
        def_obj2 = self.ctx.get_object(TestClass)
        self.assertTrue(hash(def_obj1) == hash(def_obj2))
        nci.switch_context("beta")
        def_obj3 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(def_obj1) == hash(def_obj3))
        nci.switch_context("alpha")
        def_obj4 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(def_obj4) == hash(def_obj3))
        self.assertTrue(hash(def_obj4) == hash(def_obj1))
        nci.switch_context("gamma")
        def_obj5 = self.ctx.get_object(TestClass)
        self.assertFalse(hash(def_obj5) == hash(def_obj4))
        self.assertFalse(hash(def_obj5) == hash(def_obj3))
        self.assertFalse(hash(def_obj5) == hash(def_obj2))
        nci.switch_context("beta")
        def_obj6 = self.ctx.get_object(TestClass)
        self.assertTrue(hash(def_obj6) == hash(def_obj3))

    def test_context_obj_by_str(self):
        self.registry.register(ForNameTest, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
        nci = autoinject.NamedContextInformant()
        self.ctx.register_informant(nci)
        nci.switch_context("alpha")
        def_obj1 = self.ctx.get_object("tests.test_context_manager.ForNameTest")
        self.assertIsInstance(def_obj1, ForNameTest)
        def_obj2 = self.ctx.get_object(ForNameTest)
        self.assertIsInstance(def_obj2, ForNameTest)
        self.assertEqual(hash(def_obj1), hash(def_obj2))






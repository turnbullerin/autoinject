import contextvars
import unittest
import autoinject


class ForNameTest:
    pass


test_var = contextvars.ContextVar("_test_world", default=None)


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

    def test_contextvar_context_manager(self):
        class TestClass:
            pass

        def get_obj():
            return self.ctx.get_object(TestClass)

        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)

        def from_context():
            obj1 = get_obj()
            self.assertTrue(len(self.ctx._context_cache) == 1)
            self.assertIsNone(test_var.get())
            test_var.set("foo2")
            with autoinject.informants.ContextVarManager(self.ctx.contextvar_info, "copy") as ctx:
                self.assertEqual(ctx.run(test_var.get), "foo2")
                obj2 = ctx.run(get_obj)
                obj5 = get_obj()
                self.assertEqual(hash(obj5), hash(obj1))
                self.assertNotEqual(hash(obj2), hash(obj1))
                # This only sets the LOCAL variable, not the one in ctx because we made a copy
                test_var.set("bar2")
                self.assertEqual(test_var.get(), "bar2")
                self.assertEqual(ctx.run(test_var.get), "foo2")
                # This sets the var in ctx but does not affect the local one
                ctx.run(test_var.set, "bar")
                self.assertEqual(test_var.get(), "bar2")
                self.assertEqual(ctx.run(test_var.get), "bar")
                obj3 = ctx.run(get_obj)
                self.assertEqual(hash(obj2), hash(obj3))
                self.assertEqual(len(self.ctx._context_cache), 2)
            self.assertEqual(test_var.get(), "bar2")
            self.assertEqual(len(self.ctx._context_cache), 1)
            obj4 = get_obj()
            self.assertEqual(hash(obj1), hash(obj4))
            test_var.set("roo")
        context = contextvars.Context()
        test_var.set("foo")
        context.run(from_context)
        self.assertTrue(test_var.get() == "foo")

    def test_contextvar_context_manager_same(self):
        class TestClass:
            pass

        def get_obj():
            return self.ctx.get_object(TestClass)

        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)

        def from_context():
            obj1 = get_obj()
            self.assertTrue(len(self.ctx._context_cache) == 1)
            self.assertIsNone(test_var.get())
            test_var.set("foo2")
            with autoinject.informants.ContextVarManager(self.ctx.contextvar_info, "same") as ctx:
                self.assertEqual(ctx.run(test_var.get), "foo2")
                obj2 = ctx.run(get_obj)
                obj5 = get_obj()
                self.assertNotEqual(hash(obj5), hash(obj1))
                self.assertNotEqual(hash(obj2), hash(obj1))
                self.assertEqual(hash(obj5), hash(obj2))
                # Note that, since we use the "same" context, calls to ctx.run() and direct calls are the same
                test_var.set("bar")
                self.assertEqual(test_var.get(), "bar")
                self.assertEqual(ctx.run(test_var.get), "bar")
                ctx.run(test_var.set, "bar2")
                self.assertEqual(test_var.get(), "bar2")
                self.assertEqual(ctx.run(test_var.get), "bar2")
                obj3 = ctx.run(get_obj)
                self.assertEqual(hash(obj2), hash(obj3))
                self.assertEqual(len(self.ctx._context_cache), 2)
            self.assertEqual(test_var.get(), "bar2")
            self.assertEqual(len(self.ctx._context_cache), 1)
            obj4 = get_obj()
            self.assertEqual(hash(obj1), hash(obj4))
            test_var.set("roo")
        context = contextvars.Context()
        test_var.set("foo")
        context.run(from_context)
        self.assertTrue(test_var.get() == "foo")

    def test_contextvar_context_manager_map(self):
        with autoinject.informants.ContextVarManager(self.ctx.contextvar_info, "empty") as ctx:
            self.assertFalse(test_var in ctx)
            test_var.set("bar")
            self.assertFalse(test_var in ctx)
            self.assertIsNone(ctx.get(test_var))
            self.assertEqual(ctx.get(test_var, "foo"), "foo")
            ctx.run(test_var.set, "bar")
            self.assertTrue(test_var in ctx)
            self.assertEqual(ctx.get(test_var, "foo"), "bar")
            self.assertEqual(ctx[test_var], "bar")
            x = 0
            key_list = list()
            for key in ctx:
                self.assertIsInstance(key, contextvars.ContextVar)
                key_list.append(key)
                x += 1
            self.assertEqual(len(ctx), x)
            value_list = list()
            for key in ctx.keys():
                self.assertIsInstance(key, contextvars.ContextVar)
                self.assertIn(key, key_list)
                value_list.append(ctx[key])
            for value in ctx.values():
                self.assertIn(value, value_list)
            for key, value in ctx.items():
                self.assertIn(key, key_list)
                self.assertIn(value, value_list)
                self.assertEqual(ctx[key], value)

    def test_contextvar_context_manager_empty(self):
        class TestClass:
            pass

        def get_obj():
            return self.ctx.get_object(TestClass)

        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)

        def from_context():
            obj1 = get_obj()
            self.assertTrue(len(self.ctx._context_cache) == 1)
            self.assertIsNone(test_var.get())
            test_var.set("foo2")
            with autoinject.informants.ContextVarManager(self.ctx.contextvar_info, "empty") as ctx:
                # Empty context resets the variables
                self.assertIsNone(ctx.run(test_var.get))
                self.assertEqual(test_var.get(), "foo2")
                obj2 = ctx.run(get_obj)
                obj5 = get_obj()  # should use outside context still
                self.assertNotEqual(hash(obj2), hash(obj1))
                self.assertEqual(hash(obj5), hash(obj1))
                # This only sets the LOCAL variable, not the one in ctx because we made a copy
                test_var.set("bar2")
                self.assertEqual(test_var.get(), "bar2")
                self.assertIsNone(ctx.run(test_var.get))
                # This sets the var in ctx but does not affect the local one
                ctx.run(test_var.set, "bar")
                self.assertEqual(test_var.get(), "bar2")
                self.assertEqual(ctx.run(test_var.get), "bar")
                obj3 = ctx.run(get_obj)
                self.assertEqual(hash(obj2), hash(obj3))
                self.assertEqual(len(self.ctx._context_cache), 2)
            self.assertEqual(test_var.get(), "bar2")
            self.assertEqual(len(self.ctx._context_cache), 1)
            obj4 = get_obj()
            self.assertEqual(hash(obj1), hash(obj4))
            test_var.set("roo")
        context = contextvars.Context()
        test_var.set("foo")
        context.run(from_context)
        self.assertTrue(test_var.get() == "foo")

    def test_contextvar(self):
        class TestClass:
            pass
        self.registry.register(TestClass, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)

        def get_obj():
            return self.ctx.get_object(TestClass)

        # Same context, same objects
        context = contextvars.Context()
        obj1 = context.run(get_obj)
        obj2 = context.run(get_obj)
        self.assertTrue(hash(obj1) == hash(obj2))

        # Copy context, by default, means the same value
        context2 = context.copy()
        obj3 = context.run(get_obj)
        obj4 = context2.run(get_obj)
        self.assertTrue(hash(obj3) == hash(obj4))
        self.assertTrue(hash(obj3) == hash(obj2))

        # Fresh context, new object
        context3 = contextvars.Context()
        obj5 = context3.run(get_obj)
        self.assertFalse(hash(obj5) == hash(obj1))

        # Copy of new fresh context, same but different
        context4 = context3.copy()
        obj6 = context4.run(get_obj)
        self.assertTrue(hash(obj5) == hash(obj6))

        # Copying the context before the call means we don't get the original value
        context5 = contextvars.Context()
        context6 = context5.copy()
        obj7 = context5.run(get_obj)
        obj8 = context6.run(get_obj)
        self.assertFalse(hash(obj7) == hash(obj8))

        # Test using fresh_context to ensure consistent behaviour when copying context
        context7 = contextvars.Context()
        obj9 = context7.run(get_obj)
        context8 = context7.copy()
        # This makes the contexts independent in terms of autoinjection variables
        autoinject.informants.ContextVarManager.freshen_context(context8)
        obj10 = context8.run(get_obj)
        self.assertFalse(hash(obj9) == hash(obj10))
        obj11 = context7.run(get_obj)
        obj12 = context8.run(get_obj)
        self.assertFalse(hash(obj11) == hash(obj12))
        self.assertTrue(hash(obj11) == hash(obj9))
        self.assertTrue(hash(obj12) == hash(obj10))

        # test destroy
        context9 = contextvars.Context()
        obj13 = context9.run(get_obj)
        self.ctx.contextvar_info.destroy_self(context9)
        obj14 = context9.run(get_obj)
        self.assertFalse(hash(obj13) == hash(obj14))

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






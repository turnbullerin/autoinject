import unittest
import autoinject


class TestNonStandardMethods(unittest.TestCase):

    def test_arbitrary_string(self):
        injector = autoinject.InjectionManager(False)

        class TestClass:
            pass

        injector.register_constructor("foo", TestClass)
        self.assertIsInstance(injector.get("foo"), TestClass)

    def test_function_injection(self):
        injector = autoinject.InjectionManager(False)

        @injector.register("foo")
        def _create_function():
            def foo_function(bar):
                return "!{}!".format(bar)
            return foo_function

        f = injector.get("foo")
        self.assertTrue(callable(f))
        self.assertEqual(f("bar"), "!bar!")

    def test_function_override_injection(self):
        injector = autoinject.InjectionManager(False)

        @injector.register("foo")
        def _create_function():
            def foo_function(bar):
                return "!{}!".format(bar)
            return foo_function

        @injector.register("foo")
        def _create_function():
            def foo_function(bar):
                return bar.upper()
            return foo_function

        f = injector.get("foo")
        self.assertTrue(callable(f))
        self.assertNotEqual(f("bar"), "!bar!")
        self.assertEqual(f("bar"), "BAR")

    def test_function_override_injection_clears_cache(self):
        injector = autoinject.InjectionManager(False)

        @injector.register("foo")
        def _create_function():
            def foo_function(bar):
                return "!{}!".format(bar)
            return foo_function

        g = injector.get("foo")

        @injector.register("foo")
        def _create_function():
            def foo_function(bar):
                return bar.upper()
            return foo_function

        f = injector.get("foo")
        self.assertTrue(callable(f))
        self.assertNotEqual(f("bar"), "!bar!")
        self.assertEqual(f("bar"), "BAR")

    def test_function_override_with_weight_injection(self):
        injector = autoinject.InjectionManager(False)

        @injector.register("foo", weight=5)
        def _create_function():
            def foo_function(bar):
                return "!{}!".format(bar)
            return foo_function

        @injector.register("foo")
        def _create_function():
            def foo_function(bar):
                return bar.upper()
            return foo_function

        f = injector.get("foo")
        self.assertTrue(callable(f))
        self.assertNotEqual(f("bar"), "BAR")
        self.assertEqual(f("bar"), "!bar!")

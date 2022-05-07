import unittest

import autoinject


class TestInjection(unittest.TestCase):

    def test_injectable(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

    def test_injection(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        class TestInjectClass:
            @injector.inject
            def __init__(self, x: TestClass):
                self.x = x

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, TestClass)

    def test_positional_before(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        class TestInjectClass:
            @injector.inject
            def __init__(self, arg_one, x: TestClass):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass("foo")
        self.assertIsInstance(obj.x, TestClass)
        self.assertEqual(obj.arg_one, "foo")

    def test_positional_after(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        class TestInjectClass:
            @injector.inject
            def __init__(self, x: TestClass, arg_one):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass("foo")
        self.assertIsInstance(obj.x, TestClass)
        self.assertEqual(obj.arg_one, "foo")

    def test_keyword_arg(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        class TestInjectClass:
            @injector.inject
            def __init__(self, /, x: TestClass, arg_one):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass(arg_one="foo")
        self.assertIsInstance(obj.x, TestClass)
        self.assertEqual(obj.arg_one, "foo")

    def test_missing_keyword_arg(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        class TestInjectClass:
            @injector.inject
            def __init__(self, x: TestClass, *extra_args, arg_one):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(autoinject.MissingArgumentError, lambda: TestInjectClass("foo"))

    def test_missing_pos_arg(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        class TestInjectClass:
            @injector.inject
            def __init__(self, arg_one, x: TestClass, /):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(autoinject.MissingArgumentError, lambda: TestInjectClass(arg_one="foo"))

    def test_extra_pos_arg(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        class TestInjectClass:
            @injector.inject
            def __init__(self, arg_one, x: TestClass, /):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(autoinject.ExtraPositionalArgumentsError, lambda: TestInjectClass("foo", "bar"))

    def test_extra_kwarg_arg(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        class TestInjectClass:
            @injector.inject
            def __init__(self, arg_one, x: TestClass):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(autoinject.ExtraKeywordArgumentsError, lambda: TestInjectClass(arg_one="foo", arg_two="bar"))

    def test_double_inject(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        @injector.injectable
        class TestClass2:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass2))

        class TestInjectClass:
            @injector.inject
            def __init__(self, x: TestClass, y: TestClass2):
                self.x = x
                self.y = y

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, TestClass)
        self.assertIsInstance(obj.y, TestClass2)

    def test_complex_arguments(self):
        injector = autoinject.InjectionManager()

        @injector.injectable
        class TestClass:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

        @injector.injectable
        class TestClass2:
            pass

        self.assertTrue(injector.cls_registry.is_injectable(TestClass2))

        class TestInjectClass:
            @injector.inject
            def __init__(self, pos_one, x: TestClass, pos_two, /, y: TestClass2, *args, kw_one, kw_def='test', **kwargs):
                self.pos_one = pos_one
                self.pos_two = pos_two
                self.x = x
                self.y = y
                self.args = args
                self.kw_one = kw_one
                self.kw_def = kw_def
                self.kwargs = kwargs

        obj = TestInjectClass(5, "hello world", "one", "two", "three", kw_one="foo", kw_three="test", kw_four="bar")
        self.assertEqual(obj.pos_one, 5)
        self.assertEqual(obj.pos_two, "hello world")
        self.assertEqual(obj.kw_one, "foo")
        self.assertIsInstance(obj.x, TestClass)
        self.assertIsInstance(obj.y, TestClass2)
        self.assertTupleEqual(obj.args, ("one", "two", "three"))
        self.assertDictEqual(obj.kwargs, {"kw_three": "test", "kw_four": "bar"})

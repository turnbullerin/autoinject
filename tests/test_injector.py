import unittest

import autoinject


class TestInjection(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.injector = autoinject.InjectionManager()

        @self.injector.injectable
        class TestClass:
            pass

        self.test_class = TestClass

        @self.injector.injectable
        class TestClass2:
            pass

        self.test_class2 = TestClass2

    def test_same_context(self):
        cls = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: cls):
                self.x = x

        obj = TestInjectClass()
        obj2 = TestInjectClass()
        self.assertIsInstance(obj.x, self.test_class)
        self.assertIsInstance(obj2.x, self.test_class)
        self.assertNotEqual(hash(obj), hash(obj2))
        self.assertEqual(hash(obj.x), hash(obj2.x))

    def test_injectable(self):
        self.assertTrue(self.injector.cls_registry.is_injectable(self.test_class))

    def test_injection(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: tc):
                self.x = x

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, self.test_class)

    def test_positional_before(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, arg_one, x: tc):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass("foo")
        self.assertIsInstance(obj.x, self.test_class)
        self.assertEqual(obj.arg_one, "foo")

    def test_positional_after(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: tc, arg_one):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass("foo")
        self.assertIsInstance(obj.x, self.test_class)
        self.assertEqual(obj.arg_one, "foo")

    def test_default_values(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: tc, y="one", z=2):
                self.x = x
                self.y = y
                self.z = z

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, self.test_class)
        self.assertEqual(obj.y, "one")
        self.assertEqual(obj.z, 2)

    def test_keyword_arg(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, /, x: tc, arg_one):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass(arg_one="foo")
        self.assertIsInstance(obj.x, self.test_class)
        self.assertEqual(obj.arg_one, "foo")

    def test_missing_keyword_arg(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: tc, *extra_args, arg_one):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(autoinject.MissingArgumentError, lambda: TestInjectClass("foo"))

    def test_missing_pos_arg(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, arg_one, x: tc, /):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(autoinject.MissingArgumentError, lambda: TestInjectClass(arg_one="foo"))

    def test_extra_pos_arg(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, arg_one, x: tc, /):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(autoinject.ExtraPositionalArgumentsError, lambda: TestInjectClass("foo", "bar"))

    def test_extra_kwarg_arg(self):
        tc = self.test_class
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, arg_one, x: tc):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(autoinject.ExtraKeywordArgumentsError, lambda: TestInjectClass(arg_one="foo", arg_two="bar"))

    def test_double_inject(self):
        tc = self.test_class
        tc2 = self.test_class2
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: tc, y: tc2):
                self.x = x
                self.y = y

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, self.test_class)
        self.assertIsInstance(obj.y, self.test_class2)

    def test_complex_arguments(self):
        tc = self.test_class
        tc2 = self.test_class2
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, pos_one, x: tc, pos_two, /, y: tc2, *args, kw_one, kw_def='test', **kwargs):
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
        self.assertIsInstance(obj.x, self.test_class)
        self.assertIsInstance(obj.y, self.test_class2)
        self.assertTupleEqual(obj.args, ("one", "two", "three"))
        self.assertDictEqual(obj.kwargs, {"kw_three": "test", "kw_four": "bar"})

    def test_construct(self):
        cls = self.test_class
        class TestInjectClass:

            tc: cls = None

            @self.injector.construct
            def __init__(self):
                pass

        tic = TestInjectClass()
        self.assertTrue(hasattr(tic, 'tc'))
        self.assertIsInstance(tic.tc, self.test_class)

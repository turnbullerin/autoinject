import unittest
import inspect
import contextvars
import autoinject


cv: contextvars.ContextVar[str] = contextvars.ContextVar[str]("_test_hello", default=None)
cv2 = contextvars.ContextVar[str]("_test2", default=None)


class NonLocalInjectionOne:
    pass


class TestInjection(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.injector = autoinject.InjectionManager(False)

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

    def test_register_class(self):
        class TestClassFoo:

            def __init__(self, arg=1):
                self.arg = arg

        self.injector.register_constructor(TestClassFoo, TestClassFoo)
        obj = self.injector.get(TestClassFoo)
        self.assertIsInstance(obj, TestClassFoo)
        self.assertEqual(obj.arg, 1)

    def test_value_exception_in_block(self):

        @self.injector.with_contextvars
        def make_error():
            def do_error():
                raise ValueError("foobar")

            try:
                contextvars.copy_context().run(do_error)
            except Exception as ex:
                raise ValueError("inner")
                print(ex)
        self.assertRaises(ValueError, make_error)

    def test_exception_in_block(self):

        class CustomException(Exception):
            pass

        @self.injector.with_contextvars
        def make_error():
            def do_error():
                raise CustomException()

            do_error()
        self.assertRaises(CustomException, make_error)

    def test_inherited_injection(self):

        @self.injector.injectable
        class InjectableOne:
            pass

        class ParentInjectable:

            one: InjectableOne = None

            @self.injector.construct
            def __init__(self):
                pass

        class SubInjectable(ParentInjectable):

            two: InjectableOne = None

            @self.injector.construct
            def __init__(self):
                super().__init__()

        t = SubInjectable()
        self.assertIsInstance(t.two, InjectableOne)
        self.assertIsInstance(t.one, InjectableOne)

    def test_contextvar_param(self):
        @self.injector.with_contextvars
        def test_method(set_to: str, ctx: contextvars.Context = None):
            self.assertIsNotNone(ctx)
            original = cv.get()
            self.assertEqual(ctx.get(cv), cv.get())
            token = cv.set(set_to)
            self.assertEqual(ctx.get(cv), cv.get())
            self.assertEqual(cv.get(), set_to)
            ctx.reset(cv, token)
            self.assertEqual(ctx.get(cv), cv.get())
            self.assertEqual(cv.get(), original)
            token = ctx.set(cv, set_to)
            self.assertEqual(ctx.get(cv), cv.get())
            self.assertEqual(cv.get(), set_to)
            cv.reset(token)
            self.assertEqual(ctx.get(cv), cv.get())
            self.assertEqual(cv.get(), original)
            cv.set(set_to)
            return ctx.get(cv)
        self.assertIsNone(cv.get())
        cv.set("first")
        self.assertEqual(cv.get(), "first")
        c = contextvars.Context()
        result = test_method("second")
        self.assertEqual(result, "second")
        self.assertEqual(cv.get(), "first")

    def test_test_case_wrapper_local(self):

        class TestClassFoo:

            def __init__(self, arg=1):
                self.arg = arg

        self.injector.injectable(TestClassFoo)
        obj = self.injector.get(TestClassFoo)
        self.assertIsInstance(obj, TestClassFoo)
        self.assertEqual(obj.arg, 1)

        @self.injector.test_case
        def example_test_case():
            obj2 = self.injector.get(TestClassFoo)
            self.assertIsInstance(obj2, TestClassFoo)
            self.assertNotEqual(hash(obj), hash(obj2))

        example_test_case()

        obj3 = self.injector.get(TestClassFoo)
        self.assertEqual(hash(obj), hash(obj3))

    def test_test_case_wrapper_obj(self):

        class TestClassFoo:

            def __init__(self, arg=1):
                self.arg = arg

        self.injector.injectable(TestClassFoo)
        obj = self.injector.get(TestClassFoo)
        self.assertIsInstance(obj, TestClassFoo)
        self.assertEqual(obj.arg, 1)

        @self.injector.test_case({TestClassFoo: TestClassFoo(5)})
        def example_test_case():
            obj2 = self.injector.get(TestClassFoo)
            self.assertIsInstance(obj2, TestClassFoo)
            self.assertEqual(obj2.arg, 5)
            self.assertNotEqual(hash(obj), hash(obj2))

        example_test_case()

        obj3 = self.injector.get(TestClassFoo)
        self.assertEqual(hash(obj), hash(obj3))

    def test_test_case_wrapper_global(self):

        class TestClassFoo:

            def __init__(self, arg=1):
                self.arg = arg

        self.injector.injectable_global(TestClassFoo)
        obj = self.injector.get(TestClassFoo)
        self.assertIsInstance(obj, TestClassFoo)
        self.assertEqual(obj.arg, 1)

        @self.injector.test_case
        def example_test_case():
            obj2 = self.injector.get(TestClassFoo)
            self.assertIsInstance(obj2, TestClassFoo)
            self.assertNotEqual(hash(obj), hash(obj2))

        example_test_case()

        obj3 = self.injector.get(TestClassFoo)
        self.assertEqual(hash(obj), hash(obj3))

    def test_test_case_wrapper_fixture_type(self):

        class TestClassFoo:

            def __init__(self, arg=1):
                self.arg = arg

        class TestClassBar:

            def __init__(self):
                self.arg = 3

        self.injector.injectable_global(TestClassFoo)
        obj = self.injector.get(TestClassFoo)
        self.assertIsInstance(obj, TestClassFoo)
        self.assertEqual(obj.arg, 1)

        @self.injector.test_case({TestClassFoo: TestClassBar})
        def example_test_case():
            obj2 = self.injector.get(TestClassFoo)
            self.assertIsInstance(obj2, TestClassBar)
            self.assertNotEqual(hash(obj), hash(obj2))
            self.assertEqual(obj2.arg, 3)

        example_test_case()

        obj3 = self.injector.get(TestClassFoo)
        self.assertEqual(hash(obj3), hash(obj))
        self.assertEqual(obj3.arg, 1)

    def test_register_class_with_args(self):
        class TestClassFoo:

            def __init__(self, arg=1, kwarg=1):
                self.arg = arg
                self.kwarg = kwarg

        self.injector.register_constructor(TestClassFoo, TestClassFoo, 2, kwarg=3)
        obj = self.injector.get(TestClassFoo)
        self.assertIsInstance(obj, TestClassFoo)
        self.assertEqual(obj.arg, 2)
        self.assertEqual(obj.kwarg, 3)

    def test_injectable(self):
        self.assertTrue(self.injector.cls_registry.is_injectable(self.test_class))
        self.assertEqual(self.injector.cls_registry.get_cache_strategy(self.test_class), autoinject.CacheStrategy.CONTEXT_CACHE)

    def test_injectable_global(self):

        @self.injector.injectable_global
        class TestClassBar:
            pass

        self.assertTrue(self.injector.cls_registry.is_injectable(TestClassBar))
        self.assertEqual(self.injector.cls_registry.get_cache_strategy(TestClassBar), autoinject.CacheStrategy.GLOBAL_CACHE)

    def test_injectable_nocache(self):

        @self.injector.injectable_nocache
        class TestClassBar:
            pass

        self.assertTrue(self.injector.cls_registry.is_injectable(TestClassBar))
        self.assertEqual(self.injector.cls_registry.get_cache_strategy(TestClassBar), autoinject.CacheStrategy.NO_CACHE)

    def test_override(self):

        class TestClassOverride:
            pass

        self.injector.override(self.test_class, TestClassOverride)
        self.assertIsInstance(self.injector.get(self.test_class), TestClassOverride)

    def test_override_by_name(self):

        class TestClassOverride:
            pass

        qn = "tests.test_injector.TestInjection.setUp.<locals>.TestClass"
        self.assertIsInstance(self.injector.get(qn), self.test_class)
        self.injector.override(qn, TestClassOverride)
        self.assertIsInstance(self.injector.get(qn), TestClassOverride)
        self.assertIsInstance(self.injector.get(self.test_class), TestClassOverride)

    def test_named_constructor(self):
        qn = "tests.test_injector.NonLocalInjectionOne"
        self.injector.register_constructor(qn, qn)
        self.assertIsInstance(self.injector.get(qn), NonLocalInjectionOne)
        self.assertIsInstance(self.injector.get(NonLocalInjectionOne), NonLocalInjectionOne)

    def test_override_preserves_scope(self):

        @self.injector.injectable_global
        class BaseTestClass:
            pass

        class TestClassOverride:
            pass

        self.injector.override(BaseTestClass, TestClassOverride)
        self.assertEqual(self.injector.cls_registry.get_cache_strategy(BaseTestClass), autoinject.CacheStrategy.GLOBAL_CACHE)
        self.assertIsInstance(self.injector.get(BaseTestClass), TestClassOverride)

    def test_get_object(self):
        self.assertIsInstance(self.injector.get(self.test_class), self.test_class)

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

    def test_blank_default_value(self):
        tc = self.test_class

        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: tc, y=None, z="", a=0):
                self.x = x
                self.y = y
                self.z = z
                self.a = a

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, self.test_class)
        self.assertIsNone(obj.y)
        self.assertEqual(obj.z, "")
        self.assertEqual(obj.a, 0)

    def test_keyword_arg(self):
        tc = self.test_class

        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: tc, arg_one):
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

    def test_extra_pos_arg(self):
        tc = self.test_class

        class TestInjectClass:
            @self.injector.inject
            def __init__(self, arg_one, x: tc):
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
            def __init__(self, pos_one, x: tc, pos_two, y: tc2, *args, kw_one, kw_def='test', **kwargs):
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

    def test_method_signature(self):
        tc = self.test_class

        @self.injector.inject
        def test_method(param1: tc, param2: int, param3: str):
            pass
        sig = inspect.signature(test_method)
        self.assertEqual(len(sig.parameters), 3)
        parameter_names = [param for param in sig.parameters]
        self.assertIn("param1", parameter_names)
        self.assertIn("param2", parameter_names)
        self.assertIn("param3", parameter_names)

    def test_function_injection(self):
        tc = self.test_class

        @self.injector.inject
        def test_method(param1: tc=None, param2='one'):
            return param1, param2

        a, b = test_method('two')
        self.assertIsInstance(a, self.test_class)
        self.assertEqual(b, 'two')



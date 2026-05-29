import typing
import unittest
import inspect
import contextvars
import autoinject
import typing as t
from autoinject import reflect, CacheStrategy, InjectionManager
from autoinject.injection import _InjectWrapper

cv: contextvars.ContextVar[t.Optional[str]] = contextvars.ContextVar[t.Optional[str]]("_test_hello", default=None)
cv2 = contextvars.ContextVar[t.Optional[str]]("_test2", default=None)


class NonLocalInjectionOne:
    pass


class TestClass:
    pass


class TestClass2:
    pass


class TestInjection(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.injector = autoinject.InjectionManager(False)
        self.injector.injectable(TestClass)
        self.injector.injectable(TestClass2)

    def test_same_context(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: TestClass):
                self.x = x
        obj = TestInjectClass()
        obj2 = TestInjectClass()
        self.assertIsInstance(obj.x, TestClass)
        self.assertIsInstance(obj2.x, TestClass)
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

            one: typing.Optional[InjectableOne] = None

            @self.injector.construct
            def __init__(self):
                pass

        class SubInjectable(ParentInjectable):

            two: typing.Optional[InjectableOne] = None

            @self.injector.construct
            def __init__(self):
                super().__init__()

        t2 = SubInjectable()
        self.assertIsInstance(t2.two, InjectableOne)
        self.assertIsInstance(t2.one, InjectableOne)

    def test_contextvar_param(self):
        @self.injector.with_contextvars
        def test_method(set_to: str, ctx: t.Optional[contextvars.Context] = None):
            self.assertIsNotNone(ctx)
            ctx = t.cast(contextvars.Context, ctx)
            original = cv.get()
            self.assertEqual(ctx.get(cv), cv.get())
            token = cv.set(set_to)
            self.assertEqual(ctx.get(cv), cv.get())
            self.assertEqual(cv.get(), set_to)
            cv.reset(token)
            self.assertEqual(ctx.get(cv), cv.get())
            self.assertEqual(cv.get(), original)
            token = cv.set(set_to)
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
            return self.injector.get(TestClassFoo)

        obj2 = example_test_case()
        self.assertIsInstance(obj2, TestClassFoo)
        self.assertNotEqual(hash(obj), hash(obj2))

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

        @self.injector.test_case({TestClassFoo: lambda: TestClassFoo(5)})
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
            return obj2

        obj2 = example_test_case()

        obj3 = self.injector.get(TestClassFoo)
        self.assertEqual(hash(obj3), hash(obj))
        self.assertEqual(obj3.arg, 1)

    def test_test_case_wrapper_fixture_separate_decorator(self):
        class TestClassFoo:

            def __init__(self, arg=1):
                self.arg = arg

        self.injector.injectable_global(TestClassFoo)
        obj = self.injector.get(TestClassFoo)
        self.assertIsInstance(obj, TestClassFoo)
        self.assertEqual(obj.arg, 1)

        @self.injector.test_case()
        @self.injector.with_fixture(TestClassFoo, TestClassFoo(5))
        def example_test_case():
            obj2 = self.injector.get(TestClassFoo)
            self.assertIsInstance(obj2, TestClassFoo)
            self.assertNotEqual(hash(obj), hash(obj2))
            self.assertEqual(obj2.arg, 5)

        example_test_case()

        obj3 = self.injector.get(TestClassFoo)
        self.assertEqual(hash(obj3), hash(obj))
        self.assertEqual(obj3.arg, 1)

    def test_test_case_wrapper_fixture_separate_decorator_cb(self):
        class TestClassFoo:

            def __init__(self, arg=1):
                self.arg = arg

        self.injector.injectable_global(TestClassFoo)
        obj = self.injector.get(TestClassFoo)
        self.assertIsInstance(obj, TestClassFoo)
        self.assertEqual(obj.arg, 1)

        @self.injector.test_case()
        @self.injector.with_fixture(TestClassFoo, lambda: TestClassFoo(6))
        def example_test_case():
            obj2 = self.injector.get(TestClassFoo)
            self.assertIsInstance(obj2, TestClassFoo)
            self.assertNotEqual(hash(obj), hash(obj2))
            self.assertEqual(obj2.arg, 6)

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
        self.assertTrue(self.injector.cls_registry.is_injectable(TestClass))
        self.assertEqual(self.injector.cls_registry.get_class_info(TestClass).strategy, autoinject.CacheStrategy.CONTEXT_CACHE)

    def test_injectable_global(self):

        @self.injector.injectable_global
        class TestClassBar:
            pass

        self.assertTrue(self.injector.cls_registry.is_injectable(TestClassBar))
        self.assertEqual(self.injector.cls_registry.get_class_info(TestClassBar).strategy, autoinject.CacheStrategy.GLOBAL_CACHE)

    def test_injectable_nocache(self):

        @self.injector.injectable_nocache
        class TestClassBar:
            pass

        self.assertTrue(self.injector.cls_registry.is_injectable(TestClassBar))
        self.assertEqual(self.injector.cls_registry.get_class_info(TestClassBar).strategy, autoinject.CacheStrategy.NO_CACHE)

    def test_override(self):

        class TestClassOverride:
            pass

        self.injector.override(TestClass, TestClassOverride)
        self.assertIsInstance(self.injector.get(TestClass), TestClassOverride)

    def test_override_by_name(self):

        class TestClassOverride:
            pass

        qn = reflect.fqn(TestClass)
        self.assertIsInstance(self.injector.get(qn), TestClass)
        self.injector.override(qn, TestClassOverride)
        self.assertIsInstance(self.injector.get(qn), TestClassOverride)
        self.assertIsInstance(self.injector.get(TestClass), TestClassOverride)

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

        self.injector.override(BaseTestClass, TestClassOverride, caching_strategy=CacheStrategy.GLOBAL_CACHE)
        self.assertEqual(
            self.injector.cls_registry.get_class_info(BaseTestClass).strategy,
            autoinject.CacheStrategy.GLOBAL_CACHE
        )
        self.assertIsInstance(self.injector.get(BaseTestClass), TestClassOverride)

    def test_get_object(self):
        self.assertIsInstance(self.injector.get(TestClass), TestClass)

    def test_injection(self):

        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: TestClass):
                self.x = x

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, TestClass)

    def test_positional_before(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, arg_one, x: TestClass):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass("foo")
        self.assertIsInstance(obj.x, TestClass)
        self.assertEqual(obj.arg_one, "foo")

    def test_positional_after(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: TestClass, arg_one):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass(..., "foo")
        self.assertIsInstance(obj.x, TestClass)
        self.assertEqual(obj.arg_one, "foo")

    def test_default_values(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: TestClass, y="one", z=2):
                self.x = x
                self.y = y
                self.z = z

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, TestClass)
        self.assertEqual(obj.y, "one")
        self.assertEqual(obj.z, 2)

    def test_blank_default_value(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: TestClass, y=None, z="", a=0):
                self.x = x
                self.y = y
                self.z = z
                self.a = a

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, TestClass)
        self.assertIsNone(obj.y)
        self.assertEqual(obj.z, "")
        self.assertEqual(obj.a, 0)

    def test_keyword_arg(self):

        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: TestClass, arg_one):
                self.arg_one = arg_one
                self.x = x

        obj = TestInjectClass(arg_one="foo")
        self.assertIsInstance(obj.x, TestClass)
        self.assertEqual(obj.arg_one, "foo")

    def test_missing_keyword_arg(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: TestClass, *extra_args, arg_one):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(TypeError, lambda: TestInjectClass("foo"))

    def test_extra_pos_arg(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, arg_one, x: TestClass):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(TypeError, lambda: TestInjectClass("foo", None, "bar"))

    def test_extra_kwarg_arg(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, arg_one, x: TestClass):
                self.arg_one = arg_one
                self.x = x

        self.assertRaises(TypeError, lambda: TestInjectClass(arg_one="foo", arg_two="bar"))

    def test_double_inject(self):

        class TestInjectClass:
            @self.injector.inject
            def __init__(self, x: TestClass, y: TestClass2):
                self.x = x
                self.y = y

        obj = TestInjectClass()
        self.assertIsInstance(obj.x, TestClass)
        self.assertIsInstance(obj.y, TestClass2)

    def test_complex_arguments(self):
        class TestInjectClass:
            @self.injector.inject
            def __init__(self, pos_one, x: t.Optional[TestClass], pos_two, y: t.Optional[TestClass2], *args, kw_one, kw_def='test', **kwargs):
                self.pos_one = pos_one
                self.pos_two = pos_two
                self.x = x
                self.y = y
                self.args = args
                self.kw_one = kw_one
                self.kw_def = kw_def
                self.kwargs = kwargs

        obj = TestInjectClass(5, None, "hello world", None, "three", kw_one="foo", kw_three="test", kw_four="bar")
        self.assertEqual(obj.pos_one, 5)
        self.assertEqual(obj.pos_two, "hello world")
        self.assertEqual(obj.kw_one, "foo")
        self.assertIsInstance(obj.x, TestClass)
        self.assertIsInstance(obj.y, TestClass2)
        self.assertTupleEqual(obj.args, ("three",))
        self.assertDictEqual(obj.kwargs, {"kw_three": "test", "kw_four": "bar"})

    def test_construct(self):
        class TestInjectClass:

            tc: t.Optional[TestClass] = None

            @self.injector.construct
            def __init__(self):
                pass

        tic = TestInjectClass()
        self.assertTrue(hasattr(tic, 'tc'))
        self.assertIsInstance(tic.tc, TestClass)

    def test_method_signature(self):
        @self.injector.inject
        def test_method(param1: TestClass, param2: int, param3: str):
            pass
        sig = inspect.signature(test_method)
        parameter_names = [param for param in sig.parameters]
        self.assertIn("param1", parameter_names)
        self.assertIn("param2", parameter_names)
        self.assertIn("param3", parameter_names)

    def test_wrap_wrapper(self):
        injector = InjectionManager()
        iw = injector.build_injector_wrapper(lambda x: x)
        iw2 = injector.build_injector_wrapper(iw)
        self.assertIs(iw, iw2)

    def test_bad_wrap(self):
        injector = InjectionManager()
        with self.assertRaises(ValueError):
            injector.build_injector_wrapper(t.cast(t.Callable, "foobar"))

    def test_wrap_existing_test_features(self):
        injector = InjectionManager()
        iw = injector.build_injector_wrapper(None, test_fixtures={'foo': lambda: 'x', 'bar': lambda: 'y'})
        iw2: _InjectWrapper = t.cast(_InjectWrapper, injector.build_injector_wrapper(iw, test_fixtures={'foo': lambda: 'X', 'monkey': lambda: 'Z'}))
        self.assertIsInstance(iw2, _InjectWrapper)
        fixtures: dict = t.cast(dict, iw2.test_fixtures)
        self.assertIsNotNone(fixtures)
        self.assertIn("foo", fixtures)
        self.assertIn("bar", fixtures)
        self.assertIn("monkey", fixtures)
        self.assertEqual(fixtures["foo"](), "X")
        self.assertEqual(fixtures["bar"](), "y")
        self.assertEqual(fixtures["monkey"](), "Z")

    def test_init_on_str_fails(self):
        injector = InjectionManager()
        with self.assertRaises(TypeError):
            injector.construct(str)


    def test_function_injection(self):
        @self.injector.inject
        def test_method(param1='one', param2: t.Optional[TestClass] = None):
            return param1, param2

        a, b = test_method('two')
        self.assertIsInstance(b, TestClass)
        self.assertEqual(a, 'two')

    def test_no_call(self):
        iw = _InjectWrapper(None, self.injector)
        with self.assertRaises(TypeError):
            _ = iw.call

    def test_set_call_if_none(self):
        iw = _InjectWrapper(None, self.injector)
        self.assertTrue(iw.set_call_if_none(self.test_no_call))
        self.assertFalse(iw.set_call_if_none(self.test_set_call_if_none))

import typing
from unittest import TestCase
import autoinject.reflect as reflect
from autoinject import ClassRegistry, DelayedParameter, DelayedCallable, InjectionManager
from autoinject.injection import _InjectWrapper


class TestReflectionLibrary(TestCase):

    def test_python_builtin(self):
        self.assertIs(str, reflect.resolve_fqn('str'))

    def test_child_class(self):
        obj = reflect.resolve_fqn("tests.package._child_object.MyClass.SubClass")
        from tests.package._child_object import MyClass
        self.assertIs(obj, MyClass.SubClass)

    def test_abc_is_not_concrete(self):
        from tests.package._abstract import AbstractObj
        self.assertFalse(reflect.is_concrete(AbstractObj))

    def test_abc_subclass_is_not_concrete(self):
        from tests.package._abstract import ConcreteObj
        self.assertTrue(reflect.is_concrete(ConcreteObj))

    def test_fqn_of_object_class(self):
        from tests.package._abstract import ConcreteObj
        x = ConcreteObj()
        self.assertEqual(reflect.type_fqn(x), reflect.fqn(ConcreteObj))

    def test_unpack_str_returns_str(self):
        self.assertEqual({"foobar"}, reflect.unpack_type_annotation("foobar"))

    def test_unpack_random_stuff(self):
        self.assertEqual({5}, reflect.unpack_type_annotation(5))

    def test_unpack_union(self):
        y = typing.Union[TestCase, typing.List]
        self.assertEqual(y, reflect.resolve_annotation(None, y))

    def test_wrong_annotation(self):
        y = "builtin_str"
        self.assertEqual(y, reflect.resolve_annotation(TestReflectionLibrary, y))

    def test_none_is_none(self):
        self.assertIsNone(reflect._build_injectable_info(TestReflectionLibrary, None, ClassRegistry()))

    def test_delayed_parameter(self):
        x = DelayedCallable(dict)
        creg = ClassRegistry()
        creg.register_delayed_parameter(DelayedParameter)
        self.assertIs(x, reflect._build_injectable_info(TestReflectionLibrary, x, creg))

    def test_no_constructor_error(self):
        injector = InjectionManager()
        with self.assertRaises(TypeError):
            injector.with_fixture("foobar")

    def test_with_old_fixture_style(self):
        injector = InjectionManager()
        with self.assertWarns(DeprecationWarning):
            x = injector.with_fixture("foobar", fixture_callback=lambda: "x")
            self.assertIsInstance(x, _InjectWrapper)

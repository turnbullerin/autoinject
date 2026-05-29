import typing as t
from unittest import TestCase

from autoinject import DelayedParameter, InjectionManager
injector = InjectionManager()

class FreshDict(DelayedParameter):

    def resolve(self, *args, **kwargs) -> t.Any:
        return dict()


def delayed_dict() -> dict:
    return t.cast(dict, FreshDict())

@injector.inject
def my_func(x: dict = delayed_dict()):
    return x


class TestFreshDict(TestCase):

    def test_not_same(self):
        self.assertIsInstance(my_func(), dict)
        self.assertNotEqual(id(my_func()), id(my_func()))

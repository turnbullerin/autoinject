import typing as t
from unittest import TestCase

from autoinject import delayed_call, InjectionManager
injector = InjectionManager()


@injector.inject
def my_func(x: dict = delayed_call(dict)):
    return x


class TestFreshDict(TestCase):

    def test_not_same(self):
        self.assertIsInstance(my_func(), dict)
        self.assertNotEqual(id(my_func()), id(my_func()))

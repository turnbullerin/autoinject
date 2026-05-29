import unittest
from autoinject import InjectionManager
import typing as t
injector = InjectionManager()


@injector.injectable
class Service: ...


@injector.inject
def get_service(__obj1: int, __obj2: int = 5, service: Service = None, /) -> t.Tuple[int, int, Service]:  # type: ignore
    return __obj1, __obj2, service


class Test(unittest.TestCase):
    def test(self):
        value1, value2, service = get_service(8)
        self.assertEqual(8, value1)
        self.assertEqual(5, value2)
        self.assertIsInstance(service, Service)

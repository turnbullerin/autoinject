import typing as t
import unittest
from autoinject import InjectionManager, auto
injector = InjectionManager()

@injector.injectable
class Service: ...


@injector.inject
def get_service(service: Service = auto()) -> Service:
    return t.cast(Service, service)


class Test(unittest.TestCase):
    def test(self):
        service = get_service()
        self.assertIsInstance(service, Service)

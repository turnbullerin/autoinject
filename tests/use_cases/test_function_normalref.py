import typing as t
import unittest
from autoinject import InjectionManager
injector = InjectionManager()


@injector.injectable
class Service: ...


@injector.inject
def get_service(service: t.Optional[Service] = None) -> Service:
    return t.cast(Service, service)


class Test(unittest.TestCase):
    def test(self):
        service = get_service()
        self.assertIsInstance(service, Service)

import unittest
from autoinject import InjectionManager
injector = InjectionManager()


@injector.injectable
class Service: ...


@injector.inject
def get_service(service: Service = None) -> Service:  # type: ignore
    return service


class Test(unittest.TestCase):
    def test(self):
        service = get_service()
        self.assertIsInstance(service, Service)

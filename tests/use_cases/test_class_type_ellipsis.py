import unittest
from autoinject import InjectionManager
injector = InjectionManager()


@injector.injectable
class Service: ...


class Client:

    service: Service = ...  # type: ignore

    @injector.construct
    def __init__(self): ...


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service, Service)

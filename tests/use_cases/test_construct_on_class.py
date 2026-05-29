import unittest
from autoinject import InjectionManager
injector = InjectionManager()


@injector.injectable
class Service: ...


@injector.construct
class Client(object):
    service: Service


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service, Service)

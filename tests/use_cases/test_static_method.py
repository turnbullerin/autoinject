import unittest
import typing as t
from autoinject import InjectionManager
injector = InjectionManager()


@injector.injectable
class Service: ...


class Client:

    def __init__(self): ...

    @injector.inject
    @staticmethod
    def service(srv: t.Optional[Service] = None) -> t.Optional[Service]:
        return srv


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service(), Service)

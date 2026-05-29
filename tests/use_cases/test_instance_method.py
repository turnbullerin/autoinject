import unittest
from autoinject import InjectionManager
import typing as t
injector = InjectionManager()


@injector.injectable
class Service: ...


class Client:

    def __init__(self): ...

    @injector.inject
    def service(self, srv: t.Optional[Service] = None) -> t.Optional[Service]:
        return srv


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service(), Service)

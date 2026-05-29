import unittest
import typing as t
from autoinject import InjectionManager
injector = InjectionManager()


@injector.injectable
class Service: ...


class Client:

    service: t.Optional[Service] = None  # type: ignore

    @injector.construct
    def __init__(self): ...


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service, Service)

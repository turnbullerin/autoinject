from __future__ import annotations
import unittest
from autoinject import InjectionManager
injector = InjectionManager()


class Client:

    service: "Service"

    @injector.construct
    def __init__(self): ...


@injector.injectable
class Service: ...


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service, Service)

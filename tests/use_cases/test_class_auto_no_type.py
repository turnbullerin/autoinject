import typing
import unittest
from autoinject import InjectionManager, auto
injector = InjectionManager()


@injector.injectable
class Service: ...


class Client:

    service: Service = auto()

    @injector.construct
    def __init__(self: typing.Self):
        typing.assert_type(self.service, Service)


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service, Service)

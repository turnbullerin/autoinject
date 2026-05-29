import unittest
import typing as t

from tests.package._indirect import injector

if t.TYPE_CHECKING:
    import tests


class Client:

    service: "tests.package._indirect.Service"  # type: ignore # testing purposes

    @injector.construct
    def __init__(self): ...


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        from tests.package._indirect import Service
        self.assertIsInstance(obj.service, Service)

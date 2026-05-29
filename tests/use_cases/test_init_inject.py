import unittest
from autoinject import InjectionManager
import typing as t
injector = InjectionManager()


@injector.injectable
class Service: ...


class Client:

    # NB: This causes a mypy type error because inject isn't a simple decorator
    @injector.inject
    def __init__(self, srv: t.Optional[Service] = None):
        self.service = srv

class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service, Service)

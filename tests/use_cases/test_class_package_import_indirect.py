import unittest

from tests.package._indirect import Service, injector



class Client:

    service: Service

    @injector.construct
    def __init__(self): ...


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service, Service)

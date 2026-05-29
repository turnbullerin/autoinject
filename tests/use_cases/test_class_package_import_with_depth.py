import unittest

import tests.package as package



class Client:

    service: package._service.Service

    @package._service.injector.construct
    def __init__(self): ...


class Test(unittest.TestCase):
    def test(self):
        obj = Client()
        self.assertIsInstance(obj.service, package._service.Service)

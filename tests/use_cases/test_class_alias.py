import unittest
from autoinject import InjectionManager
injector = InjectionManager()


@injector.injectable
class MyLongAndComplicatedServiceName: ...


@injector.alias(MyLongAndComplicatedServiceName)
class Service(MyLongAndComplicatedServiceName): ...


class OtherService(MyLongAndComplicatedServiceName): ...
injector.alias(MyLongAndComplicatedServiceName, OtherService)


@injector.construct
class Client:
    service: Service
    oservice: OtherService
    ogservice: MyLongAndComplicatedServiceName


class TestAliases(unittest.TestCase):

    def test_aliases(self):
        obj = Client()
        self.assertIsInstance(obj.service, MyLongAndComplicatedServiceName)
        self.assertIsInstance(obj.oservice, MyLongAndComplicatedServiceName)
        self.assertIsInstance(obj.ogservice, MyLongAndComplicatedServiceName)

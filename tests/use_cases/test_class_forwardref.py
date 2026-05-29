import sys

if sys.version_info.major == 3 and sys.version_info.minor >= 14:

    import unittest
    from autoinject import InjectionManager
    injector = InjectionManager()


    class Client:

        service: Service

        @injector.construct
        def __init__(self): ...


    @injector.injectable
    class Service: ...


    class Test(unittest.TestCase):
        def test(self):
            obj = Client()
            self.assertIsInstance(obj.service, Service)

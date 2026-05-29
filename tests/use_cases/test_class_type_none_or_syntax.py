import sys


if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    import unittest
    from autoinject import InjectionManager
    injector = InjectionManager()


    @injector.injectable
    class Service: ...


    class Client:

        service: Service | None = None  # type: ignore

        @injector.construct
        def __init__(self): ...


    class Test(unittest.TestCase):
        def test(self):
            obj = Client()
            self.assertIsInstance(obj.service, Service)

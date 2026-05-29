import sys


if sys.version_info.major == 3 and sys.version_info.minor >= 10:
    import unittest
    import typing as t
    from autoinject import InjectionManager
    injector = InjectionManager()


    @injector.injectable
    class Service: ...


    @injector.inject
    def get_service(service: Service | None = None) -> Service:
        return t.cast(Service, service)


    class Test(unittest.TestCase):
        def test(self):
            service = get_service()
            self.assertIsInstance(service, Service)

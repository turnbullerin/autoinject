import sys

if sys.version_info.major == 3 and sys.version_info.minor >= 14:
    import typing as t
    import unittest
    from autoinject import InjectionManager
    injector = InjectionManager()


    @injector.inject
    def get_service(service: Service | None = None) -> Service | None:
        return t.cast(Service, service)


    @injector.injectable
    class Service: ...


    class Test(unittest.TestCase):
        def test(self):
            service = get_service()
            self.assertIsInstance(service, Service)

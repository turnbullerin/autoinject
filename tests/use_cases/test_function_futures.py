from __future__ import annotations
import typing as t
import unittest
from autoinject import InjectionManager
injector = InjectionManager()


@injector.inject
def get_service(service: "Service" = None) -> "Service":  # type: ignore
    return t.cast(Service, service)


@injector.injectable
class Service: ...


class Test(unittest.TestCase):
    def test(self):
        service = get_service()
        self.assertIsInstance(service, Service)

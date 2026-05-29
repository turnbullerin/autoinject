from ._tests import TestInjectable
import tests.package._service as _service
import tests.package._service as _service2

def _register_injectable(injector):
    injector.register_constructor(TestInjectable, constructor=TestInjectable)

import unittest

import autoinject


class TestInjection(unittest.TestCase):

    def test_injectable(self):
        injector = autoinject.InjectionManager()
        @injector.injectable
        class TestClass:
            pass
        self.assertTrue(injector.cls_registry.is_injectable(TestClass))



import unittest

import autoinject


class TestInjection(unittest.TestCase):

    def test_injectable(self):
        injector = autoinject.InjectionManager()
        @injector.injectable
        class TestClass:
            pass
        self.assertTrue(injector.cls_registry.is_injectable(TestClass))

    def test_injection(self):
        injector = autoinject.InjectionManager()
        @injector.injectable
        class TestClass:
            pass

        class TestInjectClass:
            @injector.inject
            def __init__(self, x: TestClass):
                self.x = x

        obj = TestInjectClass()
        self.assertTrue(isinstance(obj.x, TestClass))

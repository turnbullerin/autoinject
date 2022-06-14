import unittest
import autoinject
import autoinject._tests
import eptest


class TestEntryPoint(unittest.TestCase):

    def setUp(self):
        self.finder = eptest.TestFinder()
        self.finder.register()

    def tearDown(self):
        self.finder.clear()
        self.finder.unregister()

    def test_base_isnot_injectable(self):
        injector = autoinject.InjectionManager()
        self.assertFalse(injector.cls_registry.is_injectable(autoinject._tests.TestInjectable))

    def test_injectable_ep(self):
        package = eptest.TestPackage("foobar")
        package.add_entry_point(eptest.TestEntryPoint(
            "foo",
            "autoinject.injectables",
            "autoinject._tests",
            "TestInjectable"
        ))
        self.finder.add_package(package)
        injector = autoinject.InjectionManager()
        self.assertTrue(injector.cls_registry.is_injectable(autoinject._tests.TestInjectable))

    def test_registrar_ep(self):
        package = eptest.TestPackage("foobar")
        package.add_entry_point(eptest.TestEntryPoint(
            "foo",
            "autoinject.registrars",
            "autoinject._tests",
            "_register_injectable"
        ))
        self.finder.add_package(package)
        injector = autoinject.InjectionManager()
        self.assertTrue(injector.cls_registry.is_injectable(autoinject._tests.TestInjectable))

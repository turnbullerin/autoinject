import unittest
import autoinject
import tests.package as ep_test

try:
    import eptest   # type: ignore # just for testing
    EP = True
except ModuleNotFoundError:
    EP = False

@unittest.skipIf(not EP, 'eptest package is not installed')
class TestEntryPoint(unittest.TestCase):

    def setUp(self):
        self.finder = eptest.TestFinder()
        self.finder.register()

    def tearDown(self):
        self.finder.clear()
        self.finder.unregister()

    def test_base_is_not_injectable(self):
        injector = autoinject.InjectionManager()
        self.assertFalse(injector.cls_registry.is_injectable(ep_test._tests.TestInjectable))

    def test_injectable_ep(self):
        package = eptest.TestPackage("foobar")
        package.add_entry_point(eptest.TestEntryPoint(
            name="foo",
            group="autoinject.injectables",
            module="tests.package",
            attr="TestInjectable"
        ))
        self.finder.add_package(package)
        injector = autoinject.InjectionManager()
        self.assertTrue(injector.cls_registry.is_injectable(ep_test._tests.TestInjectable))

    def test_registrar_ep(self):
        package = eptest.TestPackage("foobar")
        package.add_entry_point(eptest.TestEntryPoint(
            name="foo",
            group="autoinject.registrars",
            module="tests.package",
            attr="_register_injectable"
        ))
        self.finder.add_package(package)
        injector = autoinject.InjectionManager()
        self.assertTrue(injector.cls_registry.is_injectable(ep_test._tests.TestInjectable))



class TestInjectable:
    """ This is a test injectable class that isn't registered. """

    pass


def _register_injectable(injector):
    injector.register_constructor(TestInjectable, constructor=TestInjectable)

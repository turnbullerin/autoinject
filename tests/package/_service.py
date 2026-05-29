from autoinject import InjectionManager

injector = InjectionManager()

@injector.injectable
class Service: ...

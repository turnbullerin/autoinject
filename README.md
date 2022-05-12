# Autoinject

A clean, simple framework for automatically injecting dependencies into objects and functions
based around Python's type-hinting system. The framework provides caching of injectable objects,
though this may be disabled on a class-by-class basis. It also supports managing independent
caches for different contexts.

## Define Injectable Classes


    from autoinject import injector

    @injector.injectable
    class MyInjectableClass:

        def __init__():
            pass

    
## Inject Objects With Decorators
    
    @injector.inject
    def inject_me(param1, param2, injected_param: MyInjectableClass):
        # injected_param is set to an instance of MyInjectableClass
        pass

    inject_me("arg1", "arg2") # don't provide anything for injected_param

    
    class InjectMe

        injected_attribute: MyInjectableClass = None

        @injector.construct
        def __init__(self):
            # self.injected_attribute is set to an instance of MyInjectableClass
            pass

Read the [full documentation](https://autoinject.readthedocs.io/en/latest/?) for more details.
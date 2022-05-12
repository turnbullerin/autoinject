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
 
    # Decorate with @injector.inject for functions/methods:

    @injector.inject
    def inject_me(param1, param2, injected_param: MyInjectableClass):
        # injected_param is set to an instance of MyInjectableClass
        pass

    # Omit the injected parameters when calling it:

    inject_me("arg1", "arg2")

 
    # For classes, use @injector.construct to set instance attributes 
    # based on the class attributes   
    class InjectMe:

        injected_attribute: MyInjectableClass = None

        @injector.construct
        def __init__(self):
            # self.injected_attribute is set to an instance of MyInjectableClass
            pass

    # No need to do anything special here:

    obj = InjectMe()
    # obj.injected_attribute is set by the decorator before __init__() is called.

Read the [full documentation](https://autoinject.readthedocs.io/en/latest/?) for more details.
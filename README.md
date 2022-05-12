# Autoinject

A clean, simple framework for automatically injecting dependencies into objects and functions.

## Define Injectable Classes


    from autoinject import injector

    @injector.injectable
    class MyInjectableClass:

        def __init__():
            pass

    
## Inject Objects With Decorators
    
    @injector.inject
    def inject_me(param1, param2, injected_param: MyInjectableClass):
        pass    # do stuff

    inject_me("arg1", "arg2") # don't provide anything for injected_param

    
    class InjectMe

        injected_attribute: MyInjectableClass = None

        @injector.construct
        def __init__(self):
            # self.injected_attribute is already set now
            pass

Read the [full documentation](https://autoinject.readthedocs.io/en/latest/?) for more details.
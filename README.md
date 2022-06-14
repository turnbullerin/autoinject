# Autoinject

[![Documentation Status](https://readthedocs.org/projects/autoinject/badge/?version=latest)](https://autoinject.readthedocs.io/en/latest/?badge=latest)

A clean, simple framework for automatically injecting dependencies into objects and functions
based around Python's type-hinting system. The framework provides caching of injectable objects,
though this may be disabled on a class-by-class basis. It also supports managing independent
caches for different contexts.

## Define Injectable Classes

```python
# Easy mode

from autoinject import injector

@injector.injectable
class MyInjectableClass:

    # __init__() should have no additional required arguments
    def __init__(self):
        pass


# Hard mode, must specify the fully-qualified name of the class,
# but gain control over the arguments

@injector.register("example.MyInjectableClass", os.environ("MY_CONFIG_FILE"))
class MyInjectableClass:

    def __init__(self, config_file):
        # we receive os.environ("MY_CONFIG_FILE") as config_file here
        # positional and keyword arguments to @injector.register() are supported
        pass
```
    
## Inject Objects With Decorators
 
```python
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
```

Read the [full documentation](https://autoinject.readthedocs.io/en/latest/?) for more details.

## Changelog

### v0.2.0
- Objects with a cache strategy of `CONTEXT_CACHE` will now have separate instances within threads
- Added `injector.get()` as a fast way to get the object that would be injected (useful if operating outside of
  a function or method)
- Added `injector.register_constructor()` as a wrapper to register a class in a non-decorated fashion
- Added the entry point `autoinject.injectables` to directly register injectable classes
- Added the entry point `autoinject.registrars`
- Support for overriding injectables and for injecting functions 
- Added a `weight` keyword argument to `register()` and `register_construct()` to control overriding order
- There is now a `cleanup()` function in the `ContextManager()` class which triggers informant objects to check for
  old items that are no longer needed. This was added mostly to support the thread-based context informant, since it 
  has no easy way of calling `destroy()` whenever the thread ends (unless one manually calls it). It is the best 
  practice if you can call `destroy()` directly whenever a context ceases to exist instead of relying on `cleanup()`.

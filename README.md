# Autoinject

[![Documentation Status](https://readthedocs.org/projects/autoinject/badge/?version=latest)](https://autoinject.readthedocs.io/en/latest/?badge=latest)

[![CircleCI](https://dl.circleci.com/status-badge/img/gh/turnbullerin/autoinject/tree/main.svg?style=shield)](https://dl.circleci.com/status-badge/redirect/gh/turnbullerin/autoinject/tree/main)

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

## Specifying injected classes in tests

You can override injected classes in your unit tests using the `@injector.test_case()` decorator. This provides an 
independent global context within the test case function and allows you to pass a map of objects to inject. For example,

```python

from autoinject import injector 

# Your injectable original class
@injector.injectable_global 
class ServiceConnection:
  
  def execute(self) -> int:
    # Real connection code here, returns HTTP status code
    pass
  

# The class you want to write a test case for that uses the injectable class.
class UsesServiceConnection:
  
  connection: ServiceConnection = None
  
  @injector.construct 
  def __init__(self):
    pass
  
  def test_me(self) -> bool:
    # Super simple, check if response code is under 400
    resp_code = self.connection.execute()
    return resp_code < 400
  
  
# Testing stuff
import unittest
  
# Stub for testing
class _StubServiceFixture:
  
  def __init__(self, response_code):
    self.response_code = response_code
  
  def execute(self) -> int:
    return self.response_code


# Test case
class TestUsesServiceConnection(unittest.TestCase):

    @injector.test_case({
      ServiceConnection: _StubServiceFixture(200)
    })
    def test_success_200(self):
        test_obj = UsesServiceConnection()  # this will use the injected objects now
        self.assertTrue(test_obj.test_me())


    @injector.test_case({
      ServiceConnection: _StubServiceFixture(400)
    })
    def test_failure_400(self):
        test_obj = UsesServiceConnection() 
        self.assertFalse(test_obj.test_me())


```

Read the [full documentation](https://autoinject.readthedocs.io/en/latest/?) for more details.

## Changelog

### v1.3.3
- Member lists of objects are now cached to prevent multiple calls to ``inspect.getmembers()`` when the 
same class is created many times. This results in significant speed increases.

### v1.3.0
- The new `@injector.test_case()` decorator is available for use with unit testing frameworks. It executes the decorated
  function with a different global and non-global context to ensure the independence of test functions. In addition, one
  can override the injected classes to provide specific test fixtures. These are passed as a dict of either `type` objects 
  or fully qualified class names as strings as keys and either the `type` or class name as string (to create the object), 
  or an object or function to use as the injected object.
- A bug was fixed where exceptions within a context caused issues with the new contextvars integration.

### v1.2.0
- Contextvar-driven contexts are now respected by default
- Several wrappers exist to better support using contextvars. All of them provide for a separate set of injected 
  CONTEXT_CACHE dependencies. In addition, each is a wrapper around `@injector.inject`, so both are not needed.
  - `@injector.with_contextvars`: Creates a new context that is a copy of the current one 
  - `@injector.with_same_contextvars`: Uses the current context
  - `@injector.with_empty_contextvars`: Creates a new empty context
- When using a `with_contextvars` wrapper, you can inject the context object using type-hinting (e.g. 
  `ctx: contextvars.Context`). Note that this is actually an instance of `ContextVarsManager` which is a context manager
  that delegates most functionality to the current `contextvars.Context` object with a few modifications:
  - It provides the method `set(context_var, value) -> token` and the complementary `reset(context_var, token)` to
    handle variable setting and resetting within the context manager.
    - If the "same" context is used, these methods are equivalent to calling the methods directly on the `context_var`
    - In all other cases, they are equivalent to calling `ctx.run(context_var.METHOD, *args, **kwargs)`. 
    - In essence, this makes sure the `set()` and `reset()` operations are performed in the context that the manager is
      managing (since the manager doesn't run the inner block in the context).
  - If the "same" context is used:
    - `run()` will just directly call the function (it is in the current context essentially)
    - `copy()` is an alias for `contextvars.copy_context()`
    - Other functions besides `set()` and `reset()` make a copy of the current context and return the results of its
      method. This copy is transient and remade each time, so modules making extensive use of it can call `copy()` and
      check the copy.
- Note that, unlike the context manager, the decorators also RUN the inner code in the given context.  
- Thread-handling was improved significantly and now also includes a wrapper function for `threading.Thread.run()` methods to
  ensure clean-up (`@injector.as_thread_run()`). This also is a wrapper around `@injector.inject` so you can inject
  variables into your `run()` method directly.

### v1.1.0
- Injectable objects may now define a `__cleanup__()` method which will be invoked when the global cache or context
  cache is cleared.
- Note that `__cleanup__()` IS NOT INVOKED for one-time use objects at the moment, but this is planned as a feature.

### v1.0.1
- Inherited injectable class members are now supported properly

### v1.0.0
- Official initial release
- Added support for @injector.injectable_global which registers with GLOBAL cache instead of context-specific cache
- Added support for @injector.injectable_nocache which registers with NO_CACHE instead 
- Added support for injector.override() as a helper function to replace one constructor with another.
- Added support for any constructor argument (e.g. via override() or register_constructor()) to be specified
  by fully-qualified Python name (e.g. package.module.MyInjectableClass) to better support systems where injected
  classes are specified by name.
- Fixed a bug whereby the cache wasn't cleared

### v0.2.2
- Fixed a bug for injection when a non-truthy default value needed to be used.

### v0.2.1
- Fixed a bug in Python 3.8 and 3.9 where `entry_points(group=?)` was not supported

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

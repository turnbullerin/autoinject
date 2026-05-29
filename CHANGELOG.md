
## Changelog

### v2.0.0
- Updated to Python 3.9 minimum requirement.
- Added support for `from __futures__ import annotations` and Python 3.14's `annotationlib.ForwardRef` style annotations.
- Type hints provided in a `if typing.TYPE_CHECKING` block should now be supported in most cases. Be aware that this 
  feature relies on `inspect.getsourcecode()` and `ast` - if the source code of the original module is not available, it
  will fail. It also takes significantly longer, especially if you use multiple aliases. Use `TYPE_CHECKING` blocks only
  when the cost of importing the module is very high. As an alternative, you can implement a stub class for injection
  and override it with the full implementation.
- The previous behaviour that the argument that was being injected was skipped was confusing for positional arguments. 
  As of 2.0.0, if you have a signature like `func(a=5, b: InjectMe = None, c=6)` and you want to specify a different 
  value for `c`, you must call it as either `func(5, c=10)` or `func(5, None, 6)` (prior to 2.0.0, `func(5, 6)` would
  have worked but was very confusing). It is strongly recommended to put injectable parameters at the end of your 
  parameter list.
- 2.0.0 offers support for a more declarative form of injection - instead of declaring `func(b: InjectMe=None)`, you can
  now declare `func(b = injector.Dependency(InjectMe))`. The decorator `@injector.inject` is still required.
- As a side-benefit of the previous feature, a new class is available `autoinject.DelayedParameter(callable, *args, **kwargs)`.
  When you specify this as a default parameter for a function, the return value of `callable(*args, **kwargs)` is given 
  to the function by `@injector.inject`. Resolving the callable is done at call-time and is not cached by the injection 
  system, meaning you could make a new dictionary with `DelayedParameter(dict)` for example that avoids issues with passing
 a default dictionary by reference.

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

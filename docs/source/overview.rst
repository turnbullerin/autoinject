Usage Information
=================

.. highlight:: python

Basic Usage
-----------

Classes that can be injected as a dependency are decorated as ``injectable``::

    from autoinject import injector

    @injector.injectable
    class DatabaseManager:

        # The __init__ method should not require parameters
        def __init__(self):
            pass

Functions or methods that then need this object use the ``injector.inject`` decorator and type-hint the parameter where
the dependency is to be provided. The type-hint can be provided as a ``type`` or as a string with the fully-qualified
class name. When calling the method or function, completely omit the argument - it will be provided for you::

    from autoinject import injector

    @injector.inject
    def do_database_stuff(a_parameter, db: DatabaseManager, another_parameter):
        pass

    do_database_stuff("a", "another")

Classes that want to store the dependency as an instance attribute can define an appropriately type-hinted class
attribute set to None and decorate the ``__init__()`` method with ``injector.construct``::

    from autoinject import injector

    class MyClass

        db: DatabaseManager = None

        @injector.construct
        def __init__(self):
            # By now, self.db will be set to an instance of DatabaseManager
            pass


Customizing Injectables
-----------------------

By default, injectable objects are created with no arguments. If arguments are required, they should be provided when
registering the object (they may also be provided via ``autoinject`` using class attributes and the ``construct``
decorator. The ``injector.register()`` decorator provides this function. It can be used to either decorate a class or a
function that will build an instance of the class::

    from autoinject import injector

    # The string should be the fully-qualified name of the class that would match a string type-hint
    @injector.register("my.package.ExampleClass", "arg", kwarg1=4)
    class ExampleClass:

        def __init__(self, arg1, kwarg1):
            pass

    # Alternatively, use it on a factory method; this example is equivalent to the above example.
    @injector.register("my.package.ExampleClass", "arg")
    def build_example_class(arg1):
        return ExampleClass(arg1, kwarg1=4)

    # As of 0.2.0, you can instead use register_constructor() to provide defaults to the constructor
    injector.register_constructor(ExampleClass, constructor=ExampleClass, "arg", kwarg1=4)


As of 0.2.0, function-based injections are now possible using a decorator-like constructor for the function::

    from autoinject import injector

    @injector.register("my.package.function")
    def _create_function():
        def do_stuff(arg1, arg2):
            pass
        return do_stuff

The value in doing this lies in the other change in 0.2.0, that one can override the constructor function by registering
another constructor to the same object name. This lets other libraries extend and enhance the functionality of an
injectable object without having to change how the object is injected in other dependencies. By supporting functions,
a function can also be overridden as needed. A weight parameter for ``register()`` and ``register_constructor()`` is now
available, with higher weight constructors overriding lower weight ones::

    from autoinject import injector

    # Note also that arbitrary strings are now supported as the identifier, but keeping to package-style notation is
    # probably the clearest way to proceed
    @injector.register("my.package.formatter")
    def _create_function1():
        def do_stuff(arg):
            return arg
        return do_stuff


    @injector.register("my.package.formatter", weight=20)
    def _create_function2():
        def do_stuff(arg):
            return "!{}!".format(arg.upper())
        return do_stuff


    @injector.register("my.package.formatter", weight=10)
    def _create_function3():
        def do_stuff(arg1):
            return arg.upper()
        return do_stuff


    class Stuff:

        formatter: "my.package.formatter" = None

        @injector.construct
        def __init__(self):
            print(self.formatter("bar"))

    Stuff()
    # This should print "!BAR!", as the weight of the second constructor is higher than the first or third

From 1.1.0, objects may define a ``__cleanup__()`` method which is called when they are removed from the global or
context cache. It is also called via the ``atexit`` module at the end of program execution. A future version will add
this behaviour to non-cached objects when they leave the scope from which they were invoked. The intended purpose is to
ensure resources are cleaned up properly from injected classes (e.g. database connections).::

    from autoinject import injector

    @injector.injectable
    class InjectableClass:

        def __init__():
            self._is_active = True

        def __cleanup__():
            self._is_active = False


Leveraging Entry Points
-----------------------

Most applications should be fine registering their injectables in the source code. When the class is imported for the
first time (so that it can be used as a type-hint), the class is registered as an injectable. However, if you do not
want to follow this pattern, autoinject exposes two entry points that your package can use::

    # setup.cfg
    [options.entry_points]

    # Specify the path to your class to the autoinject.injectables entry point (equivalent to @injector.injectable)
    autoinject.injectables =
        my_class = mylib.MyClass

    # Specify a custom function to handle registration
    autoinject.registrars =
        my_reg = mylib._register_my_class2


    # mylib.__init__.py

    # This one will get registered automatically
    from foo import MyClass

    # This one is done by the registration function below
    from bar import MyClass2

    def _register_my_class2(injector):
        # Perhaps we need some keyword arguments for this class's constructor
        injector.register_constructor(MyClass2, MyClass2, arg="bar")

A common use case I have found for this is if you are creating an integration with an existing package; you can't add
the appropriate decorators directly and users would have to remember to import your integration package to get the
injection to work. By registering your integration with the entry point, it will automatically be included when the
autoinject singleton is constructed. Another exception would be if you wanted to facilitate people using string type-
hinting instead of the type itself or you wanted to provide an override class to inject.

Note that the registrar functions take the injector as an argument, to ensure they are operating on the singleton. This
is necessary because the registrar functions are called during ``__init__()`` and so the global ``autoinject.injector``
object is not yet available.


Contexts
--------

By default, autoinject caches objects in a context. This is intended to support use cases where a global object cache
will not be appropriate, such as in a WSGI application where objects may need to be kept independent by request. In
order to allow applications to customize how context management happens, the ``ContextManager`` class allows for
informants to be added to it. Each of these should provide the ``ContextManager`` with a unique value and the
manager then ensures that objects are never shared where the informant has provided a different value.

:class:`autoinject.informants.NamedContextInformant` is provided to demonstrate how this works::

    from autoinject import injector, NamedContextInformant

    # Create a named context informant
    context = NamedContextInformant()

    # Register it
    injector.register_informant(context)

    # We can now change the context; none of the previously created objects are available until
    # we switch back
    context.switch_context("new_context")

While this toy example helps to understand how it works, the intention is for applications that require context to
implement and provide their own ``ContextInformant`` objects that implement ``get_context_id()`` which should return a
unique value for each context.

The default is to cache objects by context (which amounts to singleton objects in a script and per-request objects in a
WSGI environment). If this is not the desired behaviour, the caching strategy can be defined using @register::

    from autoinject import injector, CacheStrategy

    # This class will never be cached
    @injector.injectable_nocache
    class ExampleNoCacheClass:

        def __init__(self):
            pass

    # This class will ignore the context and cache itself globally. Make sure it is thread-safe!
    @injector.injectable_global
    class ExampleGlobalClass:

        def __init__(self):
            pass

Currently, two context providers are provided natively for integration with common Python techniques for handling
context-specific global variables: ``threading`` and ``contextvars``. Threads are handled automatically and are
cleaned up "soon" after the thread terminates. For extra safety, threads should clean up their own context variables
when they are done.::

    from autoinject import injector

    # If you can't change the thread, this is the best practice
    thread = MyThread()
    thread.start()
    thread.join()
    # Call this immediately after the thread ends before a new thread might get started.
    injector.thread_cleanup(thread)


    # If you are in control of the thread design, use the decorator for the run() method
    class MyThread(threading.Thread)

        @injector.as_thread_run
        # This wraps @injector.inject so you don't need both.
        def run(self):
            # dostuff
            pass
            # When complete, the decorator ensures thread_cleanup() is called.

    class MyThread2(threading.Thread)
        # Alternatively, you can combine this with the normal @injector.inject method. This lets you use
        # type hinting for where to put the context argument.
        @injector.inject(as_thread_run=True)
        def run(_ctx: contextvars.Context):
            pass
    thread = MyThread()
    thread.start()
    thread.join()
    # Nothing else needed

Contextvars requires some special support because there is no method to hook into the creation or destruction of
contexts and, by default, copying a ``contextvars.Context`` copies the values as well. Therefore, contexts would
essentially share the context of their parents if their parents used an autoinjected variable, otherwise they do not.
Autoinject provides some helper methods for those wishing to use autoinjection with contextvars.::

    from autoinject import injector
    from contextvars import Context, copy_context

    @injector.inject
    def do_stuff(injectable: Type = None):
        return injectable

    context_fresh = Context()
    context_copy = context_fresh.copy()
    context_main_copy = copy_context()

    # Note that all four of these objects will be different, since
    # the contexts were created before an injectable was called on them
    object1 = do_stuff()
    object2 = context_fresh.run(do_stuff)
    object3 = context_copy.run(do_stuff)
    object4 = context_main_copy.run(do_stuff)

    # Now that we have run an autoinjector command, the contexts will maintain their state
    still_object2 = context_fresh.run(do_stuff)

    # If we copy a context that has had a command run on it, that context will have the same state
    context_fresh_new_copy = context_fresh.copy()
    still_object2_again = context_fresh_new_copy.run(do_stuff)

    # To give the context a new set of autoinjected commands, we can ask the injector to "freshen" it:
    context_refreshed = context_fresh.copy()
    injector.cv_freshen(context_refreshed)
    no_longer_object2 = context_refreshed.run(do_stuff)

    # To ensure that context is properly passed when copied, we can ask the injector to "touch" it BEFORE copying:
    new_context = Context()
    injector.cv_touch(new_context)
    new_context_copy = new_context.copy()
    object5 = new_context.run(do_stuff)
    still_object5 = new_context_copy.run(do_stuff)

    # We can also freshen or touch the current context by omitting the argument
    # Note that "touch" does not change the ID if it already exists and "freshen" always changes it.
    def example():
        injector.cv_touch()
        subcontext1 = copy_context()
        subcontext2 = copy_context()
        actually_still_object5 = subcontext1.run(do_stuff)
        yep_still_object5 = subcontext2.run(do_stuff)
    new_context.run(example)

    # Freshening the context ID also returns the old ID (if it existed), which can be restored with cv_restore:
    def example():
        token = injector.cv_freshen()
        subcontext1 = copy_context()
        subcontext2 = copy_context()
        object6_now = subcontext1.run(do_stuff)
        still_object6 = subcontext2.run(do_stuff)
    new_context.run(example)
    but_still_object5_here = new_context.run(do_stuff)

    # This last example gives a good example of how to handle working with a class that
    # implements contextvars but not autoinject:
    def user_method():
        token = injector.cv_freshen()
        # do stuff with the injector
        injector.cv_cleanup()
        injector.cv_restore(token)

    # The API will then call user_method() in whatever context it wants,
    # but we have ensured that our autoinject-enabled functionality is
    # operating within a unique context for each time user_method() is
    # called.

    # Note the use of cv_cleanup() in the last example. This is used to remove all the
    # current object caches (much like thread_cleanup()). It is especially important for
    # contextvars because there is currently no way to ensure that the cleanup happens
    # otherwise (except when the process ends). As with thread_cleanup(), calling it
    # with no arguments calls it on the current context.
    injector.cv_cleanup(new_context)

    # Note that the actual ID underlying the context is preserved. If, after a cleanup, the
    # injector was used again, a new object is made but it would be the same across previously
    # linked contexts.
    object7_now = new_context.run(do_stuff)
    also_object7 = new_context_copy.run(do_stuff)

    # For simplicity, autoinject also provides a context manager named ContextVars which can help you
    achieve these goals:

    # The default is to COPY the existing context exactly and freshen the context ID
    with injector.ContextVars() as ctx:
        # This automatically creates a new sub-context with a copy of all values, and
        # freshens the context ID inside the block. It is the equivalent of
        # injector.cv_touch()
        # ctx = contextvars.copy_context()
        # original_token = injector.cv_freshen(ctx)
        # Note that injector.ContextVars(ContextVarManager.COPY) has the same behaviour.

        # ctx exposes the contextvars.Context() API
        object1 = ctx.run(do_stuff)

        # It also can make copies with an option to preserve or freshen the context ID
        # The first call to copy_context() sets the context ID like it was injected, so
        # the behaviour is consistent.
        same_injector_ctx = ctx.copy(True) # doesn't matter if you did stuff first or not
        still_object1 = same_injector_ctx.run(do_stuff)
        new_injector_ctx = ctx.copy() # always Fresh
        object2 = new_injector_ctx.run(do_stuff)

        # Note that you can pass a context to use instead of the current one to the context manager
        with injector.ContextVars(same_injector_ctx) as ctx2:
            # ctx2's ID is DIFFERENT here because the context manager freshens it
            # other contextvars as the same as in same_injector_ctx
            now_object3 = ctx2.run(do_stuff)
        but_still_object1_here = ctx.run(do_stuff)

        # We can also wrap ContextVarManager objects in the same way
        with injector.ContextVars(ctx) as ctx3:
            # same context as outside, but different injector ID
            # maybe not very useful


        # When the block ends, the cache related to the context ID is removed automatically
        # and the previous context ID is restored. This is the equivalent of
        # injector.destroy_self(new_context)
        # injector.cv_restore(original_token)

    # This special value creates a new EMPTY context:
    with injector.ContextVars(ContextVarManager.EMPTY) as ctx:
        # Equivalent to:
        # ctx = contextvars.Context()
        # original_token = injector.cv_freshen(ctx)
        object4 = ctx.run(do_stuff)
        # cleanup the same

    # This special value re-uses the current context. It does this by essentially
    # just directly calling methods instead of using a Context class method.
    with injector.ContextVars(ContextVarManager.SAME) as ctx:
        # Equivalent to
        # original_token = injector.cv_freshen()
        object5 = ctx.run(do_stuff) # actually a direct call to do_stuff()
        new_ctx = ctx.copy_context() # actually a call to contextvars.copy_context()
        # cleanup the same

    # The context manager provided here maps 1-to-1 for a context object but also provides a set and reset method

    with injector.ContextVars(ContextVarManager.SAME) as ctx:
        token = ctx.set(my_var, "foobar")
        ctx.reset(my_var, token)

    # In addition, you can decorate a function or method to have a context manager while running:

    # This injector creates a COPY by default of the current context, but
    # the other modes work as well (SAME or EMPTY). Note that the method is
    # run IN THE NEW CONTEXT, so access to the old context is unavailable. This is the ideal way
    # to use this.
    @injector.with_contextvars([context_mode=None])
    # This wraps @injector.inject so you don't need both.
    def my_method(_ctx: contextvars.Context):
        # Use _ctx as above
        pass


    # Like above but uses context_mode="same" for using the same context but
    # a fresh autoinjection ID
    # This wraps @injector.inject so you don't need both.
    @injector.with_same_contextvars
    def my_method(_ctx: contextvars.Context):
        # Use _ctx as above
        pass


    # Like above but uses context_mode="empty" for a brand new context
    # This wraps @injector.inject so you don't need both.
    @injector.with_empty_contextvars
    def my_method(_ctx: contextvars.Context):
        # Use _ctx as above
        pass

    # Alternatively, you can combine this with the normal @injector.inject method. This lets you use
    # type hinting for where to put the context argument.
    @injector.inject(with_contextvars=True, [context_mode=None]])
    def my_method(_ctx: contextvars.Context):
        pass


Fixing IDE Problems
-------------------
Of note, IDEs may display errors on functions because the signature does not match (the Python ``__signature__`` is
updated to match, but IDEs tend to read right from the source code). This only affects code completion/syntax checking
NOT actual execution. To avoid this issue, put your dependencies after any other positional arguments and, if desired,
provide a default value::

    from autoinject import injector

    @injector.inject
    def do_database_stuff(a_parameter, another_parameter, db: DatabaseManager = None):
        pass

    do_database_stuff("a", "another")

Background
----------
For those unfamiliar, a brief background is provided here on dependency injection (DI) and the motivations of doing so.
If you are familiar with why DI is good, you can skip this section.

DI is the process by which we avoid one class having to know too much about another class or the system as a whole. For
example, if every class had to understand how the database connection is configured and create their own connection,
then there would be significant copy and pasting that is prone to error (especially once changes have to be made!).
Instead, we delegate responsibility for the database to a specific class that specializes in database connectivity.
This is the Single Responsibility Principle of software engineering. Each other object then leverages that class to
perform its database operations.

However, there exists then a problem of how do we get that database object into our object to work with it. One could
build the database object from scratch each time, but then we require knowledge on how the database is configured. This
is not ideal. Instead, we want something else to construct and maintain the database object for us. There are several
approaches to managing this, such as the singleton pattern or maintaining a package variable that is widely used. One
common approach is dependency injection, where an object/method/function is given all of the dependencies it needs
when constructed/called.

DI is very useful, but it then essentially defers responsibility to the calling function to know how to get all the
dependencies for a method. Enter automated dependency injection (ADI) where function calls are inspected and the
necessary objects automatically injected into the arguments as needed.

This package provides a set of Python tools for registering objects that can be injected, lazy instantiation, caching
them if necessary so that they can be reused, and injecting them into instance variables and function arguments.

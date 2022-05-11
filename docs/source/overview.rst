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

While the key purpose is to inject class instances based on type-hints, it is possible to inject other things. This is
not currently supported officially. However, autoinject basically matches a type-hint to a call to
``injector.register()`` and calls the decorated function if needed to build a new object. If it returned a function
instead of an object, this would probably work fine with any arbitrary strings as type-hints.

Contexts
--------

By default, autoinject caches objects in a context. This is intended to support use cases where a global object cache
will not be appropriate, such as in a WSGI application where objects may need to be kept independent by request. In
order to allow applications to customize how context management happens, the ``ContextManager`` class allows for
informants to be added to it. Each of these should provide the ``ContextManager`` with a unique value and the
manager then ensures that objects are never shared where the informant has provided a different value.

A single class, :class:`autoinject.informants.NamedContextInformant` is provided to demonstrate how this works::

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
    @injector.register("my.package.ExampleClass", caching_strategy=CacheStrategy.NO_CACHE)
    class ExampleNoCacheClass:

        def __init__(self):
            pass

    # This class will ignore the context and cache itself globally. Make sure it is thread-safe!
    @injector.register("my.package.ExampleClass", caching_strategy=CacheStrategy.GLOBAL_CACHE)
    class ExampleGlobalClass:

        def __init__(self):
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

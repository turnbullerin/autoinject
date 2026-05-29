Injectable Options
==================

.. highlight:: python


The default decorator ``injector.injectable`` provides sensible defaults that should work for most use cases.
If other options are wanted, the more advanced decorator ``injector.register()`` can be used.

What Can I Inject
-----------------

While dependency injection patterns are usually concerned with injecting objects, ``autoinject`` also supports
injecting functions::

    from autoinject import injector

    @injector.injectable
    def do_stuff(): ...


Caching
-------
Injectable objects can be cached by the autoinject engine.

There are three layers of caching:

1. Non-cached objects are built fresh each time an injected object is instantiated or an injected function is called.
2. Situationally-cached objects are built once within each given **situation** which are listed below. This is the default.
3. Globally-cached objects ignore the situations - only one object is ever built.

You can control the caching by using the decorators ``injector.injectable_global`` or ``injector.injectable_nocache``.

You can also pass ``caching_strategy=CacheStrategy.GLOBAL_CACHE`` or ``caching_strategy=CacheStrategy.NO_CACHE`` to ``injector.register()``.

You can also either set the property ``AUTOINJECT_CACHE_STRATEGY`` variable on the class or use the ``with_cache_strategy()``
decorator before calling ``injector.inject``::

    from autoinject import injector, CacheStrategy

    # These are all equivalent

    # Useful if you just need to flag it as global
    @injector.injectable_global
    class MyClass: ...

    # If you prefer a decorator approach
    @injector.injectable
    @injector.with_cache_strategy(CacheStrategy.GLOBAL_CACHE)
    class MyClass: ...

    # Arguments to the decorator can also be used
    @injector.register(cache_strategy=CacheStrategy.GLOBAL_CACHE)
    class MyClass: ...

    # This is not recommended, but it does work. The variable is read when injectable() is called, so it must be
    # set before that.
    @injector.injectable
    class MyClass:
        AUTOINJECT_CACHE_STRATEGY = CacheStrategy.GLOBAL_CACHE

Constructor Arguments
---------------------
By default, when an injectable object is built, the constructor is called with no arguments.

You can pass arguments to it by calling ``injector.register()`` with the necessary arguments and keyword arguments.

You can also pass a type or a function that will build the object as a keyword argument (i.e. ``constructor=lambda x: Service(x)``).

Note: If you pass an abstract object (either a descendant of ``abc.ABC`` that hasn't overridden all abstract methods,
or anything that implements ``typing.Protocol``) as a constructor, it will be ignored and an error raised if a concrete
constructor is not provided. ::

    from autoinject import injector

    # These are all equivalent. Note that any keyword arguments for register() itself are stripped out.

    @injector.register(5)
    class MyClass:
        def __init__(value: int): ...

    @injector.register(value=5)
    class MyClass:
        def __init__(value: int): ...

    class MyClass:
        def __init__(value: int): ...
    injector.register(Myclass, constructor=lambda: MyClass(5))

Overriding an Injectable Type
-----------------------------
You can change the type or constructor function that is actually built by calling ``injector.override(OriginalService, NewService)``
with the new constructor (a type or a function that returns the object to inject).

For example, lets say you wanted to define an injectable object ``DatabaseInterface`` and you have three implementations
of that interface: ``SqlLiteDatabase``, ``MariaDatabase``, and ``PostgresDatabase``. This is how you can implement that::

    from autoinject import injector

    # Note that because this is a protocol, it cannot be instantiated.
    @injector.injectable
    class DatabaseInterface(t.Protocol)
        def query(q: str) -> t.Iterable[list]: ...

    # These are concrete implementations, so they can be instantiated
    class SqlLiteDatabase:
        def query(s: str) -> t.Iterable[list]:
            ...

    class MariaDatabase:
        def query(s: str) -> t.Iterable[list]:
            ...

    class PostgresDatabase:
        def query(s: str) -> t.Iterable[list]:
            ...

    @injector.construct
    class DatabaseClient:
        db: DatabaseInterface

        def select_all(self, table_name: str) -> t.Iterable[list]:
            yield from self.db.query(f"SELECT * FROM {table_name}")

    # Choose the database here (really, you might look at your configuration first)
    # note that you must
    injector.override(DatabaseInterface, SqlLiteDatabase)

    # Make your client and call it
    client = DatabaseClient()
    for row in client.select_all("my_table"):
        print(row)


Note that overrides must be done before a class that uses it is instantiated or a function that uses it is called.


Weak References
---------------
By default, the cache stores a reference to the object until the program ends. If you would like the cache to clean up
unused references (at the expense of rebuilding it the next time it is needed), you can pass ``as_weakref=True`` to
``injector.register()``. This stores the object as a weak reference in the cache where it may be cleaned up if no other
object maintains a reference to it. You can also use the ``as_weakref`` decorator or ``AUTOINJECT_AS_WEAKREF = True``. ::

    from autoinject import injector

    # These are all equivalent

    @injector.register(as_weakref=True)
    class MyClass: ...

    @injector.injectable
    @injector.as_weakref
    class MyClass: ...

    @injector.injectable
    class MyClass:
        AUTOINJECT_AS_WEAKREF = True


Situations
----------
The default caching strategy uses **informants** to determine what the current situation is. By default, these are

1. Threading, which keeps one instance per thread.
2. An optional ``contextvar`` that keeps one instance per context.

A globally cached object should therefore be thread-safe and also context-insensitive.

New informants can be created by sub-classing ``SituationInformant`` and then registering it with
``injector.register_informant()``.

Note: If you use the multiprocessing module, the ``injector`` object and all the caches are independent and do not
communicate across processes. It must be correctly configured in each process.

Threading
_________
When using the ``threading`` module, it is best to clean-up the cache after the thread is done. You can use a
decorator on the ``threading.Thread.run()`` method to do so::

    from autoinject import injector
    import threading

    class MyThread(threading.Thread):

        @injector.as_thread_run
        def run(self): ...

This decorator simply removes the cache for the thread as soon as the run() call exits.

Contextvars
___________
Using contextvars requires a special flag to a function decorated with ``injector.inject(with_contextvars=True)``
which runs the function inside a context. All calls to ``injector.inject()`` once running use a separate cache.

See the injected documentation for more details.

Ignoring Specific Situations
____________________________
When registering an injectable class, you can pass ``injector.register(ignore_informants=[])`` to ignore specific
informants. For example, this class will have separate instances for each thread but one unique object between contexts ::

    from autoinject import injector

    @injector.register(ignore_informants=["contextvars"])
    def MyClass: ...

And this one is thread-safe, but will provide different objects between contexts ::

    from autoinject import injector

    @injector.register(ignore_informants=["threading"])
    def MyClass: ...


Cleanup
-------

Injectable objects may define a ``__cleanup__()`` method which is called whenever they are removed from the object
cache. An ``atexit`` is also defined to call them at the end of the program, therefore this method is very likely to
be called under most circumstances.

Entry Points
------------

Entry points can be used by libraries that want to ensure an injectable is registered even if the file containing it is
never imported it. The following is an example::


    # setup.cfg
    [options.entry_points]

    # Specify the path to your class to the autoinject.injectables entry point (equivalent to @injector.injectable)
    autoinject.injectables =
        my_class = mylib.MyClass

    # Specify a custom function to handle registration
    autoinject.registrars =
        my_reg = mylib._register_my_class2


    # mylib.__init__.py

    from autoinject import injector

    # This one will get registered automatically
    from foo import MyClass

    # This one is done by the registration function below
    from bar import MyClass2

    def _register_my_class2(injector):
        # Perhaps we need some keyword arguments for this class's constructor
        injector.register_constructor(MyClass2, MyClass2, arg="bar")

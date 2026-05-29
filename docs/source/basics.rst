Basic Info
==========

.. highlight:: python

This package provides an ``injector`` global object that caches dependencies and injects them into classes and functions automatically.
It has a minimal footprint, requiring only a decorator on the services and clients, plus a special default value to make the type-checkers happy.


Injectable Objects
------------------

Injectable objects (or services as they are known in the DI world) are decorated as ``injectable``, or one of the alternatives that provide more control over how it is instantiated::

    from autoinject import injector

    @injector.injectable
    class DatabaseService:

        def __init__(self):
            # The __init__ method should not require parameters
            pass

Note that the constructor must take no required parameters.

Injected Objects
----------------

Injected objects (aka client objects) define it as an attribute and decorate the class with ``injector.construct``.

The object is inserted immediately before ``__init__`` - until then, ``db`` will be ``None``::

    from autoinject import injector

    @injector.construct
    class DatabaseClient
        db: DatabaseService

        def __init__(self):
            # At this point, self.db is defined and an instance of DatabaseService
            pass


Injected Functions
------------------

Injected functions / methods (aka client functions) define it as a parameter, as seen below. The injection is done when
the function is called::

    from autoinject import injector, auto

    def database_client(self, service: DatabaseService = auto()):
        # at this point, service is actually an instance of DatabaseService
        pass


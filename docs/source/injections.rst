Injection Options
=================

.. highlight:: python


Objects
-------

When using an object-oriented approach, declare injected objects as attributes like so::

    from autoinject import injector
    from services import MyService

    @injector.construct
    class MyClient:

        service: MyService

The decorator will automatically wrap the ``__init__()`` method with one that scans the
class annotations for injectable objects and injects them if they are not present immediately
before the ``__init__`` method is called.


Functions
---------

Functions can also have injectables injected using the ``@injector.inject`` decorator::


    from autoinject import injector, auto
    from services import MyService

    @injector.inject
    def requires_service(service: MyService = auto()): ...

Note that ``auto()`` is optional - it is designed to make the type-checkers happy. You can also
use ``None`` or ``...`` as a default parameter, though type checkers such as mypy may not be happy with this approach.

You can also simply omit any default value, but your IDE may complain that you have not passed a value when you call it.


Referencing an Injectable Object
--------------------------------

The main way to reference an injectable object is by using the ``type`` or ``function`` object directly. However, you
may also reference them using a fully qualified name, i.e. ``"mypackage.mymodule.MyClass"`` (often useful if you don't want
to import the full package just for a type-hint) ::

    from autoinject import injector
    import typing

    if typing.TYPE_CHECKING:
        import mypackage

    @injector.construct
    class MyClient:
        service: "mypackage.mymodule.MyService"


This also means you can use the ``from futures import __annotations__`` method of typing as well, though Python 3.14's
forward references are preferred.


Context Run
-----------
You can combine injection and running in a context in one - use the decorator ``@injector.with_contextvars`` instead.


Getting an Object
-----------------
If you prefer to just get an object directly, you can call ``injector.get(TYPE OR STR)``.




""" Main class for injection tools

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import inspect
import sys
from functools import wraps

from .context_manager import ContextManager
from .class_registry import ClassRegistry, CacheStrategy

# Metadata entrypoint support depends on Python version
import importlib.util
if importlib.util.find_spec("importlib.metadata"):
    # Python 3.10 supports entry_points(group=?)
    if sys.version_info.minor >= 10:
        from importlib.metadata import entry_points
    # Python 3.8 and 3.9 have metadata, but don't support the keyword argument
    else:
        from importlib.metadata import entry_points as _entry_points

        def entry_points(group=None):
            eps = _entry_points()
            if group is None:
                return eps
            elif group in eps:
                return eps[group]
            else:
                return []

# Backwards support for Python 3.7
else:
    from importlib_metadata import entry_points


class MissingArgumentError(ValueError):
    """ Raised when a required argument is missing """
    pass


class ExtraPositionalArgumentsError(ValueError):
    """ Raised when an extra positional argument is provided """
    pass


class ExtraKeywordArgumentsError(ValueError):
    """ Raised when an extra keyword argument is provided """
    pass


class InjectionManager:
    """ Responsible for managing the class registry, context manager, and providing dependency injection tools.

        The main instance of this is provided as part of the ``autoinject`` library named ``injector``. Users should
        make use of that instance instead of creating their own.

        The primary way to register new classes for injection is using the
        :meth:`autoinject.injection.InjectionManager.injectable` decorator. This registers the class with the class
        registry and is suitable for classes that have a constructor with no arguments other than injectable ones. More
        complex classes should use the :meth:`autoinject.injection.InjectionManager.register` decorator and
        provide suitable arguments to support class construction.

        Dependencies can be injected in two fashions: as part of the arguments to a function or method, or as
        object attributes when ``__init__()`` is called. For the former, use the
        :meth:`autoinject.injection.InjectionManager.inject` decorator; it will automatically provide an appropriate
        instance of the objects based on the type-hint of the parameter. For the latter, use the
        :meth:`autoinject.injection.InjectionManager.construct` decorator on the class's ``__init__()`` method. It will
        search for CLASS attributes with an injectable type-hint and inject the objects into the INSTANCE attributes
        as required.
    """

    def __init__(self, include_entry_points=True):
        """ Constructor """
        self.cls_registry = ClassRegistry()
        self.context_manager = ContextManager(self.cls_registry)
        # Register the class registry for injection, using the local instance
        self.cls_registry.register(
            ClassRegistry,
            constructor=lambda: self.cls_registry,
            caching_strategy=CacheStrategy.GLOBAL_CACHE
        )
        # Same but for context manager
        self.cls_registry.register(
            ContextManager,
            constructor=lambda: self.context_manager,
            caching_strategy=CacheStrategy.GLOBAL_CACHE
        )
        # Same but for self
        self.cls_registry.register(
            InjectionManager,
            constructor=lambda: self,
            caching_strategy=CacheStrategy.GLOBAL_CACHE
        )
        if include_entry_points:
            # Handle the autoinject.registrars entry point
            auto_register = entry_points(group="autoinject.registrars")
            for ep in auto_register:
                registrar_func = ep.load()
                registrar_func(self)
            # Handle the autoinject.injectables entry point
            auto_inject = entry_points(group="autoinject.injectables")
            for inject in auto_inject:
                cls = inject.load()
                self.register_constructor(cls, constructor=cls)

    def register_informant(self, context_informant):
        """ Wrapper around :meth:`autoinject.context_manager.ContextManager.register_informant` """
        self.context_manager.register_informant(context_informant)

    def register_constructor(self, cls_name, constructor, *args, **kwargs):
        """ Wrapper around :meth:`autoinject.class_registry.ClassRegistry.register_class` """
        clear_cache = self.cls_registry.is_injectable(cls_name)
        self.cls_registry.register(cls_name, *args, constructor=constructor, **kwargs)
        if clear_cache:
            self.context_manager.clear_cache(cls_name)

    def get(self, cls_name):
        """ Wrapper around :meth:`autoinject.context_manager.ContextManager.get_object` """
        return self.context_manager.get_object(cls_name)

    def override(self, cls_name, new_constructor, *args, **kwargs):
        """ Override one class with another. """
        self.register_constructor(cls_name, new_constructor, *args, **kwargs)

    def register(self, cls_name, *args, **kwargs):
        r""" Decorator for advanced registration of injectable objects. Includes support for passing positional and
             keyword arguments to the constructor, and for specifying an alternative constructor method

            ::

                @injector.register("test.MyClass", "one")
                class MyClass:

                    def __init__(self, param_one):
                        pass

                # alternatively, using a function to build the object

                @injector.register("test.MyClass", "one")
                def _build_my_class(param_one):
                    return MyClass(param_one)

            :param cls_name: The name of the class being registered
            :type cls_name: str or type
            :param args: Positional arguments for the constructor
            :param kwargs: Keyword arguments for the constructor
        """
        def outer_wrap(constructor):
            self.register_constructor(cls_name, constructor, *args, **kwargs)
            return constructor
        return outer_wrap

    def injectable(self, cls):
        """injectable()

        Class decorator for basic registration of injectable objects that don't require external input.

        ::

            @injector.injectable
            class MyClass:

                def __init__(self):
                    # Cannot have any required arguments
                    pass

        """
        self.register_constructor(cls, None)
        return cls

    def injectable_global(self, cls):
        """injectable_global()

        Class decorator for basic registration of injectable objects that don't require external input, but with
        a global scope.
        """
        self.register_constructor(cls, None, caching_strategy=CacheStrategy.GLOBAL_CACHE)
        return cls

    def injectable_nocache(self, cls):
        """injectable_nocache()

        Class decorator for basic registration of injectable objects that don't require external input, but with
        no caching.
        """
        self.register_constructor(cls, None, caching_strategy=CacheStrategy.NO_CACHE)
        return cls

    def inject(self, func):
        """inject()

        Function or method decorator responsible for injecting dependencies into the argument list. A dependency is
        defined as a parameter with a type-hint that has been registered. To make sure your IDE code-completion works
        properly, it is recommended to place these at the end of the argument list and to give them a default value of
        None.

        ::

            @injector.inject
            def my_function(some_param, injected_param: MyClass = None):
                pass

        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            new_args, new_kwargs = self._bind_parameters(func, args, kwargs)
            return func(*new_args, **new_kwargs)
        return wrapper

    def construct(self, func):
        """construct()

        Method decorator for ``__init__()`` that will inspect the class attributes for those with a type-hint that is
        injectable and then inject those dependencies into the corresponding instance attribute.

        ::

            class MyInjectedClass:

                injected_attribute: MyClass = None

                @injector.construct
                def __init__(self):
                    pass

        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            obj = args[0]  # self
            type_map = self._get_bindable_attributes(obj.__class__)
            for name, val in inspect.getmembers(obj.__class__):
                if name[0:2] == "__":
                    continue
                if name in type_map and getattr(obj, name) is None:
                    if self.cls_registry.is_injectable(type_map[name]):
                        setattr(obj, name, self.context_manager.get_object(type_map[name]))
            return func(*args, **kwargs)
        return wrapper

    def _get_bindable_attributes(self, cls: type) -> dict:
        """Given a type, find all the bindable attributes using the annotations."""
        type_map = {}
        check_me = [cls, *cls.__mro__]
        for check_cls in check_me:
            if hasattr(check_cls, "__annotations__"):
                for k in check_cls.__annotations__:
                    if k not in type_map:
                        type_map[k] = check_cls.__annotations__[k]
        return type_map

    def _bind_parameters(self, func: callable, args: tuple, kwargs: dict):
        """ Inspects the given callable object and builds a new set of arguments for it with dependencies injected

            :param func: The callable to inspect
            :param args: Original positional arguments
            :param kwargs: Original keyword arguments

            :returns: A tuple of a list and a dict corresponding to updated positional and keyword arguments
            :rtype: tuple(list, dict)
        """

        # Inspect the object
        func_sig = inspect.signature(func)

        # Store the actual arguments to use here
        real_args = []
        real_kwargs = {}

        # Track the current positional argument we are working on
        arg_index = 0

        # If we encounter *args, we note that extra positional arguments can be passed.
        load_extra_args = False
        # If we encounter **kwargs, we note that extra keyword arguments can be passed.
        load_extra_kwargs = False

        # Process all the function parameters
        for parameter_name in func_sig.parameters:
            param = func_sig.parameters[parameter_name]

            # Variable-length positional argument (typically *args)
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                load_extra_args = True

            # Variable-length keyword argument (typically **kwargs)
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                load_extra_kwargs = True

            # Special handling for the "self" parameter
            # Note that this should be fixed so that it could be named anything
            elif param.name == "self" and arg_index == 0:
                real_args.append(args[arg_index])
                arg_index += 1

            # All other cases may need dependencies injected
            else:

                # Check if we can accept a keyword argument
                allow_kwarg = not param.kind == inspect.Parameter.POSITIONAL_ONLY

                # Check if we can accept a positional argument
                allow_arg = not param.kind == inspect.Parameter.KEYWORD_ONLY

                real_value = None

                # If a keyword argument was specified, we will use it.
                # If this type-hint was injectable, this just means we will use the object passed instead.
                if allow_kwarg and param.name in kwargs:
                    real_value = kwargs[param.name]
                    del kwargs[param.name]

                # If the type-hint is injectable, we'll inject it
                # Note that we don't let injectables be overridden by positional argments as this would create too
                # much confusion with the signature
                elif param.annotation and self.cls_registry.is_injectable(param.annotation):
                    real_value = self.context_manager.get_object(param.annotation)

                # Handle a positional argument
                elif allow_arg and arg_index < len(args):
                    real_value = args[arg_index]
                    arg_index += 1

                # Handle arguments with defaults
                elif not param.default == inspect.Parameter.empty:
                    real_value = param.default

                # An argument is missing if we get to this point
                else:
                    raise MissingArgumentError(param.name)

                # Insert it as positional if we are allowed, to not mess-up the positional argument list
                if allow_arg:
                    real_args.append(real_value)

                # Otherwise, it's a keyword argument
                else:
                    real_kwargs[param.name] = real_value

        # Handle extra positional arguments
        if arg_index < len(args):
            if load_extra_args:
                real_args.extend(args[arg_index:])
            else:
                raise ExtraPositionalArgumentsError()

        # Handle extra keyword arguments
        if kwargs:
            if load_extra_kwargs:
                real_kwargs.update(kwargs)
            else:
                raise ExtraKeywordArgumentsError()
            kwargs = {}
        return real_args, real_kwargs

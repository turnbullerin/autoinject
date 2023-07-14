""" Main class for injection tools

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import inspect
import sys
import threading
from functools import wraps
import contextvars
import typing as t

from .context_manager import ContextManager
from .class_registry import ClassRegistry, CacheStrategy
from .informants import ContextVarManager

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
        self._members_cache = {}
        self.cls_registry = ClassRegistry(self)
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

    def test_case(self, fixtures_or_fn: t.Union[callable, dict, None] = None) -> callable:
        """Decorate a test case to get a separate global context and to provide fixtures."""
        if isinstance(fixtures_or_fn, dict) or fixtures_or_fn is None:
            def outer_wrapper(fn):
                return self._test_case_wrapper(fn, fixtures_or_fn)
            return outer_wrapper
        return self._test_case_wrapper(fixtures_or_fn, None)

    def with_fixture(self, fixture_cls, fixture_obj_or_type=None, fixture_callback=None):
        """Register a feature object, type, or callback as a fixture"""
        if fixture_obj_or_type is None and fixture_callback is None:
            raise ValueError("One of fixture object or callback must be provided")

        def outer_wrapper(fn):
            if not hasattr(fn, "_autoinject_fixtures"):
                fn._autoinject_fixtures = {}
            fn._autoinject_fixtures[fixture_cls] = (fixture_obj_or_type, fixture_callback)
            return fn
        return outer_wrapper

    def _test_case_wrapper(self, fn: callable, fixtures: dict = None) -> callable:
        """Handle creating a separate global context and test fixtures"""
        @wraps(fn)
        def inner_wrapper(*args, **kwargs):
            # This creates an entirely different GLOBAL context as well local context, so
            # that test cases can be truly independent of the shared global state.
            with self.context_manager.subcontext() as ctx:
                _fixtures = {} if not hasattr(fn, "_autoinject_fixtures") else fn._autoinject_fixtures
                if fixtures:
                    _fixtures.update(fixtures)
                for cls_name, cls_obj in _fixtures.items():
                    cls_callback = None
                    if (isinstance(cls_obj, tuple) or isinstance(cls_obj, list)) and len(cls_obj) > 1:
                        cls_callback = cls_obj[1]
                        cls_obj = cls_obj[0]
                    if cls_callback is not None:
                        self.cls_registry.register(cls_name, constructor=cls_callback, _force_override=True)
                    elif isinstance(cls_obj, type) or isinstance(cls_obj, str):
                        self.cls_registry.register(cls_name, constructor=cls_obj, _force_override=True)
                    else:
                        self.cls_registry.register(cls_name, constructor=lambda: cls_obj, _force_override=True)
                return fn(*args, **kwargs)
        return inner_wrapper

    def ContextVars(self, context: t.Union[contextvars.Context, ContextVarManager, str, None] = "_default", suppress_exit_warning: bool = False):
        """Use as a context manager for managing an area where all context_cache injectables are the same."""
        return ContextVarManager(self.context_manager.contextvar_info, context, suppress_exit_warning=suppress_exit_warning)

    def cv_freshen(self, context: contextvars.Context = None):
        """Freshen the context var to get a new context and return the old one"""
        return ContextVarManager.freshen_context(context)

    def cv_restore(self, token, context: contextvars.Context = None):
        """Restore the context var to what it was"""
        ContextVarManager.restore_context_id(token, context)

    def cv_cleanup(self, context: contextvars.Context = None):
        """Clean up the cache for the current contextvars context or the given one"""
        self.context_manager.contextvar_info.destroy_self(context)

    def cv_touch(self, context: contextvars.Context = None):
        """Touch the contextvar for autoinjector to ensure it exists."""
        ContextVarManager.ensure_context_id(context)

    def thread_cleanup(self, thread: threading.Thread = None):
        """Clean-up after a thread (or the current one)"""
        self.context_manager.thread_info.destroy_self(thread)

    def with_contextvars(self, context_mode: t.Union[str, callable, None] = "_default", suppress_exit_warning: bool = False):
        """Decorate a function to give it a new contextvars context (see .ContextVars) and cleanup after."""
        if callable(context_mode):
            return self._injector_wrap(context_mode, with_contextvars=True, context_mode="_default", suppress_exit_warning=suppress_exit_warning)
        else:
            return self.inject(with_contextvars=True, context_mode=context_mode)

    def with_empty_contextvars(self, fn):
        """Create a new empty context to run this in"""
        return self._injector_wrap(fn, with_contextvars=True, context_mode="empty")

    def with_same_contextvars(self, fn):
        """Use the same context to run this in"""
        return self._injector_wrap(fn, with_contextvars=True, context_mode="same")

    def async_with_contextvars(self, context_mode: t.Union[str, callable, None] = "_default"):
        """Decorate a function to give it a new contextvars context (see .ContextVars) and cleanup after."""
        if callable(context_mode):
            return self._async_injector_wrap(context_mode, with_contextvars=True, context_mode="_default")
        else:
            return self.async_inject(with_contextvars=True, context_mode=context_mode)

    def async_with_empty_contextvars(self, fn):
        """Create a new empty context to run this in"""
        return self._async_injector_wrap(fn, with_contextvars=True, context_mode="empty")

    def async_with_same_contextvars(self, fn):
        """Use the same context to run this in"""
        return self._async_injector_wrap(fn, with_contextvars=True, context_mode="same")

    def as_thread_run(self, fn):
        """Decorate a threading.Thread.run() method to ensure its context variables are cleaned up."""
        return self._injector_wrap(fn, as_thread_run=True)

    def register_informant(self, context_informant):
        """ Wrapper around :meth:`autoinject.context_manager.ContextManager.register_informant` """
        self.context_manager.register_informant(context_informant)

    def register_constructor(self, cls_name, constructor, *args, **kwargs):
        """ Wrapper around :meth:`autoinject.class_registry.ClassRegistry.register_class` """
        clear_cache = self.cls_registry.is_injectable(cls_name)
        self.cls_registry.register(cls_name, *args, constructor=constructor, **kwargs)
        if clear_cache:
            self.context_manager.clear_cache(cls_name)
        self._members_cache = {}

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

    def inject(self, func=None, *, with_contextvars: bool = False, context_mode="_default", as_thread_run: bool = False):
        """Function or method decorator responsible for injecting dependencies into the argument list. A dependency is
        defined as a parameter with a type-hint that has been registered. To make sure your IDE code-completion works
        properly, it is recommended to place these at the end of the argument list and to give them a default value of
        None.

        ::

            @injector.inject
            def my_function(some_param, injected_param: MyClass = None):
                pass

        """
        if func is None:
            def inner_decorator(func):
                return self._injector_wrap(func, with_contextvars, context_mode, as_thread_run)
            return inner_decorator
        else:
            return self._injector_wrap(func, with_contextvars, context_mode, as_thread_run)

    def async_inject(self, func=None, *, with_contextvars: bool = False, context_mode="_default"):
        """Function or method decorator responsible for injecting dependencies into the argument list. A dependency is
        defined as a parameter with a type-hint that has been registered. To make sure your IDE code-completion works
        properly, it is recommended to place these at the end of the argument list and to give them a default value of
        None.

        ::

            @injector.inject
            def my_function(some_param, injected_param: MyClass = None):
                pass

        """
        if func is None:
            def inner_decorator(func):
                return self._async_injector_wrap(func, with_contextvars, context_mode)
            return inner_decorator
        else:
            return self._async_injector_wrap(func, with_contextvars, context_mode)

    def _async_injector_wrap(self, func, with_contextvars: bool = False, context_mode="_default"):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if with_contextvars:
                with ContextVarManager(self.context_manager.contextvar_info, context_mode) as ctx:
                    new_args, new_kwargs = self._bind_parameters(func, args, kwargs, ctx)
                    return await ctx.run(func, *new_args, **new_kwargs)
            else:
                new_args, new_kwargs = self._bind_parameters(func, args, kwargs)
                return await func(*new_args, **new_kwargs)
        return wrapper

    def _injector_wrap(self, func, with_contextvars: bool = False, context_mode="_default", as_thread_run: bool = False, suppress_exit_warning: bool = False):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                if with_contextvars:
                    with ContextVarManager(self.context_manager.contextvar_info, context_mode, suppress_exit_warning=suppress_exit_warning) as ctx:
                        new_args, new_kwargs = self._bind_parameters(func, args, kwargs, ctx)
                        return ctx.run(func, *new_args, **new_kwargs)
                else:
                    new_args, new_kwargs = self._bind_parameters(func, args, kwargs)
                    return func(*new_args, **new_kwargs)
            finally:
                if as_thread_run:
                    self.thread_cleanup()
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
            for attr_name, attr_type in self._get_bindable_members(obj.__class__):
                if getattr(obj, attr_name) is None:
                    setattr(obj, attr_name, self.context_manager.get_object(attr_type))
            return func(*args, **kwargs)
        return wrapper

    def _get_bindable_members(self, cls: type) -> list[str, t.Union[type, str]]:
        """Given a type, find all members we should check"""
        if cls not in self._members_cache:
            self._members_cache[cls] = []
            type_map = self._get_bindable_attributes(cls)
            for name, _ in inspect.getmembers(cls):
                if name[0:2] == "__":
                    continue
                if name not in type_map:
                    continue
                if not self.cls_registry.is_injectable(type_map[name]):
                    continue
                self._members_cache[cls].append((name, type_map[name]))
        return self._members_cache[cls]

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

    def _bind_parameters(self, func: callable, args: tuple, kwargs: dict, ctx=None):
        """ Inspects the given callable object and builds a new set of arguments for it with dependencies injected

            :param func: The callable to inspect
            :param args: Original positional arguments
            :param kwargs: Original keyword arguments
            :param ctx: The context to inject

            :returns: A tuple of a list and a dict corresponding to updated positional and keyword arguments
            :rtype: tuple(list, dict)
        """

        # Inspect the object
        func_sig = inspect.signature(func)

        # Allowed context injection types
        context_allowed = [] if ctx is None else [
            self.cls_registry.cls_to_str(contextvars.Context),
            self.cls_registry.cls_to_str(ContextVarManager)
        ]

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

                # If we are expecting a context variable and the context was provided
                # we can auto inject over contextvars.Context or the local ContextVarsManager class
                elif ctx is not None and param.annotation and self.cls_registry.cls_to_str(param.annotation) in context_allowed:
                    real_value = ctx

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

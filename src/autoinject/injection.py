""" Main class for injection tools

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import enum
import functools
import sys
import threading
import warnings
from functools import wraps
import contextvars
import typing as t
from types import EllipsisType

from autoinject.debug import debug
from autoinject.user import DelayedParameter
from autoinject.cache_manager import CacheManager, SituationInformant
from autoinject.class_registry import ClassRegistry, CacheStrategy
from autoinject.informants import ContextVarManager
import autoinject.reflect as reflect
import autoinject.types as ait

if sys.version_info.major == 3 and sys.version_info.minor < 10:
    from importlib.metadata import entry_points as _entry_points
    from importlib.metadata import EntryPoint

    def entry_points(*, group: str, **kwargs) -> t.List[EntryPoint]:
        eps = _entry_points(**kwargs)
        if group in eps:
            return t.cast(list, eps[group])
        return []

else:
    from importlib.metadata import entry_points as _entry_points
    from importlib.metadata import EntryPoint

    def entry_points(*, group: str, **kwargs) -> t.List[EntryPoint]:
        return t.cast(list, _entry_points(group=group, **kwargs))

P = t.ParamSpec('P')
Q = t.TypeVar('Q')
C = t.TypeVar('C', bound=ait.ContextProtocol)
D = t.TypeVar('D', bound=ait.DelayedProtocol)

class CallMode(enum.Enum):
    UNKNOWN = 0
    METHOD = 1
    CLASS_METHOD = 2
    STATIC = 3

class _InjectWrapper:

    def __init__(self, c: t.Optional[ait.InjectableFunction], injector: "InjectionManager"):
        self.injector: "InjectionManager" = injector
        self.call_mode: CallMode = CallMode.UNKNOWN
        self._call: t.Optional[ait.InjectableFunctionProtocol] = None
        if c is not None:
            self.call = t.cast(ait.InjectableFunctionProtocol, c)
        self.as_thread_run: bool = False
        self.as_test_case: bool = False
        self.test_fixtures: t.Optional[t.Dict[ait.InjectableType, t.Union[t.Callable, type]]] = None
        self.with_contextvars: bool = False
        self.suppress_exit_warning: bool = False
        self.context_mode: t.Union[ContextVarManager, ait.ContextMode] = "_default"

    @property
    def call(self) -> ait.InjectableFunctionProtocol:
        if self._call is None:
            debug("No callable method set", debug_type="injection")
            raise TypeError('call is not set')
        return self._call

    @call.setter
    def call(self, c: t.Optional[ait.InjectableFunction]):
        if isinstance(c, classmethod):
            self._call = t.cast(t.Callable, c.__func__)
            self.call_mode = CallMode.CLASS_METHOD
            debug("Call mode set to CLASS_METHOD, function [%s]", self._call, debug_type="injection")
        elif isinstance(c, staticmethod):
            self._call = t.cast(t.Callable, c.__func__)
            self.call_mode = CallMode.STATIC
            debug("Call mode set to STATIC, function [%s]", self._call, debug_type="injection")
        elif c is not None:
            self._call = c
            self.call_mode = CallMode.UNKNOWN
            debug("Call mode set to UNKNOWN, function [%s]", self._call, debug_type="injection")

    def set_call_if_none(self, c: ait.InjectableFunction) -> bool:
        if self._call is None and c is not None:
            self.call = t.cast(ait.InjectableFunctionProtocol, c)  # classmethod and staticmethod will be stripped out by the setter
            return True
        return False

    def __get__(self, instance, owner):
        if self.call_mode is CallMode.CLASS_METHOD:
            debug("Building partial function for class method [%s] on [%s]", self._call, owner.__class__, debug_type="injection")
            return functools.partial(self.__call__, owner)
        elif self.call_mode is CallMode.STATIC:
            debug("Building function for static method [%s] on [%s]", self._call, owner.__class__, debug_type="injection")
            return self.__call__
        else:
            debug("Building partial function for instance method [%s] on [%s]", self._call, owner, debug_type="injection")
            return functools.partial(self.__call__, instance)

    def __call__(self, *args, **kwargs):
        if self._call is None:
            debug("Called without parameters setting _call to [%s]", args[0], debug_type="injection")
            self.call = args[0]
            return functools.wraps(args[0])(self)
        elif self.test_fixtures or self.as_test_case:
            return self._call_with_text_fixtures(args, kwargs)
        else:
            return self._call_with_injection(args, kwargs)

    def _call_with_injection(self, args, kwargs):
        try:
            args = list(args)
            if self.with_contextvars:
                debug("Called with contextvars [%s]", self._call, debug_type="injection")
                with ContextVarManager(self.injector.cache_manager.contextvar_info, self.context_mode,
                                       suppress_exit_warning=self.suppress_exit_warning) as ctx:
                    self._inject_parameters(args, kwargs, ctx)
                    return ctx.run(self.call, *args, **kwargs)
            else:
                self._inject_parameters(args, kwargs)
                return self.call(*args, **kwargs)
        finally:
            if self.as_thread_run:
                debug("Cleaning up thread cache after [%s]", self._call, debug_type="injection")
                self.injector.cache_manager.thread_info.destroy_self()

    def _call_with_text_fixtures(self, args, kwargs):
        debug("Running as test case", debug_type="injection")
        with self.injector.cache_manager.subcontext() as ctx:
            if self.test_fixtures:
                for cls_name, cls_obj in self.test_fixtures.items():
                    debug("Registering test case fixture [%s] as [%s]", cls_obj, cls_name, debug_type="injection")
                    if isinstance(cls_obj, type) or callable(cls_obj):
                        ctx.cls_registry.register(cls_name, constructor=cls_obj, weight=sys.maxsize)
                    else:
                        ctx.cls_registry.register(cls_name, constructor=lambda: cls_obj, weight=sys.maxsize)
            return self._call_with_injection(args, kwargs)

    def _inject_parameters(self, args: list, kwargs: dict, ctx=None):
        """ Updates the arguments and keyword arguments based on the list of ParameterReplacements

            :param args: Original positional arguments
            :param kwargs: Original keyword arguments
            :param ctx: The context to inject

            :returns: A tuple of a list and a dict corresponding to updated positional and keyword arguments
            :rtype: tuple(list, dict)
        """
        parameters: t.List[reflect.ParameterReplacement] = self.injector.cls_registry.get_injectable_parameters(self.call)
        for parameter in parameters:
            parameter.apply(args, kwargs)
        self.injector.resolve_delayed(args, self.call, ctx)
        self.injector.resolve_delayed(kwargs, self.call, ctx)


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

    def __init__(self, include_entry_points: bool = True):
        """ Constructor """
        self.cls_registry = ClassRegistry()
        self.cache_manager = CacheManager(self.cls_registry)

        # Register the class registry for injection, using the local instance
        self.cls_registry.register(
            ClassRegistry,
            constructor=lambda: self.cls_registry,
            caching_strategy=CacheStrategy.GLOBAL_CACHE
        )

        # Same but for context manager
        self.cls_registry.register(
            CacheManager,
            constructor=lambda: self.cache_manager,
            caching_strategy=CacheStrategy.GLOBAL_CACHE
        )

        # Same but for self
        self.cls_registry.register(
            InjectionManager,
            constructor=lambda: self,
            caching_strategy=CacheStrategy.GLOBAL_CACHE
        )

        self.cls_registry.register_delayed_parameter(DelayedParameter)
        self.cls_registry.register_context(ContextVarManager)
        self.cls_registry.register_context(contextvars.Context)

        if include_entry_points and entry_points is not None:

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

    def register_informant(self, context_informant: SituationInformant):
        """ Wrapper around :meth:`autoinject.context_manager.ContextManager.register_informant` """
        self.cache_manager.register_informant(context_informant)

    def unregister_constructor(self, cls_name: t.Union[str, type], constructor: t.Union[t.Callable[..., t.Any], ait.InjectableType]):
        self.cls_registry.unregister(cls_name, constructor)

    @t.overload
    def register_constructor(self, cls_name: t.Type[Q], constructor: t.Union[t.Callable[..., Q], ait.InjectableType, None], *args, **kwargs): ...

    @t.overload
    def register_constructor(self, cls_name: str, constructor: t.Union[t.Callable[..., t.Any], ait.InjectableType, None] , *args, **kwargs): ...

    def register_constructor(self, cls_name: t.Union[t.Type[Q], str], constructor: t.Union[t.Callable[..., t.Any], ait.InjectableType, None], *args, **kwargs):
        """ Wrapper around :meth:`autoinject.class_registry.ClassRegistry.register_class` """
        clear_cache = self.cls_registry.is_injectable(cls_name)
        self.cls_registry.register(cls_name, *args, constructor=constructor, **kwargs)
        if clear_cache:
            self.cache_manager.clear_cache(cls_name)

    def alias(self, actual_cls: t.Union[str, type], alias_as: t.Optional[t.Union[str, type]] = None):
        if alias_as is None:
            def _outer(cls: t.Type[Q]) -> t.Type[Q]:
                self.cls_registry.register_alias(actual_cls, cls)
                return cls
            return _outer
        else:
            self.cls_registry.register_alias(actual_cls, alias_as)

    @staticmethod
    def with_cache_strategy(cache_strategy: CacheStrategy) -> t.Callable[[t.Type[Q]], t.Type[Q]]:
        def _outer(cls: t.Type[Q]) -> t.Type[Q]:
            setattr(cls, 'AUTOINJECT_CACHE_STRATEGY', cache_strategy)
            return cls
        return _outer

    @staticmethod
    def with_ignore_informants(informants: t.List[str]) -> t.Callable[[t.Type[Q]], t.Type[Q]]:
        def _outer(cls: t.Type[Q]) -> t.Type[Q]:
            setattr(cls, 'AUTOINJECT_IGNORE_INFORMANTS', informants)
            return cls
        return _outer

    @staticmethod
    def as_weakref(cls: t.Type[Q]) -> t.Type[Q]:
        setattr(cls, 'AUTOINJECT_AS_WEAKREF', True)
        return cls

    @staticmethod
    def with_weight(weight: int) -> t.Callable[[t.Type[Q]], t.Type[Q]]:
        def _outer(cls: t.Type[Q]) -> t.Type[Q]:
            setattr(cls, 'AUTOINJECT_WEIGHT', weight)
            return cls
        return _outer

    @t.overload
    def register(self, cls_name: t.Type[Q], *args, **kwargs) -> t.Callable[[t.Type[Q]], t.Type[Q]]: ...

    @t.overload
    def register(self, cls_name: str, *args, **kwargs) -> t.Callable[..., t.Any]: ...

    @t.overload
    def register(self, cls_name: None = None, *args, **kwargs) -> t.Callable[..., t.Any]: ...

    def register(self, cls_name: t.Optional[ait.InjectableType] = None, *args, **kwargs) -> t.Union[t.Callable[[t.Type[Q]], t.Type[Q]], t.Callable[..., t.Any]]:
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
            self.register_constructor(cls_name or constructor, constructor, *args, **kwargs)
            return constructor
        return outer_wrap

    @t.overload
    def override(self, cls_name: t.Type[Q], new_constructor: t.Union[t.Callable[..., Q], type, None], *args, **kwargs): ...

    @t.overload
    def override(self, cls_name: str, new_constructor: t.Union[t.Callable[..., t.Any], type, None], *args, **kwargs): ...

    def override(self, cls_name: t.Union[t.Type[Q], str], new_constructor: t.Union[t.Callable[..., t.Any], type, None], *args, **kwargs):
        """ Override one class with another. """
        self.register_constructor(cls_name, new_constructor, *args, **kwargs)

    def register_delayed_parameter(self, cls: t.Type[D]) -> t.Type[D]:
        self.cls_registry.register_delayed_parameter(cls)
        return cls

    def register_context(self, cls: t.Type[C]) -> t.Type[C]:
        self.cls_registry.register_context(cls)
        return cls

    @t.overload
    def get(self, cls_name: t.Type[Q]) -> Q: ...

    @t.overload
    def get(self, cls_name: str) -> t.Any: ...

    def get(self, cls_name: ait.InjectableType) -> t.Any:
        """ Wrapper around :meth:`autoinject.context_manager.ContextManager.get_object` """
        return self.cache_manager.get_object(cls_name)

    def resolve_delayed(self,
                        objs: t.Union[t.List[t.Any], t.Dict[str, t.Any]],
                        f: ait.SupportsInjection,
                        ctx: t.Optional[t.Union[ContextVarManager, contextvars.Context]] = None):
        if isinstance(objs, list):
            for idx, obj in enumerate(objs):
                if self.cls_registry.is_delayed_parameter(obj):
                    objs[idx] = obj.resolve(self, f, ctx)
        else:
            for key in list(objs.keys()):
                obj = objs[key]
                if self.cls_registry.is_delayed_parameter(obj):
                    objs[key] = obj.resolve(self, f, ctx)

    @staticmethod
    def resolve_annotation(cls_or_func: ait.SupportsInjection, annotation: ait.InjectableType):
        return reflect.resolve_annotation(cls_or_func, annotation)

    def injectable(self, cls: t.Type[Q]) -> t.Type[Q]:
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

    def injectable_global(self, cls: t.Type[Q]) -> t.Type[Q]:
        """injectable_global()

        Class decorator for basic registration of injectable objects that don't require external input, but with
        a global scope.
        """
        self.register_constructor(cls, None, caching_strategy=CacheStrategy.GLOBAL_CACHE)
        return cls

    def injectable_nocache(self, cls: t.Type[Q]) -> t.Type[Q]:
        """injectable_nocache()

        Class decorator for basic registration of injectable objects that don't require external input, but with
        no caching.
        """
        self.register_constructor(cls, None, caching_strategy=CacheStrategy.NO_CACHE)
        return cls

    def thread_cleanup(self, thread: t.Optional[threading.Thread] = None):
        """Clean-up after a thread (or the current one)"""
        self.cache_manager.thread_info.destroy_self(thread)

    def ContextVars(self, context: t.Union[ContextVarManager, ait.ContextMode] = None, suppress_exit_warning: bool = False) -> ContextVarManager:
        """Use as a context manager for managing an area where all context_cache injectables are the same."""
        return ContextVarManager(self.cache_manager.contextvar_info, context, suppress_exit_warning=suppress_exit_warning)

    def cv_freshen(self, context: t.Optional[contextvars.Context] = None) -> contextvars.Token:
        """Freshen the context var to get a new context and return the old one"""
        return ContextVarManager.freshen_context(context)

    def cv_restore(self, token: contextvars.Token, context: t.Optional[contextvars.Context] = None):
        """Restore the context var to what it was"""
        ContextVarManager.restore_context_id(token, context)

    def cv_cleanup(self, context: t.Optional[contextvars.Context] = None):
        """Clean up the cache for the current contextvars context or the given one"""
        self.cache_manager.contextvar_info.destroy_self(context)

    def cv_touch(self, context: t.Optional[contextvars.Context] = None):
        """Touch the contextvar for autoinjector to ensure it exists."""
        ContextVarManager.ensure_context_id(context)

    def as_thread_run(self, fn: t.Union[t.Callable[P,Q], _InjectWrapper]) -> t.Callable:
        """Decorate a threading.Thread.run() method to ensure its context variables are cleaned up."""
        return self.build_injector_wrapper(fn, as_thread_run=True)

    @t.overload
    def with_contextvars(self, obj: t.Union[t.Callable[P,Q], _InjectWrapper]) -> t.Callable: ...

    @t.overload
    def with_contextvars(self, *, context_mode: t.Union[ait.ContextMode, ContextVarManager], suppress_exit_warning: bool = False) -> t.Callable: ...

    def with_contextvars(self,
                         obj: t.Union[t.Callable[P,Q], _InjectWrapper, None] = None,
                         *,
                         context_mode: t.Union[ait.ContextMode, ContextVarManager] = "_default",
                         suppress_exit_warning: bool = False) -> t.Callable:
        """Decorate a function to give it a new contextvars context (see .ContextVars) and cleanup after."""
        return self.build_injector_wrapper(obj, with_contextvars=True, context_mode=context_mode, suppress_exit_warning=suppress_exit_warning)

    def with_empty_contextvars(self, fn: t.Union[t.Callable[P,Q], _InjectWrapper]) -> t.Callable:
        """Create a new empty context to run this in"""
        return self.build_injector_wrapper(fn, with_contextvars=True, context_mode="empty")

    def with_same_contextvars(self, fn: t.Union[t.Callable[P,Q], _InjectWrapper]) -> t.Callable:
        """Use the same context to run this in"""
        return self.build_injector_wrapper(fn, with_contextvars=True, context_mode="same")

    def build_injector_wrapper(self,
                               f: t.Union[ait.InjectableFunction, _InjectWrapper, None] = None,
                               test_fixtures: t.Optional[t.Dict[ait.InjectableType, t.Callable]] = None,
                               **kwargs) -> t.Callable:
        iw: _InjectWrapper
        if isinstance(f, _InjectWrapper):
            iw = f
        elif isinstance(f, (classmethod, staticmethod)):
            iw = t.cast(_InjectWrapper, functools.wraps(f.__func__)(_InjectWrapper(f, self)))
        elif f is None:
            iw = _InjectWrapper(None, self)
        elif callable(f):
            iw = t.cast(_InjectWrapper, functools.wraps(f)(_InjectWrapper(f, self)))
        else:
            raise ValueError("Invalid object to wrap")
        for key in kwargs:
            if key is not ...:
                setattr(iw, key, kwargs[key])
        if test_fixtures:
            if iw.test_fixtures is None:
                iw.test_fixtures = test_fixtures
            else:
                iw.test_fixtures.update(test_fixtures)
        return iw

    @t.overload
    def inject(self,
               *,
               with_contextvars: bool = False,
               context_mode: t.Union[ContextVarManager, ait.ContextMode] = "_default",
               as_thread_run: bool = False,
               suppress_exit_warning: bool = False) -> t.Callable: ...

    @t.overload
    def inject(self,
               func: t.Union[t.Callable[P,Q], _InjectWrapper],
               *,
               with_contextvars: bool = False,
               context_mode: t.Union[ContextVarManager, ait.ContextMode] = "_default",
               as_thread_run: bool = False,
               suppress_exit_warning: bool = False) -> t.Callable: ...

    def inject(self,
               func: t.Union[ait.InjectableFunction, _InjectWrapper, None] = None,
               *,
               with_contextvars: bool = False,
               context_mode: t.Union[ContextVarManager, ait.ContextMode] = "_default",
               as_thread_run: bool = False,
               suppress_exit_warning: bool = False) -> t.Callable:
        """Function or method decorator responsible for injecting dependencies into the argument list. A dependency is
        defined as a parameter with a type-hint that has been registered. To make sure your IDE code-completion works
        properly, it is recommended to place these at the end of the argument list and to give them a default value of
        None.

        ::

            @injector.inject
            def my_function(some_param, injected_param: MyClass = None):
                pass

        """
        return self.build_injector_wrapper(func, with_contextvars=with_contextvars, context_mode=context_mode, as_thread_run=as_thread_run, suppress_exit_warning=suppress_exit_warning)

    @t.overload
    def construct(self, func: t.Callable[P, None]) -> t.Callable[P, None]:...

    @t.overload
    def construct(self, func: t.Type[Q]) -> t.Type[Q]: ...

    def construct(self, func: t.Union[t.Callable[P, None], t.Type[Q]]) -> t.Union[t.Callable[P, None], t.Type[Q]]:
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
        if isinstance(func, type):
            if hasattr(func, '__init__'):
                func.__init__ = self.construct(func.__init__)  # type: ignore # is fine since we're just wrapping it.
            else: # pragma: no coverage # this doesn't happen AFAIK, but its here just in case there's an edge case I can't find
                raise TypeError('Cannot wrap type that does not have an __init__')
            return func
        else:
            @wraps(func)
            def wrapper(*args, **kwargs):
                obj = args[0]  # self
                injectables = self.cls_registry.get_injectable_attributes(obj.__class__)
                for attribute in injectables:
                    if (not hasattr(obj, attribute.name)) or getattr(obj, attribute.name) in (..., None):
                        setattr(obj, attribute.name, attribute.default)
                self.resolve_delayed(obj.__dict__, obj.__class__)
                func(*args, **kwargs)
            return wrapper

    @t.overload
    def test_case(self, fixtures_or_fn: t.Union[t.Callable[P,Q], _InjectWrapper]) -> t.Callable: ...

    @t.overload
    def test_case(self, fixtures_or_fn: t.Type[Q]) -> t.Type[Q]: ...

    @t.overload
    def test_case(self, fixtures_or_fn: t.Optional[t.Dict[t.Union[type, str], ait.TestFixtureBuilderType]] = None) -> t.Callable: ...

    def test_case(self, fixtures_or_fn: t.Union[t.Type[Q], t.Callable[P,Q], _InjectWrapper, t.Dict[t.Union[type, str], ait.TestFixtureBuilderType], None] = None) -> t.Union[t.Callable, t.Type[Q]]:
        """Decorate a test case to get a separate global context and to provide fixtures."""
        if isinstance(fixtures_or_fn, dict) or fixtures_or_fn is None:
            return self.build_injector_wrapper(None, test_fixtures=fixtures_or_fn, as_test_case=True)
        else:
            return self.build_injector_wrapper(fixtures_or_fn, as_test_case=True)

    def with_fixture(self,
                     fixture_cls: ait.InjectableType,
                     fixture_constructor: t.Any = None,
                     **kwargs) -> t.Callable:
        """Register a feature object, type, or callback as a fixture"""
        if fixture_constructor is None:
            if 'fixture_callback' in kwargs:
                warnings.warn('fixture_callback will be removed soon, use fixture_constructor instead', DeprecationWarning)
                fixture_constructor = kwargs['fixture_callback']
        if fixture_constructor is None:
            raise TypeError("You must pass a constructor")
        return self.build_injector_wrapper(None, test_fixtures={
            fixture_cls: fixture_constructor
        }, as_test_case=True)

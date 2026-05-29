""" The class registry stores which objects can be injected and how to
    maintain cache control over them.

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import dataclasses
import enum
import threading
import typing as t
from types import EllipsisType


import autoinject.types as ait
import autoinject.reflect as reflect
from autoinject.reflect import AttributeReplacement
from autoinject.debug import debug

if t.TYPE_CHECKING:   # pragma: no coverage # TYPE_CHECKING
    import autoinject


class CacheStrategy(enum.Enum):
    """ Defines how caching should be managed for this object """

    NO_CACHE = 1
    """ No caching allowed. Specify this when instances of the object should not be shared."""

    GLOBAL_CACHE = 2
    """ A single instance of the object is allowed. Specify this for thread-safe objects that can manage a single global
        instance even in a multi-threaded environment. 
        """

    CONTEXT_CACHE = 3
    """ A single instance of the object is allowed per context. What a context is can vary by application; for example,
        in the context of a WSGI application, each request might be an individual context. Specify this when each thread
        or context might need its own copy of the object. 
    """


class ClassNotFoundException(ValueError):
    """ Raised when a class is requested that has not been registered.

        :param cls_name: Name of the class not found in the registry
        :type cls_name: str
    """

    def __init__(self, cls_name: str):
        """ Constructor """
        super().__init__("Object {} not registered for injection".format(cls_name))

T = t.TypeVar("T")

@dataclasses.dataclass
class InjectableConstructor(t.Generic[T]):
    constructor: t.Callable[..., T]
    args: t.Sequence
    kwargs: dict
    weight: int
    strategy: CacheStrategy
    ignore_informants: t.Optional[t.List[str]] = None
    as_weakref: bool = False

    def copy(self):
        return InjectableConstructor(
            constructor=self.constructor,
            args=[x for x in self.args],
            kwargs={x: self.kwargs[x] for x in self.kwargs},
            weight=self.weight,
            strategy=self.strategy,
            ignore_informants=[x for x in self.ignore_informants] if self.ignore_informants is not None else None,
            as_weakref=self.as_weakref

        )

    def __str__(self):   # pragma: no coverage # debugging only
        arg_out = [str(x) for x in self.args]
        arg_out.extend(f"{x}={self.kwargs[x]}" for x in self.kwargs)
        properties = [
            f"weight={self.weight}",
            f"cache_strategy={self.strategy.value if self.strategy else 'inherit'}",
            f"as_weakref={self.as_weakref}",
        ]
        if self.ignore_informants is not None and self.ignore_informants is not ...:
            properties.append(f"no_inform={','.join(self.ignore_informants)}")
        return f"{self.constructor}({','.join(arg_out)});{';'.join(properties)}"

    def __call__(self) -> T:
        return self.constructor(*self.args, **self.kwargs)


@dataclasses.dataclass
class InjectableInfo:
    constructors: t.List[InjectableConstructor]

    def __str__(self):   # pragma: no coverage # debugging only
        ignores = ''
        return f"<strategy=no_inform={ignores};constructors:{len(self.constructors)}"

    def copy(self):
        return InjectableInfo(constructors=[c.copy() for c in self.constructors])

    def get_constructor(self) -> InjectableConstructor:
        best: t.Optional[InjectableConstructor] = None
        for x in self.constructors:
            if best is None or best.weight < x.weight:
                best = x
        if best is None:
            raise TypeError("Cannot find a non-abstract constructor")
        else:
            return best


@dataclasses.dataclass
class ClassInfo:
    cache_key: str
    strategy: CacheStrategy
    constructor: InjectableConstructor
    ignore_informants: t.Optional[t.List[str]] = None


class ClassRegistry:
    """ Manages a list of classes and how they can be instantiated. """

    def __init__(self: t.Self):
        """ Constructor """
        self.aliases: t.Dict[str, str] = {}
        self.object_constructors: t.Dict[str, InjectableInfo] = {}
        self._obj_lock = threading.Lock()

        self.delayed_parameters: t.Set[type] = set()
        self._dp_cache: t.Dict[type, bool] = dict()
        self._delayed_param_lock = threading.Lock()

        self.context_classes: t.Set[type] = set()
        self._context_cache: t.Dict[type, bool] = dict()
        self._context_lock = threading.Lock()

        self._attr_lock = threading.Lock()
        self.attr_cache: t.Dict[t.Hashable, t.List[reflect.AttributeReplacement]] = {}

        self._param_lock = threading.Lock()
        self.param_cache: t.Dict[t.Hashable, t.List[reflect.ParameterReplacement]] = {}


    def get_injectable_parameters(self, func: ait.InjectableFunction) -> t.List[reflect.ParameterReplacement]:
        """ Inspects the given callable object and gets a list of parameters that need to be managed.

            :param func: The callable to inspect
            :param cls_registry: The class registry to check for injectable or delayed parameters

            :returns: A list of ParameterReplacement objects
            :rtype: t.List[ParameterReplacement]
        """
        with self._param_lock:
            if func not in self.param_cache:
                iparams = reflect.get_injectable_parameters(func, self)
                self.param_cache[func] = iparams
                debug(f"Injectable parameters for [%s]: %s", func, iparams)
        return self.param_cache[func]

    def get_injectable_attributes(self, cls: type) -> t.List[AttributeReplacement]:
        """Given a type, find all members we should check for injection """
        with self._attr_lock:
            if cls not in self.attr_cache:
                iattrs = reflect.get_injectable_attributes(cls, self)
                self.attr_cache[cls] = iattrs
                debug(f"Injectable attributes for [%s]: %s", cls, iattrs)
        return self.attr_cache[cls]

    def register_alias(self, actual_cls: ait.InjectableType, alias_as: ait.InjectableType):
        with self._obj_lock:
            alias_str = self.cls_to_str(alias_as)
            cls_str = self.cls_to_str(actual_cls)
            self.aliases[alias_str] = cls_str
            debug("Aliased injectable type [%s] to [%s]", alias_str, cls_str, debug_type="registry")

    def is_context(self, cls: ait.InjectableType) -> bool:
        if isinstance(cls, type):
            if cls not in self._context_cache:
                self._is_context(cls)
            return self._context_cache[cls]
        return False

    def _is_context(self, cls: type):
        with self._context_lock:
            res = issubclass(cls, tuple(self.context_classes))
            debug("[%s] %s a context class", cls, "is" if res else "is not", debug_type="registry_check")
            self._context_cache[cls] = res

    def register_context(self, context_cls: t.Type[ait.SupportsContext]):
        with self._context_lock:
            cls_str = self.cls_to_type(context_cls)
            self.context_classes.add(cls_str)
            debug("Registered [%s] as a context class", cls_str, debug_type="registry")

    def is_delayed_parameter(self, obj: object) -> t.TypeGuard[ait.DelayedProtocol]:
        cls = obj.__class__
        if cls not in self._dp_cache:
            self._is_delayed_parameter(cls)
        return self._dp_cache[cls]

    def _is_delayed_parameter(self, cls: type):
        with self._delayed_param_lock:
            res = issubclass(cls, tuple(self.delayed_parameters))
            self._dp_cache[cls] = res
            debug("[%s] %s a delayed parameter", cls, "is" if res else "is not", debug_type="registry_check")

    def register_delayed_parameter(self, cls: t.Type[ait.ConcreteDelayedProtocol]):
        with self._delayed_param_lock:
            cls_str = self.cls_to_type(cls)
            self.delayed_parameters.add(cls_str)
            debug("Registered [%s] as a delayed parameter class", cls_str, debug_type="registry")

    @staticmethod
    def cls_to_str(cls: ait.InjectableType) -> str:
        """ Converts a type to a string that represents the fully-qualified name of the class.
        :param cls: Either a type to convert or a string representing the fully-qualified name of the class.
        :type cls: type OR str
        :return: Returns a string that could be used to import the class
        :rtype: str
        """
        if not isinstance(cls, str):
            return reflect.fqn(cls)
        return cls

    @staticmethod
    def cls_to_type(cls: ait.InjectableType) -> type:
        """ Converts a type to a string that represents the fully-qualified name of the class.
        :param cls: Either a type to convert or a string representing the fully-qualified name of the class.
        :type cls: type OR str
        :return: Returns a string that could be used to import the class
        :rtype: str
        """
        if not isinstance(cls, type):
            return t.cast(type, reflect.resolve_fqn(cls))
        return cls

    def is_injectable(self, cls: ait.InjectableType) -> bool:
        """ Checks if the given class is injectable

            :param cls: The class that is being checked
            :type cls: type OR str
            :return: Whether the class provided can be injected
            :rtype: bool
        """
        try:
            cls_str = self.cls_to_str(cls)
            with self._obj_lock:
                res = cls_str in self.object_constructors or cls_str in self.aliases
                debug("[%s] %s an injectable class", cls_str, "is" if res else "is not", debug_type="registry_check")
                return res
        except TypeError:
            return False

    def unregister(self, cls: ait.InjectableType, constructor: t.Union[t.Callable, type, str]):
        cls_str = self.cls_to_str(cls)
        real_constructor: t.Union[t.Callable, type]
        if isinstance(constructor, str):
            try:
                real_constructor = reflect.resolve_fqn(constructor)
                debug("Constructor for [%s][%s] resolved as [%s]", cls_str, constructor, real_constructor, debug_type="registry_details")
            except ValueError:
                return
        else:
            real_constructor = constructor
        with self._obj_lock:
            if cls_str in self.object_constructors:
                found_idx = None
                for idx, c in enumerate(self.object_constructors[cls_str].constructors):
                    if c.constructor is real_constructor:
                        found_idx = idx
                        break
                if found_idx is not None:
                    debug("Removing constructor [%s][%s]", cls_str, real_constructor, debug_type="registry")
                    del self.object_constructors[cls_str].constructors[found_idx]
                    if not self.object_constructors[cls_str].constructors:
                        debug("Removing registry entirely, no more constructors for [%s]", cls_str, debug_type="registry")
                        del self.object_constructors[cls_str]
                else:
                    debug("No constructor found for [%s][%s]", cls_str, real_constructor, debug_type="registry_details")
            else:
                debug("No entry found for [%s]", cls_str, debug_type="registry_details")

    def register(self,
                 cls: ait.InjectableType,
                 *args,
                 constructor: t.Optional[t.Union[t.Callable[..., t.Any], type, str]] = None,
                 weight: t.Optional[int] = None,
                 caching_strategy: t.Optional[CacheStrategy] = None,
                 as_weakref: t.Optional[bool] = None,
                 ignore_informants: t.Optional[t.List[str]] = None,
                 **kwargs):
        """ Registers a class for injection and specifies how to construct it

        The default method of construction is to call ``cls`` itself with ``args`` and ``kwargs``, i.e.:

        ``cls(*args, **kwargs)``

        Should more control over the construction of an object be required, ``constructor`` can be specified as any
        callable object. Construction is then done as follows:

        ``constructor(*args, **kwargs)``

        :param ignore_informants: A list of informant names to ignore, None to respect them all. Only works when
         cache_strategy is None or :attr:`autoinject.class_registry.CacheStrategy.CONTEXT_CACHE`.
        :param as_weakref: Set to true to force the cache manager to keep only a weakref to the object
        :param cls: The type to inject or a unique identifier
        :type cls: type or str
        :param args: Positional arguments to pass to the constructor
        :type args: any
        :param constructor: Optional callable to construct an object when required. Defaults to calling ``cls`` directly
        :type constructor: callable or None
        :param caching_strategy: Specify how instances of this class are to be cached. Defaults to
            :attr:`autoinject.class_registry.CacheStrategy.CONTEXT_CACHE`, i.e. different objects by context
        :type caching_strategy: :class:`autoinject.class_registry.CacheStrategy` or None
        :param weight: Higher values override lower values
        :type weight: int
        :param kwargs: Keyword arguments to pass to the constructor
        :type kwargs: any
        """

        cls_str = self.cls_to_str(cls)
        real_constructor: t.Union[type, t.Callable, None]
        # Default to the type as constructor
        if constructor is None:
            if isinstance(cls, str):
                real_constructor = reflect.resolve_fqn(cls)
                debug("Class constructor [%s] for [%s] resolved as [%s]", cls, cls_str, real_constructor, debug_type="registry_details")
            else:
                real_constructor = cls

        # Resolve string-like constructors
        elif isinstance(constructor, str):
            real_constructor = reflect.resolve_fqn(constructor)
            debug("Constructor string [%s] for [%s] resolved as [%s]", constructor, cls_str, real_constructor, debug_type="registry_details")

        else:
            real_constructor = constructor

        # Ensure we have a non-abstract, non-protocol value as a constructor
        if not reflect.is_concrete(real_constructor):
            debug("Constructor [%s] for [%s] identified as non-concrete, ignoring it", real_constructor, cls_str, debug_type="registry_details")
            real_constructor = None

        if real_constructor is not None:
            if weight is None and hasattr(real_constructor, 'AUTOINJECT_WEIGHT'):
                weight = int(real_constructor.AUTOINJECT_WEIGHT)
                debug("Weight set from attribute for [%s][%s]", cls_str, real_constructor, debug_type="registry_details")
            if caching_strategy is None and hasattr(real_constructor, 'AUTOINJECT_CACHE_STRATEGY') and isinstance(real_constructor.AUTOINJECT_CACHE_STRATEGY, CacheStrategy):
                caching_strategy = real_constructor.AUTOINJECT_CACHE_STRATEGY
                debug("Caching strategy set from attribute for [%s][%s]", cls_str, real_constructor, debug_type="registry_details")
            if as_weakref is None and hasattr(real_constructor, 'AUTOINJECT_AS_WEAKREF'):
                as_weakref = bool(real_constructor.AUTOINJECT_AS_WEAKREF)
                debug("As weakref set from attribute for [%s][%s]", cls_str, real_constructor, debug_type="registry_details")
            if ignore_informants is None and hasattr(real_constructor, 'AUTOINJECT_IGNORE_INFORMANTS'):
                ignore_informants = [str(x) for x in real_constructor.AUTOINJECT_IGNORE_INFORMANTS]
                debug("Ignore informants set from attribute for [%s][%s]", cls_str, real_constructor, debug_type="registry_details")

            if as_weakref is None:
                as_weakref = False
            if caching_strategy is None:
                caching_strategy = CacheStrategy.CONTEXT_CACHE

            if ignore_informants is ... or ignore_informants is None:
                ignore_informants = []

        with self._obj_lock:
            if cls_str not in self.object_constructors:
                self.object_constructors[cls_str] = InjectableInfo(constructors=[])
                debug("Registered [%s] as an injectable object", cls_str, debug_type="registry")

            if weight is None:
                weights = [0]
                weights.extend(x.weight for x in self.object_constructors[cls_str].constructors)
                weight = max(weights) + 1

            if real_constructor is not None:
                c = InjectableConstructor(
                    constructor=real_constructor,
                    args=args,
                    kwargs=kwargs,
                    weight=weight,
                    strategy=t.cast(CacheStrategy, caching_strategy),
                    as_weakref=t.cast(bool, as_weakref),
                    ignore_informants=t.cast(list, ignore_informants) if ignore_informants is not None else None
                )
                self.object_constructors[cls_str].constructors.append(c)
                debug("Constructor [%s] registered for [%s]", c, cls_str, debug_type="registry")
            else:
                debug("No constructor registered for [%s], it was missing", cls_str, debug_type="registry")

    def get_class_info(self, cls: ait.InjectableType) -> ClassInfo:
        """ Retrieves an instance of ``cls``.

        This method searches the registered classes for the spec on how to build an object of type ``cls`` and calls the
        specified constructor method (usually the class itself).

        Note that caching is not implemented here, caching is provided by
        :class:`autoinject.cache_manager.CacheManager` instead which wraps around this class.

        :param cls: The class to get an instance of
        :type cls: type OR str
        :return: An instance of ``cls``
        :rtype: cls
        """
        cls_as_str = self.cls_to_str(cls)
        with self._obj_lock:
            while cls_as_str in self.aliases:
                aliased = self.aliases[cls_as_str]
                debug("Resolving [%s] to [%s]", cls_as_str, aliased, debug_type="registry_fetch")
                cls_as_str = aliased
            if cls_as_str not in self.object_constructors:
                raise ClassNotFoundException(cls_as_str)
            constructor = self.object_constructors[cls_as_str].get_constructor()
            debug("Using constructor [%s] for [%s]", constructor, cls_as_str, debug_type="registry_fetch")
            return ClassInfo(
                cache_key=cls_as_str,
                strategy=constructor.strategy,
                constructor=constructor,
                ignore_informants=constructor.ignore_informants
            )

    def get_cache_key(self, cls: ait.InjectableType) -> str:
        return self.cls_to_str(cls)

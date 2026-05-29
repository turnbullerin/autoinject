import importlib
import sys
import types
import typing as t
import inspect
import dataclasses
from types import NoneType, EllipsisType

import autoinject.types as ait
import autoinject.user as aiu
from autoinject.debug import debug

if t.TYPE_CHECKING:  # pragma: no cover
    import autoinject


if sys.version_info[0] == 3 and sys.version_info[1] >= 14:
    debug("Using modern annotationlib", debug_type="library")
    import annotationlib

    def _get_annotations(cls: type) -> t.Dict[str, t.Any]:
        return annotationlib.get_annotations(cls, format=annotationlib.Format.FORWARDREF)

    def _cleanup_annotation(annotation: t.Any) -> t.Any:
        if isinstance(annotation, annotationlib.ForwardRef):
            try:
                annotation = annotation.evaluate()
            except (NameError, AttributeError) as ex:
                debug("Could not evaluate annotation [%s], resolving as string", annotation, debug_type="annotations")
                annotation = annotation.__forward_arg__
        return annotation

    def _inspect_signature(func: ait.InjectableFunction) -> inspect.Signature:
        return inspect.signature(t.cast(t.Callable, func), annotation_format=annotationlib.Format.FORWARDREF)

else:

    if sys.version_info.major == 3 and sys.version_info.minor >= 10:
        debug("Using inspect.get_annotations", debug_type="library")
        def _get_annotations(cls: type) -> t.Dict[str, t.Any]:
            return inspect.get_annotations(cls)

    else:
        debug("Using direct access to __annotations__", debug_type="library")
        def _get_annotations(cls: type) -> t.Dict[str, t.Any]:
            if hasattr(cls, '__annotations__'):
                return cls.__annotations__
            return {}

    def _cleanup_annotation(annotation: t.Any) -> t.Any:
        return annotation

    def _inspect_signature(func: ait.InjectableFunction) -> inspect.Signature:
        return inspect.signature(t.cast(t.Callable, func))


@dataclasses.dataclass
class ParameterReplacement:
    position: t.Optional[int] = None
    name: t.Optional[str] = None
    default: t.Any = None
    force_positional: bool = False

    def __str__(self):  # pragma: no cover
        if self.name is None or self.force_positional:
            return f"<ParameterReplacement:{self.position}->{self.default}>"
        else:
            return f"<ParameterReplacement:{self.name}->{self.default}>"

    def apply(self, args: list, kwargs: dict):
        debug("Attempting to replace argument [%s][%s] in call with [%s] args and kwargs [%s]", self.name, self.position, len(args), kwargs.keys(), debug_type="parameters")
        # If the position has been specified already
        if self.position is not None and self.position < len(args):
            debug("Positional argument detected", debug_type="parameters")
            # Check if its set and otherwise override it
            if args[self.position] in (..., None):
                debug("Replacing positional argument [%s] with default [%s]", self.position, self.default, debug_type="parameters")
                args[self.position] = self.default
            return
        else:
            debug("Positional argument not detected %s >= %s", self.position, len(args), debug_type="parameters")

        # We need to set it
        if self.position is not None and (self.name is None or self.force_positional):
            debug("Positional argument required but not yet set")

            # fill the args with ... (this shouldn't happen)
            while len(args) < self.position:  # pragma: no cover
                debug("Adding blank positional argument at [%s]", len(args), debug_type="parameters")
                args.append(...)

            # append the default onto the end.
            debug("Adding default positional argument [%s] at [%s]", self.default, len(args), debug_type="parameters")
            args.append(self.default)
            return

        if self.name is not None and (self.name not in kwargs or kwargs[self.name] in (..., None)):
            debug("Setting keyword argument [%s] to [%s]", self.name, self.default, debug_type="parameters")
            kwargs[self.name] = self.default


@dataclasses.dataclass
class AttributeReplacement:
    name: str
    default: t.Any = None

    def __str__(self): # pragma: no cover
        return f"<AttributeReplacement:{self.name}->{self.default}>"


def resolve_fqn(cls: str, base: t.Optional[str] = None) -> t.Any:
    """ """
    if '.' not in cls:
        # this should be a global builtin function for Python
        # note that in 3.8 through 3.14, __builtins__ works like a dict not a module, but type checkers don't
        # like that.
        builtins: dict = t.cast(dict, __builtins__)
        if cls in builtins:
            return builtins[cls]
    else:
        components: t.List[str] = cls.split('.')
        obj_path: t.List[str] = [components.pop(-1)]
        while components:
            module = '.'.join(components)
            try:
                current_obj = importlib.import_module(module, base)
                # in module m, m.a.b can be a thing.
                for x in obj_path:
                    current_obj = getattr(current_obj, x)
                return current_obj
            except (ModuleNotFoundError, AttributeError):
                obj_path.insert(0, components.pop(-1))
    raise ValueError(f'No such object [{cls}]{"" if base is None else "[rel:" + base + "]"}]')

def is_concrete(cls: t.Any) -> bool:
    """ Returns False if cls is an immediate subclass of typing.Protocol or a subclass of abc.ABC with abstract methods not defined. """
    if inspect.isabstract(cls):
        return False
    if not hasattr(cls, '__mro__'):
        return True
    if t.Protocol in cls.__mro__:
        return False
    return True

def type_fqn(obj: object) -> str:
    """ As per """
    return fqn(obj.__class__)


def fqn(obj: object) -> str:
    """ Given a type or function, returns a fully-qualified name for it (i.e. package.module.qualified_name).

        The provided object must provide the __module__ and __qualname__ properties that,
        together, form the fully qualified name of "{module}.{qualname}".

        If module is builtins, only the actual object name is returned.

        :raises AttributeError: If the object doesn't have a __module__ and a __qualname__
        attribute.
    """
    if hasattr(obj, '__module__') and hasattr(obj, '__qualname__'):
        if obj.__module__ == 'builtins':
            return obj.__qualname__
        return f"{obj.__module__}.{obj.__qualname__}"
    else:
        raise TypeError(f'Object type does not define __module__ or __qualname__: {obj}')


class ManyTypes(t.Protocol):
    __args__: t.List[type]

MANY_TYPES: t.List[str] = [
    'Union',
    'UnionType',
    'Optional',
    '_UnionGenericAlias',
    '_GenericAlias',  # 3.8
]

def is_many_types_annotation(annotation: object) -> t.TypeGuard[ManyTypes]:
    if not hasattr(annotation, '__args__'):
        debug("Many types check for [%s]: False (no __args__)", annotation, debug_type="annotations")
        return False
    if hasattr(types, 'UnionType') and isinstance(annotation, types.UnionType):
        debug("Many types check for [%s]: True (is union type)", annotation, debug_type="annotations")
        return True
    if not hasattr(annotation, '__name__'):
        if hasattr(annotation, '__class__') and hasattr(annotation.__class__, '__name__'):
            name_check = annotation.__class__.__name__
        else:  # pragma: no cover # this case doesn't happen but its here in case the typing library changes
            debug("Many types check for [%s]: False (no __name__)", annotation, debug_type="annotations")
            return False
    else:
        name_check = annotation.__name__
    res = name_check in MANY_TYPES
    debug("Many types check for [%s : %s]: %s", annotation, name_check, res, debug_type="annotations")
    return res

def unpack_type_annotation(annotation: object) -> t.Set[type]:
    allowed_types: t.Set[t.Any] = set()
    if is_many_types_annotation(annotation):
        debug("Annotation [%s] is a many-types annotation with [%s], expanding", annotation, annotation.__args__, debug_type="annotations")
        for x in annotation.__args__:
            allowed_types.update(unpack_type_annotation(x))
    elif isinstance(annotation, type):
        debug("Annotation [%s] is a class type", annotation, debug_type="annotations")
        allowed_types.add(annotation)
    elif isinstance(annotation, str):
        debug("Annotation [%s] is a string", annotation, debug_type="annotations")
        allowed_types.add(annotation)
    else:
        debug("Annotation [%s] is something else [%s]", annotation, type(annotation), debug_type="annotations")
        allowed_types.add(annotation)
    return allowed_types


def resolve_annotation(annotated_cls_or_func: t.Any,
                       annotation: t.Any) -> t.Optional[ait.InjectableType]:
    """Given an annotation, attempt to resolve it to a type. """

    annotation = _cleanup_annotation(annotation)

    # Types and None values can be immediately returned
    if not isinstance(annotation, str):
        many_types = [x for x in unpack_type_annotation(annotation) if x is not NoneType and x is not EllipsisType]
        if len(many_types) == 1:
            debug("Annotation [%s] has exactly one non-None type [%s], returning it", annotation, many_types[0], debug_type="annotations")
            return many_types[0]
        debug("Annotation [%s] has many types: [%s]", annotation, many_types, debug_type="annotations")
        return annotation

    # If it is a string, strip one layer of strings off in case the developer used them
    if annotation[0] == annotation[-1] and annotation[0] in '"\'':
        annotation = annotation[1:-1]

    # If we can load the type, then just return it (this is most often the case when a FQN is used)
    try:
        fqn = resolve_fqn(annotation)
        debug("Annotation [%s] is a fully-qualified name string, resolved as [%s]", annotation, fqn, debug_type="annotations")
        return fqn
    except ValueError: ...

    # It might be a relative import pre-ForwardReference being a thing
    if hasattr(annotated_cls_or_func, '__module__'):
        try:
            fqn2 = resolve_fqn(f"{annotated_cls_or_func.__module__}.{annotation}")
            debug("Annotation [%s] is a relative import from the module, resolved as [%s]", annotation, fqn2, debug_type="annotations")
            return fqn2
        except ValueError: ...
    debug("Annotation [%s] is unrecognized, returning it", annotation, debug_type="annotations")
    return annotation


def _build_injectable_info(cls_or_callable: object, annotation: t.Any, cls_registry: "autoinject.class_registry.ClassRegistry") -> t.Optional[ait.DelayedProtocol]:
    resolved = resolve_annotation(cls_or_callable, annotation)
    if resolved is None:
        return None
    elif cls_registry.is_injectable(resolved):
        return aiu.DelayedInjectable(resolved)
    elif cls_registry.is_context(resolved):
        return aiu.DelayedContext()
    elif cls_registry.is_delayed_parameter(resolved):
        return resolved
    return None

def get_injectable_attributes(cls: type, cls_registry: "autoinject.class_registry.ClassRegistry") -> t.List[AttributeReplacement]:
    """Given a type, find all the injectable attributes using the annotations."""
    type_map: t.Dict[str, AttributeReplacement] = {}
    for check_cls in cls.mro():
        annotations = _get_annotations(check_cls)
        for k in annotations:
            if k not in type_map:
                inj_info = _build_injectable_info(check_cls, annotations[k], cls_registry)
                if inj_info is not None:
                    debug("Annotation [%s] on [%s].[%s] was resolved into injectable object [%s]", annotations[k], cls, k, inj_info, debug_type="annotations")
                    type_map[k] = AttributeReplacement(name=k, default=inj_info)
    return list(type_map.values())

def get_injectable_parameters(func: ait.InjectableFunction, cls_registry: "autoinject.class_registry.ClassRegistry") -> t.List[ParameterReplacement]:
    # Inspect the object
    func_sig = _inspect_signature(func)

    injectable_parameters = []
    positional_defaults = []
    max_injectable_positional_only = None
    has_positionals = False

    # Process all the function parameters
    for idx, parameter_name in enumerate(func_sig.parameters):
        param = func_sig.parameters[parameter_name]

        # Variable-length parameters can't be injected
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        has_default = param.default not in (None, ..., inspect.Parameter.empty)

        # Delayed parameter check
        if has_default and cls_registry.is_delayed_parameter(param.default):
            debug("Parameter [%s].[%s] has a delayed parameter default [%s] we can resolve", func, parameter_name, param, debug_type="annotations")
            injectable_parameters.append(ParameterReplacement(
                position=idx if param.kind is not inspect.Parameter.KEYWORD_ONLY else None,
                name=param.name if param.kind is not inspect.Parameter.POSITIONAL_ONLY else None,
                default=param.default,
                force_positional=has_positionals and param.kind is not inspect.Parameter.KEYWORD_ONLY
            ))
            if param.kind is inspect.Parameter.POSITIONAL_ONLY:
                max_injectable_positional_only = idx

        # Injectable parameter check
        elif param.annotation is not inspect.Parameter.empty and not has_default:
            debug("Parameter [%s].[%s] has an annotation and no default value", func, parameter_name, debug_type="annotations")
            annotation = resolve_annotation(func, param.annotation)
            inj_info = _build_injectable_info(func, annotation, cls_registry)
            if inj_info is not None:
                debug("Parameter [%s].[%s] has an annotation [%s] that resolves to [%s] and makes injectable [%s]", func, parameter_name, param.annotation, annotation, inj_info, debug_type="annotations")
                injectable_parameters.append(ParameterReplacement(
                    position=idx if param.kind is not inspect.Parameter.KEYWORD_ONLY else None,
                    name=param.name if param.kind is not inspect.Parameter.POSITIONAL_ONLY else None,
                    default=inj_info,
                    force_positional=has_positionals and param.kind is not inspect.Parameter.KEYWORD_ONLY
                ))
                if param.kind is inspect.Parameter.POSITIONAL_ONLY:
                    max_injectable_positional_only = idx

        # We need to keep these as defaults
        elif param.kind is inspect.Parameter.POSITIONAL_ONLY:
            debug("Parameter [%s].[%s] is positional, tracking", func, parameter_name, debug_type="annotations")
            has_positionals = True
            if param.default is not inspect.Parameter.empty:
                positional_defaults.append(ParameterReplacement(
                    position=idx,
                    default=param.default
                ))

    # In this case, we need to make sure we provide defaults (up to the last position before we inject the arguments)
    if max_injectable_positional_only is not None and injectable_parameters:
        debug("Callable [%s] has positional arguments and injectable parameters, injecting defaults up to [%s]", func, max_injectable_positional_only, debug_type="annotations")
        injectable_parameters.extend(
            x
            for x in positional_defaults
            if (x.position is not None) and (x.position <= max_injectable_positional_only)
        )

    # Sort them in ascending order of position (keyword only parameters don't matter)
    injectable_parameters.sort(key=lambda x: x.position if x.position is not None else len(func_sig.parameters))
    return injectable_parameters

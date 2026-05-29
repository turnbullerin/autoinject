import typing as t
import autoinject.types as ait

if t.TYPE_CHECKING: # pragma: no cover
    import autoinject

T = t.TypeVar("T")

@t.overload
def auto(type_: t.Type[T]) -> T: ...

@t.overload
def auto(type_: t.Optional[str] = None) -> t.Any: ...

def auto(type_: t.Optional[t.Union[str, type]] = None):
    return None

class DelayedParameter:

    def resolve(self,
                injector: "autoinject.injection.InjectionManager",
                obj: ait.SupportsInjection,
                ctx: t.Optional[ait.SupportsContext]) -> t.Any: raise NotImplementedError


def delayed_call(cb: t.Callable, *args, **kwargs) -> t.Any:
    return DelayedCallable(cb, *args, **kwargs)


class DelayedCallable(DelayedParameter):
    """ Represents a parameter that is only built when the function is called. """

    def __init__(self, cb: t.Callable, *args, **kwargs):
        self._cb = cb
        self._args = args
        self._kwargs = kwargs

    def __str__(self): # pragma: no cover
        return f'<DelayedCallable:{self._cb}>'

    def resolve(self,
                injector: "autoinject.injection.InjectionManager",
                obj: ait.SupportsInjection,
                ctx: t.Optional[ait.SupportsContext]) -> t.Any:
        return self._cb(*self._args, **self._kwargs)


class DelayedInjectable(DelayedParameter):
    """ Indicates an injectable type in type hints or default values. """

    def __init__(self, resolved: ait.InjectableType):
        self._resolved = resolved

    def __str__(self): # pragma: no cover
        return f'<DelayedInjectable:{self._resolved}>'

    def resolve(self,
                injector: "autoinject.injection.InjectionManager",
                obj: ait.SupportsInjection,
                ctx: t.Optional[ait.SupportsContext]) -> t.Any:
        return injector.get(injector.resolve_annotation(obj, self._resolved))


class DelayedContext(DelayedParameter):

    def __str__(self): # pragma: no cover
        return '<DelayedContext>'

    def resolve(self,
                injector: "autoinject.injection.InjectionManager",
                obj: ait.SupportsInjection,
                ctx: t.Optional[ait.SupportsContext]) -> t.Any:
        return ctx

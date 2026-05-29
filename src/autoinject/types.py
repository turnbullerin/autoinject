import contextvars
import typing as t


if t.TYPE_CHECKING: # pragma: no cover
    import autoinject



@t.runtime_checkable
class ContextProtocol(t.Protocol):

    def __contains__(self, key) -> bool: ...
    def __getitem__(self, key) -> t.Any: ...
    def __iter__(self): ...
    def __len__(self) -> int: ...
    def run(self, cmd: t.Callable, *args, **kwargs) -> t.Any: ...
    def copy(self) -> t.Self: ...
    def get(self, key, default=None, /) -> t.Any: ...
    def keys(self) -> t.Iterable: ...
    def values(self) -> t.Iterable: ...
    def items(self) -> t.Iterable[tuple]: ...

_ContextModeOptions = t.Literal['_default', 'same', 'empty', 'copy']
ConcreteContextProtocol = t.TypeVar("ConcreteContextProtocol", bound=ContextProtocol)
SupportsContext = t.Union[ContextProtocol, contextvars.Context]
ContextMode = t.Optional[t.Union[_ContextModeOptions, SupportsContext]]

SupportsInjection = t.Union[type, t.Callable]
TestFixtureBuilderType = t.Union[t.Callable[[], t.Any], type]
InjectableType = t.Union[type, str]


class InjectableFunctionProtocol(t.Protocol):
    __module__: str

    def __hash__(self) -> int: ...
    def __call__(self, *args, **kwargs): ...

InjectableFunction = t.Union[t.Callable, type, classmethod, staticmethod]

class DelayedProtocol(t.Protocol):
    def resolve(self,
                injector: "autoinject.injection.InjectionManager",
                obj: SupportsInjection,
                ctx: t.Optional[SupportsContext]): ...

ConcreteDelayedProtocol = t.TypeVar("ConcreteDelayedProtocol", bound=DelayedProtocol)

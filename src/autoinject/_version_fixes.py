# mypy: ignore-errors
# These are just small polyfills so I can still use 3.14 style typing mostly but mypy really doesn't like them.
# They work though.

import typing as t
import types

if not hasattr(types, 'EllipsisType'):
    types.EllipsisType = type(...)

if not hasattr(t, 'TypeGuard'):
    T = t.TypeVar("T")
    class _Bool(t.Generic[T]):
        def __bool__(self): ...
    t.TypeGuard = _Bool

if not hasattr(t, 'ParamSpec'):
    t.ParamSpec = lambda x: ...

if not hasattr(types, 'NoneType'):
    types.NoneType = type(None)

if not hasattr(t, 'Self'):
    t.Self = t.Any

if not hasattr(t, 'assert_type'):
    t.assert_type = lambda x, y: ...

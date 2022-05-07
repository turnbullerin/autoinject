import inspect

from .context_manager import NamedContextManager
from .context_manager import ContextManager
from .class_registry import ClassRegistry


class MissingArgumentError(ValueError):
    pass


class ExtraPositionalArgumentsError(ValueError):
    pass


class ExtraKeywordArgumentsError(ValueError):
    pass


class InjectionManager:

    def __init__(self):
        self.cls_registry = ClassRegistry()
        self.context_manager = NamedContextManager(self.cls_registry)

    def set_context_manager(self, context_manager: ContextManager):
        if not isinstance(context_manager, ContextManager):
            raise ValueError("An implementation of autoinject.ContextManager is required")
        self.context_manager = context_manager

    def register_class(self, cls, *args, constructor=None, **kwargs):
        self.cls_registry.register_class(cls, *args, **kwargs, constructor=constructor)

    def injectable(self, cls):
        self.register_class(cls)
        return cls

    def inject(self, func):
        def wrapper(*args, **kwargs):
            new_args, new_kwargs = self.bind_parameters(func, args, kwargs)
            return func(*new_args, **new_kwargs)
        return wrapper

    def construct(self, func):
        def wrapper(*args, **kwargs):
            obj = args[0]
            if hasattr(obj.__class__, '__annotations__'):
                for name, val in inspect.getmembers(obj.__class__):
                    if name[0:2] == "__":
                        continue
                    if name in obj.__class__.__annotations__:
                        cls = obj.__class__.__annotations__[name]
                        if self.cls_registry.is_injectable(cls):
                            setattr(obj, name, self.context_manager.get_object(cls))
            return func(*args, **kwargs)
        return wrapper

    def bind_parameters(self, func, args, kwargs):
        real_args = []
        real_kwargs = {}
        func_sig = inspect.signature(func)
        arg_index = 0
        load_extra_args = False
        load_extra_kwargs = False
        for parameter_name in func_sig.parameters:
            param = func_sig.parameters[parameter_name]
            if param.kind == inspect.Parameter.VAR_POSITIONAL:
                load_extra_args = True
            elif param.kind == inspect.Parameter.VAR_KEYWORD:
                load_extra_kwargs = True
            elif param.name == "self":
                real_args.append(args[arg_index])
                arg_index += 1
            else:
                allow_kwarg = not param.kind == inspect.Parameter.POSITIONAL_ONLY
                allow_arg = not param.kind == inspect.Parameter.KEYWORD_ONLY
                real_value = None
                if allow_kwarg and param.name in kwargs:
                    real_value = kwargs[param.name]
                    del kwargs[param.name]
                elif param.annotation and self.cls_registry.is_injectable(param.annotation):
                    if allow_arg and arg_index < len(args) and isinstance(args[arg_index], param.annotation):
                        real_value = args[arg_index]
                        arg_index += 1
                    else:
                        real_value = self.context_manager.get_object(param.annotation)
                elif allow_arg and arg_index < len(args):
                    real_value = args[arg_index]
                    arg_index += 1
                elif param.default and not param.default == inspect.Parameter.empty:
                    real_value = param.default
                else:
                    raise MissingArgumentError(param.name)
                if allow_arg:
                    real_args.append(real_value)
                else:
                    real_kwargs[param.name] = real_value
        if load_extra_args and arg_index < len(args):
            real_args.extend(args[arg_index:])
            arg_index = len(args)
        if load_extra_kwargs and kwargs:
            real_kwargs.update(kwargs)
            kwargs = {}
        if arg_index < len(args):
            raise ExtraPositionalArgumentsError()
        if kwargs:
            raise ExtraKeywordArgumentsError()
        return real_args, real_kwargs

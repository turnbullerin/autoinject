import inspect
from functools import wraps

from .context_manager import ContextManager
from .class_registry import ClassRegistry


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
        :meth:`autoinject.injector.InjectionManager.injectable` decorator. This registers the class with the class
        registry and is suitable for classes that have a constructor with no arguments other than injectable ones. More
        complex classes should use the :meth:`autoinject.injector.InjectionManager.register` decorator and
        provide suitable arguments to support class construction.

        Dependencies can be injected in two fashions: as part of the arguments to a function or method, or as
        object attributes when ``__init__()`` is called. For the former, use the
        :meth:`autoinject.injector.InjectionManager.inject` decorator; it will automatically provide an appropriate
        instance of the objects based on the type-hint of the parameter. For the latter, use the
        :meth:`autoinject.injector.InjectionManager.construct` decorator on the class's ``__init__()`` method. It will
        search for CLASS attributes with an injectable type-hint and inject the objects into the INSTANCE attributes
        as required.
    """

    def __init__(self):
        """ Constructor """
        self.cls_registry = ClassRegistry()
        self.context_manager = ContextManager(self.cls_registry)
        self.cls_registry.register_class(ClassRegistry, constructor=lambda: self.cls_registry)
        self.cls_registry.register_class(ContextManager, constructor=lambda: self.context_manager)

    def register_informant(self, context_informant):
        self.context_manager.register_informant(context_informant)

    def register(self, cls_name, *args, **kwargs):
        def outer_wrap(constructor):
            self.cls_registry.register_class(cls_name, *args, **kwargs, constructor=constructor)
            return constructor
        return outer_wrap

    def injectable(self, cls):
        self.cls_registry.register_class(cls)
        return cls

    def inject(self, func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            new_args, new_kwargs = self.bind_parameters(func, args, kwargs)
            return func(*new_args, **new_kwargs)
        return wrapper

    def construct(self, func):
        @wraps(func)
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

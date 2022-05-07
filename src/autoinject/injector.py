from .context_manager import GlobalContextManager
from .context_manager import ContextManager
from .class_registry import ClassRegistry


class InjectionManager:

    def __init__(self):
        self.cls_registry = ClassRegistry()
        self.context_manager = GlobalContextManager()

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
        deconstructed_args = []
        
        def wrapper(*args, **kwargs):
            new_args = []
            new_kwargs = {}
            func(*new_args, **new_kwargs)
        return wrapper


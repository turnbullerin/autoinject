from .injector import InjectionManager, MissingArgumentError, ExtraKeywordArgumentsError, ExtraPositionalArgumentsError
from .class_registry import ClassRegistry, ClassNotFoundException, CacheStrategy
from .context_manager import ContextManager, NamedContextManager, GlobalContextManager, CacheStrategyNotSupportedError

__version__ = '0.0.1'

injector = InjectionManager()

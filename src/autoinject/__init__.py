"""


.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
from .injector import InjectionManager, MissingArgumentError, ExtraKeywordArgumentsError, ExtraPositionalArgumentsError
from .class_registry import ClassRegistry, ClassNotFoundException, CacheStrategy
from .context_manager import ContextManager, CacheStrategyNotSupportedError

__version__ = '0.1.0'

injector = InjectionManager()

from .informants import ContextInformant, NamedContextInformant

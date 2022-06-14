"""


.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
from .injection import InjectionManager, MissingArgumentError, ExtraKeywordArgumentsError, ExtraPositionalArgumentsError
from .class_registry import ClassRegistry, ClassNotFoundException, CacheStrategy
from .context_manager import ContextManager

__version__ = '0.2.0'

injector = InjectionManager()

from .informants import ContextInformant, NamedContextInformant

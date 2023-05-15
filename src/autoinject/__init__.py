"""


.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
from .injection import InjectionManager, MissingArgumentError, ExtraKeywordArgumentsError, ExtraPositionalArgumentsError
from .class_registry import ClassRegistry, ClassNotFoundException, CacheStrategy
from .context_manager import ContextManager
from .informants import ContextInformant, NamedContextInformant, ContextVarInformant, ThreadedContextInformant

__version__ = '1.3.0'

injector = InjectionManager()

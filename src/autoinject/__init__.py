"""


.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import autoinject._version_fixes

from .user import DelayedParameter
from .user import DelayedCallable, delayed_call
from .user import DelayedContext
from .user import DelayedInjectable as Delayed
from .user import auto
from .class_registry import ClassRegistry
from .class_registry import ClassNotFoundException
from .class_registry import CacheStrategy
from .cache_manager import CacheManager
from .informants import SituationInformant
from .informants import NamedSituationInformant
from .informants import ContextVarInformant
from .informants import ThreadedContextInformant
from .injection import InjectionManager


__version__ = '2.0.0'

injector = InjectionManager()

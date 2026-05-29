""" Context informants tell the ContextManager about the context.

    Each informant provides a unique string for each individual context. The context manager then caches objects by
    context. The context should be destroyed when it is no longer needed.

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import contextvars
from abc import ABC, abstractmethod
import threading
import secrets
import logging
import typing as t
import autoinject.types as ait

if t.TYPE_CHECKING: # pragma: no cover # type checking
    import autoinject


class SituationInformant(ABC):
    """ Base class for context informants

        :param name: A unique name for this informant. It will be used to assemble multiple contexts together.
        :type name: str
    """

    def __init__(self, name: t.Optional[str] = None):
        """ Constructor """
        if name is None:
            name = str(self.__class__)  # pragma: no cover
        self.name = name
        self._cache_manager: t.Optional["autoinject.cache_manager.CacheManager"] = None

    def set_cache_manager(self, cache_manager: "autoinject.cache_manager.CacheManager"):
        """ Set the context manager. This is called by the ``ContextManager`` when the informant is registered.

        :param cache_manager: The context manager
        :type cache_manager: autoinject.cache_manager.CacheManager
        """
        self._cache_manager = cache_manager

    @property
    def cache_manager(self) -> "autoinject.cache_manager.CacheManager":
        if self._cache_manager is None:
            raise Exception("Cache manager hasn't been set.")
        return self._cache_manager

    @abstractmethod
    def get_cache_id(self) -> str:
        """ Obtains a unique identifier for the current context. This is paired with the informant name to create a
            unique string for each context.

        :return: A unique string per context
        :rtype: str
        """
        pass  # pragma: no cover

    def destroy(self, cache_id: str):
        """ Remove all objects cached under the given context.

        :param cache_id: A value that would have been provided by get_context_id() to the ``ContextManager``
        :type cache_id: str
        """
        self.cache_manager.destroy_cache_id(self, cache_id)

    def check_expired_caches(self):
        """ Trigger to check for expired contexts so they can be cleaned-up from memory """
        pass


class NamedSituationInformant(SituationInformant):
    """ A toy class for demonstrating how contexts work. The context can be changed using ``switch_context()``::

            from autoinject import injector, NamedContextInformant

            informant = NamedContextInformant()
            injector.register_informant(informant)
            # We are now in the "_default" context
            informant.switch_context("alpha")
            # We are now in the "alpha" context

        In the above example, any calls to inject classes registered with a cache strategy of ``CONTEXT_CACHE`` (the
        default) will result in different obtains being returned for the _default context and the alpha context. If the
        class is registered with a strategy of GLOBAL_CACHE, the same object will be returned.

    """

    def __init__(self, name: str = "named_situation"):
        """ Constructor """
        super().__init__(name)
        self.cache_id = "_default"

    def switch_context(self, cache_id: str):
        """Change the context ID"""
        self.cache_id = cache_id

    def destroy_self(self):
        """Destroy the current context"""
        self.destroy(self.cache_id)

    def get_cache_id(self) -> str:
        """ Provide the context ID to the ContextManager """
        return self.cache_id


_autoinject_var = contextvars.ContextVar[t.Optional[str]]("_autoinject_context_name", default=None)


class ContextVarManager:
    """Wrapper around contexts to help manage issues with cleaning up dependencies."""

    EMPTY = "empty"
    COPY = "copy"
    SAME = "same"
    DEFAULT = "_default"

    def __init__(self, contextvar_informant: "ContextVarInformant", context: ait.ContextMode = "_default", suppress_exit_warning: bool = False):
        self._context: t.Optional[ait.SupportsContext] = None
        self._delegate_run = True
        self._suppress_exit_warning = suppress_exit_warning
        if context is ContextVarManager.EMPTY:
            self._context = contextvars.Context()
        elif context is ContextVarManager.COPY or context is ContextVarManager.DEFAULT or context is None:
            self._context = self.copy(True)
        elif context is ContextVarManager.SAME:
            self._context = None
        elif isinstance(context, str):
            raise ValueError(f"Incorrect custom setting for context {context}")
        elif isinstance(context, ContextVarManager):
            # Handle nested contexts more graciously
            self._context = context._context
        elif isinstance(context, ait.ContextProtocol):
            self._context = context
        else:
            raise TypeError('Invalid type for context argument')
        self._reset_token: t.Any = None
        self._informant = contextvar_informant
        self._test = None

    def __enter__(self):
        global _autoinject_var
        if self._reset_token is not None:
            raise ValueError("Cannot nest calls to the same context manager")
        self._reset_token = ContextVarManager.freshen_context(self)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        global _autoinject_var
        self._informant.destroy_self(self._context)
        try:
            ContextVarManager.restore_context_id(self._reset_token, self)
        except ValueError:  # pragma: no coverage (hard to test)
            if not self._suppress_exit_warning:
                logging.getLogger("autoinject").exception(f"Failure to clear context ID (likely inner block left context in an unclear state)")
        self._reset_token = None

    def __contains__(self, item):
        return self._map_to_context("__contains__", item)

    def __getitem__(self, item):
        return self.get(item)

    def __iter__(self): # pragma: no coverage
        return self._map_to_context("__iter__")

    def __len__(self): # pragma: no coverage
        return self._map_to_context("__len__")

    def iter(self):
        return self._map_to_context("iter")

    def len(self):
        return self._map_to_context("__len__")

    def keys(self):
        return self._map_to_context("keys")

    def values(self):
        return self._map_to_context("values")

    def items(self):
        return self._map_to_context("items")

    def _map_to_context(self, item: str, *args, **kwargs):
        _inner_context = self._context
        if self._context is None:
            _inner_context = contextvars.copy_context()
        return getattr(_inner_context, item)(*args, **kwargs)

    def get(self, var: contextvars.ContextVar, default: t.Any = None):
        return self.run(var.get, default)

    def set(self, var: contextvars.ContextVar, value: t.Any):
        """Set a variable and return a token"""
        return self.run(var.set, value)

    def reset(self, var: contextvars.ContextVar, token: t.Any):
        """Reset a variable."""
        return self.run(var.reset, token)

    Q = t.TypeVar("Q")
    def run(self, cmd: t.Callable[..., Q], *args, **kwargs) -> Q:
        """Run, in context if appropriate."""
        if self._delegate_run and self._context is not None:
            # Prevent running the context from within the context
            self._delegate_run = False
            try:
                return self._context.run(cmd, *args, **kwargs)
            finally:
                self._delegate_run = True
        else:
            return cmd(*args, **kwargs)

    def copy(self, same_autoinject_context: bool = False):
        """Make a copy of the context, with optional parameter to keep or reset the autoinjection variables."""
        ContextVarManager.ensure_context_id(self)
        new_context = contextvars.copy_context() if self._context is None else self._context.copy()
        if not same_autoinject_context:
            ContextVarManager.freshen_context(new_context)
        return new_context

    @staticmethod
    def freshen_context(context: t.Optional[ait.SupportsContext] = None) -> contextvars.Token:
        """Refresh the context by resetting the context ID."""
        if context is not None:
            return context.run(ContextVarManager.freshen_context)
        else:
            global _autoinject_var
            return _autoinject_var.set(secrets.token_hex(16))

    @staticmethod
    def restore_context_id(token, context: t.Optional[ait.SupportsContext] = None):
        """Refresh the context by resetting the context ID."""
        if context is not None:
            context.run(ContextVarManager.restore_context_id, token)
        else:
            global _autoinject_var
            _autoinject_var.reset(token)

    @staticmethod
    def ensure_context_id(context: t.Optional[ait.SupportsContext] = None):
        """Ensure there is a context ID."""
        if context is not None:
            return context.run(ContextVarManager.ensure_context_id)
        else:
            global _autoinject_var
            context_id = _autoinject_var.get()
            if context_id is None:
                context_id = secrets.token_hex(16)
                _autoinject_var.set(context_id)
            return context_id

    @staticmethod
    def get_context_id(context: t.Optional[ait.SupportsContext] = None) -> t.Optional[str]:
        """Retrieve the current context ID, but don't set one if there isn't one."""
        if context is not None:
            return context.run(ContextVarManager.get_context_id)
        else:
            global _autoinject_var
            return _autoinject_var.get()


class ContextVarInformant(SituationInformant):
    """Context informant for contextvars library."""

    def __init__(self):
        """Init method."""
        super().__init__("contextvars")

    def get_cache_id(self) -> str:
        """Obtain the current context ID from the contextvars."""
        return ContextVarManager.ensure_context_id()

    def destroy_self(self, context: t.Optional[ait.SupportsContext] = None):
        """Destroy the context related to the contextvars context passed or the current one if None."""
        context_id = ContextVarManager.get_context_id(context)
        if context_id is not None:
            self.destroy(context_id)


class ThreadedContextInformant(SituationInformant):
    """ Context informant for threading library """

    def __init__(self):
        """ Constructor """
        super().__init__("threading")
        self._active_threads = set()
        self._lock = threading.Lock()

    def check_expired_caches(self):
        """ Since threads don't reliably have a callback when they complete, we instead regularly monitor the active
            thread list and remove them as they complete to cut down on memory usage.
        """
        with self._lock:
            if self._active_threads:
                active_idents = [t.ident for t in threading.enumerate() if t.ident]
                remove_list = set()
                for ident in self._active_threads:
                    if ident not in active_idents:
                        remove_list.add(ident)
                        self.destroy(str(ident))
                for item in remove_list:
                    self._active_threads.remove(item)

    def destroy_self(self, thread: t.Optional[threading.Thread] = None):
        """Destroy the current thread context."""
        if thread:
            if thread.ident:
                self.destroy(str(thread.ident))
        else:
            self.destroy(self.get_cache_id())

    def get_cache_id(self):
        """ Provide the context ID to the ContextManager """
        ident = threading.get_ident()
        self._active_threads.add(ident)
        return str(ident)

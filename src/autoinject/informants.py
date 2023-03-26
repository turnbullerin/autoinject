""" Context informants tell the ContextManager about the context.

    Each informant provides a unique string for each individual context. The context manager then caches objects by
    context. The context should be destroyed when it is no longer needed.

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import contextvars
from abc import ABC, abstractmethod
import threading
import secrets


class ContextInformant(ABC):
    """ Base class for context informants

        :param name: A unique name for this informant. It will be used to assemble multiple contexts together.
        :type name: str
    """

    def __init__(self, name: str = None):
        """ Constructor """
        if name is None:
            name = str(self.__class__)  # pragma: no cover
        self.name = name
        self.context_manager = None

    def set_context_manager(self, context_manager):
        """ Set the context manager. This is called by the ``ContextManager`` when the informant is registered.

        :param context_manager: The context manager
        :type context_manager: autoinject.context_manager.ContextManager
        """
        self.context_manager = context_manager

    @abstractmethod
    def get_context_id(self) -> str:
        """ Obtains a unique identifier for the current context. This is paired with the informant name to create a
            unique string for each context.

        :return: A unique string per context
        :rtype: str
        """
        pass  # pragma: no cover

    def destroy(self, context_id: str):
        """ Remove all objects cached under the given context.

        :param context_id: A value that would have been provided by get_context_id() to the ``ContextManager``
        :type context_id: str
        """
        self.context_manager.destroy_context(self, context_id)

    def check_expired_contexts(self):
        """ Trigger to check for expired contexts so they can be cleaned-up from memory """
        pass


class NamedContextInformant(ContextInformant):
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

    def __init__(self, name="named_context"):
        """ Constructor """
        super().__init__(name)
        self.current_context = "_default"

    def switch_context(self, context_name: str):
        """Change the context ID"""
        self.current_context = context_name

    def destroy_self(self):
        """Destroy the current context"""
        self.destroy(self.current_context)

    def get_context_id(self):
        """ Provide the context ID to the ContextManager """
        return self.current_context


_autoinject_var = contextvars.ContextVar("_autoinject_context_name", default=None)


class ContextVarManager:
    """Wrapper around contexts to help manage issues with cleaning up dependencies."""

    EMPTY = "empty"
    COPY = "copy"
    SAME = "same"
    DEFAULT = "_default"

    def __init__(self, contextvar_informant, context="_default"):
        self._context = context
        self._delegate_run = True
        if self._context == ContextVarManager.EMPTY:
            self._context = contextvars.Context()
        elif self._context in (ContextVarManager.COPY, ContextVarManager.DEFAULT) or self._context is None:
            self._context = None
            self._context = self.copy(True)
        elif self._context == ContextVarManager.SAME:
            self._context = None
        elif isinstance(self._context, str):
            raise ValueError(f"Incorrect custom setting for context {context}")
        # Handle nested contexts more graciously
        elif isinstance(self._context, self.__class__):
            self._context = self._context._context
        if self._context is not None:
            assert isinstance(self._context, contextvars.Context)
        self._reset_token = None
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
        ContextVarManager.restore_context_id(self._reset_token, self)
        self._reset_token = None

    def __contains__(self, item):
        return self._map_to_context("__contains__", item)

    def __getitem__(self, item):
        return self.get(item)

    def __iter__(self):
        return self._map_to_context("__iter__")

    def __len__(self):
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

    def _map_to_context(self, item, *args, **kwargs):
        _inner_context = self._context
        if self._context is None:
            _inner_context = contextvars.copy_context()
        return getattr(_inner_context, item)(*args, **kwargs)

    def get(self, var, default=None):
        return self.run(var.get, default)

    def set(self, var, value):
        """Set a variable and return a token"""
        return self.run(var.set, value)

    def reset(self, var, token):
        """Reset a variable."""
        return self.run(var.reset, token)

    def run(self, fn, *args, **kwargs):
        """Run, in context if appropriate."""
        if self._delegate_run and self._context is not None:
            # Prevent running the context from within the context
            self._delegate_run = False
            result = self._context.run(fn, *args, **kwargs)
            self._delegate_run = True
            return result
        else:
            return fn(*args, **kwargs)

    def copy(self, same_autoinject_context: bool = False):
        """Make a copy of the context, with optional parameter to keep or reset the autoinjection variables."""
        ContextVarManager.ensure_context_id(self)
        new_context = contextvars.copy_context() if self._context is None else self._context.copy()
        if not same_autoinject_context:
            ContextVarManager.freshen_context(new_context)
        return new_context

    @staticmethod
    def freshen_context(context=None):
        """Refresh the context by resetting the context ID."""
        if context is not None:
            return context.run(ContextVarManager.freshen_context)
        else:
            global _autoinject_var
            return _autoinject_var.set(secrets.token_hex(16))

    @staticmethod
    def restore_context_id(token, context=None):
        """Refresh the context by resetting the context ID."""
        if context is not None:
            context.run(ContextVarManager.restore_context_id, token)
        else:
            global _autoinject_var
            _autoinject_var.reset(token)

    @staticmethod
    def ensure_context_id(context=None):
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
    def get_context_id(context=None):
        """Retrieve the current context ID, but don't set one if there isn't one."""
        if context is not None:
            return context.run(ContextVarManager.get_context_id)
        else:
            global _autoinject_var
            return _autoinject_var.get()


class ContextVarInformant(ContextInformant):
    """Context informant for contextvars library."""

    def __init__(self):
        """Init method."""
        super().__init__("contextvars")

    def get_context_id(self) -> str:
        """Obtain the current context ID from the contextvars."""
        return ContextVarManager.ensure_context_id()

    def destroy_self(self, context: contextvars.Context = None):
        """Destroy the context related to the contextvars context passed or the current one if None."""
        context_id = ContextVarManager.get_context_id(context)
        if context_id is not None:
            self.destroy(context_id)


class ThreadedContextInformant(ContextInformant):
    """ Context informant for threading library """

    def __init__(self):
        """ Constructor """
        super().__init__("threading")
        self._active_threads = set()
        self.lock = threading.Lock()

    def check_expired_contexts(self):
        """ Since threads don't reliably have a callback when they complete, we instead regularly monitor the active
            thread list and remove them as they complete to cut down on memory usage.
        """
        with self.lock:
            if self._active_threads:
                active_idents = [t.ident for t in threading.enumerate() if t.ident]
                remove_list = set()
                for ident in self._active_threads:
                    if ident not in active_idents:
                        remove_list.add(ident)
                        self.destroy(str(ident))
                for item in remove_list:
                    self._active_threads.remove(item)

    def destroy_self(self, thread: threading.Thread = None):
        """Destroy the current thread context."""
        if thread:
            if thread.ident:
                self.destroy(str(thread.ident))
        else:
            self.destroy(self.get_context_id())

    def get_context_id(self):
        """ Provide the context ID to the ContextManager """
        ident = threading.get_ident()
        self._active_threads.add(ident)
        return str(ident)

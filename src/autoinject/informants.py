""" Context informants tell the ContextManager about the context.

    Each informant provides a unique string for each individual context. The context manager then caches objects by
    context. The context should be destroyed when it is no longer needed.

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
from abc import ABC, abstractmethod


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
        self.context_manager.destroy_context(self.name, context_id)


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
        """ Change the context ID"""
        self.current_context = context_name

    def get_context_id(self):
        """ Provide the context ID to the ContextManager """
        return self.current_context



""" The class registry stores which objects can be injected and how to
    maintain cache control over them.

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""
import enum


class CacheStrategy(enum.Enum):
    """ Defines how caching should be managed for this object """

    NO_CACHE = 1
    """ No caching allowed. Specify this when instances of the object should not be shared."""

    GLOBAL_CACHE = 2
    """ A single instance of the object is allowed. Specify this for thread-safe objects that can manage a single global
        instance even in a multi-threaded environment. 
        """

    CONTEXT_CACHE = 3
    """ A single instance of the object is allowed per context. What a context is can vary by application; for example,
        in the context of a WSGI application, each request might be an individual context. Specify this when each thread
        or context might need its own copy of the object. 
    """


class ClassNotFoundException(ValueError):
    """ Raised when a class is requested that has not been registered.

        :param cls_name: Name of the class not found in the registry
        :type cls_name: str
    """

    def __init__(self, cls_name: str):
        """ Constructor """
        super().__init__("Object {} not registered for injection".format(cls_name))


class ClassRegistry:
    """ Manages a list of classes and how they can be instantiated. """

    def __init__(self):
        """ Constructor """
        self.object_constructors = {}

    def cls_to_str(self, cls) -> str:
        """ Converts a type to a string that represents the fully-qualified name of the class.
        :param cls: Either a type to convert or a string representing the fully-qualified name of the class.
        :type cls: type OR str
        :return: Returns a string that could be used to import the class
        :rtype: str
        """
        info = str(cls)
        if info.startswith("<class '"):
            info = info[8:-2]
        return info

    def is_injectable(self, cls: type) -> bool:
        """ Checks if the given class is injectable

            :param cls: The class that is being checked
            :type cls: type
            :return: Whether the class provided can be injected
            :rtype: bool
        """
        return self.cls_to_str(cls) in self.object_constructors

    def register(self,
                 cls: type,
                 *args,
                 weight: int = 0,
                 constructor: callable = None,
                 caching_strategy: CacheStrategy = None,
                 **kwargs):
        """ Registers a class for injection and specifies how to construct it

        The default method of construction is to call ``cls`` itself with ``args`` and ``kwargs``, i.e.:

        ``cls(*args, **kwargs)``

        Should more control over the construction of an object be required, ``constructor`` can be specified as any
        callable object. Construction is then done as follows:

        ``constructor(*args, **kwargs)``

        :param cls: The type to inject or a unique identifier
        :type cls: type or str
        :param args: Positional arguments to pass to the constructor
        :type args: any
        :param constructor: Optional callable to construct an object when required. Defaults to calling ``cls`` directly
        :type constructor: callable or None
        :param caching_strategy: Specify how instances of this class are to be cached. Defaults to
            :attr:`autoinject.class_registry.CacheStrategy.CONTEXT_CACHE`, i.e. different objects by context
        :type caching_strategy: :class:`autoinject.class_registry.CacheStrategy` or None
        :param kwargs: Keyword arguments to pass to the constructor
        :type kwargs: any
        """
        if constructor is None:
            if not isinstance(cls, type):
                raise ValueError("A valid constructor must be passed")
            constructor = cls
        if caching_strategy is None:
            caching_strategy = CacheStrategy.CONTEXT_CACHE
        cls_str = self.cls_to_str(cls)
        # Ignore if a higher-weight constructor is already present
        if cls_str in self.object_constructors and weight < self.object_constructors[cls_str][4]:
            return
        self.object_constructors[cls_str] = (constructor, args, kwargs, caching_strategy, weight)

    def get_cache_strategy(self, cls) -> CacheStrategy:
        """ Retrieves the :class:`autoinject.class_registry.CacheStrategy` associated with the given ``cls``.

        :param cls: The class to check the caching strategy of
        :type cls: type OR str
        :raises autoinject.class_registry.ClassNotFoundException: Raised if the class has not been registered.
        :return: The caching strategy for the given object
        :rtype: autoinject.class_registry.CacheStrategy
        """
        cls_as_str = self.cls_to_str(cls)
        if cls_as_str not in self.object_constructors:
            raise ClassNotFoundException(cls_as_str)
        return self.object_constructors[cls_as_str][3]

    def get_instance(self, cls):
        """ Retrieves an instance of ``cls``.

        This method searches the registered classes for the spec on how to build an object of type ``cls`` and calls the
        specified constructor method (usually the class itself).

        Note that caching is not implemented here, caching is provided by
        :class:`autoinject.context_manager.ContextManager` instead which wraps around this class.

        :param cls: The class to get an instance of
        :type cls: type OR str
        :return: An instance of ``cls``
        :rtype: cls
        """
        cls_as_str = self.cls_to_str(cls)
        if cls_as_str not in self.object_constructors:
            raise ClassNotFoundException(cls_as_str)
        call, args, kwargs, strategy, weight = self.object_constructors[cls_as_str]
        return call(*args, **kwargs)

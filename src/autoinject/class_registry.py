""" The class registry stores which objects can be injected and how to
    maintain cache control over them.

.. moduleauthor:: Erin Turnbull <erin.a.turnbull@gmail.com>

"""

import enum


class CacheStrategy(enum.Enum):
    """ Defines how caching should be managed for this object"""

    NO_CACHE = 0
    GLOBAL_CACHE = 10
    CONTEXT_CACHE = 100


class ClassNotFoundException(ValueError):
    """ Raised when a class is requested that has not been registered.
        :param cls_name: Name of the class not found in the registry
    """

    def __init__(self, cls_name: str):
        """ Constructor """
        super().__init__("Object {} not registered for injection".format(cls_name))


class ClassRegistry:
    """ Manages a list of classes and how they can be instantiated. """

    def __init__(self):
        """ Constructor """
        self.object_constructors = {}

    def is_injectable(self, cls: type) -> bool:
        """ Checks if the given class is injectable
            :param cls: The class that is being checked
            :type cls: type
            :return: Whether or not the class provided can be injected
            :rtype: bool
        """
        return str(cls) in self.object_constructors

    def register_class(self, cls, *args, constructor=None, caching_strategy=None, **kwargs):
        """ Registers a class for injection
        :param cls:
        :param args:
        :param constructor:
        :param caching_strategy:
        :param kwargs:
        :return:
        """
        if constructor is None:
            constructor = cls
        if caching_strategy is None:
            caching_strategy = CacheStrategy.GLOBAL_CACHE
        self.object_constructors[str(cls)] = (constructor, args, kwargs, caching_strategy)

    def get_cache_strategy(self, cls):
        cls_as_str = str(cls)
        if cls_as_str not in self.object_constructors:
            raise ClassNotFoundException(cls_as_str)
        return self.object_constructors[cls_as_str][3]

    def get_instance(self, cls):
        cls_as_str = str(cls)
        if cls_as_str not in self.object_constructors:
            raise ClassNotFoundException(cls_as_str)
        call, args, kwargs, strat = self.object_constructors[cls_as_str]
        return call(*args, **kwargs)

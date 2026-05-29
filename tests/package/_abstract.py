from abc import ABC, abstractmethod

class AbstractObj(ABC):

    @abstractmethod
    def abs_method(self): ...


class ConcreteObj(AbstractObj):

    def abs_method(self):
        ...

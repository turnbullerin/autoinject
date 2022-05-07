

class ClassNotFoundException(ValueError):

    def __init__(self, cls_name, *args, **kwargs):
        super().__init__("Object {} not registered for injection".format(cls_name), *args, **kwargs)


class ClassRegistry:

    def __init__(self):
        self.object_constructors = {}

    def is_injectable(self, cls):
        return str(cls) in self.object_constructors

    def register_class(self, cls, *args, constructor=None, **kwargs):
        if constructor is None:
            constructor = cls
        self.object_constructors[str(cls)] = (constructor, args, kwargs)

    def get_instance(self, cls):
        cls_as_str = str(cls)
        if cls_as_str not in self.object_constructors:
            raise ClassNotFoundException(cls_as_str)
        call, args, kwargs = self.object_constructors[cls_as_str]
        return call(*args, **kwargs)

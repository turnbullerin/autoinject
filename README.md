# Autoinject

[![Documentation Status](https://readthedocs.org/projects/autoinject/badge/?version=latest)](https://autoinject.readthedocs.io/en/latest/?badge=latest)

A clean, simple type-safe framework for using the [Dependency Injection](https://en.wikipedia.org/wiki/Dependency_injection) pattern in Python.

## Example

```python

from autoinject import injector, auto

@injector.injectable
class MyService:
    def __init__(self): ...
    

class MyClient:
  
  service: MyService
  
  @injector.construct
  def __init__(self):
    # self.service will be set before this function is called
    ...
  
@injector.inject
def my_client_function(service: MyService = auto()):
    # service will be set before this function is called
    ...

```
    
Read the [full documentation](https://autoinject.readthedocs.io/en/latest/?) for more details.

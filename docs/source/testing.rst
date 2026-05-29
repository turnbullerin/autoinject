Test Cases
==========

.. highlight:: python


Test Cases
----------

To provide different injectable objects for classes, we provide the special ``@injector.test_case(fixtures_dict)`` or
``@injector.with_fixture(cls, replacement_cls)`` decorators. These should be used on test_case
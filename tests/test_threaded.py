import unittest
import autoinject
import threading
import time


class NotThreadSafe:

    def __init__(self):
        self.lst = []
        self.in_loop = False

    def items(self):
        self.in_loop = True
        for item in self.lst:
            yield item
        self.in_loop = False

    def append(self, bar):
        if self.in_loop:
            raise ValueError("Cannot append while in a loop")
        self.lst.append(bar)


class ThreadSafe:

    def __init__(self):
        self.lst = []
        self.in_loop = False
        self.lock = threading.Lock()

    def items(self):
        with self.lock:
            self.in_loop = True
            for item in self.lst:
                yield item
            self.in_loop = False

    def append(self, bar):
        with self.lock:
            if self.in_loop:
                raise ValueError("Cannot append while in the iterator")
            self.lst.append(bar)


class ThreadedReader(threading.Thread):

    def __init__(self, injector):
        super().__init__()
        self.injector = injector
        self.stop = False
        self.daemon = True

    def run(self):
        lst = self.injector.get(NotThreadSafe)
        while not self.stop:
            for item in lst.items():
                pass


class ThreadedWriter(threading.Thread):

    def __init__(self, injector):
        super().__init__()
        self.injector = injector
        self.stop = False
        self.exc_count = 0
        self.daemon = True

    def run(self):
        lst = self.injector.get(NotThreadSafe)
        while not self.stop:
            try:
                lst.append("foo")
            except ValueError:
                self.exc_count += 1


class ThreadedReaderTS(threading.Thread):

    def __init__(self, injector):
        super().__init__()
        self.injector = injector
        self.stop = False
        self.daemon = True

    def run(self):
        lst = self.injector.get(ThreadSafe)
        while not self.stop:
            for item in lst.items():
                pass


class ThreadedWriterTS(threading.Thread):

    def __init__(self, injector):
        super().__init__()
        self.injector = injector
        self.stop = False
        self.exc_count = 0
        self.daemon = True

    def run(self):
        lst = self.injector.get(ThreadSafe)
        while not self.stop:
            try:
                lst.append("foo")
            except ValueError:
                self.exc_count += 1


class TestThreadedContext(unittest.TestCase):

    def test_threaded_global_failure(self):
        injector = autoinject.InjectionManager(False)
        injector.register_constructor(NotThreadSafe, NotThreadSafe, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        tr = ThreadedReader(injector)
        tr.start()
        tw = ThreadedWriter(injector)
        tw.start()
        time.sleep(2)
        tw.stop = True
        tr.stop = True
        tr.join()
        tw.join()
        self.assertTrue(tw.exc_count > 0)

    def test_threaded_global_success(self):
        injector = autoinject.InjectionManager(False)
        injector.register_constructor(ThreadSafe, ThreadSafe, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        tr = ThreadedReaderTS(injector)
        tr.start()
        tw = ThreadedWriterTS(injector)
        tw.start()
        time.sleep(2)
        tw.stop = True
        tr.stop = True
        tr.join()
        tw.join()
        self.assertTrue(tw.exc_count == 0)

    def test_threaded_context_success(self):
        injector = autoinject.InjectionManager(False)
        injector.register_constructor(NotThreadSafe, NotThreadSafe, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
        tr = ThreadedReader(injector)
        tr.start()
        tw = ThreadedWriter(injector)
        tw.start()
        time.sleep(2)
        tw.stop = True
        tr.stop = True
        tr.join()
        tw.join()
        self.assertTrue(tw.exc_count == 0)
        self.assertEqual(len(injector.context_manager._context_cache), 2)
        injector.context_manager.cleanup()
        self.assertEqual(len(injector.context_manager._context_cache), 0)

    def test_threaded_context_destroy(self):
        injector = autoinject.InjectionManager(False)
        injector.register_constructor(NotThreadSafe, NotThreadSafe, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
        tr = ThreadedReader(injector)
        tr.start()
        tw = ThreadedWriter(injector)
        tw.start()
        time.sleep(2)
        tw.stop = True
        tr.stop = True
        tr.join()
        tw.join()
        self.assertTrue(tw.exc_count == 0)
        self.assertEqual(len(injector.context_manager._context_cache), 2)
        injector.context_manager.thread_info.destroy_self(tr)
        self.assertEqual(len(injector.context_manager._context_cache), 1)
        injector.context_manager.thread_info.destroy_self(tw)
        self.assertEqual(len(injector.context_manager._context_cache), 0)

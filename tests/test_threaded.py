import unittest
import autoinject
import threading
import time

from autoinject import InjectionManager

injector = InjectionManager()

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

    def __init__(self):
        super().__init__()
        self.stop = False
        self.daemon = True

    @injector.as_thread_run
    def run(self):
        lst = injector.get(NotThreadSafe)
        while not self.stop:
            for _ in lst.items():
                pass


class ThreadedWriter(threading.Thread):

    def __init__(self):
        super().__init__()
        self.stop = False
        self.exc_count = 0
        self.daemon = True

    @injector.as_thread_run
    def run(self):
        lst = injector.get(NotThreadSafe)
        while not self.stop:
            try:
                lst.append("foo")
            except ValueError:
                self.exc_count += 1


class ThreadedReaderTS(threading.Thread):

    def __init__(self):
        super().__init__()
        self.stop = False
        self.daemon = True

    @injector.as_thread_run
    def run(self):
        lst = injector.get(ThreadSafe)
        while not self.stop:
            for item in lst.items():
                pass


class ThreadedWriterTS(threading.Thread):

    def __init__(self):
        super().__init__()
        self.stop = False
        self.exc_count = 0
        self.daemon = True

    @injector.as_thread_run
    def run(self):
        lst = injector.get(ThreadSafe)
        while not self.stop:
            try:
                lst.append("foo")
            except ValueError:
                self.exc_count += 1


class TestThreadedContext(unittest.TestCase):

    def test_threaded_global_failure(self):
        injector.register_constructor(NotThreadSafe, NotThreadSafe, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        try:
            tr = ThreadedReader()
            tr.start()
            tw = ThreadedWriter()
            tw.start()
            for _ in range(0, 100):
                time.sleep(0.01)
                if tw.exc_count > 0:
                    break
            tw.stop = True
            tr.stop = True
            tr.join()
            tw.join()
            self.assertTrue(tw.exc_count > 0)
        finally:
            injector.unregister_constructor(NotThreadSafe, NotThreadSafe)

    def test_threaded_global_success(self):
        injector.register_constructor(ThreadSafe, ThreadSafe, caching_strategy=autoinject.CacheStrategy.GLOBAL_CACHE)
        try:
            tr = ThreadedReaderTS()
            tr.start()
            tw = ThreadedWriterTS()
            tw.start()
            for _ in range(0, 100):
                time.sleep(0.01)
                if tw.exc_count > 0:
                    break
            tw.stop = True
            tr.stop = True
            tr.join()
            tw.join()
            self.assertTrue(tw.exc_count == 0)
        finally:
            injector.unregister_constructor(ThreadSafe, ThreadSafe)


    def test_threaded_context_success(self):
        try:
            injector.register_constructor(NotThreadSafe, NotThreadSafe, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
            tr = ThreadedReader()
            tr.start()
            tw = ThreadedWriter()
            tw.start()
            for _ in range(0, 100):
                time.sleep(0.01)
                if tw.exc_count > 0:
                    break
            tw.stop = True
            tr.stop = True
            tr.join()
            tw.join()
            self.assertTrue(tw.exc_count == 0)
            injector.cache_manager.cleanup()
            self.assertEqual(len(injector.cache_manager.context_cache), 0)
        finally:
            injector.unregister_constructor(NotThreadSafe, NotThreadSafe)

    def test_threaded_context_destroy(self):
        try:
            injector.register_constructor(NotThreadSafe, NotThreadSafe, caching_strategy=autoinject.CacheStrategy.CONTEXT_CACHE)
            tr = ThreadedReader()
            tr.start()
            tw = ThreadedWriter()
            tw.start()
            time.sleep(2)
            tw.stop = True
            tr.stop = True
            tr.join()
            tw.join()
            self.assertTrue(tw.exc_count == 0)
            self.assertEqual(len(injector.cache_manager.context_cache), 0)
        finally:
            injector.unregister_constructor(NotThreadSafe, NotThreadSafe)

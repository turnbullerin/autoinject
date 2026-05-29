import logging
import threading
import os
import datetime
import typing as t


def debug_mode(file_name: str = "./.autoinject.debug", types: t.Optional[t.List[str]] = None, is_multiprocess: bool = False):  # pragma: no cover # not called in testing
    Debugger.DEBUG_TYPES = types or []
    Debugger.DEBUG_FILE_NAME = file_name or None
    Debugger.DEBUG_MULTIPROCESS = is_multiprocess


class Debugger:

    DEBUG_TYPES: t.List[str] = []
    DEBUG_FILE_NAME: t.Optional[str] = None
    DEBUG_MULTIPROCESS: bool = False

    def __init__(self: t.Self) -> None:
        self._logger: logging.Logger = logging.getLogger("autoinject")
        self._file_lock: threading.Lock = threading.Lock()
        self._first_run: bool = True

    def debug(self, msg: str, *args, exc: t.Optional[Exception] = None, debug_type: str = 'other') -> None:
        if exc:  # pragma: no cover # not called in testing
            self._logger.debug(msg, *args, exc_info=(exc.__class__, exc, exc.__traceback__))
        else:
            self._logger.debug(msg, *args)
        if Debugger.DEBUG_FILE_NAME is not None and debug_type in Debugger.DEBUG_TYPES: # pragma: no cover # not called in testing
            with self._file_lock:
                full_name = str(Debugger.DEBUG_FILE_NAME) + (f".{os.getpid()}" if Debugger.DEBUG_MULTIPROCESS else '')
                mode = "w" if self._first_run else "a"
                with open(full_name, mode) as h:
                    self._first_run = False
                    h.write(f"{datetime.datetime.now().strftime('%H:%M:%S')}  {debug_type.ljust(25, ' ')}  {msg % args}\n")

_debugger = Debugger()
def debug(msg: str, *args, exc: t.Optional[Exception] = None, debug_type: str = 'other'):
    _debugger.debug(msg, *args, exc=exc, debug_type=debug_type)
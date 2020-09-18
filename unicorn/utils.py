from contextlib import contextmanager
import time


@contextmanager
def timer():
    start = time.monotonic()
    obj = type('', (), dict(ms=None))
    yield obj
    obj.ms = 1000 * (time.monotonic() - start)

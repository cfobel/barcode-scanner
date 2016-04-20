import contextlib
import os
import sys


@contextlib.contextmanager
def to_devnull(fileno):
    # Redirect c extensions print statements to null
    oldstderr_fno = os.dup(sys.stderr.fileno())
    devnull = open(os.devnull, 'w')
    os.dup2(devnull.fileno(), fileno)
    yield
    os.dup2(oldstderr_fno, fileno)
    devnull.close()

def nostdout():
    return to_devnull(1)

def nostderr():
    return to_devnull(2)



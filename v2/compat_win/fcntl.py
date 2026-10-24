"""Windows-only stand-in for the POSIX `fcntl` module (local development only).

V1 (`src/cost_guard.py`, `src/runner.py`) imports `fcntl` for advisory file locks, which do not exist on Windows.
This directory is put on PYTHONPATH **only on Windows** (see v2/README.md); Linux CI keeps using the real module and no
V1 file is modified.

`flock` is a no-op here. That removes the *cross-process* lock on the cost ledger, so V2 runs on Windows must use a
single process (the in-process `threading.Lock` and semaphore in CostGuard still apply).
"""
import sys

if sys.platform != "win32":  # pragma: no cover - guard against accidental use on POSIX
    raise ImportError("v2/compat_win/fcntl.py is a Windows-only shim; use the real fcntl module")

LOCK_SH = 1
LOCK_EX = 2
LOCK_NB = 4
LOCK_UN = 8


def flock(fd, operation):  # noqa: ARG001 - signature mirrors fcntl.flock
    return None

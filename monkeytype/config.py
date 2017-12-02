# Copyright (c) 2017-present, Facebook, Inc.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree. An additional grant
# of patent rights can be found in the PATENTS file in the same directory.
import os
import sys
import sysconfig

from abc import (
    ABCMeta,
    abstractmethod,
)
from types import CodeType
from typing import Optional

from monkeytype.db.base import (
    CallTraceStore,
    CallTraceStoreLogger,
)
from monkeytype.db.sqlite import SQLiteStore
from monkeytype.tracing import (
    CallTraceLogger,
    CodeFilter,
)
from monkeytype.typing import (
    DEFAULT_REWRITER,
    TypeRewriter,
)


class Config(metaclass=ABCMeta):
    """A Config ties together concrete implementations of the diffrent abstractions
    that make up a typical deployment of MonkeyType.
    """
    @abstractmethod
    def type_rewriter(self) -> TypeRewriter:
        """Return the type rewriter for use when generating stubs."""
        pass

    @abstractmethod
    def trace_store(self) -> CallTraceStore:
        """Return the CallTraceStore for storage/retrieval of call traces."""
        pass

    def trace_logger(self) -> CallTraceLogger:
        """Return the CallTraceLogger for logging call traces.

        By default, returns a CallTraceStoreLogger that logs to the configured
        trace store.
        """
        return CallTraceStoreLogger(self.trace_store())

    def code_filter(self) -> Optional[CodeFilter]:
        """Return the (optional) CodeFilter predicate for triaging calls.

        A CodeFilter is a callable that takes a code object and returns a
        boolean determining whether the call should be traced or not. If None is
        returned, all calls will be traced and logged.
        """
        return None

    def sample_rate(self) -> Optional[int]:
        """Return the sample rate for call tracing.

        By default, all calls will be traced. If an integer sample rate of N is
        set, 1/N calls will be traced.
        """
        return None


lib_paths = {sysconfig.get_path(n) for n in ['stdlib', 'purelib', 'platlib']}
# if in a virtualenv, also exclude the real stdlib location
venv_real_prefix = getattr(sys, 'real_prefix')
if venv_real_prefix:
    lib_paths.add(
        sysconfig.get_path('stdlib', vars={'installed_base': venv_real_prefix})
    )
LIB_PATHS = tuple(p for p in lib_paths if p is not None)


def default_code_filter(code: CodeType) -> bool:
    """A CodeFilter to exclude stdlib and site-packages."""
    return bool(code.co_filename and not code.co_filename.startswith(LIB_PATHS))


class DefaultConfig(Config):
    DB_PATH_VAR = 'MT_DB_PATH'

    def type_rewriter(self) -> TypeRewriter:
        return DEFAULT_REWRITER

    def trace_store(self) -> CallTraceStore:
        """By default we store traces in a local SQLite database.

        The path to this database file can be customized via the `MT_DB_PATH`
        environment variable.
        """
        db_path = os.environ.get(self.DB_PATH_VAR, "monkeytype.sqlite3")
        return SQLiteStore.make_store(db_path)

    def code_filter(self) -> CodeFilter:
        """Default code filter excludes standard library & site-packages."""
        return default_code_filter


DEFAULT_CONFIG = DefaultConfig()
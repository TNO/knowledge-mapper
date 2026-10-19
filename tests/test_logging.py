"""Regression tests for https://github.com/TNO/knowledge-mapper/issues/72.

Host applications often call `logging.basicConfig()` (or otherwise attach a
handler to the root logger) in addition to knowledge_mapper's own handler. If
knowledge_mapper's logger propagates records to the root logger, every record
is emitted twice: once by knowledge_mapper's own handler, once by the host's.
"""

import logging

import knowledge_mapper


def test_package_logger_does_not_propagate():
    """knowledge_mapper's logger must not propagate to ancestor loggers (e.g.
    root), since it already attaches its own handler."""
    logger = logging.getLogger(knowledge_mapper.__name__)
    assert logger.propagate is False


def test_log_record_does_not_reach_host_configured_root_handler():
    """Simulates a host application that configures the root logger (e.g. via
    `logging.basicConfig()`) in addition to knowledge_mapper's own handler.
    The record must not be handled twice, i.e. it must not reach the root
    logger's handler at all."""
    root = logging.getLogger()
    received: list[logging.LogRecord] = []

    class _RecordingHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            received.append(record)

    host_handler = _RecordingHandler()
    root.addHandler(host_handler)
    previous_root_level = root.level
    root.setLevel(logging.DEBUG)
    try:
        child_logger = logging.getLogger(f"{knowledge_mapper.__name__}.some_module")
        child_logger.debug("hello")
        assert received == []
    finally:
        root.removeHandler(host_handler)
        root.setLevel(previous_root_level)

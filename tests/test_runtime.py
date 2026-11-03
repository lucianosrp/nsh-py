"""The runtime's error reporting."""

import logging

from nsh import _runtime


def test_report_exception_logs(caplog):
    try:
        raise ValueError("boom")
    except ValueError as e:
        err = e
    with caplog.at_level(logging.ERROR, logger="nsh"):
        _runtime.report_exception(err)
    assert "Exception in app code" in caplog.text
    assert caplog.records[0].exc_info[1] is err

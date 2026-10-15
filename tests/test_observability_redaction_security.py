import logging

import observability


def test_redacts_quoted_json_and_python_dict_secret_fields():
    assert "JSONSECRET" not in observability.safe_error_text('{"token":"JSONSECRET"}')
    assert "DICTSECRET" not in observability.safe_error_text("{'access_token': 'DICTSECRET'}")
    assert "REDACTED" in observability.safe_error_text('{"token":"JSONSECRET"}')
    assert "REDACTED" in observability.safe_error_text("{'access_token': 'DICTSECRET'}")


def test_capture_exception_does_not_log_original_exc_info(monkeypatch):
    records = []

    class CaptureHandler(logging.Handler):
        def emit(self, record):
            records.append(record)

    logger = logging.getLogger("ai_agent_content_manager")
    handler = CaptureHandler()
    logger.addHandler(handler)
    try:
        try:
            raise RuntimeError('provider failed {"token":"VERYSECRET"}')
        except RuntimeError as exc:
            observability.capture_exception(exc)
    finally:
        logger.removeHandler(handler)

    error_records = [record for record in records if record.levelno >= logging.ERROR]
    assert error_records
    assert all(record.exc_info is None for record in error_records)
    assert all("VERYSECRET" not in record.getMessage() for record in error_records)

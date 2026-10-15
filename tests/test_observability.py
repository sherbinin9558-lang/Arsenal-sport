import logging, unittest
from observability import JsonFormatter, configure_observability, timed_operation, capture_exception

class ObservabilityTests(unittest.TestCase):
    def test_json_formatter(self):
        record=logging.LogRecord('test',logging.INFO,__file__,1,'ok',(),None); record.event='test_event'
        self.assertIn('test_event',JsonFormatter().format(record))
    def test_timing_event(self):
        configure_observability()
        with self.assertLogs('ai_agent_content_manager',level='INFO') as logs:
            with timed_operation('unit_test'): pass
        self.assertTrue(any('unit_test completed' in x for x in logs.output))
    def test_secret_redaction(self):
        configure_observability()
        try: raise RuntimeError('boom')
        except RuntimeError as exc:
            with self.assertLogs('ai_agent_content_manager',level='ERROR') as logs: capture_exception(exc,token='SECRET')
        self.assertTrue(all('SECRET' not in x for x in logs.output))

if __name__=='__main__': unittest.main()

def test_observability_loads_without_sentry_dsn(monkeypatch):
    monkeypatch.delenv("SENTRY_DSN", raising=False)
    import observability
    observability._CONFIGURED = False
    observability._SENTRY = None
    observability.configure_observability()
    assert observability._SENTRY is None


def test_observability_supports_sentry_dsn(monkeypatch):
    monkeypatch.setenv("SENTRY_DSN", "https://examplePublicKey@o0.ingest.sentry.io/0")
    import observability
    observability._CONFIGURED = False
    observability._SENTRY = None
    observability.configure_observability()
    assert observability._CONFIGURED is True


def test_redact_text_removes_credentials_and_email():
    from observability import _redact_text

    raw = (
        "request failed api_key=SECRET123 "
        "Authorization: Bearer BEARERSECRET "
        "https://user:pass@example.com/path?token=QUERYSECRET "
        "bot123456:ABCDEFGHIJKLMNOPQRSTUVWXYZ "
        "owner@example.com"
    )
    safe = _redact_text(raw)
    for secret in (
        "SECRET123", "BEARERSECRET", "user:pass", "QUERYSECRET",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ", "owner@example.com",
    ):
        assert secret not in safe
    assert "[REDACTED]" in safe
    assert "[REDACTED_EMAIL]" in safe


def test_json_formatter_redacts_exception_message():
    import json
    formatter = JsonFormatter()
    try:
        raise RuntimeError("provider failed token=RAWSECRET owner@example.com")
    except RuntimeError as exc:
        record = logging.LogRecord("test", logging.ERROR, __file__, 1, str(exc), (), (type(exc), exc, exc.__traceback__))
    rendered = formatter.format(record)
    assert "RAWSECRET" not in rendered
    assert "owner@example.com" not in rendered
    payload = json.loads(rendered)
    assert payload["exception"]["type"] == "RuntimeError"


def test_capture_exception_sends_only_redacted_exception_to_sentry(monkeypatch):
    import contextlib
    import observability

    class FakeScope:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def set_tag(self, *_args):
            pass

    class FakeSentry:
        captured = None
        def push_scope(self):
            return FakeScope()
        def capture_exception(self, exc):
            self.captured = exc

    fake = FakeSentry()
    monkeypatch.setattr(observability, "_SENTRY", fake)
    try:
        raise RuntimeError("provider failed token=RAW_SENTRY_SECRET email=owner@example.com")
    except RuntimeError as exc:
        with contextlib.redirect_stderr(__import__("io").StringIO()):
            observability.capture_exception(exc)

    assert fake.captured is not None
    assert "RAW_SENTRY_SECRET" not in str(fake.captured)
    assert "owner@example.com" not in str(fake.captured)
    assert fake.captured.__traceback__ is not None


def test_redact_text_removes_provider_key_prefixes():
    from observability import _redact_text

    openai_key = "sk-proj-" + "A" * 36
    stripe_key = "sk_live_" + "B" * 24
    supabase_key = "sb_secret_" + "C" * 24
    safe = _redact_text(f"OpenAI {openai_key} Stripe {stripe_key} Supabase {supabase_key}")
    assert openai_key not in safe
    assert stripe_key not in safe
    assert supabase_key not in safe

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

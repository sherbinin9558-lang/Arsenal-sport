"""Structured production observability for the Streamlit runtime."""
from __future__ import annotations
import json, logging, os, sys, time
from contextlib import contextmanager
from datetime import datetime, timezone

_CONFIGURED = False
_SENTRY = None

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {'ts': datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z'), 'level': record.levelname, 'logger': record.name, 'message': record.getMessage()}
        for key in ('event','operation','duration_ms','component','status','error_type'):
            value = getattr(record, key, None)
            if value is not None: payload[key] = value
        if record.exc_info: payload['exception'] = {'type': record.exc_info[0].__name__, 'message': str(record.exc_info[1])}
        return json.dumps(payload, ensure_ascii=False, separators=(',', ':'))

def configure_observability():
    global _CONFIGURED, _SENTRY
    if _CONFIGURED: return
    root = logging.getLogger('ai_agent_content_manager')
    root.setLevel(logging.INFO)
    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout); handler.setFormatter(JsonFormatter()); root.addHandler(handler)
    root.propagate = False
    dsn = os.getenv('SENTRY_DSN','').strip()
    if dsn:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=dsn, environment=os.getenv('APP_ENV','production'), traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE','0.05')), send_default_pii=False)
            _SENTRY = sentry_sdk
        except Exception: root.warning('Sentry initialization failed', extra={'event':'sentry_init_failed'})
    _CONFIGURED = True

def logger(): configure_observability(); return logging.getLogger('ai_agent_content_manager')

def security_event(event, **context):
    """Emit a structured security audit event without sensitive values."""
    safe = {}
    for key, value in context.items():
        if value is None:
            continue
        if key in ("user_id", "tenant_id", "identity"):
            import hashlib
            safe[key] = hashlib.sha256(str(value).encode("utf-8")).hexdigest()[:16]
        elif any(x in key.lower() for x in ("token", "secret", "password", "authorization", "api_key")):
            safe[key] = "[REDACTED]"
        else:
            safe[key] = str(value)[:200]
    logger().info("security event", extra={"event": "security_audit", "operation": event, **safe})

def capture_exception(exc, **context):
    safe={}
    for key,value in context.items():
        safe[key] = '[REDACTED]' if any(x in key.lower() for x in ('token','secret','password','authorization','api_key')) else str(value)[:300]
    logger().error(str(exc), exc_info=(type(exc),exc,exc.__traceback__), extra={'event':'exception', **safe})
    if _SENTRY is not None:
        try: _SENTRY.capture_exception(exc)
        except Exception: logger().warning('Sentry capture failed', extra={'event':'sentry_capture_failed'})

@contextmanager
def timed_operation(name):
    started=time.perf_counter()
    try: yield
    except Exception as exc:
        duration=round((time.perf_counter()-started)*1000,1); logger().error(str(exc),exc_info=True,extra={'event':'operation_failed','operation':name,'duration_ms':duration}); capture_exception(exc,operation=name); raise
    else:
        duration=round((time.perf_counter()-started)*1000,1); logger().info(name+' completed',extra={'event':'operation_completed','operation':name,'duration_ms':duration})

def record_health(status, component='app', latency_ms=None):
    extra={'event':'healthcheck','component':component,'status':status}
    if latency_ms is not None: extra['duration_ms']=round(float(latency_ms),1)
    logger().info('health '+component+': '+status,extra=extra)

def install_exception_hook():
    configure_observability(); previous=sys.excepthook
    if getattr(previous,'_ai_agent_observability',False): return
    def hook(exc_type,exc_value,exc_traceback):
        capture_exception(exc_value,event='uncaught_exception'); previous(exc_type,exc_value,exc_traceback)
    hook._ai_agent_observability=True; sys.excepthook=hook
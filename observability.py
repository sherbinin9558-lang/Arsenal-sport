"""Structured production observability for the Streamlit runtime."""
from __future__ import annotations
import json, logging, os, re, sys, time
from contextlib import contextmanager
from datetime import datetime, timezone

_CONFIGURED = False
_SENTRY = None

# Redact secrets in exception messages before they reach stdout or Sentry.
_SECRET_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(password|passwd|secret|api[_-]?key|access[_-]?token|refresh[_-]?token|"
    r"authorization|service[_-]?role[_-]?key|client[_-]?secret|signature)\b"
    r"(\s*[:=]\s*)(?:\"[^\"]*\"|'[^']*'|[^\s,;&]+)"
)
_BEARER_RE = re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._~+/=-]+")
_TELEGRAM_BOT_TOKEN_RE = re.compile(r"(?i)\bbot\d{5,}:[A-Za-z0-9_-]{20,}")
_JWT_RE = re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b")
_URL_CREDENTIALS_RE = re.compile(r"(://)[^/@\s:]+:[^/@\s]+@")
_QUERY_SECRET_RE = re.compile(r"(?i)([?&](?:token|key|secret|password|signature|authorization)=)[^&\s]+")
_EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def _redact_text(value):
    """Return bounded log-safe text without common credential/PII patterns."""
    text = str(value or "")
    text = _SECRET_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]", text)
    text = _BEARER_RE.sub("Bearer [REDACTED]", text)
    text = _TELEGRAM_BOT_TOKEN_RE.sub("bot[REDACTED]", text)
    text = _JWT_RE.sub("[REDACTED_JWT]", text)
    text = _URL_CREDENTIALS_RE.sub(r"\1[REDACTED]@", text)
    text = _QUERY_SECRET_RE.sub(r"\1[REDACTED]", text)
    text = _EMAIL_RE.sub("[REDACTED_EMAIL]", text)
    return text[:2000]

class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {'ts': datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00','Z'), 'level': record.levelname, 'logger': record.name, 'message': _redact_text(record.getMessage())}
        for key in ('event','operation','duration_ms','component','status','error_type'):
            value = getattr(record, key, None)
            if value is not None: payload[key] = value
        if record.exc_info: payload['exception'] = {'type': record.exc_info[0].__name__, 'message': _redact_text(record.exc_info[1])}
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
            safe[key] = _redact_text(str(value)[:200])
    logger().info("security event", extra={"event": "security_audit", "operation": event, **safe})

def capture_exception(exc, **context):
    safe={}
    for key,value in context.items():
        safe[key] = '[REDACTED]' if any(x in key.lower() for x in ('token','secret','password','authorization','api_key')) else _redact_text(str(value)[:300])
    logger().error(_redact_text(str(exc)), exc_info=(type(exc),exc,exc.__traceback__), extra={'event':'exception', 'error_type': type(exc).__name__, **safe})
    if _SENTRY is not None:
        try:
            # Preserve the stack trace while ensuring the exception value sent to
            # Sentry is sanitized. The original exception object may contain URLs,
            # provider response fragments, or credentials.
            safe_exc = RuntimeError(_redact_text(str(exc)) or "Unhandled exception")
            with _SENTRY.push_scope() as scope:
                scope.set_tag("original_exception_type", type(exc).__name__)
                _SENTRY.capture_exception(safe_exc.with_traceback(exc.__traceback__))
        except Exception: logger().warning('Sentry capture failed', extra={'event':'sentry_capture_failed'})

@contextmanager
def timed_operation(name):
    started=time.perf_counter()
    try: yield
    except Exception as exc:
        duration=round((time.perf_counter()-started)*1000,1); logger().error(_redact_text(str(exc)),exc_info=True,extra={'event':'operation_failed','operation':name,'duration_ms':duration}); capture_exception(exc,operation=name); raise
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
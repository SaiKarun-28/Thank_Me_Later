"""
Per-request security utilities, ContextVar secret registry, and logging sanitizers.
Zero backend persistence & zero secret leakage.
"""
import contextvars
import ipaddress
import logging
import re
from typing import Optional, Set
from urllib.parse import urlparse

# Request-scoped isolated registry for sensitive values (keys, tokens, passwords)
active_secrets: contextvars.ContextVar[Set[str]] = contextvars.ContextVar("active_secrets", default=set())

# Common API key token patterns (Groq, Gemini, NVIDIA, Mistral, OpenRouter, generic Bearer)
TOKEN_PATTERNS = [
    re.compile(r"gsk_[a-zA-Z0-9]{20,}", re.IGNORECASE),
    re.compile(r"AIza[0-9A-Za-z\-_]{20,}", re.IGNORECASE),
    re.compile(r"nvapi-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"csk-[a-zA-Z0-9_\-]{20,}", re.IGNORECASE),
    re.compile(r"Bearer\s+[A-Za-z0-9_\-\.]{15,}", re.IGNORECASE),
    re.compile(r"SENTINEL-[a-zA-Z0-9_\-]+", re.IGNORECASE),
]


def register_secret(secret: Optional[str]) -> None:
    """Register a secret string into the current request context for automated scrubbing."""
    if not secret:
        return
    cleaned = str(secret).strip()
    # Avoid scrubbing trivial short strings like 'yes', 'true', empty
    if len(cleaned) < 4:
        return
    current = set(active_secrets.get())
    current.add(cleaned)
    active_secrets.set(current)


def redact_text(text: str) -> str:
    """
    Scrub all registered active secrets and known API key patterns from text.
    Replaces matches with [REDACTED].
    """
    if not text:
        return ""
    
    redacted = str(text)

    # 1. Exact matches for active request secrets
    current_secrets = active_secrets.get()
    for secret in current_secrets:
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "[REDACTED]")

    # 2. Known regex token patterns
    for pattern in TOKEN_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)

    return redacted


class SecretRedactingLoggingFilter(logging.Filter):
    """
    Logging filter that sanitizes record messages and arguments,
    ensuring no active secrets or API key patterns are written to stdout or logs.
    """
    def filter(self, record: logging.LogRecord) -> bool:
        try:
            if isinstance(record.msg, str):
                record.msg = redact_text(record.msg)
            elif hasattr(record, "msg") and record.msg is not None:
                record.msg = redact_text(str(record.msg))

            if record.args:
                if isinstance(record.args, dict):
                    record.args = {k: redact_text(str(v)) if isinstance(v, str) else v for k, v in record.args.items()}
                elif isinstance(record.args, (list, tuple)):
                    record.args = tuple(redact_text(str(arg)) if isinstance(arg, str) else arg for arg in record.args)
        except Exception:
            # Never let logging filter failure abort application flow
            pass
        return True


def configure_secure_logging() -> None:
    """
    Configures root logging with SecretRedactingLoggingFilter
    and suppresses noisy/sensitive third-party HTTP logs.
    """
    redacting_filter = SecretRedactingLoggingFilter()
    root_logger = logging.getLogger()
    
    # Attach filter to root logger and all existing handlers
    root_logger.addFilter(redacting_filter)
    for handler in root_logger.handlers:
        handler.addFilter(redacting_filter)

    # Silence httpx and httpcore loggers to WARNING and redact query strings/urls
    for name in ("httpx", "httpcore", "urllib3"):
        logger = logging.getLogger(name)
        logger.setLevel(logging.WARNING)
        logger.addFilter(redacting_filter)


def sanitize_url(url: Optional[str]) -> Optional[str]:
    """
    Validates outbound job application URLs.
    Enforces HTTP/HTTPS protocol, rejects non-web schemes (e.g. javascript:, file:),
    and rejects private/local IPs.
    Returns cleaned URL string or None if invalid.
    """
    if not url or not isinstance(url, str):
        return None
    
    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
        if parsed.scheme.lower() not in ("http", "https"):
            return None
        
        hostname = parsed.hostname
        if not hostname:
            return None
        
        hostname_lower = hostname.lower()
        if hostname_lower in ("localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal", "::1"):
            return None

        # Check for private IP ranges (e.g. 10.x, 192.168.x, 169.254.x)
        try:
            ip = ipaddress.ip_address(hostname_lower)
            if ip.is_private or ip.is_loopback or ip.is_link_local:
                return None
        except ValueError:
            # Not an IP address string, which is normal for domain names
            pass

        return cleaned
    except Exception:
        return None

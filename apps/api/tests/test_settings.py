from app.observability import log_event, redact
from app.settings import Settings


def test_settings_summary_never_contains_api_key():
    settings = Settings(llm_enabled=True, llm_api_key="super-secret", supabase_url="https://example.supabase.co")
    summary = settings.safe_runtime_summary()
    assert "llm_api_key" not in summary
    assert summary["supabase_configured"] is True


def test_redaction_removes_secret_looking_values():
    assert redact({"api_key": "not-for-logs", "code": "def f(): pass"}) == {"api_key": "[REDACTED]", "code": "def f(): pass"}


def test_structured_event_redacts_secret_values(caplog):
    with caplog.at_level("INFO", logger="complexity_library"):
        log_event("analysis.completed", request_id="trace-123", llm_api_key="private-value")
    assert "trace-123" in caplog.text
    assert "private-value" not in caplog.text
    assert "[REDACTED]" in caplog.text

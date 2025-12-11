from app.services.session_manager import SessionManager


def test_session_manager_set_get():
    sm = SessionManager(ttl_seconds=2)
    assert sm.get() is None
    sm.set("abc123")
    assert sm.get() == "abc123"


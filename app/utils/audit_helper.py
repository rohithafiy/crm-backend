from datetime import datetime, timezone

from app.utils import db as _db


def log_audit(actor, action, target, metadata=None):
    """Immutable audit logging for security compliance.
    Stores metadata: Timestamp, Actor, Action, Target
    """
    try:
        db = _db.get_db()
        db.audit_logs.insert_one({
            "timestamp": datetime.now(timezone.utc),
            "actor": actor,
            "action": action,
            "target": target,
            "metadata": metadata or {}
        })
    except Exception as e:
        # Prevent audit logging failure from crashing main request thread, but log it
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Audit log insertion failed: {e}")

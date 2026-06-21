"""
Portal 5 - CRM & Client Management
Activity Service: Aggregated activity logging and retrieval

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from bson import ObjectId
from app.database.db import db_manager

logger = logging.getLogger(__name__)


class ActivityService:
    """Service encapsulating CRM activity feed business logic."""

    @staticmethod
    def log_activity(
        action: str,
        performed_by: str,
        details: str,
        resource_type: str,
        resource_id: str,
        status: str = "success"
    ) -> dict[str, Any]:
        """
        Create a new log entry in p5_activity_logs.

        Args:
            action: Action string (e.g. 'lead_created')
            performed_by: User ID performing the action
            details: Human-readable details
            resource_type: 'lead', 'client', or 'communication'
            resource_id: Resource ID string/ObjectId
            status: 'success' or 'rejected'

        Returns:
            The created log document dict
        """
        db = db_manager.db
        logs = db["p5_activity_logs"]

        doc = {
            "action": action,
            "performed_by": performed_by,
            "details": details,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
            "timestamp": datetime.now(timezone.utc)
        }

        try:
            logs.insert_one(doc)
            logger.info("Activity logged: %s - %s", action, details)
        except Exception:
            logger.exception("Failed to write to p5_activity_logs")

        return doc

    @staticmethod
    def get_activities(limit: int = 50) -> list[dict[str, Any]]:
        """
        Fetch recent activities from p5_activity_logs, sorted by newest first.

        Args:
            limit: Maximum logs to return (default 50)

        Returns:
            List of serialized activity log dicts
        """
        db = db_manager.db
        logs = db["p5_activity_logs"]
        records = list(logs.find().sort("timestamp", -1).limit(limit))

        serialized = []
        for r in records:
            serialized.append({
                "id": str(r["_id"]),
                "action": r.get("action"),
                "performed_by": r.get("performed_by"),
                "details": r.get("details"),
                "resource_type": r.get("resource_type"),
                "resource_id": str(r.get("resource_id")),
                "status": r.get("status"),
                "timestamp": r["timestamp"].isoformat() if isinstance(r.get("timestamp"), datetime) else None
            })
        return serialized

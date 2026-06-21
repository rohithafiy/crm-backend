"""
Portal 5 - CRM & Client Management
Pipeline Service: Stage management and board aggregation

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId

from app.database.db import get_leads_collection
from app.models.p5_lead import LeadStatus, serialize_lead
from app.validators.pipeline_validator import validate_stage_transition

logger = logging.getLogger(__name__)


class PipelineService:
    """Service for pipeline stage management and board views."""

    # ------------------------------------------------------------------ #
    #  UPDATE STAGE                                                        #
    # ------------------------------------------------------------------ #

    @staticmethod
    def update_stage(
        lead_id: str,
        new_status: str,
        updated_by: str,
    ) -> Optional[dict[str, Any]]:
        """
        Move a lead to a new pipeline stage.

        Enforces allowed transition rules.

        Args:
            lead_id: MongoDB ObjectId string
            new_status: Target stage
            updated_by: User ID from JWT

        Returns:
            Updated serialized lead or None if not found

        Raises:
            ValueError: On invalid ID or illegal transition
        """
        try:
            oid = ObjectId(lead_id)
        except InvalidId:
            raise ValueError(f"'{lead_id}' is not a valid lead ID.")

        collection = get_leads_collection()
        lead = collection.find_one({"_id": oid, "is_deleted": False})
        if not lead:
            return None

        current_status = lead.get("status", LeadStatus.NEW)
        errors = validate_stage_transition(current_status, new_status)
        if errors:
            raise ValueError(errors[0])

        collection.update_one(
            {"_id": oid},
            {"$set": {"status": new_status, "updated_at": datetime.now(timezone.utc)}},
        )

        logger.info(
            "Pipeline: lead %s moved %s → %s by %s",
            lead_id,
            current_status,
            new_status,
            updated_by,
        )

        updated = collection.find_one({"_id": oid})
        return serialize_lead(updated)

    # ------------------------------------------------------------------ #
    #  GET BOARD                                                           #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_pipeline_board() -> dict[str, list[dict]]:
        """
        Return all active leads grouped by pipeline stage.

        Returns:
            Dict mapping stage name → list of serialized leads,
            sorted by updated_at descending within each stage.
        """
        collection = get_leads_collection()

        # Initialize board with all stages (preserves order even for empty stages)
        board: dict[str, list[dict]] = {stage.value: [] for stage in LeadStatus}

        leads = list(
            collection.find({"is_deleted": False}).sort("updated_at", -1)
        )

        for lead in leads:
            stage = lead.get("status", LeadStatus.NEW)
            if stage in board:
                board[stage].append(serialize_lead(lead))

        return board

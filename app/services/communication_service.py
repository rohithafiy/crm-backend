"""
Portal 5 - CRM & Client Management
Communication Service: Timeline logging and history retrieval

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId

from app.database.db import get_communications_collection
from app.models.communication_model import (
    CommunicationType,
    build_communication_document,
    serialize_communication,
)

logger = logging.getLogger(__name__)

VALID_TYPES = {t.value for t in CommunicationType}


def _validate_communication_payload(data: dict[str, Any]) -> list[str]:
    """
    Validate a communication creation payload.

    Args:
        data: Request JSON payload

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []

    # Accept either `type` or `communication_type` as the field
    comm_type = (data.get("type") or data.get("communication_type") or "").strip()
    if not comm_type:
        errors.append("'type' is required.")
    elif comm_type not in VALID_TYPES:
        errors.append(
            f"Invalid type '{comm_type}'. Allowed: {sorted(VALID_TYPES)}."
        )

    if not data.get("content", "").strip():
        errors.append("'content' is required and cannot be empty.")

    if not data.get("client_id") and not data.get("lead_id"):
        errors.append("Either 'client_id' or 'lead_id' must be provided.")

    return errors


class CommunicationService:
    """Service for communication history management."""

    # ------------------------------------------------------------------ #
    #  CREATE                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_communication(
        data: dict[str, Any], created_by: str
    ) -> tuple[dict[str, Any], list[str]]:
        """
        Log a new communication entry.

        Args:
            data: Validated communication payload
            created_by: User ID from JWT

        Returns:
            (serialized_doc, errors) tuple
        """
        errors = _validate_communication_payload(data)
        if errors:
            return {}, errors

        # Validate ObjectId references if provided
        if data.get("client_id"):
            try:
                data["client_id"] = ObjectId(data["client_id"])
            except InvalidId:
                return {}, [f"'{data['client_id']}' is not a valid client_id."]

        if data.get("lead_id"):
            try:
                data["lead_id"] = ObjectId(data["lead_id"])
            except InvalidId:
                return {}, [f"'{data['lead_id']}' is not a valid lead_id."]

        collection = get_communications_collection()
        doc = build_communication_document(data, created_by)
        result = collection.insert_one(doc)
        doc["_id"] = result.inserted_id

        logger.info(
            "Communication created: %s (type=%s) by %s",
            result.inserted_id,
            data.get("type"),
            created_by,
        )

        return serialize_communication(doc), []

    # ------------------------------------------------------------------ #
    #  GET BY CLIENT                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_by_client(
        client_id: str,
        comm_type: Optional[str] = None,
        order: str = "desc",
    ) -> tuple[list[dict], list[str]]:
        """
        Retrieve communication timeline for a client.

        Args:
            client_id: MongoDB ObjectId string
            comm_type: Optional type filter

        Returns:
            (records, errors) tuple
        """
        try:
            oid = ObjectId(client_id)
        except InvalidId:
            return [], [f"'{client_id}' is not a valid client ID."]

        collection = get_communications_collection()
        query: dict[str, Any] = {"client_id": oid}

        if comm_type:
            if comm_type not in VALID_TYPES:
                return [], [
                    f"Invalid type '{comm_type}'. Allowed: {sorted(VALID_TYPES)}."
                ]
            query["type"] = comm_type
        # Determine sort order: 'asc' for oldest-first, 'desc' for newest-first
        sort_dir = -1 if order.lower() == "desc" else 1

        if order.lower() not in {"asc", "desc"}:
            return [], ["Invalid 'order' value. Allowed: 'asc', 'desc'."]

        records = list(collection.find(query).sort("created_at", sort_dir))
        return [serialize_communication(r) for r in records], []

    # ------------------------------------------------------------------ #
    #  GET BY LEAD                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_by_lead(
        lead_id: str,
        comm_type: Optional[str] = None,
        order: str = "desc",
    ) -> tuple[list[dict], list[str]]:
        """
        Retrieve communication timeline for a lead.

        Args:
            lead_id: MongoDB ObjectId string
            comm_type: Optional type filter

        Returns:
            (records, errors) tuple
        """
        try:
            oid = ObjectId(lead_id)
        except InvalidId:
            return [], [f"'{lead_id}' is not a valid lead ID."]

        collection = get_communications_collection()
        query: dict[str, Any] = {"lead_id": oid}

        if comm_type:
            if comm_type not in VALID_TYPES:
                return [], [
                    f"Invalid type '{comm_type}'. Allowed: {sorted(VALID_TYPES)}."
                ]
            query["type"] = comm_type
        # Determine sort order: 'asc' for oldest-first, 'desc' for newest-first
        sort_dir = -1 if order.lower() == "desc" else 1

        if order.lower() not in {"asc", "desc"}:
            return [], ["Invalid 'order' value. Allowed: 'asc', 'desc'."]

        records = list(collection.find(query).sort("created_at", sort_dir))
        return [serialize_communication(r) for r in records], []

    # ------------------------------------------------------------------ #
    #  DELETE                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def delete_communication(comm_id: str) -> tuple[bool, Optional[str]]:
        """
        Hard-delete a communication timeline entry.

        Args:
            comm_id: MongoDB ObjectId string

        Returns:
            (success, error_message) tuple
        """
        try:
            oid = ObjectId(comm_id)
        except InvalidId:
            return False, f"'{comm_id}' is not a valid communication ID."

        collection = get_communications_collection()
        result = collection.delete_one({"_id": oid})
        return result.deleted_count > 0, None


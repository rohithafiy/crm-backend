"""
Portal 5 - CRM & Client Management
Client Service: Business logic for all client operations

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.database.db import get_clients_collection
from app.models.p5_client import build_client_document, serialize_client
from app.utils.phone_helper import normalize_phone
from app.utils.pagination_helper import build_pagination_query
from app.services.communication_service import CommunicationService

logger = logging.getLogger(__name__)


class ClientService:
    """Service class encapsulating all client business logic."""

    # ------------------------------------------------------------------ #
    #  CREATE                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_client(
        data: dict[str, Any],
        created_by: str,
        lead_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new client record.

        Args:
            data: Validated client payload
            created_by: User ID from JWT
            lead_id: Optional originating lead ID

        Returns:
            Serialized client document

        Raises:
            ValueError: On duplicate email
        """
        collection = get_clients_collection()

        existing = collection.find_one(
            {"email": data["email"].strip().lower(), "is_deleted": False}
        )
        if existing:
            raise ValueError(
                f"A client with email '{data['email']}' already exists "
                f"(id: {str(existing['_id'])})."
            )

        # Normalize phone for duplicate detection and storage
        pn = normalize_phone(data.get("phone"))
        if pn:
            existing_phone = collection.find_one({"phone_normalized": pn, "is_deleted": False})
            if existing_phone:
                raise ValueError(
                    f"A client with phone '{data.get('phone')}' already exists (id: {str(existing_phone['_id'])})."
                )

        doc = build_client_document(data, created_by, lead_id=lead_id)

        try:
            result = collection.insert_one(doc)
            doc["_id"] = result.inserted_id
            logger.info("Client created: %s by %s", result.inserted_id, created_by)
            return serialize_client(doc)
        except DuplicateKeyError:
            raise ValueError(
                f"A client with email '{data['email']}' already exists."
            )

    # ------------------------------------------------------------------ #
    #  READ — LIST                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_clients(
        page: int,
        limit: int,
        status: Optional[str] = None,
        industry: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        assigned_user: Optional[str] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], int]:
        """
        List clients with filtering, search, and pagination.

        Args:
            page: Page number (1-indexed)
            limit: Records per page
            status: Optional status filter
            industry: Optional industry filter
            search: Optional full-text search term

        Returns:
            (records, total_count) tuple
        """
        collection = get_clients_collection()
        query: dict[str, Any] = {"is_deleted": False}

        if status:
            query["status"] = status
        if industry:
            query["industry"] = {"$regex": industry, "$options": "i"}
        if assigned_user:
            query["user_id"] = assigned_user

        # Date range filtering on created_at (ISO8601 expected)
        from datetime import datetime
        created_query = {}
        if date_from:
            try:
                created_query["$gte"] = datetime.fromisoformat(date_from)
            except Exception:
                raise ValueError("Invalid date_from format. Expected ISO 8601.")
        if date_to:
            try:
                created_query["$lte"] = datetime.fromisoformat(date_to)
            except Exception:
                raise ValueError("Invalid date_to format. Expected ISO 8601.")
        if created_query:
            query["created_at"] = created_query
        # date range filtering on created_at
        from datetime import datetime
        date_from = None
        date_to = None
        # caller may pass via kwargs in future; ignore if not provided
        # (route will pass these in recent changes)
        # If provided in query dict (search service style), attempt to use
        # but for now we'll read from environment via optional params later.
        if search:
            query["$or"] = [
                {"company_name": {"$regex": search, "$options": "i"}},
                {"contact_person": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]

        total = collection.count_documents(query)
        skip, lim = build_pagination_query(page, limit)

        allowed = {"created_at", "updated_at", "company_name", "contact_person", "email", "status"}
        sf = sort_field if sort_field in allowed else "created_at"
        sd = -1 if sort_order.lower() == "desc" else 1

        clients = list(
            collection.find(query)
            .sort(sf, sd)
            .skip(skip)
            .limit(lim)
        )

        return [serialize_client(c) for c in clients], total

    # ------------------------------------------------------------------ #
    #  READ — SINGLE                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_client_by_id(client_id: str) -> Optional[dict[str, Any]]:
        """
        Fetch a single active client by ID.

        Args:
            client_id: MongoDB ObjectId string

        Returns:
            Serialized client or None

        Raises:
            ValueError: On invalid ObjectId format
        """
        try:
            oid = ObjectId(client_id)
        except InvalidId:
            raise ValueError(f"'{client_id}' is not a valid client ID.")

        collection = get_clients_collection()
        client = collection.find_one({"_id": oid, "is_deleted": False})
        if not client:
            return None

        # Attach communication history
        try:
            comms, errors = CommunicationService.get_by_client(str(client_id))
        except Exception:
            comms = []

        serialized = serialize_client(client)
        serialized["communications"] = comms
        return serialized

    # ------------------------------------------------------------------ #
    #  UPDATE                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def update_client(
        client_id: str, data: dict[str, Any], updated_by: str = "system"
    ) -> Optional[dict[str, Any]]:
        """
        Partially update a client document.

        Args:
            client_id: MongoDB ObjectId string
            data: Fields to update

        Returns:
            Updated serialized client or None if not found

        Raises:
            ValueError: On invalid ID or duplicate email
        """
        try:
            oid = ObjectId(client_id)
        except InvalidId:
            raise ValueError(f"'{client_id}' is not a valid client ID.")

        collection = get_clients_collection()
        client = collection.find_one({"_id": oid, "is_deleted": False})
        if not client:
            return None

        if "email" in data:
            new_email = data["email"].strip().lower()
            duplicate = collection.find_one({
                "email": new_email,
                "is_deleted": False,
                "_id": {"$ne": oid},
            })
            if duplicate:
                raise ValueError(
                    f"Another client with email '{new_email}' already exists."
                )
            data["email"] = new_email

        # If phone updated, normalize and check duplicates
        if "phone" in data:
            pn = normalize_phone(data.get("phone"))
            if pn:
                duplicate = collection.find_one({
                    "phone_normalized": pn,
                    "is_deleted": False,
                    "_id": {"$ne": oid},
                })
                if duplicate:
                    raise ValueError(f"Another client with phone '{data.get('phone')}' already exists.")
            data["phone_normalized"] = pn

        protected = {"_id", "created_at", "created_by", "lead_id", "is_deleted"}
        updates = {k: v for k, v in data.items() if k not in protected}
        updates["updated_at"] = datetime.utcnow()

        collection.update_one({"_id": oid}, {"$set": updates})

        # Log activity
        try:
            from app.services.activity_service import ActivityService
            ActivityService.log_activity(
                action="client_updated",
                performed_by=updated_by,
                details=f"Client updated fields: {', '.join(list(updates.keys()))}",
                resource_type="client",
                resource_id=client_id
            )
        except Exception:
            logger.exception("Failed to log activity for client update %s", client_id)

        updated = collection.find_one({"_id": oid})
        return serialize_client(updated)

    # ------------------------------------------------------------------ #
    #  DELETE (soft)                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def delete_client(client_id: str, deleted_by: str = "system") -> bool:
        """
        Soft-delete a client.

        Args:
            client_id: MongoDB ObjectId string

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: On invalid ObjectId format
        """
        try:
            oid = ObjectId(client_id)
        except InvalidId:
            raise ValueError(f"'{client_id}' is not a valid client ID.")

        collection = get_clients_collection()
        result = collection.update_one(
            {"_id": oid, "is_deleted": False},
            {"$set": {"is_deleted": True, "deleted_at": datetime.utcnow(), "updated_at": datetime.utcnow()}},
        )
        if result.modified_count > 0:
            try:
                from app.services.activity_service import ActivityService
                ActivityService.log_activity(
                    action="client_deleted",
                    performed_by=deleted_by,
                    details="Client soft-deleted",
                    resource_type="client",
                    resource_id=client_id
                )
            except Exception:
                logger.exception("Failed to log activity for client deletion %s", client_id)
        return result.modified_count > 0

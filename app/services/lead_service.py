"""
Portal 5 - CRM & Client Management
Lead Service: Business logic for all lead operations

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from datetime import datetime
from typing import Any, Optional

from bson import ObjectId
from bson.errors import InvalidId
from pymongo.errors import DuplicateKeyError

from app.database.db import get_leads_collection
from app.models.p5_lead import (
    LeadStatus,
    build_lead_document,
    serialize_lead,
)
from app.utils.phone_helper import normalize_phone
from app.utils.pagination_helper import build_pagination_query

logger = logging.getLogger(__name__)


def parse_date(date_str: Any) -> Optional[datetime]:
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return date_str
    try:
        return datetime.fromisoformat(str(date_str).replace("Z", "+00:00"))
    except Exception:
        return None


class LeadService:
    """Service class encapsulating all lead business logic."""

    # ------------------------------------------------------------------ #
    #  CREATE                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def create_lead(data: dict[str, Any], created_by: str) -> dict[str, Any]:
        """
        Create a new lead with duplicate email prevention.

        Args:
            data: Validated lead payload
            created_by: User ID from JWT

        Returns:
            Serialized lead document

        Raises:
            ValueError: On duplicate email
        """
        collection = get_leads_collection()

        # Check for existing active lead with same email
        existing = collection.find_one(
            {"email": data["email"].strip().lower(), "is_deleted": False}
        )
        if existing:
            raise ValueError(
                f"A lead with email '{data['email']}' already exists "
                f"(id: {str(existing['_id'])})."
            )

        # Normalize phone for duplicate-check
        pn = normalize_phone(data.get("phone"))
        if pn:
            existing_phone = collection.find_one({"phone_normalized": pn, "is_deleted": False})
            if existing_phone:
                raise ValueError(
                    f"A lead with phone '{data.get('phone')}' already exists (id: {str(existing_phone['_id'])})."
                )

        # Parse follow_up_date
        if "follow_up_date" in data:
            data["follow_up_date"] = parse_date(data["follow_up_date"])

        # Normalize assigned_to to ObjectId when possible and record initial assignment
        if data.get("assigned_to"):
            try:
                data["assigned_to"] = ObjectId(data["assigned_to"])
            except Exception:
                # leave as-is (string) if not a valid ObjectId
                pass

        doc = build_lead_document(data, created_by)

        # If initial assignee present, create an assignment history entry
        if doc.get("assigned_to"):
            try:
                assignment_entry = {
                    "assigned_to": doc.get("assigned_to"),
                    "assigned_by": created_by,
                    "note": data.get("assignment_note", ""),
                    "assigned_at": datetime.utcnow(),
                }
                doc.setdefault("assignment_history", []).append(assignment_entry)
            except Exception:
                logger.exception("Failed to attach initial assignment for lead")

        try:
            # Add initial audit log
            doc.setdefault("audit_logs", []).append({
                "action": "create",
                "performed_by": created_by,
                "details": f"Lead created (email={data.get('email')})",
                "timestamp": datetime.utcnow(),
            })
            result = collection.insert_one(doc)
            doc["_id"] = result.inserted_id
            logger.info("Lead created: %s by %s", result.inserted_id, created_by)

            # Log to aggregated activity feed
            try:
                from app.services.activity_service import ActivityService
                ActivityService.log_activity(
                    action="lead_created",
                    performed_by=created_by,
                    details=f"Lead '{doc.get('full_name')}' created.",
                    resource_type="lead",
                    resource_id=str(result.inserted_id)
                )
            except Exception:
                logger.exception("Failed to log activity event for lead creation")

            return serialize_lead(doc)
        except DuplicateKeyError:
            raise ValueError(
                f"A lead with email '{data['email']}' already exists."
            )

    # ------------------------------------------------------------------ #
    #  READ — LIST                                                         #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_leads(
        page: int,
        limit: int,
        status: Optional[str] = None,
        assigned_to: Optional[str] = None,
        source: Optional[str] = None,
        search: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        pipeline_stage: Optional[str] = None,
        sort_field: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[list[dict], int]:
        """
        List leads with filtering, search, and pagination.

        Args:
            page: Page number (1-indexed)
            limit: Records per page
            status: Optional status filter
            assigned_to: Optional assignee user ID filter
            source: Optional source filter
            search: Optional full-text search term

        Returns:
            (records, total_count) tuple
        """
        collection = get_leads_collection()
        query: dict[str, Any] = {"is_deleted": False}

        # pipeline_stage is an alias for status
        if pipeline_stage and not status:
            status = pipeline_stage

        if status:
            query["status"] = status
        if assigned_to:
            query["assigned_to"] = assigned_to
        if source:
            query["source"] = source
        if search:
            query["$or"] = [
                {"full_name": {"$regex": search, "$options": "i"}},
                {"company_name": {"$regex": search, "$options": "i"}},
                {"email": {"$regex": search, "$options": "i"}},
            ]

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

        total = collection.count_documents(query)
        skip, lim = build_pagination_query(page, limit)

        # Sorting
        allowed = {"created_at", "updated_at", "full_name", "company_name", "email", "status"}
        sf = sort_field if sort_field in allowed else "created_at"
        sd = -1 if sort_order.lower() == "desc" else 1

        leads = list(
            collection.find(query)
            .sort(sf, sd)
            .skip(skip)
            .limit(lim)
        )

        return [serialize_lead(lead) for lead in leads], total

    # ------------------------------------------------------------------ #
    #  READ — SINGLE                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def get_lead_by_id(lead_id: str) -> Optional[dict[str, Any]]:
        """
        Fetch a single active lead by ID.

        Args:
            lead_id: MongoDB ObjectId string

        Returns:
            Serialized lead or None if not found

        Raises:
            ValueError: On invalid ObjectId format
        """
        try:
            oid = ObjectId(lead_id)
        except InvalidId:
            raise ValueError(f"'{lead_id}' is not a valid lead ID.")

        collection = get_leads_collection()
        lead = collection.find_one({"_id": oid, "is_deleted": False})
        return serialize_lead(lead) if lead else None

    # ------------------------------------------------------------------ #
    #  UPDATE                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def update_lead(lead_id: str, data: dict[str, Any], updated_by: str = "system") -> Optional[dict[str, Any]]:
        """
        Partially update a lead document.

        Args:
            lead_id: MongoDB ObjectId string
            data: Fields to update
            updated_by: User ID performing update

        Returns:
            Updated serialized lead or None if not found

        Raises:
            ValueError: On invalid ID or duplicate email
        """
        try:
            oid = ObjectId(lead_id)
        except InvalidId:
            raise ValueError(f"'{lead_id}' is not a valid lead ID.")

        collection = get_leads_collection()
        lead = collection.find_one({"_id": oid, "is_deleted": False})
        if not lead:
            return None

        # Parse follow_up_date
        if "follow_up_date" in data:
            data["follow_up_date"] = parse_date(data["follow_up_date"])

        # If email is being changed, check for duplicates
        if "email" in data:
            new_email = data["email"].strip().lower()
            duplicate = collection.find_one({
                "email": new_email,
                "is_deleted": False,
                "_id": {"$ne": oid},
            })
            if duplicate:
                raise ValueError(
                    f"Another lead with email '{new_email}' already exists."
                )
            data["email"] = new_email

        # Sanitize and build $set payload
        protected = {"_id", "created_at", "created_by", "assignment_history", "is_deleted", "assigned_to"}
        updates = {k: v for k, v in data.items() if k not in protected}
        updates["updated_at"] = datetime.utcnow()

        if "estimated_value" in updates and updates["estimated_value"] is not None:
            updates["estimated_value"] = float(updates["estimated_value"])

        collection.update_one({"_id": oid}, {"$set": updates})
        # Append audit log for the update
        try:
            audit_entry = {
                "action": "update",
                "performed_by": updated_by,
                "details": f"Updated fields: {', '.join(list(updates.keys()))}",
                "timestamp": datetime.utcnow(),
            }
            collection.update_one({"_id": oid}, {"$push": {"audit_logs": audit_entry}})
        except Exception:
            logger.exception("Failed to append audit log for lead %s", lead_id)

        # Log to aggregated activity feed
        try:
            from app.services.activity_service import ActivityService
            ActivityService.log_activity(
                action="lead_updated",
                performed_by=updated_by,
                details=f"Lead updated fields: {', '.join(list(updates.keys()))}",
                resource_type="lead",
                resource_id=lead_id
            )
        except Exception:
            logger.exception("Failed to log activity event for lead update")

        updated = collection.find_one({"_id": oid})
        return serialize_lead(updated)

    # ------------------------------------------------------------------ #
    #  DELETE (soft)                                                       #
    # ------------------------------------------------------------------ #

    @staticmethod
    def delete_lead(lead_id: str, deleted_by: str = "system") -> bool:
        """
        Soft-delete a lead by setting is_deleted=True.

        Args:
            lead_id: MongoDB ObjectId string

        Returns:
            True if deleted, False if not found

        Raises:
            ValueError: On invalid ObjectId format
        """
        try:
            oid = ObjectId(lead_id)
        except InvalidId:
            raise ValueError(f"'{lead_id}' is not a valid lead ID.")

        collection = get_leads_collection()
        result = collection.update_one(
            {"_id": oid, "is_deleted": False},
            {"$set": {"is_deleted": True, "deleted_at": datetime.utcnow()}},
        )
        # Audit deletion
        if result.modified_count > 0:
            try:
                collection.update_one({"_id": oid}, {"$push": {"audit_logs": {
                    "action": "delete",
                    "performed_by": deleted_by,
                    "details": "Soft-deleted lead",
                    "timestamp": datetime.utcnow(),
                }}})
            except Exception:
                logger.exception("Failed to append delete audit for lead %s", lead_id)
        return result.modified_count > 0

    # ------------------------------------------------------------------ #
    #  ASSIGN                                                              #
    # ------------------------------------------------------------------ #

    @staticmethod
    def assign_lead(
        lead_id: str,
        assigned_to: str,
        assigned_by: str,
        note: str = "",
    ) -> Optional[dict[str, Any]]:
        """
        Assign a lead to a user and record the assignment history.

        Args:
            lead_id: MongoDB ObjectId string
            assigned_to: Target user ID
            assigned_by: Requesting user ID (from JWT)
            note: Optional assignment note

        Returns:
            Updated serialized lead or None if not found

        Raises:
            ValueError: On invalid ObjectId format
        """
        try:
            oid = ObjectId(lead_id)
        except InvalidId:
            raise ValueError(f"'{lead_id}' is not a valid lead ID.")

        collection = get_leads_collection()
        lead = collection.find_one({"_id": oid, "is_deleted": False})
        if not lead:
            return None

        # Normalize assigned_to / assigned_by to ObjectId when possible
        try:
            assigned_to_val = ObjectId(assigned_to)
        except Exception:
            assigned_to_val = assigned_to

        try:
            assigned_by_val = ObjectId(assigned_by)
        except Exception:
            assigned_by_val = assigned_by

        assignment_entry = {
            "assigned_to": assigned_to_val,
            "assigned_by": assigned_by_val,
            "note": note,
            "assigned_at": datetime.utcnow(),
        }

        collection.update_one(
            {"_id": oid},
            {
                "$set": {
                    "assigned_to": assigned_to_val,
                    "updated_at": datetime.utcnow(),
                },
                "$push": {"assignment_history": assignment_entry},
            },
        )

        # Audit assignment
        try:
            audit_entry = {
                "action": "assign",
                "performed_by": assigned_by,
                "details": f"Assigned to {assigned_to}",
                "timestamp": datetime.utcnow(),
            }
            collection.update_one({"_id": oid}, {"$push": {"audit_logs": audit_entry}})
        except Exception:
            logger.exception("Failed to append assignment audit for lead %s", lead_id)

        logger.info("Lead %s assigned to %s by %s", lead_id, assigned_to, assigned_by)

        # Log to aggregated activity feed
        try:
            from app.services.activity_service import ActivityService
            ActivityService.log_activity(
                action="lead_assigned",
                performed_by=assigned_by,
                details=f"Lead assigned to {assigned_to}",
                resource_type="lead",
                resource_id=lead_id
            )
        except Exception:
            logger.exception("Failed to log activity event for lead assignment")

        updated = collection.find_one({"_id": oid})
        return serialize_lead(updated)

    # ------------------------------------------------------------------ #
    #  CONVERT                                                             #
    # ------------------------------------------------------------------ #

    @staticmethod
    def convert_lead(lead_id: str, converted_by: str) -> Optional[dict[str, Any]]:
        """
        Convert a qualified lead to a client record.

        Rules:
        - Lead must exist and not be deleted
        - Lead status must be 'qualified'
        - Creates a client document
        - Sets lead status to 'won'

        Args:
            lead_id: MongoDB ObjectId string
            converted_by: User ID performing the conversion

        Returns:
            Dict with {"lead": ..., "client": ...} or None if not found

        Raises:
            ValueError: On invalid ID or business rule violation
        """
        from app.services.client_service import ClientService

        try:
            oid = ObjectId(lead_id)
        except InvalidId:
            raise ValueError(f"'{lead_id}' is not a valid lead ID.")

        collection = get_leads_collection()
        lead = collection.find_one({"_id": oid, "is_deleted": False})

        if not lead:
            return None

        if lead.get("status") != LeadStatus.QUALIFIED:
            raise ValueError(
                f"Lead must be in 'qualified' status to convert. "
                f"Current status: '{lead.get('status')}'."
            )

        # Build client data from lead
        client_data = {
            "company_name": lead.get("company_name") or lead.get("full_name", ""),
            "contact_person": lead.get("full_name", ""),
            "email": lead.get("email", ""),
            "phone": lead.get("phone", ""),
            "industry": lead.get("industry", ""),
        }

        client = ClientService.create_client(
            data=client_data,
            created_by=converted_by,
            lead_id=lead_id,
        )

        # Link communications from lead -> client (preserve lead_id but add client_id)
        try:
            from app.database.db import get_communications_collection
            from bson import ObjectId as BsonObjectId

            comm_collection = get_communications_collection()
            client_oid = BsonObjectId(client.get("id"))
            comm_collection.update_many(
                {"lead_id": oid},
                {"$set": {"client_id": client_oid}},
            )
        except Exception:
            logger.exception("Failed to link communications from lead %s to client %s", lead_id, client.get("id"))

        # Add origin_lead metadata to client (assignment history + audits)
        try:
            from app.database.db import get_clients_collection

            clients_coll = get_clients_collection()
            origin_meta = {
                "origin_lead_id": str(lead.get("_id")),
                "assignment_history": lead.get("assignment_history", []),
                "audit_logs": lead.get("audit_logs", []),
            }
            clients_coll.update_one({"_id": BsonObjectId(client.get("id"))}, {"$set": {"origin_lead": origin_meta}})
        except Exception:
            logger.exception("Failed to attach origin_lead metadata for client %s", client.get("id"))

        # Update lead status to won
        collection.update_one(
            {"_id": oid},
            {"$set": {"status": LeadStatus.WON, "updated_at": datetime.utcnow()}},
        )

        updated_lead = collection.find_one({"_id": oid})
        logger.info(
            "Lead %s converted to client %s by %s",
            lead_id,
            client.get("id"),
            converted_by,
        )

        # Log to aggregated activity feed
        try:
            from app.services.activity_service import ActivityService
            ActivityService.log_activity(
                action="lead_converted",
                performed_by=converted_by,
                details=f"Lead converted to client {client.get('id')}",
                resource_type="lead",
                resource_id=lead_id
            )
        except Exception:
            logger.exception("Failed to log activity event for lead conversion")

        return {
            "lead": serialize_lead(updated_lead),
            "client": client,
        }

    # ------------------------------------------------------------------ #
    #  BULK OPERATIONS                                                     #
    # ------------------------------------------------------------------ #

    @staticmethod
    def bulk_assign(
        lead_ids: list[str],
        assigned_to: str,
        assigned_by: str,
        note: str = ""
    ) -> int:
        collection = get_leads_collection()
        oids = []
        for lid in lead_ids:
            try:
                oids.append(ObjectId(lid))
            except InvalidId:
                raise ValueError(f"'{lid}' is not a valid lead ID.")

        # Validate that all leads exist and are active
        existing_count = collection.count_documents({"_id": {"$in": oids}, "is_deleted": False})
        if existing_count != len(oids):
            raise ValueError("One or more lead IDs do not exist or are deleted.")

        try:
            assigned_to_val = ObjectId(assigned_to)
        except Exception:
            assigned_to_val = assigned_to

        try:
            assigned_by_val = ObjectId(assigned_by)
        except Exception:
            assigned_by_val = assigned_by

        assignment_entry = {
            "assigned_to": assigned_to_val,
            "assigned_by": assigned_by_val,
            "note": note,
            "assigned_at": datetime.utcnow()
        }

        audit_entry = {
            "action": "bulk_assign",
            "performed_by": assigned_by,
            "details": f"Bulk assigned to {assigned_to}",
            "timestamp": datetime.utcnow()
        }

        result = collection.update_many(
            {"_id": {"$in": oids}},
            {
                "$set": {
                    "assigned_to": assigned_to_val,
                    "updated_at": datetime.utcnow()
                },
                "$push": {
                    "assignment_history": assignment_entry,
                    "audit_logs": audit_entry
                }
            }
        )

        from app.services.activity_service import ActivityService
        for lid in lead_ids:
            try:
                ActivityService.log_activity(
                    action="lead_assigned",
                    performed_by=assigned_by,
                    details=f"Lead bulk assigned to {assigned_to}",
                    resource_type="lead",
                    resource_id=lid
                )
            except Exception:
                pass

        return result.modified_count

    @staticmethod
    def bulk_status(
        lead_ids: list[str],
        status: str,
        updated_by: str
    ) -> int:
        from app.validators.lead_validator import VALID_STATUSES
        if status not in VALID_STATUSES:
            raise ValueError(f"Invalid status '{status}'.")

        collection = get_leads_collection()
        oids = []
        for lid in lead_ids:
            try:
                oids.append(ObjectId(lid))
            except InvalidId:
                raise ValueError(f"'{lid}' is not a valid lead ID.")

        existing_count = collection.count_documents({"_id": {"$in": oids}, "is_deleted": False})
        if existing_count != len(oids):
            raise ValueError("One or more lead IDs do not exist or are deleted.")

        audit_entry = {
            "action": "bulk_status_update",
            "performed_by": updated_by,
            "details": f"Bulk status updated to {status}",
            "timestamp": datetime.utcnow()
        }

        result = collection.update_many(
            {"_id": {"$in": oids}},
            {
                "$set": {
                    "status": status,
                    "updated_at": datetime.utcnow()
                },
                "$push": {"audit_logs": audit_entry}
            }
        )

        from app.services.activity_service import ActivityService
        for lid in lead_ids:
            try:
                action = "lead_converted" if status == "won" else "lead_updated"
                ActivityService.log_activity(
                    action=action,
                    performed_by=updated_by,
                    details=f"Lead status bulk updated to {status}",
                    resource_type="lead",
                    resource_id=lid
                )
            except Exception:
                pass

        return result.modified_count

    @staticmethod
    def bulk_delete(
        lead_ids: list[str],
        deleted_by: str
    ) -> int:
        collection = get_leads_collection()
        oids = []
        for lid in lead_ids:
            try:
                oids.append(ObjectId(lid))
            except InvalidId:
                raise ValueError(f"'{lid}' is not a valid lead ID.")

        existing_count = collection.count_documents({"_id": {"$in": oids}, "is_deleted": False})
        if existing_count != len(oids):
            raise ValueError("One or more lead IDs do not exist or are already deleted.")

        audit_entry = {
            "action": "bulk_delete",
            "performed_by": deleted_by,
            "details": "Bulk soft-deleted lead",
            "timestamp": datetime.utcnow()
        }

        result = collection.update_many(
            {"_id": {"$in": oids}},
            {
                "$set": {
                    "is_deleted": True,
                    "deleted_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                },
                "$push": {"audit_logs": audit_entry}
            }
        )

        from app.services.activity_service import ActivityService
        for lid in lead_ids:
            try:
                ActivityService.log_activity(
                    action="lead_deleted",
                    performed_by=deleted_by,
                    details="Lead bulk soft-deleted",
                    resource_type="lead",
                    resource_id=lid
                )
            except Exception:
                pass

        return result.modified_count


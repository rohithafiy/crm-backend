"""
Portal 5 - CRM & Client Management
Search Service: Multi-target search across leads and clients

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from typing import Any, List, Tuple

from bson import ObjectId
from pymongo.errors import OperationFailure

from app.database.db import get_clients_collection, get_leads_collection
from app.models.p5_client import serialize_client
from app.models.p5_lead import serialize_lead

logger = logging.getLogger(__name__)


class SearchService:
    """Simple search façade that uses MongoDB text indexes if available
    and falls back to case-insensitive regex partial matching.
    """

    @staticmethod
    def _regex_query(fields: List[str], q: str) -> dict[str, Any]:
        regex = {"$regex": q, "$options": "i"}
        return {"$or": [{f: regex} for f in fields]}

    @staticmethod
    def _paginate_list(items: List[dict], page: int, limit: int) -> Tuple[List[dict], int]:
        total = len(items)
        start = (page - 1) * limit
        end = start + limit
        return items[start:end], total

    @staticmethod
    def search(
        q: str,
        target: str = "all",
        page: int = 1,
        limit: int = 20,
    ) -> Tuple[List[dict], int]:
        """Search across targets: leads, clients, companies, assigned_users, or all.

        Returns a flat list of result objects with a `type` key identifying the hit.
        """
        q = (q or "").strip()
        if not q:
            return [], 0

        targets = set([t.strip().lower() for t in (target or "all").split(",")])
        use_leads = "all" in targets or "leads" in targets or "companies" in targets or "assigned_users" in targets
        use_clients = "all" in targets or "clients" in targets or "companies" in targets

        results: List[dict] = []

        # Try text search first on leads
        if use_leads:
            leads_coll = get_leads_collection()
            try:
                cursor = leads_coll.find({"$text": {"$search": q}}, {"score": {"$meta": "textScore"}}).sort([("score", {"$meta": "textScore"})]).limit(100)
                leads = list(cursor)
                for l in leads:
                    results.append({"type": "lead", "result": serialize_lead(l)})
            except Exception:
                logger.debug("Text search not supported for leads or failed; falling back to regex.")
                # Fallback to regex partial matching on name/company/email
                qry = SearchService._regex_query(["full_name", "company_name", "email"], q)
                qry["is_deleted"] = False
                leads = list(get_leads_collection().find(qry).limit(100))
                for l in leads:
                    results.append({"type": "lead", "result": serialize_lead(l)})

        # Clients
        if use_clients:
            clients_coll = get_clients_collection()
            try:
                cursor = clients_coll.find({"$text": {"$search": q}}, {"score": {"$meta": "textScore"}}).sort([("score", {"$meta": "textScore"})]).limit(100)
                clients = list(cursor)
                for c in clients:
                    results.append({"type": "client", "result": serialize_client(c)})
            except Exception:
                logger.debug("Text search not supported for clients or failed; falling back to regex.")
                qry = SearchService._regex_query(["company_name", "contact_person", "email"], q)
                qry["is_deleted"] = False
                clients = list(clients_coll.find(qry).limit(100))
                for c in clients:
                    results.append({"type": "client", "result": serialize_client(c)})

        # Companies: treat as clients + leads company_name matches
        if "companies" in targets:
            seen: set[str] = set()
            # Search client company names
            try:
                clients_q = SearchService._regex_query(["company_name"], q)
                for c in get_clients_collection().find(clients_q).limit(200):
                    name = (c.get("company_name") or "").strip()
                    if not name or name.lower() in seen:
                        continue
                    seen.add(name.lower())
                    results.append({"type": "company", "result": {"company_name": name, "id": str(c.get("_id")), "source": "client"}})
            except Exception:
                logger.debug("Failed company search against clients; continuing")

            # Search lead company names
            try:
                leads_q = SearchService._regex_query(["company_name"], q)
                for l in get_leads_collection().find(leads_q).limit(200):
                    name = (l.get("company_name") or "").strip()
                    if not name or name.lower() in seen:
                        continue
                    seen.add(name.lower())
                    results.append({"type": "company", "result": {"company_name": name, "id": str(l.get("_id")), "source": "lead"}})
            except Exception:
                logger.debug("Failed company search against leads; continuing")

        # Assigned users: find leads where assigned_to matches partial q
        if "assigned_users" in targets:
            # assigned_to may be user_id string; match with regex
            qry = {"assigned_to": {"$regex": q, "$options": "i"}, "is_deleted": False}
            assigned_hits = list(get_leads_collection().find(qry).limit(200))
            for l in assigned_hits:
                results.append({"type": "lead_assigned", "result": serialize_lead(l)})

        # Simple in-memory pagination
        page = max(1, int(page))
        limit = max(1, int(limit))
        paged, total = SearchService._paginate_list(results, page, limit)
        return paged, total

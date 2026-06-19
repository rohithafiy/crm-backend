import csv
import io
from datetime import datetime, timezone

from flask import Blueprint, g, request

from app.utils import db as _db
from app.utils.api_response import api_response, success
from app.utils.permission_helper import require_permission

analytics_bp = Blueprint("analytics", __name__)


def _build_query():
    query = {}
    if g.roles and not any(r in g.roles for r in ["super_admin", "ops_lead"]):
        query["owner_id"] = g.user_id
    return query


def _count_with_scoping(collection_name):
    db = _db.get_db()
    return getattr(db, collection_name).count_documents(_build_query())


def _sum_with_scoping(collection_name, field="amount"):
    db = _db.get_db()
    pipeline = [
        {"$match": _build_query()},
        {"$group": {"_id": None, "total": {"$sum": f"${field}"}}},
    ]
    result = list(getattr(db, collection_name).aggregate(pipeline))
    return result[0]["total"] if result else 0


def _breakdown_by_status(collection_name):
    db = _db.get_db()
    pipeline = [
        {"$match": _build_query()},
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]
    return {r["_id"]: r["count"] for r in getattr(db, collection_name).aggregate(pipeline)}


@analytics_bp.route("/dashboard", methods=["GET"])
@require_permission("analytics:read")
@api_response
def dashboard():
    totals = {
        "total_leads": _count_with_scoping("leads"),
        "total_clients": _count_with_scoping("clients"),
        "total_proposals": _count_with_scoping("proposals"),
        "total_invoices": _count_with_scoping("invoices"),
        "total_payments": _count_with_scoping("payments"),
    }

    return success(data={
        "summary": {
            **totals,
            "invoice_amount_total": _sum_with_scoping("invoices"),
            "payment_amount_total": _sum_with_scoping("payments"),
        },
        "breakdowns": {
            "leads_by_status": _breakdown_by_status("leads"),
            "proposals_by_status": _breakdown_by_status("proposals"),
            "invoices_by_status": _breakdown_by_status("invoices"),
            "payments_by_status": _breakdown_by_status("payments"),
        },
    })


@analytics_bp.route("/export", methods=["GET"])
@require_permission("analytics:export")
@api_response
def export_data():
    db = _db.get_db()
    fmt = request.args.get("format", "json")
    resource = request.args.get("resource", "all")

    collections_map = {
        "leads": ("leads", ["name", "email", "phone", "status", "source"]),
        "clients": ("clients", ["name", "email", "phone", "company", "owner_id", "created_at"]),
        "proposals": ("proposals", ["title", "client_id", "amount", "status"]),
        "invoices": ("invoices", ["client_id", "amount", "status", "due_date"]),
        "payments": ("payments", ["client_id", "invoice_id", "amount", "method", "status"]),
    }

    if resource == "all":
        data = {}
        for key, (col, _) in collections_map.items():
            data[key] = list(getattr(db, col).find(_build_query()).sort("created_at", -1))
            for doc in data[key]:
                doc["_id"] = str(doc["_id"])
    elif resource in collections_map:
        col, _ = collections_map[resource]
        data = list(getattr(db, col).find(_build_query()).sort("created_at", -1))
        for doc in data:
            doc["_id"] = str(doc["_id"])
    else:
        data = []

    if fmt == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        if isinstance(data, list) and data:
            writer.writerow(data[0].keys())
            for row in data:
                writer.writerow(row.values())
        elif isinstance(data, dict):
            for col_name, docs in data.items():
                writer.writerow([f"--- {col_name} ---"])
                if docs:
                    writer.writerow(docs[0].keys())
                    for row in docs:
                        writer.writerow(row.values())
        csv_output = output.getvalue()
        output.close()

        from flask import Response
        return Response(
            csv_output,
            mimetype="text/csv",
            headers={"Content-Disposition": f"attachment; filename={resource}_export.csv"},
        )

    return success(data={
        "exported_at": datetime.now(timezone.utc).isoformat(),
        "resource": resource,
        "data": data,
    })

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
from bson.objectid import ObjectId


def _valid_token_payload(roles=None):
    return {
        "sub": "665a00000000000000000001",
        "roles": roles or ["super_admin"],
        "portals": [],
        "type": "access",
        "jti": "test-jti-001",
    }


@contextmanager
def auth_context(roles, db):
    payload = _valid_token_payload(roles)
    patchers = [
        patch("app.middleware.auth_middleware.decode_token", return_value=payload),
        patch("app.middleware.auth_middleware._is_token_blacklisted", return_value=False),
    ]
    for p in patchers:
        p.start()
    yield db
    for p in patchers:
        p.stop()


def mock_crm_collections():
    collection = MagicMock()
    collection.find.return_value.sort.return_value = []
    collection.find_one.return_value = None
    collection.insert_one.return_value = type(
        "obj", (), {"inserted_id": ObjectId("665a0000000000000000000f")}
    )()
    collection.delete_one.return_value = type("obj", (), {"deleted_count": 1})()
    collection.update_one.return_value = type("obj", (), {"matched_count": 1})()
    collection.count_documents.return_value = 5

    def aggregate_side_effect(pipeline):
        if pipeline and pipeline[-1].get("$group", {}).get("_id") is None:
            return [{"total": 1000}]
        return [{"_id": "new", "count": 3}, {"_id": "qualified", "count": 2}]

    collection.aggregate.side_effect = aggregate_side_effect

    db = MagicMock()
    db.__getitem__.return_value = collection
    db.leads = collection
    db.clients = collection
    db.proposals = collection
    db.invoices = collection
    db.payments = collection
    return db, collection


UNAUTH_ROUTES = [
    ("GET", "/leads"),
    ("POST", "/leads", {"name": "Test Lead"}),
    ("GET", "/leads/665a00000000000000000001"),
    ("PUT", "/leads/665a00000000000000000001", {"name": "Updated"}),
    ("DELETE", "/leads/665a00000000000000000001"),
    ("POST", "/leads/665a00000000000000000001/assign", {"assignee_id": "u2"}),
    ("GET", "/clients"),
    ("POST", "/clients", {"name": "Test Client"}),
    ("GET", "/clients/665a00000000000000000001"),
    ("PUT", "/clients/665a00000000000000000001", {"name": "Updated"}),
    ("DELETE", "/clients/665a00000000000000000001"),
    ("GET", "/proposals"),
    ("POST", "/proposals", {"title": "Prop", "client_id": "c1"}),
    ("GET", "/proposals/665a00000000000000000001"),
    ("PUT", "/proposals/665a00000000000000000001", {"title": "Updated"}),
    ("DELETE", "/proposals/665a00000000000000000001"),
    ("POST", "/proposals/665a00000000000000000001/approve"),
    ("GET", "/invoices"),
    ("POST", "/invoices", {"client_id": "c1", "amount": 100}),
    ("GET", "/invoices/665a00000000000000000001"),
    ("PUT", "/invoices/665a00000000000000000001", {"amount": 200}),
    ("DELETE", "/invoices/665a00000000000000000001"),
    ("POST", "/invoices/665a00000000000000000001/approve"),
    ("GET", "/payments"),
    ("POST", "/payments", {"client_id": "c1", "amount": 50}),
    ("GET", "/payments/665a00000000000000000001"),
    ("PUT", "/payments/665a00000000000000000001", {"amount": 75}),
    ("DELETE", "/payments/665a00000000000000000001"),
    ("POST", "/payments/665a00000000000000000001/refund"),
    ("GET", "/analytics/dashboard"),
    ("GET", "/analytics/export"),
]


class TestProtectedRouteAccess:
    @pytest.mark.parametrize("method,path,body", [
        (m, p, b if len(t) == 3 else None)
        for t in UNAUTH_ROUTES
        for m, p, b in [(
            t[0], t[1],
            t[2] if len(t) == 3 else None
        )]
    ])
    def test_returns_401_without_auth(self, client, method, path, body):
        if body:
            resp = client.open(path, method=method, json=body)
        else:
            resp = client.open(path, method=method)
        assert resp.status_code == 401, f"{method} {path} should return 401"


class TestLeadRoutes:
    def test_create_lead_requires_write(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["client"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/leads", json={"name": "New Lead"},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 403

    def test_create_lead_success(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["ops_lead"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/leads", json={"name": "New Lead"},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 201

    def test_delete_lead_requires_delete_perm(self, client):
        db, _ = mock_crm_collections()
        db.leads.delete_one.return_value = type("obj", (), {"deleted_count": 1})()
        with auth_context(["ops_lead"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.delete(
                "/leads/665a00000000000000000001",
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 403

    def test_delete_lead_super_admin(self, client):
        db, _ = mock_crm_collections()
        db.leads.delete_one.return_value = type("obj", (), {"deleted_count": 1})()
        with auth_context(["super_admin"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.delete(
                "/leads/665a00000000000000000001",
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 200

    def test_assign_lead_requires_assign_perm(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["project_manager"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/leads/665a00000000000000000001/assign",
                json={"assignee_id": "user123"},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 403


class TestClientRoutes:
    def test_create_client_ops_lead(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["ops_lead"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/clients", json={"name": "New Client"},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 201

    def test_create_client_project_mgr_denied(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["project_manager"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/clients", json={"name": "New Client"},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 403

    def test_delete_client_role_enforcement(self, client):
        db, _ = mock_crm_collections()
        db.clients.delete_one.return_value = type("obj", (), {"deleted_count": 1})()
        cases = [("super_admin", 200), ("ops_lead", 403), ("project_manager", 403)]
        for role, expected in cases:
            with auth_context([role], db), \
                 patch("app.utils.db.get_db", return_value=db):
                resp = client.delete(
                    "/clients/665a00000000000000000001",
                    headers={"Authorization": "Bearer token"},
                )
            assert resp.status_code == expected, f"{role} got {resp.status_code}"


class TestAnalyticsRoutes:
    def test_dashboard_client_denied(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["client"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.get(
                "/analytics/dashboard",
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 403

    def test_dashboard_project_manager_allowed(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["project_manager"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.get(
                "/analytics/dashboard",
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 200

    def test_export_enforcement(self, client):
        db, _ = mock_crm_collections()
        cases = [("super_admin", 200), ("ops_lead", 200),
                 ("project_manager", 403), ("client", 403)]
        for role, expected in cases:
            with auth_context([role], db), \
                 patch("app.utils.db.get_db", return_value=db):
                resp = client.get(
                    "/analytics/export",
                    headers={"Authorization": "Bearer token"},
                )
            assert resp.status_code == expected, f"{role}: expected {expected}"


class TestProposalRoutes:
    def test_create_proposal_project_manager(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["project_manager"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/proposals", json={"title": "Prop", "client_id": "c1"},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 201

    def test_create_proposal_client_denied(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["client"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/proposals", json={"title": "Prop", "client_id": "c1"},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 403


class TestPaymentRoutes:
    def test_record_payment_ops_lead(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["ops_lead"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/payments", json={"client_id": "c1", "amount": 100},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 201

    def test_record_payment_project_mgr_denied(self, client):
        db, _ = mock_crm_collections()
        with auth_context(["project_manager"], db), \
             patch("app.utils.db.get_db", return_value=db):
            resp = client.post(
                "/payments", json={"client_id": "c1", "amount": 100},
                headers={"Authorization": "Bearer token"},
            )
        assert resp.status_code == 403

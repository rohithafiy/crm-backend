from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import pytest
from bson.objectid import ObjectId


def mock_db():
    sessions = []
    blacklist = []
    users = []

    def find_one(q, projection=None):
        col_map = [("token_blacklist", blacklist), ("sessions", sessions), ("users", users)]
        for col_name, store in col_map:
            qq = {k: v for k, v in q.items() if k != "_collection"}
            for item in store:
                if all(item.get(k) == v for k, v in qq.items()):
                    if projection and "password_hash" in projection:
                        item.pop("password_hash", None)
                    return item
        return None

    def find(q, projection=None):
        results = [
            u for u in users
            if all(u.get(k) == v for k, v in q.items() if k != "_collection")
        ]
        cursor = MagicMock()
        cursor.sort.return_value = results
        cursor.__iter__.return_value = iter(results)
        return cursor

    collection = MagicMock()
    collection.find_one.side_effect = find_one
    collection.find.side_effect = find

    def insert_one(d):
        if "password_hash" in d:
            users.append(d)
        elif "access_jti" in d:
            sessions.append(d)
        elif "jti" in d:
            blacklist.append(d)
        return type("obj", (), {"inserted_id": ObjectId("665a1b2c3d4e5f6a7b8c9d0e")})()

    collection.insert_one.side_effect = insert_one

    def update_one(q, upd):
        qq = {k: v for k, v in q.items() if k != "_collection"}
        if "email" in qq:
            for u in users:
                if u.get("email") == qq["email"]:
                    u.update(upd.get("$set", {}))
        if "_id" in qq:
            for s in sessions:
                if str(s.get("_id", "")) == str(qq["_id"]):
                    s.update(upd.get("$set", {}))

    collection.update_one.side_effect = update_one

    def update_many(q, upd):
        qq = {k: v for k, v in q.items() if k != "_collection"}
        for s in sessions:
            if all(s.get(k) == v for k, v in qq.items()):
                s.update(upd.get("$set", {}))

    collection.update_many.side_effect = update_many

    db = MagicMock()
    db.__getitem__.return_value = collection
    db.users = collection
    db.sessions = collection
    db.token_blacklist = collection
    return db


TOKEN_PLACEHOLDER = "eyJhbGciOiJIUzI1NiJ9.test"


@pytest.fixture(autouse=True)
def patch_create_tokens():
    patchers = [
        patch("app.services.auth_service.create_access_token",
              return_value=(TOKEN_PLACEHOLDER, "jti-access")),
        patch("app.services.auth_service.create_refresh_token",
              return_value=(TOKEN_PLACEHOLDER, "jti-refresh")),
    ]
    with ExitStack() as stack:
        for p in patchers:
            stack.enter_context(p)
        yield


def _mock_access_payload(**overrides):
    payload = {
        "sub": "665a1b2c3d4e5f6a7b8c9d0e",
        "roles": ["agent"],
        "portals": [],
        "type": "access",
        "jti": "jti-valid",
    }
    payload.update(overrides)
    return payload


class TestAuthRegister:
    @patch("app.utils.db.get_db")
    def test_register_success(self, mock_get_db, client):
        mock_get_db.return_value = mock_db()
        resp = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123",
        })
        assert resp.status_code == 201
        body = resp.get_json()
        assert body["status"] == "success"
        assert "access_token" in body["data"]
        assert "refresh_token" in body["data"]
        assert body["message"] == "User registered successfully"

    def test_register_missing_fields(self, client):
        resp = client.post("/auth/register", json={})
        assert resp.status_code == 400

    @patch("app.utils.db.get_db")
    def test_register_invalid_role(self, mock_get_db, client):
        mock_get_db.return_value = mock_db()
        resp = client.post("/auth/register", json={
            "email": "test@example.com",
            "password": "SecurePass123",
            "roles": ["superadmin"],
        })
        assert resp.status_code == 400


class TestAuthLogin:
    @patch("app.utils.db.get_db")
    def test_login_success(self, mock_get_db, client):
        mdb = mock_db()
        mdb.users.insert_one({
            "_id": ObjectId("665a1b2c3d4e5f6a7b8c9d0e"),
            "email": "login@example.com",
            "password_hash": "$2b$12$dummyhash",
            "roles": ["agent"],
            "portals": [],
            "is_active": True,
        })
        mock_get_db.return_value = mdb
        with patch("bcrypt.checkpw", return_value=True):
            resp = client.post("/auth/login", json={
                "email": "login@example.com",
                "password": "SecurePass123",
            })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "success"
        assert "access_token" in body["data"]

    @patch("app.utils.db.get_db")
    def test_login_wrong_password(self, mock_get_db, client):
        mock_get_db.return_value = mock_db()
        with patch("bcrypt.checkpw", return_value=False):
            resp = client.post("/auth/login", json={
                "email": "nonexistent@example.com",
                "password": "wrong",
            })
        assert resp.status_code == 401

    def test_login_missing_fields(self, client):
        resp = client.post("/auth/login", json={})
        assert resp.status_code == 400


class TestAuthRefresh:
    @patch("app.utils.db.get_db")
    def test_refresh_success(self, mock_get_db, client):
        mdb = mock_db()
        mdb.users.insert_one({
            "_id": ObjectId("665a1b2c3d4e5f6a7b8c9d0e"),
            "email": "test@example.com",
            "password_hash": "$2b$12$hash",
            "roles": ["admin"],
            "is_active": True,
        })
        mock_get_db.return_value = mdb
        mock_payload = _mock_access_payload(type="refresh", jti="jti-refresh-ok")
        with patch("app.services.auth_service.decode_token", return_value=mock_payload):
            resp = client.post("/auth/refresh", json={
                "refresh_token": "valid-refresh-token",
            })
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["status"] == "success"
        assert "access_token" in body["data"]

    @patch("app.utils.db.get_db")
    def test_refresh_with_revoked_token(self, mock_get_db, client):
        mdb = mock_db()
        mdb.token_blacklist.insert_one({"jti": "jti-revoked"})
        mock_get_db.return_value = mdb
        mock_payload = _mock_access_payload(type="refresh", jti="jti-revoked")
        with patch("app.services.auth_service.decode_token", return_value=mock_payload):
            resp = client.post("/auth/refresh", json={
                "refresh_token": "revoked-refresh-token",
            })
        assert resp.status_code == 401


class TestAuthLogout:
    @patch("app.middleware.auth_middleware._is_token_blacklisted")
    @patch("app.middleware.auth_middleware.decode_token")
    def test_logout_success(self, mock_decode, mock_blacklisted, client):
        mock_blacklisted.return_value = False
        mock_decode.return_value = _mock_access_payload(jti="jti-logout")
        resp = client.post(
            "/auth/logout",
            headers={"Authorization": "Bearer valid-token"},
        )
        assert resp.status_code == 200
        assert resp.get_json()["message"] == "Logged out successfully"


class TestAuthMe:
    def test_me_unauthenticated(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_me_with_invalid_token(self, client):
        with patch("app.middleware.auth_middleware.decode_token", return_value=None):
            resp = client.get(
                "/auth/me",
                headers={"Authorization": "Bearer invalidtoken"},
            )
        assert resp.status_code == 401


class TestAuthVerify:
    def test_verify_unauthenticated(self, client):
        resp = client.get("/auth/verify")
        assert resp.status_code == 401


class TestMiddlewareSecurity:
    def test_protected_route_no_token(self, client):
        resp = client.get("/auth/me")
        assert resp.status_code == 401

    def test_public_route_no_token(self, client):
        resp = client.get("/health")
        assert resp.status_code == 200

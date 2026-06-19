import pytest

from app import create_app


@pytest.fixture
def app():
    application = create_app()
    application.config.update({
        "TESTING": True,
    })
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def auth_headers(app, client):
    # This fixture expects a user to exist; tests that need it
    # should create the user first or mock the DB call.
    return {}

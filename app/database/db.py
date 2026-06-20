"""
Portal 5 - CRM & Client Management
Database Module: MongoDB Atlas Connection with Index Management

Author: P5-A2 (CRM Backend Engineer)
"""

import logging
from functools import lru_cache
from typing import Optional

from pymongo import MongoClient, ASCENDING, DESCENDING, TEXT
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError, OperationFailure

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    Singleton MongoDB Atlas connection manager.
    Manages connection pooling, index creation, and collection access.
    """

    _instance: Optional["DatabaseManager"] = None
    _client: Optional[MongoClient] = None
    _db: Optional[Database] = None

    def __new__(cls) -> "DatabaseManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def init_app(self, app) -> None:
        """
        Initialize database with Flask app context.

        Args:
            app: Flask application instance
        """
        mongo_uri = app.config.get("MONGO_URI")
        db_name = app.config.get("MONGO_DB_NAME", "lti_hub")

        if not mongo_uri:
            raise ValueError("MONGO_URI is not configured in the Flask app.")

        # Clean fallback for development: start mock mode directly if requested
        if mongo_uri.lower() == "mock":
            logger.info("Initializing in-memory mongomock database: %s", db_name)
            try:
                import mongomock
                self._client = mongomock.MongoClient()
                self._db = self._client[db_name]
                self._create_indexes()
                return
            except ImportError as exc:
                logger.critical("mongomock package not installed. Cannot start mock mode.")
                raise exc

        try:
            self._client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=2000,
                connectTimeoutMS=2000,
                socketTimeoutMS=45000,
                maxPoolSize=50,
                minPoolSize=5,
                retryWrites=True,
                w="majority",
            )
            # Validate connection
            self._client.admin.command("ping")
            self._db = self._client[db_name]

            logger.info("MongoDB Atlas connected successfully to database: %s", db_name)
            self._create_indexes()

        except (ConnectionFailure, ServerSelectionTimeoutError, OperationFailure) as exc:
            logger.warning("MongoDB connection failed: %s. Falling back to in-memory mongomock database...", str(exc))
            if self._client:
                try:
                    self._client.close()
                except Exception:
                    pass
                self._client = None
            try:
                import mongomock
                self._client = mongomock.MongoClient()
                self._db = self._client[db_name]
                logger.info("Using in-memory mongomock database: %s", db_name)
                self._create_indexes()
            except ImportError:
                logger.critical("mongomock package not installed. Cannot fallback. Failing database initialization.")
                raise exc

    def _create_indexes(self) -> None:
        """Create all required indexes for Portal 5 collections."""
        self._create_leads_indexes()
        self._create_clients_indexes()
        self._create_communications_indexes()
        logger.info("All Portal 5 MongoDB indexes created/verified.")

    def _create_leads_indexes(self) -> None:
        """Create indexes for p5_leads collection."""
        leads = self._db["p5_leads"]

        # Unique email index (sparse to allow null)
        leads.create_index(
            [("email", ASCENDING)],
            unique=True,
            sparse=True,
            name="idx_leads_email_unique",
        )
        # Simple email index
        leads.create_index([("email", ASCENDING)], name="idx_leads_email")
        # Company name index
        leads.create_index([("company_name", ASCENDING)], name="idx_leads_company_name")
        # Status index
        leads.create_index([("status", ASCENDING)], name="idx_leads_status")
        # Assigned to index
        leads.create_index([("assigned_to", ASCENDING)], name="idx_leads_assigned_to")
        # Follow up date index
        leads.create_index([("follow_up_date", ASCENDING)], name="idx_leads_follow_up_date")
        # Created_at for sorting
        leads.create_index([("created_at", DESCENDING)], name="idx_leads_created_at")

        # Status + assigned_to compound index for pipeline queries
        leads.create_index(
            [("status", ASCENDING), ("assigned_to", ASCENDING)],
            name="idx_leads_status_assigned",
        )
        # Source index for filtering
        leads.create_index([("source", ASCENDING)], name="idx_leads_source")
        # Soft delete filter
        leads.create_index([("is_deleted", ASCENDING)], name="idx_leads_is_deleted")
        # Portal1 request reference
        leads.create_index(
            [("portal1_request_id", ASCENDING)],
            sparse=True,
            name="idx_leads_portal1_ref",
        )
        # Full-text search index
        leads.create_index(
            [("full_name", TEXT), ("company_name", TEXT), ("email", TEXT)],
            name="idx_leads_text_search",
        )
        # Normalized phone index to help prevent duplicates (sparse)
        leads.create_index(
            [("phone_normalized", ASCENDING)],
            unique=True,
            sparse=True,
            name="idx_leads_phone_normalized",
        )
        logger.debug("p5_leads indexes created.")

    def _create_clients_indexes(self) -> None:
        """Create indexes for p5_clients collection."""
        clients = self._db["p5_clients"]

        # Email unique index (sparse)
        clients.create_index(
            [("email", ASCENDING)],
            unique=True,
            sparse=True,
            name="idx_clients_email_unique",
        )
        # Simple email index
        clients.create_index([("email", ASCENDING)], name="idx_clients_email")
        # Company name index
        clients.create_index([("company_name", ASCENDING)], name="idx_clients_company_name")
        # Status index
        clients.create_index([("status", ASCENDING)], name="idx_clients_status")
        # Assigned to index (supports assigned_to and user_id)
        clients.create_index([("assigned_to", ASCENDING)], sparse=True, name="idx_clients_assigned_to")
        clients.create_index([("user_id", ASCENDING)], sparse=True, name="idx_clients_user_id")
        # Follow up date index
        clients.create_index([("follow_up_date", ASCENDING)], sparse=True, name="idx_clients_follow_up_date")
        # Created at index
        clients.create_index([("created_at", DESCENDING)], name="idx_clients_created_at")

        # Lead reference
        clients.create_index(
            [("lead_id", ASCENDING)], sparse=True, name="idx_clients_lead_id"
        )
        # Industry filter
        clients.create_index([("industry", ASCENDING)], name="idx_clients_industry")
        # Soft delete
        clients.create_index([("is_deleted", ASCENDING)], name="idx_clients_is_deleted")
        # Full-text search
        clients.create_index(
            [("company_name", TEXT), ("contact_person", TEXT), ("email", TEXT)],
            name="idx_clients_text_search",
        )
        # Normalized phone index for clients
        clients.create_index(
            [("phone_normalized", ASCENDING)],
            unique=True,
            sparse=True,
            name="idx_clients_phone_normalized",
        )
        logger.debug("p5_clients indexes created.")


    def _create_communications_indexes(self) -> None:
        """Create indexes for p5_communications collection."""
        comms = self._db["p5_communications"]

        # Client reference + created_at for timeline
        comms.create_index(
            [("client_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_comms_client_timeline",
        )
        # Lead reference + created_at for timeline
        comms.create_index(
            [("lead_id", ASCENDING), ("created_at", DESCENDING)],
            name="idx_comms_lead_timeline",
        )
        # Type filter
        comms.create_index([("communication_type", ASCENDING)], name="idx_comms_communication_type")
        # Created_by
        comms.create_index([("created_by", ASCENDING)], name="idx_comms_created_by")
        logger.debug("p5_communications indexes created.")
        # Activity logs index (ensure efficient recent feed fetch)
        try:
            self._db["p5_activity_logs"].create_index([("timestamp", DESCENDING)], name="idx_activity_ts")
        except Exception:
            logger.exception("Failed to create p5_activity_logs index")
    @property
    def db(self) -> Database:
        """Return the active database instance."""
        if self._db is None:
            raise RuntimeError("Database not initialized. Call init_app() first.")
        return self._db

    def get_collection(self, name: str) -> Collection:
        """
        Return a MongoDB collection by name.

        Args:
            name: Collection name

        Returns:
            PyMongo Collection instance
        """
        return self.db[name]

    def close(self) -> None:
        """Close the MongoDB connection."""
        if self._client:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed.")


# Module-level singleton
db_manager = DatabaseManager()


def get_db() -> Database:
    """Convenience function to get the active database."""
    return db_manager.db


def get_leads_collection() -> Collection:
    """Return p5_leads collection."""
    return db_manager.get_collection("p5_leads")


def get_clients_collection() -> Collection:
    """Return p5_clients collection."""
    return db_manager.get_collection("p5_clients")


def get_communications_collection() -> Collection:
    """Return p5_communications collection."""
    return db_manager.get_collection("p5_communications")

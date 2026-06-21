from pymongo import MongoClient

from app.configs.env_config import EnvConfig

_client = None


def get_db():
    global _client
    if _client is None:
        _client = MongoClient(
            EnvConfig.MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=False,
            retryWrites=True,
            w="majority",
            maxPoolSize=50,
            connectTimeoutMS=5000,
            serverSelectionTimeoutMS=5000,
        )
    return _client[EnvConfig.MONGO_DB_NAME]

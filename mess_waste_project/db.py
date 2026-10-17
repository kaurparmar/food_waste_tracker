"""Database connection helper (PyMongo).

Every other module calls get_db() so the connection is created only once.
"""
from pymongo import MongoClient

MONGO_URI = "mongodb://localhost:27017/"
DB_NAME = "mess_waste_db"
_client = None


def get_client():
    """Return one shared MongoClient (created on first use)."""
    global _client
    if _client is None:
        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
    return _client


def get_db():
    """Return the mess_waste_db database object."""
    return get_client()[DB_NAME]

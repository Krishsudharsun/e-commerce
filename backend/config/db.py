from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME   = os.getenv("DB_NAME",   "ecommerce")

client = None
db     = None


def connect_db():
    global client, db
    try:
        client = MongoClient(
            MONGO_URI,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=5,
        )
        client.admin.command("ping")
        db = client[DB_NAME]
        print(f"✅ Connected to MongoDB: {DB_NAME}")
        return db
    except ConnectionFailure as e:
        print(f"❌ MongoDB connection failed: {e}")
        raise


def get_db():
    global db
    if db is None:
        connect_db()
    return db


def close_db():
    global client, db
    if client:
        client.close()
        client = None
        db     = None
        print("🔌 MongoDB connection closed.")

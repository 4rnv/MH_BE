"""
Database configuration and connection
"""
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.server_api import ServerApi
from dotenv import load_dotenv
import os
load_dotenv()
# MongoDB Atlas connection
MONGODB_URI = os.getenv("MONGO_URL")
print(MONGODB_URI)
# Create synchronous PyMongo client
client = MongoClient(MONGODB_URI, server_api=ServerApi('1'))
db = client["safebalance_db"]

# Collections
users_collection = db["users"]
questionnaires_collection = db["questionnaires"]
virtual_accounts_collection = db["virtual_accounts"]
transactions_collection = db["transactions"]
scheduled_payments_collection = db["scheduled_payments"]
insights_collection = db["insights"]

# Create indexes for better query performance
def create_indexes():
    """Create database indexes"""
    users_collection.create_index([("phone", ASCENDING)], unique=True)
    users_collection.create_index([("aadhaar", ASCENDING)], unique=True)
    virtual_accounts_collection.create_index([("user_id", ASCENDING)])
    transactions_collection.create_index([("acct_id", ASCENDING)])
    transactions_collection.create_index([("datetime", DESCENDING)])
    scheduled_payments_collection.create_index([("user_id", ASCENDING)])
    questionnaires_collection.create_index([("user_id", ASCENDING)])
    insights_collection.create_index([("user_id", ASCENDING)])
    insights_collection.create_index([("created_at", DESCENDING)])
    insights_collection.create_index([("read", ASCENDING)])
    print("Database indexes created")

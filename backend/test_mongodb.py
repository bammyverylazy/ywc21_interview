import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "yasafe")

client = MongoClient(
    MONGODB_URI,
    serverSelectionTimeoutMS=5000
)

try:
    client.admin.command("ping")
    print("MongoDB connected successfully!")

    db = client[DATABASE_NAME]
    print("Database:", db.name)

except Exception as error:
    print("MongoDB connection failed:", error)

finally:
    client.close()
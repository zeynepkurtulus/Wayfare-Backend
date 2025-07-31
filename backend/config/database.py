
#MongoDB Driver
import motor.motor_asyncio
import asyncio
import os
from dotenv import load_dotenv

#connection between the database.py and MongoDB
# Note: Using only motor.motor_asyncio for async operations
# Removed pymongo.MongoClient to avoid sync/async conflicts

# Load environment variables
load_dotenv()

# Get database credentials from environment variables
MONGO_USERNAME = os.getenv("MONGO_USERNAME", "default_username")
MONGO_PASSWORD = os.getenv("MONGO_PASSWORD", "default_password") 
MONGO_CLUSTER = os.getenv("MONGO_CLUSTER", "defaultcluster.zkvwswc.mongodb.net")
MONGO_DATABASE = os.getenv("MONGO_DATABASE", "Wayfare")

# Build MongoDB URL from environment variables
MONGO_URL = f"mongodb+srv://{MONGO_USERNAME}:{MONGO_PASSWORD}@{MONGO_CLUSTER}/"
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)

database = client["Wayfare"]
user_collection = database["user"]
route_collection = database["route"]
places_collection = database["places"]
cities_collection = database["cities"]
countries_collection = database["countries"]
place_feedback_collection = database["place_feedback"]
route_feedback_collection = database["route_feedback"]